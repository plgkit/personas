/**
 * Audience checks a nudge can call.
 *
 * Copy this file next to your nudge messages. In an app, import persona from
 * "@plgkit/personas" instead of the relative path below. A message lists one
 * of these names under audience.require_all.
 *
 *   import { audiences } from "./audiences.ts";
 *   decide("home", { user: { id: userId } }, messages, { audiences });
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { loadMapping, loadPolicy, persona, type SqlDB } from "../../../packages/node/src/index.ts";

export function bind(options: {
  db?: SqlDB | null;
  now?: string | null;
  mapping?: Record<string, string> | null;
  policy?: unknown;
} = {}): Record<string, (ctx: unknown) => boolean> {
  const label = (ctx: unknown) => {
    const userId = userIdOf(ctx);
    if (userId === "") return "unknown";
    let mapping = options.mapping;
    let policy = options.policy;
    if (mapping == null || policy == null) {
      const found = fromFiles();
      if (mapping == null) mapping = found.mapping;
      if (policy == null) policy = found.policy;
    }
    return persona(userId, {
      db: options.db,
      now: options.now,
      mapping,
      config: policy,
    }).persona;
  };
  return {
    persona_is_blocked: (ctx) => label(ctx) === "blocked",
    persona_is_champion: (ctx) => label(ctx) === "champion",
  };
}

/** Live clock and the default database. This is what an app passes to decide(). */
export const audiences = bind();

function userIdOf(ctx: unknown): string {
  if (!isRecord(ctx)) return "";
  const user = ctx.user;
  if (!isRecord(user) || typeof user.id !== "string") return "";
  return user.id;
}

function fromFiles(): { mapping: Record<string, string> | null; policy: unknown } {
  const here = path.dirname(fileURLToPath(import.meta.url));
  const app = path.join(process.cwd(), "plgkit", "personas");
  const sample = path.resolve(here, "..");
  const mappingPath = first(path.join(app, "mapping.yml"), path.join(sample, "mapping.yml"));
  const configPath = first(path.join(app, "config.yml"), path.join(sample, "config.yml"));
  return {
    mapping: mappingPath ? loadMapping(mappingPath) : null,
    policy: configPath ? loadPolicy(configPath) : null,
  };
}

function first(...paths: string[]): string | null {
  for (const candidate of paths) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
