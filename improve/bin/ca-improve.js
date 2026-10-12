#!/usr/bin/env node
// CA improvement runtime CLI. Narrow JSON boundary for core/improve.py.

import { discoverTranscripts } from "../src/discovery.js";
import { runPipeline } from "../src/pipeline.js";
import { defaultStateDir } from "../src/state.js";

function flagValue(args, name) {
  const index = args.indexOf(name);
  if (index === -1) return null;
  return args[index + 1] ?? null;
}

async function main() {
  const [, , command, ...rest] = process.argv;
  if (command === "discover") {
    const home = flagValue(rest, "--home") || undefined;
    const stateDir = flagValue(rest, "--state-dir") || null;
    const since = flagValue(rest, "--since") || "30d";
    const harnessFlags = rest.filter((arg, i) => rest[i - 1] === "--harness");
    try {
      const result = discoverTranscripts({
        // Absent --home keeps ambient HERMES_HOME/CLAUDE_CONFIG_DIR/CODEX_HOME;
        // an explicit --home scopes every store under it (hermetic runs/tests).
        home: home || undefined,
        stateDir,
        since,
        harnesses: harnessFlags.length ? harnessFlags : null,
      });
      console.log(JSON.stringify(result));
      return 0;
    } catch (err) {
      process.stderr.write(`ca-improve discover: ${err?.message || err}\n`);
      return 2;
    }
  }
  if (command === "run") {
    if (!rest.includes("--headless")) {
      process.stderr.write("ca-improve run: only --headless is supported in this slice\n");
      return 2;
    }
    const home = flagValue(rest, "--home") || undefined;
    const stateDir = flagValue(rest, "--state-dir") || defaultStateDir();
    const since = flagValue(rest, "--since") || "30d";
    const analyzer = flagValue(rest, "--analyzer") || "acpx";
    const soulPath = flagValue(rest, "--soul-path") || null;
    const posturePath = flagValue(rest, "--posture-path") || null;
    const minGapEvidence = Number(flagValue(rest, "--min-gap-evidence") || 2);
    const harnessFlags = rest.filter((arg, i) => rest[i - 1] === "--harness");
    return runPipeline({
      home: home || undefined,
      stateDir,
      since,
      harnesses: harnessFlags.length ? harnessFlags : null,
      analyzer,
      soulPath,
      posturePath,
      minGapEvidence,
    }).then(
      (proposal) => {
        console.log(JSON.stringify(proposal));
        return 0;
      },
      (err) => {
        process.stderr.write(`ca-improve run: ${err?.stack || err?.message || err}\n`);
        return 1;
      },
    );
  }
  process.stderr.write(`ca-improve: unknown command "${command || ""}" (expected: discover, run)\n`);
  return 2;
}

process.exitCode = await main();
