import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { bind } from "../../../spec/examples/nudges/audiences.ts";
import { loadMessages } from "../../../spec/examples/nudges/messages.ts";
import { connect, migrate, track } from "../src/index.ts";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const fixture = JSON.parse(fs.readFileSync(path.join(root, "spec", "fixtures", "cases.json"), "utf8"));
const nudgesDir = path.join(root, "spec", "examples", "nudges");

test("message files hold the two lines", () => {
  const loaded = loadMessages(path.join(nudgesDir, "messages"));
  const bodies = Object.fromEntries(
    loaded.map((item) => [item.id, (item.render_props as { body: string }).body]),
  );
  assert.deepEqual(bodies, {
    "20261110150400-home-blocked-help": "Want help with the step you stopped on?",
    "20261110150401-home-champion-invite": "Bring in the person you invited.",
  });
});

test("checks follow the label", () => {
  for (const item of fixture.cases) {
    const db = connect("sqlite:///:memory:");
    migrate(db);
    const now = item.calculated_at as string;
    for (const event of item.events) {
      const stored = track(item.user_id, event.action, { occurred_at: event.occurred_at }, { db, now });
      assert.equal(stored, true, item.name);
    }
    const checks = bind({ db, now, mapping: fixture.mapping, policy: fixture.config });
    const ctx = { user: { id: item.user_id } };
    assert.equal(checks.persona_is_blocked(ctx), item.persona === "blocked", item.name);
    assert.equal(checks.persona_is_champion(ctx), item.persona === "champion", item.name);
  }
});

test("sample files mark Avery blocked", () => {
  const item = fixture.cases.find((entry: { name: string }) => entry.name === "avery_blocked");
  const db = connect("sqlite:///:memory:");
  migrate(db);
  const now = item.calculated_at as string;
  for (const event of item.events) {
    track(item.user_id, event.action, { occurred_at: event.occurred_at }, { db, now });
  }
  const checks = bind({ db, now });
  assert.equal(checks.persona_is_blocked({ user: { id: "avery" } }), true);
  assert.equal(checks.persona_is_champion({ user: { id: "avery" } }), false);
  assert.equal(checks.persona_is_blocked({}), false);
});
