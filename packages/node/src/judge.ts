/** Turn stored events into one persona. No database, no clock of its own. */
import { normalizePolicy, type Policy } from "./config.ts";
import { PlgkitError } from "./errors.ts";
import { CATEGORIES, normalizeMapping, type Category } from "./mapping.ts";

const REASON_LIMIT = 5;
const SUPPORTS: Record<string, Set<string>> = {
  champion: new Set(["invite_sent"]),
  power_user: new Set(["core_action"]),
  blocked: new Set(CATEGORIES),
  implementer: new Set(["setup_step"]),
  evaluator: new Set(CATEGORIES),
  unknown: new Set(),
};

export type Reason = { action: string; category: Category; occurred_at: string };

export type PersonaResult = {
  user_id: string;
  persona: string;
  reasons: Reason[];
  counts: Record<Category, number>;
  matched: string[];
  calculated_at: string;
};

type Counted = { action: string; category: Category; occurredAt: Date; seq: number };

export function judge(
  userId: unknown,
  events: unknown,
  options: { mapping?: unknown; policy?: unknown; now?: string | null } = {},
): PersonaResult {
  const id = requireText(userId, "user_id");
  const moment = options.now != null ? parseTime(options.now) : new Date();
  const rules = normalizePolicy(options.policy ?? null);
  const categories = normalizeMapping(options.mapping ?? null);
  const counted = inWindow(events, categories, moment, rules.lookback_days);
  const counts = emptyCounts();
  for (const event of counted) counts[event.category] += 1;
  const newest = counted.length > 0 ? counted[counted.length - 1]!.occurredAt : null;
  const silenceAt = new Date(moment.getTime() - rules.silence_days * 86_400_000);
  const quiet = newest !== null && newest.getTime() <= silenceAt.getTime();
  const started = counts.setup_step >= 1 || counts.core_action >= 1;
  const matched: string[] = [];
  if (counts.invite_sent >= rules.champion_min) matched.push("champion");
  if (counts.core_action >= rules.power_user_min) matched.push("power_user");
  if (started && quiet) matched.push("blocked");
  if (counts.setup_step >= rules.implementer_min) matched.push("implementer");
  if (counted.length > 0) matched.push("evaluator");
  const personaName = matched[0] ?? "unknown";
  return {
    user_id: id,
    persona: personaName,
    reasons: reasons(counted, personaName),
    counts,
    matched,
    calculated_at: formatTime(moment),
  };
}

export function parseTime(value: unknown): Date {
  if (typeof value !== "string") {
    throw new PlgkitError("occurred_at must be an ISO-8601 timestamp with a timezone.");
  }
  let text = value.trim();
  if (text.endsWith("Z")) text = `${text.slice(0, -1)}+00:00`;
  if (!/[+-]\d{2}:\d{2}$/.test(text)) {
    throw new PlgkitError("occurred_at must include a timezone, for example 2026-11-09T15:00:00Z.");
  }
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) {
    throw new PlgkitError("occurred_at must be an ISO-8601 timestamp with a timezone.");
  }
  return parsed;
}

export function formatTime(moment: Date): string {
  return moment.toISOString().replace(/\.(\d{3})Z$/, ".$1000Z");
}

export function requireText(value: unknown, name: string): string {
  if (typeof value !== "string" || value.trim() === "") throw new PlgkitError(`${name} is required.`);
  return value.trim();
}

function emptyCounts(): Record<Category, number> {
  return { core_action: 0, invite_sent: 0, setup_step: 0 };
}

function inWindow(events: unknown, mapping: Record<string, Category>, moment: Date, lookbackDays: number): Counted[] {
  const list = events ?? [];
  if (!Array.isArray(list)) throw new PlgkitError("events must be a list.");
  const start = moment.getTime() - lookbackDays * 86_400_000;
  const end = moment.getTime();
  const counted: Counted[] = [];
  list.forEach((event, index) => {
    if (typeof event !== "object" || event === null || Array.isArray(event)) {
      throw new PlgkitError("each event must be an object.");
    }
    const actionRaw = (event as { action?: unknown }).action;
    if (typeof actionRaw !== "string" || actionRaw.trim() === "") {
      throw new PlgkitError("each event needs an action.");
    }
    const action = actionRaw.trim();
    const category = mapping[action];
    if (!category || !CATEGORIES.includes(category)) return;
    const occurredAt = parseTime((event as { occurred_at?: unknown }).occurred_at);
    const millis = occurredAt.getTime();
    if (millis < start || millis > end) return;
    counted.push({ action, category, occurredAt, seq: index });
  });
  counted.sort((a, b) => compare(a, b));
  return counted;
}

function reasons(counted: Counted[], personaName: string): Reason[] {
  const supported = counted.filter((event) => SUPPORTS[personaName]?.has(event.category));
  supported.sort((a, b) => compare(b, a));
  return supported.slice(0, REASON_LIMIT).map((event) => ({
    action: event.action,
    category: event.category,
    occurred_at: formatTime(event.occurredAt),
  }));
}

function compare(a: Counted, b: Counted): number {
  const time = a.occurredAt.getTime() - b.occurredAt.getTime();
  if (time !== 0) return time;
  if (a.action < b.action) return -1;
  if (a.action > b.action) return 1;
  return a.seq - b.seq;
}

export type { Policy };
