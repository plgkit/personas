/** Personas you define, and the conditions that match them. */
import fs from "node:fs";
import path from "node:path";

import { PlgkitError } from "./errors.ts";
import { parseYaml } from "./yaml.ts";

export type CountCondition = {
  kind: "count";
  actions: string[];
  at_least: number;
  at_most: number | null;
  within_days: number;
};

export type TraitCondition = { kind: "trait"; key: string; equals: string };

export type Condition = CountCondition | TraitCondition;

export type PersonaRule = {
  name: string;
  priority: number;
  order: number;
  require_all: Condition[];
  require_one_of: Condition[];
  exclude: Condition[];
};

export type Rules = { groups: Record<string, string[]>; personas: PersonaRule[] };

const PERSONA_KEYS = new Set(["name", "priority", "require_all", "require_one_of", "exclude"]);
const COUNT_KEYS = new Set(["action", "actions", "group", "at_least", "at_most", "within_days"]);
const TRAIT_KEYS = new Set(["key", "equals"]);

export function defaultRulesPath(): string | null {
  const candidate = path.join(process.cwd(), "plgkit", "personas", "personas.yml");
  return fs.existsSync(candidate) ? candidate : null;
}

export function loadRules(filePath?: string | null): Rules {
  const resolved = filePath === undefined || filePath === null ? defaultRulesPath() : filePath;
  if (!resolved) return normalizeRules({ groups: {}, personas: [] });
  return normalizeRules(parseYaml(fs.readFileSync(resolved, "utf8")));
}

export function normalizeRules(raw: unknown): Rules {
  if (alreadyNormalized(raw)) return raw;
  const source = raw == null ? {} : raw;
  if (!isRecord(source)) throw new PlgkitError("personas.yml must be a mapping.");
  const unknown = Object.keys(source).filter((key) => key !== "groups" && key !== "personas").sort();
  if (unknown.length > 0) throw new PlgkitError(`Unknown rules key: ${unknown.join(", ")}.`);
  const groups = readGroups(source.groups);
  const personasRaw = source.personas == null ? [] : source.personas;
  if (!Array.isArray(personasRaw)) throw new PlgkitError("personas must be a list.");
  const names = new Set<string>();
  const personas: PersonaRule[] = personasRaw.map((item, index) => {
    const persona = readPersona(item, groups);
    if (names.has(persona.name)) throw new PlgkitError(`Duplicate persona: ${persona.name}.`);
    names.add(persona.name);
    persona.order = index;
    return persona;
  });
  return { groups, personas };
}

function alreadyNormalized(raw: unknown): raw is Rules {
  if (!isRecord(raw) || !Array.isArray(raw.personas) || raw.personas.length === 0) return false;
  const first = raw.personas[0];
  return isRecord(first) && "order" in first;
}

function readGroups(raw: unknown): Record<string, string[]> {
  if (raw == null) return {};
  if (!isRecord(raw)) throw new PlgkitError("groups must be a mapping of name to actions.");
  const groups: Record<string, string[]> = {};
  for (const [name, actions] of Object.entries(raw)) {
    if (name.trim() === "") throw new PlgkitError("group names must be non-empty strings.");
    if (!Array.isArray(actions) || actions.length === 0) throw new PlgkitError(`${name} needs a list of actions.`);
    groups[name.trim()] = actions.map((action) => {
      if (typeof action !== "string" || action.trim() === "") {
        throw new PlgkitError(`${name} actions must be non-empty strings.`);
      }
      return action.trim();
    });
  }
  return groups;
}

function readPersona(item: unknown, groups: Record<string, string[]>): PersonaRule {
  if (!isRecord(item)) throw new PlgkitError("each persona must be a mapping.");
  const unknown = Object.keys(item).filter((key) => !PERSONA_KEYS.has(key)).sort();
  if (unknown.length > 0) throw new PlgkitError(`Unknown persona key: ${unknown.join(", ")}.`);
  const name = item.name;
  if (typeof name !== "string" || name.trim() === "") throw new PlgkitError("persona name is required.");
  if (!("priority" in item)) throw new PlgkitError(`${name} needs a priority.`);
  return {
    name: name.trim(),
    priority: wholeNumber("priority", item.priority, null),
    order: 0,
    require_all: conditions(item.require_all, "require_all", groups, name),
    require_one_of: conditions(item.require_one_of, "require_one_of", groups, name),
    exclude: conditions(item.exclude, "exclude", groups, name),
  };
}

