/** Print a nudge for Avery and a nudge for Blake. The sentence comes from nudges. */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

import { bind } from "../../../spec/examples/nudges/audiences.ts";
import { loadMessages } from "../../../spec/examples/nudges/messages.ts";
import { calculate, connect, loadRules, migrate, persona, track } from "./index.ts";

const NUDGES_SHA = "db82c8caba8309266ef0b8cd39d98d9fb4f89e35";
const SHOW = ["avery_blocked", "blake_champion"];

const repo = repoRoot();
const fixture = JSON.parse(fs.readFileSync(path.join(repo, "spec", "fixtures", "cases.json"), "utf8"));
const examples = path.join(repo, "spec", "examples");
const rules = loadRules(path.join(examples, "personas.yml"));
const now = fixture.calculated_at as string;
const byName = new Map(fixture.cases.map((item: { name: string }) => [item.name, item]));
const messages = loadMessages(path.join(examples, "nudges", "messages"));
const db = connect("sqlite:///:memory:");
migrate(db);

for (const name of SHOW) {
  const caseItem = byName.get(name) as {
    user_id: string;
    events: { action: string; occurred_at: string }[];
  };
  for (const event of caseItem.events) {
    const stored = track(caseItem.user_id, event.action, { occurred_at: event.occurred_at }, { db, now });
    if (!stored) {
      console.error(`Could not store ${event.action} for ${caseItem.user_id}.`);
      process.exit(1);
    }
  }
}
calculate({ db, now, rules });

const nudges = await import(pathToFileURL(path.join(nudgesRoot(), "packages", "node", "src", "decide.ts")).href);
const nudgeStore = await import(pathToFileURL(path.join(nudgesRoot(), "packages", "node", "src", "store.ts")).href);
const nudgeDb = nudgeStore.connect("sqlite:///:memory:");
nudgeStore.migrate(nudgeDb);
const audiences = bind({ db });

for (const name of SHOW) {
  const caseItem = byName.get(name) as { user_id: string; persona: string };
  const result = persona(caseItem.user_id, { db });
  if (result.persona !== caseItem.persona) {
    console.error(`${caseItem.user_id} is ${result.persona}, expected ${caseItem.persona}.`);
    process.exit(1);
  }
  const shown = nudges.decide(
    "home",
    { user: { id: caseItem.user_id } },
    messages,
    { db: nudgeDb, audiences },
  ) as { render_props?: { body?: string } }[];
  if (shown.length !== 1 || !shown[0].render_props?.body) {
    console.error(`${caseItem.user_id} matched ${shown.length} nudges.`);
    process.exit(1);
  }
  const label = caseItem.user_id.charAt(0).toUpperCase() + caseItem.user_id.slice(1);
  console.log(`${label.padEnd(8, " ")} ${result.persona.padEnd(12, " ")} ${shown[0].render_props.body}`);
}

function nudgesRoot(): string {
  const env = process.env.PLGKIT_NUDGES_ROOT?.trim();
  if (env) return env;
  const cache = path.join(os.homedir(), ".cache", "plgkit-nudges", NUDGES_SHA);
  if (fs.existsSync(path.join(cache, "packages", "node", "src", "decide.ts"))) return cache;
  console.error(`Set PLGKIT_NUDGES_ROOT to a nudges checkout at ${NUDGES_SHA}.`);
  process.exit(1);
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
