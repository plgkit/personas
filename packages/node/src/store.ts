/**
 * Open the database, run migrations, and read persona events.
 *
 * The database address lives in an environment variable named by
 * `database_url_env` in config.yml. A postgres:// or postgresql:// address
 * uses Postgres. If that variable is unset, we use a SQLite file,
 * `plgkit_events.sqlite`, in the current directory.
 */
import { DatabaseSync } from "node:sqlite";
import fs from "node:fs";
import path from "node:path";
import { Worker } from "node:worker_threads";
import { fileURLToPath } from "node:url";

import { PlgkitError } from "./errors.ts";
import { readFlat } from "./flat.ts";

export const DEFAULT_DATABASE_URL_ENV = "PLGKIT_DATABASE_URL";
export const DEFAULT_DATABASE_URL = "sqlite:///plgkit_events.sqlite";
const ENV_NAME = /^[A-Za-z_][A-Za-z0-9_]*$/;
const MIGRATION_NAME = /^(\d+)_.+\.sql$/;

export type SqlDB = {
  exec(sql: string): void;
  prepare(sql: string): {
    run(...params: unknown[]): unknown;
    get(...params: unknown[]): unknown;
    all(...params: unknown[]): unknown[];
  };
  close?(): void;
};

let defaultDb: SqlDB | null = null;
let warnedDefault = false;
let silencedSqliteWarning = false;

export function resolveDatabaseURL(
  configPath?: string | null,
  environ?: Record<string, string | undefined>,
): { url: string; usedDefault: boolean } {
  const env = environ ?? process.env;
  const name = envVarName(configPath);
  const value = String(env[name] ?? "").trim();
  if (!value) return { url: DEFAULT_DATABASE_URL, usedDefault: true };
  const scheme = schemeOf(value);
  if (scheme === "sqlite" || scheme === "postgres" || scheme === "postgresql") {
    return { url: value, usedDefault: false };
  }
  throw new PlgkitError(
    `${name} uses the ${JSON.stringify(scheme)} scheme. ` +
      "plgkit-personas supports SQLite (sqlite:///plgkit_events.sqlite) and Postgres " +
      "(postgres:// or postgresql://). " +
      "Unset the variable to use the local SQLite file.",
  );
}

export function connect(url?: string | null): SqlDB {
  let resolved = url ?? "";
  if (!resolved) {
    const found = resolveDatabaseURL();
    resolved = found.url;
    if (found.usedDefault) warnDefault(envVarName(null));
  }
  const scheme = schemeOf(resolved);
  if (scheme === "sqlite") return openSqlite(resolved);
  if (scheme === "postgres" || scheme === "postgresql") return openPostgres(resolved);
  throw new PlgkitError(
    `Unsupported database scheme ${JSON.stringify(scheme)}. ` +
      "Use a SQLite URL or a Postgres URL (postgres:// or postgresql://).",
  );
}

export function migrate(db?: SqlDB | null, migrationsDir?: string | null): SqlDB {
  const database = db ?? getDefaultDb();
  const directory = packagedMigrationsDir(migrationsDir);
  database.exec(
    "CREATE TABLE IF NOT EXISTS plgkit_persona_schema_migrations (version TEXT PRIMARY KEY)",
  );
  const applied = new Set(
    (database.prepare("SELECT version FROM plgkit_persona_schema_migrations").all() as { version: string }[]).map(
      (row) => row.version,
    ),
  );
  for (const file of migrationFiles(directory)) {
    if (applied.has(file.version)) continue;
    const statements = sqlStatements(fs.readFileSync(file.path, "utf8"));
    database.exec("BEGIN");
    try {
      for (const statement of statements) database.exec(statement);
      database.prepare("INSERT INTO plgkit_persona_schema_migrations (version) VALUES (?)").run(file.version);
      database.exec("COMMIT");
    } catch {
      try {
        database.exec("ROLLBACK");
      } catch {
        // The failed migration is already being reported.
      }
      throw new PlgkitError(`Migration ${file.version} failed.`);
    }
  }
  return database;
}

export function getDefaultDb(): SqlDB {
  if (!defaultDb) defaultDb = connect();
  return defaultDb;
}

export function setDefaultDb(db: SqlDB | null): void {
  defaultDb = db;
}

export function insertEvent(
  db: SqlDB,
  userId: string,
  action: string,
  eventId: string | null,
  metadata: unknown,
  occurredAt: string,
  receivedAt: string,
): boolean {
  try {
    db.prepare(
      "INSERT INTO plgkit_persona_events " +
        "(id, user_id, action, event_id, metadata, occurred_at, received_at) " +
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
    ).run(crypto.randomUUID(), userId, action, eventId, JSON.stringify(metadata), occurredAt, receivedAt);
    return true;
  } catch (err) {
    if (isUnique(err)) return false;
    throw err;
  }
}

