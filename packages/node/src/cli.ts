/** `plgkit-personas migrate` and `plgkit-personas calculate`. */
import { calculate } from "./calculate.ts";
import { PlgkitError } from "./errors.ts";
import { migrate } from "./store.ts";

export function main(argv = process.argv.slice(2)): number {
  if (argv.length === 0 || argv[0] === "-h" || argv[0] === "--help") {
    usage();
    return argv.length === 0 ? 1 : 0;
  }
  if (argv[0] === "migrate") {
    if (argv.length !== 1) {
      usage();
      return 1;
    }
    return runMigrate();
  }
  if (argv[0] === "calculate") return runCalculate(argv.slice(1));
  console.error(`Unknown command: ${argv[0]}`);
  usage();
  return 1;
}

function usage(): void {
  console.error("Usage: plgkit-personas migrate");
  console.error("       plgkit-personas calculate [--user ID] [--now TIMESTAMP]");
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

function runCalculate(args: string[]): number {
  let userId: string | null = null;
  let now: string | null = null;
  for (let index = 0; index < args.length; index += 1) {
    const flag = args[index];
    if ((flag === "--user" || flag === "--now") && index + 1 < args.length) {
      if (flag === "--user") userId = args[index + 1]!;
      else now = args[index + 1]!;
      index += 1;
      continue;
    }
    usage();
    return 1;
  }
  try {
    const result = calculate({ userId, now });
    console.log(`Calculated ${result.users} users. ${result.assigned} assigned. ${result.unmatched} unmatched.`);
    return 0;
  } catch (err) {
    console.error(err instanceof PlgkitError ? err.message : String(err));
    return 1;
  }
}

if (process.argv[1] && fileIsCli(process.argv[1])) process.exit(main());

function fileIsCli(file: string): boolean {
  return file.endsWith("cli.ts") || file.endsWith("cli.js");
}
