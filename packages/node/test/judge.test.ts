import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { judge, loadRules, normalizeRules, PlgkitError } from "../src/index.ts";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const fixture = JSON.parse(fs.readFileSync(path.join(root, "spec", "fixtures", "cases.json"), "utf8"));

test("example file matches the fixture", () => {
  assert.deepEqual(loadRules(path.join(root, "spec", "examples", "personas.yml")), normalizeRules(fixture.rules));
});

test("shared cases", () => {
  const names = fixture.cases.map((item: { name: string }) => item.name);
  assert.ok(names.includes("developer_member"));
  assert.ok(names.includes("avery_blocked"));
  assert.ok(names.includes("blake_champion"));
  for (const item of fixture.cases) {
    const result = judge(item.user_id, item.events, item.traits, item.rules ?? fixture.rules, item.calculated_at);
    assert.equal(result.persona, item.persona, item.name);
    assert.deepEqual(result.matched, item.matched, item.name);
    assert.deepEqual(result.reasons, item.reasons, item.name);
    assert.equal(result.calculated_at, item.calculated_at, item.name);
  }
});

test("bad rules", () => {
  assert.throws(() => normalizeRules({ personas: [{ name: "a", require_all: [] }] }), PlgkitError);
  assert.throws(() => normalizeRules({ mystery: 1 }), PlgkitError);
});
