import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { calculate, connect, identify, migrate, persona, personaIs, PlgkitError, track, type SqlDB } from "../src/index.ts";

const NOW = "2026-11-10T15:00:00Z";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const fixture = JSON.parse(fs.readFileSync(path.join(root, "spec", "fixtures", "cases.json"), "utf8"));

function memory(): SqlDB {
  const db = connect("sqlite:///:memory:");
  migrate(db);
  return db;
}

test("round trip matches every case", () => {
  for (const item of fixture.cases) {
    const db = memory();
    for (const event of item.events) {
      assert.equal(
        track(item.user_id, event.action, { occurred_at: event.occurred_at }, { db, now: item.calculated_at }),
        true,
        item.name,
      );
    }
    if (Object.keys(item.traits).length > 0) identify(item.user_id, item.traits, { db, now: item.calculated_at });
    assert.equal(persona(item.user_id, { db }).persona, "");
    calculate({ db, now: item.calculated_at, userId: item.user_id, rules: item.rules ?? fixture.rules });
    const result = persona(item.user_id, { db });
    assert.equal(result.persona, item.persona, item.name);
    assert.deepEqual(result.matched, item.matched, item.name);
    assert.deepEqual(result.reasons, item.reasons, item.name);
    assert.equal(personaIs(item.user_id, item.persona || "missing", { db }), Boolean(item.persona));
    db.close?.();
  }
});

test("identify keeps the latest value", () => {
  const db = memory();
  identify("ada", { role: "member" }, { db, now: NOW });
  identify("ada", { role: "billing_admin" }, { db, now: NOW });
  calculate({ db, now: NOW, rules: fixture.rules });
  assert.equal(persona("ada", { db }).persona, "billing_admin");
  db.close?.();
});

test("duplicate event id keeps the first write", () => {
  const db = memory();
  assert.equal(track("jordan", "created_doc", { occurred_at: "2026-11-09T15:00:00Z", event_id: "once", page: "home" }, { db, now: NOW }), true);
  assert.equal(track("jordan", "edited_doc", { occurred_at: "2026-11-09T16:00:00Z", event_id: "once" }, { db, now: NOW }), false);
  const row = db.prepare("SELECT metadata FROM plgkit_persona_events WHERE user_id = ?").get("jordan") as { metadata: string };
  assert.equal(JSON.parse(row.metadata).page, "home");
  db.close?.();
});

test("bad calls store nothing", () => {
  const db = memory();
  assert.throws(() => track("", "created_doc", {}, { db, now: NOW }), PlgkitError);
  assert.throws(() => identify("jordan", { role: 1 }, { db, now: NOW }), PlgkitError);
  const count = db.prepare("SELECT COUNT(*) AS n FROM plgkit_persona_events").get() as { n: number };
  assert.equal(count.n, 0);
  db.close?.();
});

test("persona before migrate explains the next step", () => {
  const db = connect("sqlite:///:memory:");
  assert.throws(() => persona("jordan", { db }), /migrate/);
  db.close?.();
});
