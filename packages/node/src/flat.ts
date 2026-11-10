/** Read a flat `key: value` file. Indentation is rejected. */
import fs from "node:fs";

import { PlgkitError } from "./errors.ts";

export function readFlat(filePath: string): Record<string, string> {
  let text: string;
  try {
    text = fs.readFileSync(filePath, "utf8");
  } catch {
    throw new PlgkitError(`Could not read ${filePath}.`);
  }
  const found: Record<string, string> = {};
  for (const raw of text.split(/\r?\n/)) {
    if (raw.startsWith(" ") || raw.startsWith("\t")) {
      if (raw.trim() !== "") throw new PlgkitError(`${filePath} must be a flat key: value file.`);
      continue;
    }
    const line = (raw.split("#", 1)[0] ?? "").trim();
    if (line === "") continue;
    const colon = line.indexOf(":");
    if (colon < 0) throw new PlgkitError(`${filePath} must be a flat key: value file.`);
    const key = line.slice(0, colon).trim();
    let value = line.slice(colon + 1).trim();
    if (value.length >= 2 && (value[0] === "'" || value[0] === '"') && value[0] === value[value.length - 1]) {
      value = value.slice(1, -1);
    }
    if (key === "") throw new PlgkitError(`${filePath} has an empty key.`);
    if (value === "") throw new PlgkitError(`${key} in ${filePath} needs a value.`);
    if (Object.hasOwn(found, key)) throw new PlgkitError(`${key} is set more than once in ${filePath}.`);
    found[key] = value;
  }
  return found;
}
