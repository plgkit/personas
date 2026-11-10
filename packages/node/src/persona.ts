/** Read the persona row written by calculate. */
import { PlgkitError } from "./errors.ts";
import { requireText, type PersonaResult } from "./judge.ts";
import { getDefaultDb, readSnapshot, type SqlDB } from "./store.ts";

export function persona(userId: unknown, options: { db?: SqlDB | null } = {}): PersonaResult {
  const id = requireText(userId, "user_id");
  const db = options.db ?? getDefaultDb();
  let row: PersonaResult | null;
  try {
    row = readSnapshot(db, id);
  } catch (err) {
    if (err instanceof PlgkitError) throw err;
    throw new PlgkitError("Could not read the persona. Run plgkit-personas migrate.");
  }
  if (!row) {
    return { user_id: id, persona: "", matched: [], reasons: [], calculated_at: "" };
  }
  return row;
}

export function personaIs(userId: unknown, name: unknown, options: { db?: SqlDB | null } = {}): boolean {
  const personaName = requireText(name, "persona");
  return persona(userId, options).persona === personaName;
}
