/** Load one user's events and judge them. */
import { loadPolicy } from "./config.ts";
import { judge, requireText, type PersonaResult } from "./judge.ts";
import { loadMapping } from "./mapping.ts";
import { getDefaultDb, listEvents, type SqlDB } from "./store.ts";

export function persona(
  userId: unknown,
  options: {
    db?: SqlDB | null;
    now?: string | null;
    mapping?: unknown;
    config?: unknown;
    mappingPath?: string | null;
    configPath?: string | null;
  } = {},
): PersonaResult {
  const id = requireText(userId, "user_id");
  const db = options.db ?? getDefaultDb();
  const mapping = options.mapping === undefined ? loadMapping(options.mappingPath) : options.mapping;
  const config = options.config === undefined ? loadPolicy(options.configPath) : options.config;
  const events = listEvents(db, id);
  return judge(id, events, { mapping, policy: config, now: options.now });
}
