import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { connect, migrate, persona, PlgkitError, track, type SqlDB } from "../src/index.ts";

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
    const result = persona(item.user_id, {
      db,
      now: item.calculated_at,
      mapping: fixture.mapping,
      config: fixture.config,
    });
    assert.equal(result.persona, item.persona, item.name);
    assert.deepEqual(result.reasons, item.reasons, item.name);
    assert.deepEqual(result.counts, item.counts, item.name);
    db.close?.();
  }
});

test("duplicate event id keeps the first write", () => {
  const db = memory();
  assert.equal(
    track("jordan", "created_doc", { occurred_at: "2026-11-09T15:00:00Z", event_id: "once", page: "home" }, { db, now: NOW }),
    true,
  );
  assert.equal(
    track("jordan", "edited_doc", { occurred_at: "2026-11-09T16:00:00Z", event_id: "once", page: "away" }, { db, now: NOW }),
    false,
  );
  const result = persona("jordan", {
    db,
    now: NOW,
    mapping: { created_doc: "core_action", edited_doc: "core_action" },
    config: fixture.config,
  });
  assert.equal(result.counts.core_action, 1);
  assert.equal(result.reasons[0]?.action, "created_doc");
  assert.equal(result.reasons[0]?.occurred_at, "2026-11-09T15:00:00.000000Z");
  const row = db.prepare("SELECT metadata FROM plgkit_persona_events WHERE user_id = ?").get("jordan") as {
    metadata: string;
  };
  assert.equal(row.metadata, '{"page":"home"}');
  db.close?.();
});

test("bad calls store nothing", () => {
  const db = memory();
  assert.throws(() => track("", "created_doc", null, { db, now: NOW }), PlgkitError);
  assert.throws(() => track("jordan", "created_doc", ["nope"], { db, now: NOW }), PlgkitError);
  assert.throws(() => track("jordan", "created_doc", { occurred_at: "yesterday" }, { db, now: NOW }), PlgkitError);
  assert.throws(() => track("jordan", "created_doc", { occurred_at: "2026-11-09T15:00:00" }, { db, now: NOW }), PlgkitError);
  const row = db.prepare("SELECT COUNT(*) AS n FROM plgkit_persona_events").get() as { n: number | bigint };
  assert.equal(Number(row.n), 0);
  db.close?.();
});

test("persona before migrate explains the next step", () => {
  const db = connect("sqlite:///:memory:");
  assert.throws(() => persona("jordan", { db, now: NOW, mapping: {}, config: fixture.config }), /migrate/);
  db.close?.();
});
