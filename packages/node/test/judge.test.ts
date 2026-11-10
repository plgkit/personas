import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { DEFAULT_POLICY, judge, loadMapping, loadPolicy } from "../src/index.ts";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const fixture = JSON.parse(fs.readFileSync(path.join(root, "spec", "fixtures", "cases.json"), "utf8"));

test("defaults and examples match the fixture", () => {
  assert.deepEqual(DEFAULT_POLICY, fixture.config);
  assert.deepEqual(loadMapping(path.join(root, "spec", "examples", "mapping.yml")), fixture.mapping);
  assert.deepEqual(loadPolicy(path.join(root, "spec", "examples", "config.yml")), fixture.config);
});

test("shared cases", () => {
  const names = fixture.cases.map((item: { name: string }) => item.name);
  assert.ok(names.includes("avery_blocked"));
  assert.ok(names.includes("blake_champion"));
  for (const item of fixture.cases) {
    const result = judge(item.user_id, item.events, {
      mapping: fixture.mapping,
      policy: fixture.config,
      now: item.calculated_at,
    });
    assert.equal(result.persona, item.persona, item.name);
    assert.deepEqual(result.matched, item.matched, item.name);
    assert.deepEqual(result.counts, item.counts, item.name);
    assert.deepEqual(result.reasons, item.reasons, item.name);
    assert.equal(result.calculated_at, item.calculated_at, item.name);
    assert.ok(result.reasons.length <= 5, item.name);
  }
});

test("a lower power threshold promotes an evaluator", () => {
  const jordan = fixture.cases.find((item: { name: string }) => item.name === "evaluator");
  const policy = { ...fixture.config, power_user_min: 2 };
  const result = judge(jordan.user_id, jordan.events, {
    mapping: fixture.mapping,
    policy,
    now: jordan.calculated_at,
  });
  assert.equal(result.persona, "power_user");
});
