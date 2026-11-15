import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { mockInvoke } from "../src/mock.js";
import { fakeLangfuse } from "./fake-langfuse.mjs";

export const QUOTE_A = "alpha quote one";
export const QUOTE_B = "beta quote two";

export function tmpDir(prefix = "ca-improve-") {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

export function writeSoul(dir, text = "# SOUL\n\nBe direct.\n") {
  const file = path.join(dir, "SOUL.md");
  fs.writeFileSync(file, text, "utf8");
  return file;
}

/**
 * A fake Langfuse holding `n` substantial, finished Claude sessions
 * (claude-0 ...), plus a fresh state dir and SOUL.
 */
export function setup(n = 2) {
  const root = tmpDir();
  const langfuse = fakeLangfuse();
  for (let i = 0; i < n; i += 1) langfuse.add("claude", `claude-${i}`);
  return { langfuse, client: langfuse.client, stateDir: path.join(root, "state"), soulPath: writeSoul(root) };
}

/** One eligible cluster (s1, s2) with distinct per-source quotes, plus an ineligible one. */
export function ledger() {
  return {
    version: 1,
    minGapEvidence: 2,
    clusters: [
      {
        id: "g-aaa",
        proposedInstruction: "Bootstrap context once",
        representativeQuote: QUOTE_A,
        mistake: "sessions re-derive context",
        sources: ["s1", "s2"],
        count: 2,
        eligible: true,
        perSource: { s1: { quote: QUOTE_A, mistake: "m" }, s2: { quote: QUOTE_B, mistake: "m" } },
      },
      {
        id: "g-inelig",
        proposedInstruction: "Ineligible thing",
        representativeQuote: "zzz quote",
        mistake: "m-zzz",
        sources: ["sx"],
        count: 1,
        eligible: false,
        perSource: { sx: { quote: "zzz quote", mistake: "m-zzz" } },
      },
    ],
  };
}

export function evidenceIndex() {
  return new Map([
    ["s1", [{ quote: QUOTE_A, effect: "e1" }]],
    ["s2", [{ quote: QUOTE_B, effect: "e2" }]],
    ["s9", [{ quote: "outsider quote nine", effect: "e9" }]],
  ]);
}

export function record(overrides = {}) {
  return {
    id: "exp-bootstrap-context-a1b2c3d4e5f6",
    title: "Bootstrap context once",
    body: "Recurring gap seen in 2 sessions.",
    sources: ["s1", "s2"],
    clusterId: "g-aaa",
    evidence: [
      { polarity: "negative", text: QUOTE_A, source: "s1", effect: "m" },
      { polarity: "negative", text: QUOTE_B, source: "s2", effect: "m" },
    ],
    counterevidence: "none observed",
    compilerImplication: "compiler appends this record to the experience block",
    ...overrides,
  };
}

export const plan = (overrides = {}) => ({
  id: "e1",
  kind: "add",
  clusterId: "g-aaa",
  provisionalIntent: "Bootstrap context once",
  provisionalSources: ["s1", "s2"],
  provisionalCount: 2,
  ...overrides,
});

/** The mock invoke with some roles replaced; records every call. */
export function invokeWith(overrides = {}) {
  const calls = [];
  const invoke = async (role, prompt, context) => {
    calls.push({ role, prompt });
    return overrides[role] ? overrides[role](context, prompt) : mockInvoke(role, prompt, context);
  };
  invoke.calls = calls;
  return invoke;
}
