/** Read the two sample nudge files. Same shape as messages.py. */

import fs from "node:fs";
import path from "node:path";

export function loadMessages(directory: string): Record<string, unknown>[] {
  return fs
    .readdirSync(directory)
    .filter((name) => name.endsWith(".yml"))
    .sort()
    .map((name) => loadMessage(path.join(directory, name)));
}

export function loadMessage(filePath: string): Record<string, unknown> {
  const data = parseYaml(fs.readFileSync(filePath, "utf8"));
  if (data === null || typeof data !== "object" || Array.isArray(data)) {
    throw new Error(`${path.basename(filePath)} must be a mapping.`);
  }
  const message = data as Record<string, unknown>;
  const name = path.basename(filePath);
  message.id = name.endsWith(".yml") ? name.slice(0, -4) : name;
  return message;
}

export function parseYaml(text: string): unknown {
  const lines = text
    .split(/\r?\n/)
    .filter((raw) => raw.trim() !== "" && !raw.trimStart().startsWith("#"))
    .map((raw) => raw.replace(/\t/g, "    "));
  const [value, index] = parseBlock(lines, 0, 0);
  if (index !== lines.length) throw new Error("Could not read the nudge file.");
  return value;
}

function parseBlock(lines: string[], index: number, indent: number): [unknown, number] {
  if (index >= lines.length) return [{}, index];
  if (content(lines[index]).startsWith("- ")) return parseList(lines, index, indent);
  const mapping: Record<string, unknown> = {};
  while (index < lines.length) {
    if (leading(lines[index]) < indent) break;
    if (leading(lines[index]) !== indent) throw new Error(lines[index]);
    const text = content(lines[index]);
    if (text.startsWith("- ")) break;
    const splitAt = text.indexOf(":");
    if (splitAt <= 0) throw new Error(lines[index]);
    const key = text.slice(0, splitAt).trim();
    const rest = text.slice(splitAt + 1).trim();
    index += 1;
    if (rest === "") {
      if (index < lines.length && leading(lines[index]) > indent) {
        const [child, next] = parseBlock(lines, index, leading(lines[index]));
        mapping[key] = child;
        index = next;
      } else {
        mapping[key] = {};
      }
    } else {
      mapping[key] = scalar(rest);
    }
  }
  return [mapping, index];
}

function parseList(lines: string[], index: number, indent: number): [unknown[], number] {
  const items: unknown[] = [];
  while (index < lines.length) {
    if (leading(lines[index]) < indent) break;
    if (leading(lines[index]) !== indent) throw new Error(lines[index]);
    const text = content(lines[index]);
    if (!text.startsWith("- ")) break;
    items.push(scalar(text.slice(2).trim()));
    index += 1;
  }
  return [items, index];
}

function leading(line: string): number {
  return line.length - line.trimStart().length;
}

function content(line: string): string {
  return line.trim();
}

function scalar(value: string): unknown {
  if (value.length >= 2 && (value[0] === "'" || value[0] === '"') && value[value.length - 1] === value[0]) {
    return value.slice(1, -1);
  }
  if (value === "true") return true;
  if (value === "false") return false;
  if (/^\d+$/.test(value)) return Number(value);
  return value;
}
