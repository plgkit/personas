/** Action names to the three shared categories. */
import fs from "node:fs";
import path from "node:path";

import { PlgkitError } from "./errors.ts";
import { readFlat } from "./flat.ts";

export const CATEGORIES = ["core_action", "invite_sent", "setup_step"] as const;
export type Category = (typeof CATEGORIES)[number];

const CATEGORY_SET = new Set<string>(CATEGORIES);

export function defaultMappingPath(): string | null {
  const candidate = path.join(process.cwd(), "plgkit", "personas", "mapping.yml");
  return fs.existsSync(candidate) ? candidate : null;
}

export function loadMapping(filePath?: string | null): Record<string, Category> {
  const resolved = filePath === undefined || filePath === null ? defaultMappingPath() : filePath;
  if (!resolved) return {};
  return normalizeMapping(readFlat(resolved));
}

export function normalizeMapping(mapping: unknown): Record<string, Category> {
  if (mapping == null) return {};
  if (typeof mapping !== "object" || Array.isArray(mapping)) {
    throw new PlgkitError("mapping must be an object of action to category.");
  }
  const cleaned: Record<string, Category> = {};
  for (const [action, category] of Object.entries(mapping)) {
    if (action.trim() === "") throw new PlgkitError("mapping actions must be non-empty strings.");
    if (typeof category !== "string" || !CATEGORY_SET.has(category)) {
      const shown = typeof category === "string" ? `'${category}'` : JSON.stringify(category);
      throw new PlgkitError(`${action} maps to ${shown}. Use one of: ${CATEGORIES.join(", ")}.`);
    }
    cleaned[action] = category as Category;
  }
  return cleaned;
}