function conditions(raw: unknown, field: string, groups: Record<string, string[]>, personaName: string): Condition[] {
  if (raw == null) return [];
  if (!Array.isArray(raw)) throw new PlgkitError(`${personaName} ${field} must be a list.`);
  return raw.map((item) => condition(item, groups, personaName));
}

function condition(item: unknown, groups: Record<string, string[]>, personaName: string): Condition {
  if (!isRecord(item) || Object.keys(item).length !== 1) {
    throw new PlgkitError(`${personaName} conditions must be a count or a trait.`);
  }
  const [kind, body] = Object.entries(item)[0]!;
  if (kind === "count") return count(body, groups, personaName);
  if (kind === "trait") return trait(body, personaName);
  throw new PlgkitError(`${personaName} conditions must be a count or a trait.`);
}

function count(body: unknown, groups: Record<string, string[]>, personaName: string): CountCondition {
  if (!isRecord(body)) throw new PlgkitError(`${personaName} count must be a mapping.`);
  const unknown = Object.keys(body).filter((key) => !COUNT_KEYS.has(key)).sort();
  if (unknown.length > 0) throw new PlgkitError(`Unknown count key: ${unknown.join(", ")}.`);
  const choices = ["action", "actions", "group"].filter((key) => key in body && body[key] != null);
  if (choices.length !== 1) throw new PlgkitError(`${personaName} count needs one of action, actions, or group.`);
  let actions: string[];
  if (choices[0] === "action") {
    const action = body.action;
    if (typeof action !== "string" || action.trim() === "") {
      throw new PlgkitError(`${personaName} action must be a non-empty string.`);
    }
    actions = [action.trim()];
  } else if (choices[0] === "actions") {
    if (!Array.isArray(body.actions) || body.actions.length === 0) {
      throw new PlgkitError(`${personaName} actions must be a list.`);
    }
    actions = body.actions.map((action) => {
      if (typeof action !== "string" || action.trim() === "") {
        throw new PlgkitError(`${personaName} actions must be non-empty strings.`);
      }
      return action.trim();
    });
  } else {
    const group = body.group;
    if (typeof group !== "string" || group.trim() === "") {
      throw new PlgkitError(`${personaName} group must be a non-empty string.`);
    }
    const found = groups[group.trim()];
    if (!found) throw new PlgkitError(`Unknown group: ${group.trim()}.`);
    actions = [...found];
  }
  if (!("at_least" in body)) throw new PlgkitError(`${personaName} count needs at_least.`);
  const atLeast = wholeNumber("at_least", body.at_least, 0);
  let atMost: number | null = null;
  if ("at_most" in body && body.at_most != null) {
    atMost = wholeNumber("at_most", body.at_most, 0);
    if (atMost < atLeast) throw new PlgkitError("at_most must be at least at_least.");
  }
  if (!("within_days" in body)) throw new PlgkitError(`${personaName} count needs within_days.`);
  return {
    kind: "count",
    actions,
    at_least: atLeast,
    at_most: atMost,
    within_days: wholeNumber("within_days", body.within_days, 1),
  };
}

function trait(body: unknown, personaName: string): TraitCondition {
  if (!isRecord(body)) throw new PlgkitError(`${personaName} trait must be a mapping.`);
  const unknown = Object.keys(body).filter((key) => !TRAIT_KEYS.has(key)).sort();
  if (unknown.length > 0) throw new PlgkitError(`Unknown trait key: ${unknown.join(", ")}.`);
  const key = body.key;
  if (typeof key !== "string" || key.trim() === "") throw new PlgkitError(`${personaName} trait key is required.`);
  if (typeof body.equals !== "string") throw new PlgkitError(`${personaName} trait equals must be a string.`);
  return { kind: "trait", key: key.trim(), equals: body.equals };
}

function wholeNumber(name: string, value: unknown, minimum: number | null): number {
  if (typeof value === "string" && /^-?\d+$/.test(value)) value = Number(value);
  if (typeof value === "boolean" || typeof value !== "number" || !Number.isInteger(value)) {
    throw new PlgkitError(`${name} must be a whole number.`);
  }
  if (minimum != null && value < minimum) {
    if (minimum === 1) throw new PlgkitError(`${name} must be a whole number of 1 or more.`);
    throw new PlgkitError(`${name} must be a whole number of 0 or more.`);
  }
  return value;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
