/** Judge every known user and store the winner. */
import { PlgkitError } from "./errors.ts";
import { formatTime, judge, parseTime, requireText } from "./judge.ts";
import { loadRules, normalizeRules, type Rules } from "./rules.ts";
import { getDefaultDb, listEvents, listTraits, listUserIds, writeSnapshot, type SqlDB } from "./store.ts";

export function calculate(options: {
  db?: SqlDB | null;
  now?: string | null;
  userId?: string | null;
  rules?: unknown;
  rulesPath?: string | null;
} = {}): { users: number; assigned: number; unmatched: number } {
  const db = options.db ?? getDefaultDb();
  const rules: Rules = options.rules === undefined ? loadRules(options.rulesPath) : normalizeRules(options.rules);
  const moment = options.now != null ? parseTime(options.now) : new Date();
  const stamp = formatTime(moment);
  let userIds: string[];
  if (options.userId == null) {
    try {
      userIds = listUserIds(db);
    } catch (err) {
      if (err instanceof PlgkitError) throw err;
      throw new PlgkitError("Could not calculate personas. Run plgkit-personas migrate.");
    }
  } else {
    userIds = [requireText(options.userId, "user_id")];
  }
  let assigned = 0;
  for (const current of userIds) {
    let events;
    let traits;
    try {
      events = listEvents(db, current);
      traits = listTraits(db, current);
    } catch (err) {
      if (err instanceof PlgkitError) throw err;
      throw new PlgkitError("Could not calculate personas. Run plgkit-personas migrate.");
    }
    const result = judge(current, events, traits, rules, stamp);
    try {
      writeSnapshot(db, result);
    } catch (err) {
      if (err instanceof PlgkitError) throw err;
      throw new PlgkitError("Could not calculate personas. Run plgkit-personas migrate.");
    }
    if (result.persona) assigned += 1;
  }
  return { users: userIds.length, assigned, unmatched: userIds.length - assigned };
}
