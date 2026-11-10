package plgkit

import (
	"crypto/rand"
	"database/sql"
	"embed"
	"encoding/hex"
	"fmt"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"

	_ "github.com/jackc/pgx/v5/stdlib"
	_ "modernc.org/sqlite"
)

//go:embed migrations/*.sql
var migrationFS embed.FS

const (
	DefaultDatabaseURLEnv = "PLGKIT_DATABASE_URL"
	DefaultDatabaseURL    = "sqlite:///plgkit_events.sqlite"
)

var (
	envNamePattern = regexp.MustCompile(`^[A-Za-z_][A-Za-z0-9_]*$`)
	migrationName  = regexp.MustCompile(`^(\d+)_.+\.sql$`)
	mu             sync.Mutex
	warnMu         sync.Mutex
	defaultDB      *sql.DB
	warnedDefault  bool
	dialects       sync.Map
)

type Error struct{ Msg string }

func (e *Error) Error() string { return e.Msg }

func fail(msg string) error { return &Error{Msg: msg} }

func ResolveDatabaseURL(configPath string, environ map[string]string) (string, bool, error) {
	name, err := envVarName(configPath)
	if err != nil {
		return "", false, err
	}
	var value string
	if environ == nil {
		value = os.Getenv(name)
	} else {
		value = environ[name]
	}
	value = strings.TrimSpace(value)
	if value == "" {
		return DefaultDatabaseURL, true, nil
	}
	scheme := schemeOf(value)
	if scheme == "sqlite" || scheme == "postgres" || scheme == "postgresql" {
		return value, false, nil
	}
	return "", false, fail(fmt.Sprintf(
		"%s uses the %q scheme. plgkit-personas supports SQLite (sqlite:///plgkit_events.sqlite) and Postgres (postgres:// or postgresql://). Unset the variable to use the local SQLite file.",
		name, scheme,
	))
}

func Connect(url string) (*sql.DB, error) {
	if url == "" {
		resolved, usedDefault, err := ResolveDatabaseURL("", nil)
		if err != nil {
			return nil, err
		}
		if usedDefault {
			warnDefault(envVarNameOrDefault(""))
		}
		url = resolved
	}
	switch schemeOf(url) {
	case "sqlite":
		return openSQLite(url)
	case "postgres", "postgresql":
		return openPostgres(url)
	default:
		return nil, fail(fmt.Sprintf(
			"Unsupported database scheme %q. Use a SQLite URL or a Postgres URL (postgres:// or postgresql://).",
			schemeOf(url),
		))
	}
}

func Migrate(db *sql.DB) error {
	mu.Lock()
	defer mu.Unlock()
	if db == nil {
		var err error
		db, err = openDefaultLocked()
		if err != nil {
			return err
		}
	}
	return migrateLocked(db)
}

func SetDefault(db *sql.DB) {
	mu.Lock()
	defer mu.Unlock()
	defaultDB = db
}

func openDefaultLocked() (*sql.DB, error) {
	if defaultDB != nil {
		return defaultDB, nil
	}
	db, err := Connect("")
	if err != nil {
		return nil, err
	}
	defaultDB = db
	return db, nil
}

func migrateLocked(db *sql.DB) error {
	if _, err := dbExec(db, "CREATE TABLE IF NOT EXISTS plgkit_persona_schema_migrations (version TEXT PRIMARY KEY)"); err != nil {
		return fail("Migration setup failed.")
	}
	rows, err := dbQuery(db, "SELECT version FROM plgkit_persona_schema_migrations")
	if err != nil {
		return fail("Migration setup failed.")
	}
	applied := map[string]bool{}
	for rows.Next() {
		var version string
		if err := rows.Scan(&version); err != nil {
			rows.Close()
			return fail("Migration setup failed.")
		}
		applied[version] = true
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return fail("Migration setup failed.")
	}
	rows.Close()
	sources, err := migrationsFromEmbed()
	if err != nil {
		return err
	}
	for _, source := range sources {
		if applied[source.version] {
			continue
		}
		tx, err := db.Begin()
		if err != nil {
			return fail("Migration " + source.version + " failed.")
		}
		failed := false
		for _, statement := range sqlStatements(source.sql) {
			if _, err := tx.Exec(rewriteQuery(db, statement)); err != nil {
				failed = true
				break
			}
		}
		if !failed {
			if _, err := tx.Exec(rewriteQuery(db, "INSERT INTO plgkit_persona_schema_migrations (version) VALUES (?)"), source.version); err != nil {
				failed = true
			}
		}
		if failed {
			_ = tx.Rollback()
			return fail("Migration " + source.version + " failed.")
		}
		if err := tx.Commit(); err != nil {
			return fail("Migration " + source.version + " failed.")
		}
	}
	return nil
}

func insertEvent(db *sql.DB, userID, action string, eventID *string, metadata []byte, occurredAt, receivedAt string) (bool, error) {
	var eventArg any
	if eventID != nil {
		eventArg = *eventID
	}
	_, err := dbExec(
		db,
		"INSERT INTO plgkit_persona_events (id, user_id, action, event_id, metadata, occurred_at, received_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
		newID(), userID, action, eventArg, string(metadata), occurredAt, receivedAt,
	)
	if err == nil {
		return true, nil
	}
	if isUnique(err) {
		return false, nil
	}
	return false, err
}

