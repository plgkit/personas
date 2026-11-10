/** Save one product event. */
import { PlgkitError } from "./errors.ts";
import { formatTime, parseTime, requireText } from "./judge.ts";
import { getDefaultDb, insertEvent, type SqlDB } from "./store.ts";

export function track(
  userId: unknown,
  action: unknown,
  metadata?: unknown,
  options: { db?: SqlDB | null; now?: string | null } = {},
): boolean {
  const id = requireText(userId, "user_id");
  const verb = requireText(action, "action");
  const received = options.now != null ? parseTime(options.now) : new Date();
  const cleaned = cleanMetadata(metadata, received);
  const db = options.db ?? getDefaultDb();
  try {
    return insertEvent(
      db,
      id,
      verb,
      cleaned.eventId,
      cleaned.body,
      formatTime(cleaned.occurred),
      formatTime(received),
    );
  } catch (err) {
    if (err instanceof PlgkitError) throw err;
    throw new PlgkitError("Could not store the event. Run plgkit-personas migrate.");
  }
}

function cleanMetadata(metadata: unknown, received: Date): { body: unknown; eventId: string | null; occurred: Date } {
  if (metadata == null) metadata = {};
  if (typeof metadata !== "object" || Array.isArray(metadata)) throw new PlgkitError("metadata must be an object.");
  let body: Record<string, unknown>;
  try {
    body = JSON.parse(JSON.stringify(sortValue(metadata))) as Record<string, unknown>;
  } catch {
    throw new PlgkitError("metadata must be JSON.");
  }
  const occurredAt = body.occurred_at;
  const eventId = body.event_id;
  delete body.occurred_at;
  delete body.event_id;
  let occurred = received;
  if (occurredAt !== undefined) {
    if (typeof occurredAt !== "string") {
      throw new PlgkitError("occurred_at must be an ISO-8601 timestamp with a timezone.");
    }
    occurred = parseTime(occurredAt);
  }
  if (eventId === undefined || eventId === null) return { body, eventId: null, occurred };
  if (typeof eventId !== "string") throw new PlgkitError("event_id must be a string.");
  const trimmed = eventId.trim();
  return { body, eventId: trimmed === "" ? null : trimmed, occurred };
}

function sortValue(value: unknown): unknown {
  if (value === null || typeof value === "string" || typeof value === "boolean") return value;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new PlgkitError("metadata must be JSON.");
    return value;
  }
  if (Array.isArray(value)) return value.map((item) => sortValue(item));
  if (typeof value === "object") {
    const proto = Object.getPrototypeOf(value);
    if (proto !== Object.prototype && proto !== null) throw new PlgkitError("metadata must be JSON.");
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(value as object).sort()) out[key] = sortValue((value as Record<string, unknown>)[key]);
    return out;
  }
  throw new PlgkitError("metadata must be JSON.");
}
