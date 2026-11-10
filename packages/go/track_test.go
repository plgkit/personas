package plgkit

import (
	"database/sql"
	"os"
	"path/filepath"
	"testing"
)

func TestRoundTrip(t *testing.T) {
	fixture := loadFixture(t)
	for _, item := range fixture.Cases {
		db := memoryDB(t)
		for _, event := range item.Events {
			action, _ := event["action"].(string)
			occurred, _ := event["occurred_at"].(string)
			stored, err := Track(item.UserID, action, map[string]any{"occurred_at": occurred}, db, item.CalculatedAt)
			if err != nil || !stored {
				t.Fatalf("%s track %v %v", item.Name, stored, err)
			}
		}
		if len(item.Traits) > 0 {
			if err := Identify(item.UserID, item.Traits, db, item.CalculatedAt); err != nil {
				t.Fatal(item.Name, err)
			}
		}
		before, err := Persona(item.UserID, db)
		if err != nil || before.Persona != "" {
			t.Fatalf("%s before calculate %#v %v", item.Name, before, err)
		}
		raw := fixture.Rules
		if len(item.Rules) > 0 && string(item.Rules) != "null" {
			raw = item.Rules
		}
		rules, err := rulesFromRaw(raw)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := Calculate(db, item.CalculatedAt, item.UserID, &rules); err != nil {
			t.Fatal(item.Name, err)
		}
		result, err := Persona(item.UserID, db)
		if err != nil {
			t.Fatal(item.Name, err)
		}
		if result.Persona != item.Persona || stringsJoin(result.Matched) != stringsJoin(item.Matched) || !sameReasons(result.Reasons, item.Reasons) {
			t.Fatalf("%s got %s %#v %#v", item.Name, result.Persona, result.Matched, result.Reasons)
		}
		ok, err := PersonaIs(item.UserID, "missing", db)
		if err != nil || ok {
			t.Fatalf("%s persona_is missing %v %v", item.Name, ok, err)
		}
		if item.Persona != "" {
			ok, err = PersonaIs(item.UserID, item.Persona, db)
			if err != nil || !ok {
				t.Fatalf("%s persona_is %v %v", item.Name, ok, err)
			}
		}
	}
}

func TestIdentifyKeepsLatest(t *testing.T) {
	fixture := loadFixture(t)
	rules, err := rulesFromRaw(fixture.Rules)
	if err != nil {
		t.Fatal(err)
	}
	db := memoryDB(t)
	now := "2026-11-10T15:00:00Z"
	if err := Identify("ada", map[string]string{"role": "member"}, db, now); err != nil {
		t.Fatal(err)
	}
	if err := Identify("ada", map[string]string{"role": "billing_admin"}, db, now); err != nil {
		t.Fatal(err)
	}
	if _, err := Calculate(db, now, "", &rules); err != nil {
		t.Fatal(err)
	}
	result, err := Persona("ada", db)
	if err != nil || result.Persona != "billing_admin" {
		t.Fatalf("%#v %v", result, err)
	}
}

func TestDuplicateEventID(t *testing.T) {
	db := memoryDB(t)
	now := "2026-11-10T15:00:00Z"
	stored, err := Track("jordan", "created_doc", map[string]any{
		"occurred_at": "2026-11-09T15:00:00Z",
		"event_id":    "once",
		"page":        "home",
	}, db, now)
	if err != nil || !stored {
		t.Fatal(stored, err)
	}
	stored, err = Track("jordan", "edited_doc", map[string]any{
		"occurred_at": "2026-11-09T16:00:00Z",
		"event_id":    "once",
		"page":        "away",
	}, db, now)
	if err != nil || stored {
		t.Fatal(stored, err)
	}
	var metadata string
	if err := db.QueryRow("SELECT metadata FROM plgkit_persona_events WHERE user_id = ?", "jordan").Scan(&metadata); err != nil {
		t.Fatal(err)
	}
	if metadata != `{"page":"home"}` {
		t.Fatal(metadata)
	}
}

