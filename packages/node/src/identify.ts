/** Store the latest value of each trait. Traits have no history. */
import { PlgkitError } from "./errors.ts";
import { formatTime, parseTime, requireText } from "./judge.ts";
import { getDefaultDb, upsertTrait, type SqlDB } from "./store.ts";

export function identify(
  userId: unknown,
  traits: unknown,
  options: { db?: SqlDB | null; now?: string | null } = {},
): void {
  const id = requireText(userId, "user_id");
  if (typeof traits !== "object" || traits === null || Array.isArray(traits) || Object.keys(traits).length === 0) {
    throw new PlgkitError("traits must be an object of strings.");
  }
  const moment = options.now != null ? parseTime(options.now) : new Date();
  const cleaned: [string, string][] = [];
  for (const [key, value] of Object.entries(traits)) {
    if (key.trim() === "") throw new PlgkitError("trait keys must be non-empty strings.");
    if (typeof value !== "string") throw new PlgkitError("trait values must be strings.");
    cleaned.push([key.trim(), value]);
  }
  const db = options.db ?? getDefaultDb();
  const stamp = formatTime(moment);
  try {
    for (const [key, value] of cleaned) upsertTrait(db, id, key, value, stamp);
  } catch (err) {
    if (err instanceof PlgkitError) throw err;
    throw new PlgkitError("Could not store traits. Run plgkit-personas migrate.");
  }
}
