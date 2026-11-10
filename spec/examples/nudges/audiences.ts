/**
 * Audience checks a nudge can call.
 *
 * Copy this file next to your nudge messages. In an app, import personaIs from
 * "@plgkit/personas" instead of the relative path below. Each function calls
 * personaIs with the persona name from personas.yml.
 *
 *   import { audiences } from "./audiences.ts";
 *   decide("home", { user: { id: userId } }, messages, { audiences });
 */
import { personaIs, type SqlDB } from "../../../packages/node/src/index.ts";

export function bind(options: { db?: SqlDB | null } = {}): Record<string, (ctx: unknown) => boolean> {
  const check = (name: string) => (ctx: unknown) => {
    const userId = userIdOf(ctx);
    if (userId === "") return false;
    return personaIs(userId, name, { db: options.db });
  };
  return {
    persona_is_blocked: check("blocked"),
    persona_is_champion: check("champion"),
  };
}

/** The default database. This is what an app passes to decide(). */
export const audiences = bind();

function userIdOf(ctx: unknown): string {
  if (!isRecord(ctx)) return "";
  const user = ctx.user;
  if (!isRecord(user) || typeof user.id !== "string") return "";
  return user.id;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
