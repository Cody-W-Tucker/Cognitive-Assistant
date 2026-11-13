#!/usr/bin/env node
// CA improvement runtime CLI, called by core/improve.py. Prints exactly one
// JSON proposal on stdout; progress (--tui) and errors go to stderr.

import { runPipeline } from "../src/pipeline.js";
import { runSynthesizeResume } from "../src/resume.js";
import { startTui } from "../src/tui.js";

const USAGE = `usage:
  ca-improve run (--headless|--tui) --state-dir D --soul-path S [--experience-file E] [--posture-path P]
                 [--since 30d] [--analyzer model|mock] [--min-gap-evidence N] [--home H] [--harness X]...
  ca-improve synthesize --state-dir D --soul-path S [--min-gap-evidence N]`;

function parseFlags(args) {
  const flags = { harness: [] };
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--headless" || arg === "--tui") {
      flags[arg.slice(2)] = true;
      continue;
    }
    if (!arg.startsWith("--") || args[i + 1] === undefined) throw new Error(`unexpected argument ${JSON.stringify(arg)}`);
    const name = arg.slice(2);
    const value = args[(i += 1)];
    if (name === "harness") flags.harness.push(value);
    else flags[name] = value;
  }
  for (const required of ["state-dir", "soul-path"]) {
    if (!flags[required]) throw new Error(`--${required} is required`);
  }
  return flags;
}

async function main() {
  const [, , command, ...rest] = process.argv;
  if (command !== "run" && command !== "synthesize") {
    process.stderr.write(`ca-improve: unknown command "${command || ""}"\n${USAGE}\n`);
    return 2;
  }
  let flags;
  try {
    flags = parseFlags(rest);
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
            harnesses: flags.harness.length ? flags.harness : null,
            strictHarnesses: flags.harness.length > 0,
            analyzer,
            minGapEvidence,
            progress: tui?.event,
          })
        : await runSynthesizeResume({
            stateDir: flags["state-dir"],
            soulPath: flags["soul-path"],
            minGapEvidence,
          });
    tui?.stop();
    process.stdout.write(`${JSON.stringify(proposal)}\n`);
    return 0;
  } catch (err) {
    tui?.stop();
    process.stderr.write(`ca-improve ${command}: ${err.message}\n`);
    return 1;
  }
}

process.exitCode = await main();
