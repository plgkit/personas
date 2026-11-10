/** Read the small YAML shape used by personas.yml. */
import { PlgkitError } from "./errors.ts";

export function parseYaml(text: string): unknown {
  const lines = text
    .split(/\r?\n/)
    .filter((raw) => raw.trim() !== "" && !raw.trimStart().startsWith("#"))
    .map((raw) => raw.replace(/\t/g, "    "));
  if (lines.length === 0) return {};
  const [value, index] = parseBlock(lines, 0, 0);
  if (index !== lines.length) throw new PlgkitError("Could not read personas.yml.");
  return value;
}

function parseBlock(lines: string[], index: number, indent: number): [unknown, number] {
  if (index >= lines.length) return [{}, index];
  if (content(lines[index]).startsWith("- ")) return parseList(lines, index, indent);
  const mapping: Record<string, unknown> = {};
  while (index < lines.length) {
    if (leading(lines[index]) < indent) break;
    if (leading(lines[index]) !== indent) throw new PlgkitError("Could not read personas.yml.");
    const text = content(lines[index]);
    if (text.startsWith("- ")) break;
    const taken = takePair(lines, index, indent);
    put(mapping, taken.key, taken.value);
    index = taken.index;
  }
  return [mapping, index];
}

function parseList(lines: string[], index: number, indent: number): [unknown[], number] {
  const items: unknown[] = [];
  while (index < lines.length) {
    if (leading(lines[index]) < indent) break;
    if (leading(lines[index]) !== indent) throw new PlgkitError("Could not read personas.yml.");
    const text = content(lines[index]);
    if (!text.startsWith("- ")) break;
    const rest = text.slice(2).trim();
    index += 1;
    if (rest === "") {
      if (index < lines.length && leading(lines[index]) > indent) {
        const [child, next] = parseBlock(lines, index, leading(lines[index]));
        items.push(child);
        index = next;
      } else {
        items.push(null);
      }
      continue;
    }
    if (isKey(rest)) {
      const splitAt = rest.indexOf(":");
      const key = rest.slice(0, splitAt).trim();
      const rawValue = rest.slice(splitAt + 1).trim();
      const mapping: Record<string, unknown> = {};
      if (rawValue === "") {
        if (index < lines.length && leading(lines[index]) > indent) {
          const [child, next] = parseBlock(lines, index, leading(lines[index]));
          mapping[key] = child;
          index = next;
        } else {
          mapping[key] = {};
        }
      } else {
        mapping[key] = scalar(rawValue);
      }
      if (
        index < lines.length &&
        leading(lines[index]) > indent &&
        !content(lines[index]).startsWith("- ")
      ) {
        const [more, next] = parseBlock(lines, index, leading(lines[index]));
        index = next;
        if (isRecord(more)) {
          for (const [itemKey, itemValue] of Object.entries(more)) put(mapping, itemKey, itemValue);
        }
      }
      items.push(mapping);
      continue;
    }
    items.push(scalar(rest));
  }
  return [items, index];
}

function takePair(lines: string[], index: number, indent: number): { key: string; value: unknown; index: number } {
  const text = content(lines[index]);
  if (!isKey(text)) throw new PlgkitError("Could not read personas.yml.");
  const splitAt = text.indexOf(":");
  const key = text.slice(0, splitAt).trim();
  const rawValue = text.slice(splitAt + 1).trim();
  index += 1;
  if (rawValue === "") {
    if (index < lines.length && leading(lines[index]) > indent) {
      const [child, next] = parseBlock(lines, index, leading(lines[index]));
      return { key, value: child, index: next };
    }
    return { key, value: {}, index };
  }
  return { key, value: scalar(rawValue), index };
}

function put(mapping: Record<string, unknown>, key: string, value: unknown): void {
  if (Object.hasOwn(mapping, key)) throw new PlgkitError(`Duplicate key: ${key}.`);
  mapping[key] = value;
}

function isKey(text: string): boolean {
  if (text.startsWith("'") || text.startsWith('"') || text.startsWith("- ")) return false;
  const splitAt = text.indexOf(":");
  return splitAt > 0;
}

function leading(line: string): number {
  return line.length - line.trimStart().length;
}

function content(line: string): string {
  return line.trim();
}

function scalar(value: string): unknown {
  const flow = flowList(value);
  if (flow) return flow;
  if (value.length >= 2 && (value[0] === "'" || value[0] === '"') && value.at(-1) === value[0]) {
    return value.slice(1, -1);
  }
  if (value === "true") return true;
  if (value === "false") return false;
  if (/^-?\d+$/.test(value)) return Number(value);
  return value;
}

function flowList(value: string): unknown[] | null {
  if (!(value.startsWith("[") && value.endsWith("]"))) return null;
  const inner = value.slice(1, -1).trim();
  if (inner === "") return [];
  const parts: string[] = [];
  let buf = "";
  let quote = "";
  for (const char of inner) {
    if (quote) {
      buf += char;
      if (char === quote) quote = "";
      continue;
    }
    if (char === "'" || char === '"') {
      quote = char;
      buf += char;
      continue;
    }
    if (char === ",") {
      parts.push(buf.trim());
      buf = "";
      continue;
    }
    buf += char;
  }
  if (quote) throw new PlgkitError("Could not read personas.yml.");
  parts.push(buf.trim());
  return parts.filter((part) => part !== "").map((part) => scalar(part));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
