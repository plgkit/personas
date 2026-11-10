import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { DatabaseSync } from "node:sqlite";

const here = path.dirname(fileURLToPath(import.meta.url));
const cli = path.resolve(here, "../src/cli.ts");

test("migrate creates the table", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "plgkit-personas-"));
  const database = path.join(dir, "events.sqlite");
  const env = {
    ...process.env,
    PLGKIT_DATABASE_URL: `sqlite:///${database}`,
  };
  delete env.PLGKIT_PERSONA_MIGRATIONS_DIR;
  for (let i = 0; i < 2; i += 1) {
    const completed = spawnSync(
      process.execPath,
      ["--disable-warning=ExperimentalWarning", "--experimental-strip-types", cli, "migrate"],
      { cwd: dir, env, encoding: "utf8" },
    );
    assert.equal(completed.status, 0, completed.stderr);
    assert.match(completed.stdout, /Migrations are up to date/);
  }
  const db = new DatabaseSync(database);
  const row = db.prepare(
    "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'plgkit_persona_events'",
  ).get() as { name: string } | undefined;
  assert.equal(row?.name, "plgkit_persona_events");
  db.close();
});
