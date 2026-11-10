/** Policy numbers from plgkit/personas/config.yml. */
import fs from "node:fs";
import path from "node:path";

import { PlgkitError } from "./errors.ts";
import { readFlat } from "./flat.ts";

export const DEFAULT_POLICY = {
  lookback_days: 14,
  silence_days: 7,
  champion_min: 1,
  power_user_min: 8,
  implementer_min: 2,
};

export type Policy = typeof DEFAULT_POLICY;

const POLICY_KEYS = Object.keys(DEFAULT_POLICY) as (keyof Policy)[];
const FILE_KEYS = new Set<string>([...POLICY_KEYS, "database_url_env"]);

export function defaultConfigPath(): string | null {
  const candidate = path.join(process.cwd(), "plgkit", "personas", "config.yml");
  return fs.existsSync(candidate) ? candidate : null;
}

export function loadPolicy(filePath?: string | null): Policy {
  const resolved = filePath === undefined || filePath === null ? defaultConfigPath() : filePath;
  if (!resolved) return normalizePolicy(null);
  const raw = readFlat(resolved);
  const unknown = Object.keys(raw).filter((key) => !FILE_KEYS.has(key)).sort();
  if (unknown.length > 0) throw new PlgkitError(`Unknown config key: ${unknown.join(", ")}.`);
  const values: Record<string, unknown> = {};
  for (const key of POLICY_KEYS) {
    if (Object.hasOwn(raw, key)) values[key] = raw[key];
  }
  return normalizePolicy(values);
}

export function normalizePolicy(policy: unknown): Policy {
  const merged: Policy = { ...DEFAULT_POLICY };
  const source = policy ?? {};
  if (!isRecord(source)) throw new PlgkitError("config must be an object of policy numbers.");
  const unknown = Object.keys(source).filter((key) => !POLICY_KEYS.includes(key as keyof Policy)).sort();
  if (unknown.length > 0) throw new PlgkitError(`Unknown config key: ${unknown.join(", ")}.`);
  for (const key of POLICY_KEYS) {
    if (Object.hasOwn(source, key)) merged[key] = positiveInt(key, source[key]);
  }
  if (merged.silence_days >= merged.lookback_days) {
    throw new PlgkitError("silence_days must be smaller than lookback_days.");
  }
  return merged;
}

function positiveInt(key: string, value: unknown): number {
  let number = value;
  if (typeof number === "string") {
    if (!/^[0-9]+$/.test(number)) throw new PlgkitError(`${key} must be a whole number of 1 or more.`);
    number = Number(number);
  }
  if (typeof number !== "number" || !Number.isInteger(number) || number < 1) {
    throw new PlgkitError(`${key} must be a whole number of 1 or more.`);
  }
  return number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