export function upsertTrait(db: SqlDB, userId: string, key: string, value: string, updatedAt: string): void {
  db.prepare(
    "INSERT INTO plgkit_persona_traits (user_id, key, value, updated_at) VALUES (?, ?, ?, ?) " +
      "ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
  ).run(userId, key, value, updatedAt);
}

export function listTraits(db: SqlDB, userId: string): Record<string, string> {
  const rows = db.prepare(
    "SELECT key, value FROM plgkit_persona_traits WHERE user_id = ? ORDER BY key ASC",
  ).all(userId) as { key: string; value: string }[];
  const traits: Record<string, string> = {};
  for (const row of rows) traits[row.key] = row.value;
  return traits;
}

export function listUserIds(db: SqlDB): string[] {
  const rows = db.prepare(
    "SELECT user_id FROM plgkit_persona_events UNION SELECT user_id FROM plgkit_persona_traits ORDER BY user_id ASC",
  ).all() as { user_id: string }[];
  return rows.map((row) => row.user_id);
}

export function writeSnapshot(db: SqlDB, result: {
  user_id: string;
  persona: string;
  matched: string[];
  reasons: unknown[];
  calculated_at: string;
}): void {
  db.prepare(
    "INSERT INTO plgkit_persona_snapshots (user_id, persona, matched, reasons, calculated_at) VALUES (?, ?, ?, ?, ?) " +
      "ON CONFLICT(user_id) DO UPDATE SET persona = excluded.persona, matched = excluded.matched, " +
      "reasons = excluded.reasons, calculated_at = excluded.calculated_at",
  ).run(
    result.user_id,
    result.persona,
    JSON.stringify(result.matched),
    JSON.stringify(result.reasons),
    result.calculated_at,
  );
}

export function readSnapshot(db: SqlDB, userId: string): {
  user_id: string;
  persona: string;
  matched: string[];
  reasons: { kind: string; action?: string; occurred_at?: string; key?: string; equals?: string }[];
  calculated_at: string;
} | null {
  const row = db.prepare(
    "SELECT user_id, persona, matched, reasons, calculated_at FROM plgkit_persona_snapshots WHERE user_id = ?",
  ).get(userId) as {
    user_id: string;
    persona: string;
    matched: string;
    reasons: string;
    calculated_at: string;
  } | undefined;
  if (!row) return null;
  return {
    user_id: row.user_id,
    persona: row.persona,
    matched: JSON.parse(row.matched),
    reasons: JSON.parse(row.reasons),
    calculated_at: row.calculated_at,
  };
}

export function listEvents(db: SqlDB, userId: string): { action: string; occurred_at: string }[] {
  try {
    const rows = db
      .prepare(
        "SELECT action, occurred_at FROM plgkit_persona_events " +
          "WHERE user_id = ? ORDER BY occurred_at ASC, id ASC",
      )
      .all(userId) as { action: string; occurred_at: string }[];
    return rows.map((row) => ({ action: row.action, occurred_at: row.occurred_at }));
  } catch {
    throw new PlgkitError("Could not read persona events. Run plgkit-personas migrate.");
  }
}

function openSqlite(url: string): SqlDB {
  silenceSqliteWarning();
  let db: DatabaseSync;
  try {
    db = new DatabaseSync(sqlitePath(url));
    db.exec("PRAGMA busy_timeout = 5000");
  } catch {
    throw new PlgkitError("Could not open the database.");
  }
  return db as unknown as SqlDB;
}

function openPostgres(url: string): SqlDB {
  const readySab = new SharedArrayBuffer(4);
  const ready = new Int32Array(readySab);
  const worker = new Worker(new URL("./pg-worker.js", import.meta.url), {
    workerData: { url, ready: readySab },
  });
  Atomics.wait(ready, 0, 0, 10000);
  const status = Atomics.load(ready, 0);
  if (status === 3) {
    worker.terminate();
    throw new PlgkitError("Postgres needs the pg package. Install it with: npm install pg");
  }
  if (status !== 1) {
    worker.terminate();
    throw new PlgkitError("Could not open the database.");
  }
  return postgresDb(worker);
}

