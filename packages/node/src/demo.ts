/** Print a nudge for Avery and a nudge for Blake. */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { connect, loadMapping, loadPolicy, migrate, persona, track } from "./index.ts";

const LINES: Record<string, string> = {
  blocked: "Want help with the step you stopped on?",
  champion: "Bring in the person you invited.",
};
const SHOW = ["avery_blocked", "blake_champion"];

const repo = repoRoot();
const fixture = JSON.parse(fs.readFileSync(path.join(repo, "spec", "fixtures", "cases.json"), "utf8"));
const examples = path.join(repo, "spec", "examples");
const mapping = loadMapping(path.join(examples, "mapping.yml"));
const policy = loadPolicy(path.join(examples, "config.yml"));
const now = fixture.calculated_at as string;
const byName = new Map(fixture.cases.map((item: { name: string }) => [item.name, item]));
const db = connect("sqlite:///:memory:");
migrate(db);

for (const name of SHOW) {
  const caseItem = byName.get(name) as {
    user_id: string;
    persona: string;
    events: { action: string; occurred_at: string }[];
  };
  for (const event of caseItem.events) {
    const stored = track(caseItem.user_id, event.action, { occurred_at: event.occurred_at }, { db, now });
    if (!stored) {
      console.error(`Could not store ${event.action} for ${caseItem.user_id}.`);
      process.exit(1);
    }
  }
  const result = persona(caseItem.user_id, { db, now, mapping, config: policy });
  if (result.persona !== caseItem.persona) {
    console.error(`${caseItem.user_id} is ${result.persona}, expected ${caseItem.persona}.`);
    process.exit(1);
  }
  const label = caseItem.user_id.charAt(0).toUpperCase() + caseItem.user_id.slice(1);
  const line = LINES[result.persona];
  if (!line) process.exit(1);
  console.log(`${label.padEnd(8, " ")} ${result.persona.padEnd(12, " ")} ${line}`);
}

function repoRoot(): string {
  let dir = path.dirname(fileURLToPath(import.meta.url));
  for (let i = 0; i < 6; i += 1) {
    if (fs.existsSync(path.join(dir, "spec", "fixtures", "cases.json"))) return dir;
    dir = path.dirname(dir);
  }
  console.error("Could not find the personas repo.");
  process.exit(1);
}