func listEvents(db *sql.DB, userID string) ([]map[string]any, error) {
	rows, err := dbQuery(
		db,
		"SELECT action, occurred_at FROM plgkit_persona_events WHERE user_id = ? ORDER BY occurred_at ASC, id ASC",
		userID,
	)
	if err != nil {
		return nil, fail("Could not read persona events. Run plgkit-personas migrate.")
	}
	defer rows.Close()
	events := []map[string]any{}
	for rows.Next() {
		var action, occurredAt string
		if err := rows.Scan(&action, &occurredAt); err != nil {
			return nil, fail("Could not read persona events. Run plgkit-personas migrate.")
		}
		events = append(events, map[string]any{"action": action, "occurred_at": occurredAt})
	}
	if err := rows.Err(); err != nil {
		return nil, fail("Could not read persona events. Run plgkit-personas migrate.")
	}
	return events, nil
}

func openSQLite(url string) (*sql.DB, error) {
	file, err := sqlitePath(url)
	if err != nil {
		return nil, err
	}
	db, err := sql.Open("sqlite", file)
	if err != nil {
		return nil, fail("Could not open the database.")
	}
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)
	if _, err := db.Exec("PRAGMA busy_timeout = 5000"); err != nil {
		_ = db.Close()
		return nil, fail("Could not open the database.")
	}
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, fail("Could not open the database.")
	}
	dialects.Store(db, "sqlite")
	return db, nil
}

func openPostgres(url string) (*sql.DB, error) {
	db, err := sql.Open("pgx", url)
	if err != nil {
		return nil, fail("Could not open the database.")
	}
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, fail("Could not open the database.")
	}
	dialects.Store(db, "postgres")
	return db, nil
}

type migrationSource struct {
	version string
	sql     string
}

func migrationsFromEmbed() ([]migrationSource, error) {
	entries, err := migrationFS.ReadDir("migrations")
	if err != nil {
		return nil, fail("The plgkit package is missing its migration files. Rebuild the package.")
	}
	var found []migrationSource
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		match := migrationName.FindStringSubmatch(entry.Name())
		if match == nil {
			continue
		}
		text, err := migrationFS.ReadFile("migrations/" + entry.Name())
		if err != nil {
			return nil, fail("Could not read migration " + match[1] + ".")
		}
		found = append(found, migrationSource{version: match[1], sql: string(text)})
	}
	sort.Slice(found, func(i, j int) bool {
		a, _ := strconv.Atoi(found[i].version)
		b, _ := strconv.Atoi(found[j].version)
		return a < b
	})
	if len(found) == 0 {
		return nil, fail("The plgkit package is missing its migration files. Rebuild the package.")
	}
	return found, nil
}

func dbExec(db *sql.DB, query string, args ...any) (sql.Result, error) {
	return db.Exec(rewriteQuery(db, query), args...)
}

func dbQuery(db *sql.DB, query string, args ...any) (*sql.Rows, error) {
	return db.Query(rewriteQuery(db, query), args...)
}

func rewriteQuery(db *sql.DB, query string) string {
	kind, _ := dialects.Load(db)
	if kind != "postgres" {
		return query
	}
	var b strings.Builder
	n := 0
	for _, r := range query {
		if r == '?' {
			n++
			b.WriteByte('$')
			b.WriteString(strconv.Itoa(n))
			continue
		}
		b.WriteRune(r)
	}
	return b.String()
}

func schemeOf(url string) string {
	if strings.HasPrefix(strings.ToLower(url), "sqlite:") {
		return "sqlite"
	}
	if i := strings.Index(url, "://"); i >= 0 {
		return strings.ToLower(url[:i])
	}
	return "unknown"
}

func sqlitePath(url string) (string, error) {
	if url == "sqlite:///:memory:" || url == "sqlite::memory:" {
		return ":memory:", nil
	}
	const prefix = "sqlite:///"
	if !strings.HasPrefix(url, prefix) {
		return "", fail("The SQLite URL must look like sqlite:///plgkit_events.sqlite or sqlite:///:memory:.")
	}
	return url[len(prefix):], nil
}

func sqlStatements(text string) []string {
	var lines []string
	for _, line := range strings.Split(text, "\n") {
		if i := strings.Index(line, "--"); i >= 0 {
			line = line[:i]
		}
		lines = append(lines, line)
	}
	var found []string
	for _, part := range strings.Split(strings.Join(lines, "\n"), ";") {
		part = strings.TrimSpace(part)
		if part != "" {
			found = append(found, part)
		}
	}
	return found
}

func envVarName(configPath string) (string, error) {
	path := configPath
	if path == "" {
		path = defaultConfigPath()
	}
	if path == "" {
		return DefaultDatabaseURLEnv, nil
	}
	raw, err := readFlat(path)
	if err != nil {
		return "", err
	}
	name := raw["database_url_env"]
	if name == "" {
		name = DefaultDatabaseURLEnv
	}
	if !envNamePattern.MatchString(name) {
		return "", fail("database_url_env in config.yml must be the name of an environment variable, not the database address. The address can contain a password, so put it in the environment. Example: database_url_env: PLGKIT_DATABASE_URL")
	}
	return name, nil
}

func envVarNameOrDefault(configPath string) string {
	name, err := envVarName(configPath)
	if err != nil || name == "" {
		return DefaultDatabaseURLEnv
	}
	return name
}

func isUnique(err error) bool {
	return strings.Contains(strings.ToLower(err.Error()), "unique")
}

func newID() string {
	buf := make([]byte, 16)
	if _, err := rand.Read(buf); err != nil {
		return strconv.Itoa(os.Getpid())
	}
	return hex.EncodeToString(buf)
}

func warnDefault(name string) {
	warnMu.Lock()
	defer warnMu.Unlock()
	if warnedDefault {
		return
	}
	warnedDefault = true
	fmt.Fprintf(os.Stderr, "%s is unset. Using a SQLite file at plgkit_events.sqlite in the current directory.\n", name)
}