func TestBadCallsStoreNothing(t *testing.T) {
	db := memoryDB(t)
	now := "2026-11-10T15:00:00Z"
	if _, err := Track("", "created_doc", nil, db, now); err == nil {
		t.Fatal("empty user")
	}
	if _, err := Track("jordan", "created_doc", []any{"nope"}, db, now); err == nil {
		t.Fatal("bad metadata")
	}
	if _, err := Track("jordan", "created_doc", map[string]any{"occurred_at": "yesterday"}, db, now); err == nil {
		t.Fatal("bad time")
	}
	if err := Identify("jordan", map[string]string{}, db, now); err == nil {
		t.Fatal("empty traits")
	}
	var count int
	if err := db.QueryRow("SELECT COUNT(*) FROM plgkit_persona_events").Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 0 {
		t.Fatal(count)
	}
}

func TestPersonaBeforeMigrate(t *testing.T) {
	db, err := Connect("sqlite:///:memory:")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	_, err = Persona("jordan", db)
	if err == nil || !contains(err.Error(), "migrate") {
		t.Fatal(err)
	}
}

func TestCLIMigrate(t *testing.T) {
	dir := t.TempDir()
	SetDefault(nil)
	t.Cleanup(func() { SetDefault(nil) })
	t.Setenv("PLGKIT_DATABASE_URL", "sqlite:///"+filepath.ToSlash(filepath.Join(dir, "events.sqlite")))
	t.Setenv("PLGKIT_PERSONA_MIGRATIONS_DIR", "")
	if code := RunCLI(nil); code != 1 {
		t.Fatal(code)
	}
	if code := RunCLI([]string{"migrate"}); code != 0 {
		t.Fatal(code)
	}
	if code := RunCLI([]string{"migrate"}); code != 0 {
		t.Fatal(code)
	}
	db, err := sql.Open("sqlite", filepath.Join(dir, "events.sqlite"))
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	var name string
	if err := db.QueryRow("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'plgkit_persona_events'").Scan(&name); err != nil {
		t.Fatal(err)
	}
	if name != "plgkit_persona_events" {
		t.Fatal(name)
	}
}

func TestCLICalculate(t *testing.T) {
	dir := t.TempDir()
	SetDefault(nil)
	t.Cleanup(func() { SetDefault(nil) })
	if err := os.MkdirAll(filepath.Join(dir, "plgkit", "personas"), 0o755); err != nil {
		t.Fatal(err)
	}
	rules := "personas:\n  - name: everyone\n    priority: 1\n"
	if err := os.WriteFile(filepath.Join(dir, "plgkit", "personas", "personas.yml"), []byte(rules), 0o644); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PLGKIT_DATABASE_URL", "sqlite:///"+filepath.ToSlash(filepath.Join(dir, "events.sqlite")))
	old, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(dir); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { os.Chdir(old) })
	db := memoryDB(t)
	SetDefault(db)
	if _, err := Track("ada", "app_opened", map[string]any{"occurred_at": "2026-11-10T14:00:00Z"}, db, "2026-11-10T15:00:00Z"); err != nil {
		t.Fatal(err)
	}
	if code := RunCLI([]string{"calculate", "--now", "2026-11-10T15:00:00Z"}); code != 0 {
		t.Fatal(code)
	}
	result, err := Persona("ada", db)
	if err != nil || result.Persona != "everyone" {
		t.Fatalf("%#v %v", result, err)
	}
}

func memoryDB(t *testing.T) *sql.DB {
	t.Helper()
	db, err := Connect("sqlite:///:memory:")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	if err := Migrate(db); err != nil {
		t.Fatal(err)
	}
	return db
}

func contains(text, part string) bool {
	return len(text) >= len(part) && (text == part || len(part) == 0 || (len(text) > 0 && (indexOf(text, part) >= 0)))
}

func indexOf(text, part string) int {
	for i := 0; i+len(part) <= len(text); i++ {
		if text[i:i+len(part)] == part {
			return i
		}
	}
	return -1
}
