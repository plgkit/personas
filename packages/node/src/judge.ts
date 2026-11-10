/** Match one user against the personas in personas.yml. No database. */
import { PlgkitError } from "./errors.ts";
import { normalizeRules, type Condition, type PersonaRule, type Rules } from "./rules.ts";

const REASON_LIMIT = 5;

export type Reason =
  | { kind: "event"; action: string; occurred_at: string }
  | { kind: "trait"; key: string; equals: string };

export type PersonaResult = {
  user_id: string;
  persona: string;
  matched: string[];
  reasons: Reason[];
  calculated_at: string;
};

type Prepared = { action: string; occurredAt: Date; seq: number };

export function judge(
  userId: unknown,
  events: unknown,
  traits: unknown = {},
  rules: unknown = { groups: {}, personas: [] },
  now?: string | null,
): PersonaResult {
  const id = requireText(userId, "user_id");
  const moment = now != null ? parseTime(now) : new Date();
  const normalized: Rules = normalizeRules(rules);
  const stored = readTraits(traits);
  const prepared = prepareEvents(events);
  const ordered = [...normalized.personas].sort((a, b) => a.priority - b.priority || a.order - b.order);
  const matched: string[] = [];
  let winner: PersonaRule | null = null;
  for (const persona of ordered) {
    if (matches(persona, prepared, stored, moment)) {
      matched.push(persona.name);
      if (!winner) winner = persona;
    }
  }
  return {
    user_id: id,
    persona: winner ? winner.name : "",
    matched,
    reasons: winner ? reasonsFor(winner, prepared, stored, moment) : [],
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

function matches(persona: PersonaRule, events: Prepared[], traits: Record<string, string>, moment: Date): boolean {
  for (const condition of persona.require_all) {
    if (!holds(condition, events, traits, moment)) return false;
  }
  if (persona.require_one_of.length > 0) {
    if (!persona.require_one_of.some((condition) => holds(condition, events, traits, moment))) return false;
  }
  for (const condition of persona.exclude) {
    if (holds(condition, events, traits, moment)) return false;
  }
  return true;
}

function holds(condition: Condition, events: Prepared[], traits: Record<string, string>, moment: Date): boolean {
  if (condition.kind === "trait") return traits[condition.key] === condition.equals;
  const count = counted(condition, events, moment).length;
  if (count < condition.at_least) return false;
  if (condition.at_most != null && count > condition.at_most) return false;
  return true;
}

function counted(condition: Extract<Condition, { kind: "count" }>, events: Prepared[], moment: Date): Prepared[] {
  const start = moment.getTime() - condition.within_days * 86_400_000;
  const end = moment.getTime();
  const actions = new Set(condition.actions);
  return events.filter((event) => actions.has(event.action) && event.occurredAt.getTime() >= start && event.occurredAt.getTime() <= end);
}

function reasonsFor(persona: PersonaRule, events: Prepared[], traits: Record<string, string>, moment: Date): Reason[] {
  const supporting = [...persona.require_all, ...persona.require_one_of].filter((condition) =>
    holds(condition, events, traits, moment),
  );
  const seen = new Set<string>();
  const chosen: Prepared[] = [];
  for (const condition of supporting) {
    if (condition.kind !== "count") continue;
    for (const event of counted(condition, events, moment)) {
      const key = `${event.occurredAt.getTime()}\0${event.action}\0${event.seq}`;
      if (seen.has(key)) continue;
      seen.add(key);
      chosen.push(event);
    }
  }
  chosen.sort((a, b) => {
    const time = b.occurredAt.getTime() - a.occurredAt.getTime();
    if (time !== 0) return time;
    if (a.action !== b.action) return a.action < b.action ? 1 : -1;
    return b.seq - a.seq;
  });
  const reasons: Reason[] = chosen.map((event) => ({
    kind: "event",
    action: event.action,
    occurred_at: formatTime(event.occurredAt),
  }));
  for (const condition of supporting) {
    if (condition.kind === "trait") reasons.push({ kind: "trait", key: condition.key, equals: condition.equals });
  }
  return reasons.slice(0, REASON_LIMIT);
}

function prepareEvents(events: unknown): Prepared[] {
  const list = events ?? [];
  if (!Array.isArray(list)) throw new PlgkitError("events must be a list.");
  return list.map((event, index) => {
    if (typeof event !== "object" || event === null || Array.isArray(event)) {
      throw new PlgkitError("each event must be an object.");
    }
    const action = (event as { action?: unknown }).action;
    if (typeof action !== "string" || action.trim() === "") throw new PlgkitError("each event needs an action.");
    return {
      action: action.trim(),
      occurredAt: parseTime((event as { occurred_at?: unknown }).occurred_at),
      seq: index,
    };
  });
}

function readTraits(traits: unknown): Record<string, string> {
  if (traits == null) return {};
  if (typeof traits !== "object" || Array.isArray(traits)) throw new PlgkitError("traits must be an object of strings.");
  const cleaned: Record<string, string> = {};
  for (const [key, value] of Object.entries(traits)) {
    if (key.trim() === "") throw new PlgkitError("trait keys must be non-empty strings.");
    if (typeof value !== "string") throw new PlgkitError("trait values must be strings.");
    cleaned[key.trim()] = value;
  }
  return cleaned;
}
