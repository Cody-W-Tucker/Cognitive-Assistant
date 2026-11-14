#!/usr/bin/env node
// CA improvement runtime CLI, called by core/improve.py. Prints exactly one
// JSON proposal on stdout; progress (--tui) and errors go to stderr.

import { runOutcome } from "../src/outcome.js";
import { runPipeline } from "../src/pipeline.js";
import { runSynthesizeResume } from "../src/resume.js";
import { startTui } from "../src/tui.js";

const USAGE = `usage:
  ca-improve run (--headless|--tui) --state-dir D --soul-path S [--experience-file E] [--posture-path P]
                 [--since 30d] [--idle-hours 12] [--analyzer model|mock] [--min-gap-evidence N] [--home H] [--harness X]...
  ca-improve synthesize --state-dir D --soul-path S [--min-gap-evidence N]
  ca-improve outcome --state-dir D [--since 70d] [--limit N] [--mature-days 3] [--dry-run] [--rescore] [--home H] [--analyzer model|mock]`;

function parseFlags(args, command) {
  const flags = { harness: [] };
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (["--headless", "--tui", "--dry-run", "--rescore"].includes(arg)) {
      flags[arg.slice(2)] = true;
      continue;
    }
    if (!arg.startsWith("--") || args[i + 1] === undefined) throw new Error(`unexpected argument ${JSON.stringify(arg)}`);
    const name = arg.slice(2);
    const value = args[(i += 1)];
    if (name === "harness") flags.harness.push(value);
    else flags[name] = value;
  }
  for (const required of command === "outcome" ? ["state-dir"] : ["state-dir", "soul-path"]) {
    if (!flags[required]) throw new Error(`--${required} is required`);
  }
  return flags;
}

async function main() {
  const [, , command, ...rest] = process.argv;
  if (command !== "run" && command !== "synthesize" && command !== "outcome") {
    process.stderr.write(`ca-improve: unknown command "${command || ""}"\n${USAGE}\n`);
    return 2;
  }
  let flags;
  try {
    flags = parseFlags(rest, command);
    if (command === "run" && Boolean(flags.headless) === Boolean(flags.tui)) {
      throw new Error("pass exactly one of --headless (JSON only) or --tui (live stderr progress + JSON stdout)");
    }
  } catch (err) {
    process.stderr.write(`ca-improve ${command}: ${err.message}\n${USAGE}\n`);
    return 2;
  }
  const minGapEvidence = flags["min-gap-evidence"] ?? 2;
  const since = flags.since || "30d";
  const analyzer = flags.analyzer || "model";
  const tui = flags.tui ? startTui({ since, analyzer }) : null;
  try {
    const proposal =
      command === "run"
        ? await runPipeline({
            home: flags.home,
            stateDir: flags["state-dir"],
            soulPath: flags["soul-path"],
            posturePath: flags["posture-path"] || null,
            experiencePath: flags["experience-file"] || null,
            since,
            idleHours: flags["idle-hours"] ?? 12,
            harnesses: flags.harness.length ? flags.harness : null,
            strictHarnesses: flags.harness.length > 0,
            analyzer,
            minGapEvidence,
            progress: tui?.event,
          })
        : command === "outcome" ? await runOutcome({ home: flags.home, stateDir: flags["state-dir"], since: flags.since || "all", limit: flags.limit ?? null, matureDays: flags["mature-days"] ?? 3, dryRun: !!flags["dry-run"], rescore: !!flags.rescore, analyzer })
        : await runSynthesizeResume({
            stateDir: flags["state-dir"],
            soulPath: flags["soul-path"],
            minGapEvidence,
          });
    tui?.stop();
    const output = command === "outcome" ? { runId: proposal.runId, preview: proposal.preview, selected: proposal.selected, scored: proposal.scored, unscored: proposal.unscored } : proposal;
    process.stdout.write(`${JSON.stringify(output)}\n`);
    return 0;
  } catch (err) {
    tui?.stop();
    process.stderr.write(`ca-improve ${command}: ${err.message}\n`);
    return 1;
  }
}

process.exitCode = await main();
