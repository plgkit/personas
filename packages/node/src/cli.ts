/** `plgkit-personas migrate` creates the persona events table. */
import { PlgkitError } from "./errors.ts";
import { migrate } from "./store.ts";

export function main(argv = process.argv.slice(2)): number {
  if (argv.length === 0 || argv[0] === "-h" || argv[0] === "--help") {
    usage();
    return argv.length === 0 ? 1 : 0;
  }
  if (argv[0] === "migrate") return runMigrate();
  console.error(`Unknown command: ${argv[0]}`);
  usage();
  return 1;
}

function usage(): void {
  console.error("Usage: plgkit-personas migrate");
}

function runMigrate(): number {
  try {
    migrate();
  } catch (err) {
    console.error(err instanceof PlgkitError ? err.message : String(err));
    return 1;
  }
  console.log("Migrations are up to date.");
  return 0;
}

if (process.argv[1] && fileIsCli(process.argv[1])) process.exit(main());

function fileIsCli(file: string): boolean {
  return file.endsWith("cli.ts") || file.endsWith("cli.js");
}