function postgresDb(worker: Worker): SqlDB {
  const ask = (sql: string, params: unknown[]): unknown[] => {
    const sab = new SharedArrayBuffer(256 * 1024);
    const view = new Int32Array(sab);
    worker.postMessage({ sql: postgresSQL(sql), params, sab });
    Atomics.wait(view, 0, 0, 30000);
    const status = Atomics.load(view, 0);
    const length = Atomics.load(view, 1);
    const text = Buffer.from(sab).subarray(8, 8 + length).toString("utf8");
    if (status === 2) {
      const error = new Error(text || "Could not run the database statement.");
      throw error;
    }
    if (status !== 1) throw new PlgkitError("Could not run the database statement.");
    const rows = text ? JSON.parse(text) : [];
    return Array.isArray(rows) ? rows : [];
  };
  return {
    exec(sql: string) {
      ask(sql, []);
    },
    prepare(sql: string) {
      return {
        run(...params: unknown[]) {
          ask(sql, params);
        },
        get(...params: unknown[]) {
          return ask(sql, params)[0];
        },
        all(...params: unknown[]) {
          return ask(sql, params);
        },
      };
    },
    close() {
      worker.terminate();
    },
  };
}

function postgresSQL(sql: string): string {
  let n = 0;
  return sql.replace(/\?/g, () => `$${++n}`);
}

function packagedMigrationsDir(migrationsDir?: string | null): string {
  if (migrationsDir) return migrationsDir;
  const fromEnv = (process.env.PLGKIT_PERSONA_MIGRATIONS_DIR ?? "").trim();
  if (fromEnv) return fromEnv;
  return fileURLToPath(new URL("../migrations/", import.meta.url));
}

function migrationFiles(directory: string): { version: string; path: string }[] {
  let names: string[];
  try {
    names = fs.readdirSync(directory);
  } catch {
    throw new PlgkitError(`Migrations folder does not exist: ${directory}`);
  }
  const found = names
    .map((name) => {
      const match = MIGRATION_NAME.exec(name);
      return match ? { version: match[1]!, path: path.join(directory, name) } : null;
    })
    .filter((item): item is { version: string; path: string } => item !== null)
    .sort((a, b) => Number(a.version) - Number(b.version));
  if (found.length === 0) throw new PlgkitError(`No migration files in ${directory}.`);
  return found;
}

function sqlStatements(text: string): string[] {
  const lines = text.split(/\r?\n/).map((line) => {
    const mark = line.indexOf("--");
    return mark >= 0 ? line.slice(0, mark) : line;
  });
  return lines.join("\n").split(";").map((part) => part.trim()).filter((part) => part !== "");
}

function envVarName(configPath?: string | null): string {
  let resolved = configPath ?? null;
  if (!resolved) resolved = defaultConfigFile();
  if (!resolved) return DEFAULT_DATABASE_URL_ENV;
  const raw = readFlat(resolved);
  const unknown = Object.keys(raw).filter((key) => key !== "database_url_env").sort();
  if (unknown.length > 0) throw new PlgkitError(`Unknown config key: ${unknown.join(", ")}.`);
  const name = raw.database_url_env ?? DEFAULT_DATABASE_URL_ENV;
  if (!ENV_NAME.test(name)) {
    throw new PlgkitError(
      "database_url_env in config.yml must be the name of an environment " +
        "variable, not the database address. The address can contain a " +
        "password, so put it in the environment. " +
        "Example: database_url_env: PLGKIT_DATABASE_URL",
    );
  }
  return name;
}

function defaultConfigFile(): string | null {
  const candidate = path.join(process.cwd(), "plgkit", "personas", "config.yml");
  return fs.existsSync(candidate) ? candidate : null;
}

function schemeOf(url: string): string {
  if (!url) return "unknown";
  if (url.startsWith("sqlite:")) return "sqlite";
  const mark = url.indexOf("://");
  if (mark >= 0) return url.slice(0, mark).toLowerCase();
  return "unknown";
}

function sqlitePath(url: string): string {
  if (url === "sqlite:///:memory:" || url === "sqlite::memory:") return ":memory:";
  const prefix = "sqlite:///";
  if (!url.startsWith(prefix)) {
    throw new PlgkitError(
      "The SQLite URL must look like sqlite:///plgkit_events.sqlite or sqlite:///:memory:.",
    );
  }
  return url.slice(prefix.length);
}

function isUnique(err: unknown): boolean {
  const text = String((err as { message?: string })?.message ?? err).toLowerCase();
  return text.includes("unique");
}

function warnDefault(name: string): void {
  if (warnedDefault) return;
  warnedDefault = true;
  console.error(
    `${name} is unset. Using a SQLite file at plgkit_events.sqlite in the current directory.`,
  );
}

function silenceSqliteWarning(): void {
  if (silencedSqliteWarning) return;
  silencedSqliteWarning = true;
  const emit = process.emitWarning.bind(process);
  process.emitWarning = ((warning: unknown, ...rest: unknown[]) => {
    const text = typeof warning === "string" ? warning : (warning as { message?: string })?.message ?? "";
    if (text.includes("SQLite is an experimental feature")) return;
    return (emit as (...args: unknown[]) => void)(warning, ...rest);
  }) as typeof process.emitWarning;
}
