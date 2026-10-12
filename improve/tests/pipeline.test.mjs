import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

import { runPipeline } from "../src/pipeline.js";
import { synthesizeWithAcpx } from "../src/synthesize.js";
import { consolidateLedger } from "../src/consolidate.js";

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "ca-pipe-"));
}

function homeWithTranscripts(n = 2) {
  const home = tmpDir();
  const dir = path.join(home, ".codex", "sessions");
  fs.mkdirSync(dir, { recursive: true });
  for (let i = 0; i < n; i += 1) {
    const payload = JSON.stringify({ role: "user", text: `bootstrap context please ${i}` });
    fs.writeFileSync(path.join(dir, `2026-01-0${i + 1}T00-00-00Z.jsonl`), `${payload}\n`, "utf8");
  }
  return home;
}

const GAP_QUOTE = "sessions re-derive project context from scratch";
const GAP_QUOTE_B = "sessions never record why a fix was chosen";

/** Same gap sightings for every trace so the fold floor is met twice. */
function gapEvidence() {
  const gap = (quote) => ({
    proposedInstruction: quote === GAP_QUOTE ? "Bootstrap context once" : "Record why a fix was chosen",
    mistake: quote,
    quote,
    recurrenceRisk: "every new session pays the same cost",
  });
  return { status: "ok", positive: [], negative: [], gaps: [gap(GAP_QUOTE), gap(GAP_QUOTE_B)] };
}

/** Build a strictly valid candidate from the actual folded ledger. */
function candidateForLedger(ledger) {
  const cluster = (ledger?.clusters || []).find((c) => c.eligible);
  assert.ok(cluster, "ledger must hold an eligible cluster");
  assert.ok(cluster.sources.length >= 2);
  return {
    record: {
      title: cluster.proposedInstruction,
      body: `Recurring gap seen in ${cluster.count} session(s): ${cluster.mistake}`,
      clusterId: cluster.id,
      sources: [...cluster.sources],
      evidence: cluster.sources.map((source) => ({
        polarity: "negative",
        text: (cluster.perSource || {})[source]?.quote || cluster.representativeQuote,
        source,
        effect: cluster.mistake,
      })),
      counterevidence: "none observed",
      compilerImplication: "compiler appends this record to the experience block",
    },
  };
}

describe("pipeline production wiring (injectable invokes, no real acpx)", () => {
  it("production success persists prompts + proposal notes with injected invokes", async () => {
    const home = homeWithTranscripts(2);
    const stateDir = tmpDir();
    const proposal = await runPipeline({
      home,
      stateDir,
      analyzer: "acpx",
      runId: "run-PIPE1",
      analyzeInvoke: () => ({ status: "ok", evidence: gapEvidence() }),
      consolidateInvoke: () => ({ status: "ok", result: { merges: [] } }),
      synthesizeInvoke: ({ ledger }) => ({ status: "ok", result: { candidates: [candidateForLedger(ledger)] } }),
    });
    assert.equal(proposal.edits.length, 1);
    assert.ok(fs.existsSync(path.join(stateDir, "prompts", "run-PIPE1__consolidate.md")));
    assert.ok(fs.existsSync(path.join(stateDir, "prompts", "run-PIPE1__synthesis.md")));
    assert.ok(Array.isArray(proposal.notes));
    assert.equal(proposal.synthesis.failed, false);
  });

  it("production synthesis failure yields no edits plus a visible proposal note", async () => {
    const home = homeWithTranscripts(2);
    const stateDir = tmpDir();
    const proposal = await runPipeline({
      home,
      stateDir,
      analyzer: "acpx",
      runId: "run-PIPE2",
      analyzeInvoke: () => ({ status: "ok", evidence: gapEvidence() }),
      consolidateInvoke: () => ({ status: "failed", error: "boom-consolidate" }),
      synthesizeInvoke: () => ({ status: "failed", error: "boom-synth" }),
    });
    assert.deepEqual(proposal.edits, []);
    assert.equal(proposal.synthesis.failed, true);
    assert.ok(typeof proposal.synthesis.note === "string" && proposal.synthesis.note.length > 0);
    assert.ok(proposal.notes.some((n) => /boom-synth|fail/i.test(n)));
  });

  it("prompt persistence failure surfaces a visible proposal/run note", async () => {
    const blocker = path.join(tmpDir(), "blocker");
    fs.writeFileSync(blocker, "x", "utf8");
    const badState = path.join(blocker, "nope");
    const ledger = {
      version: 1,
      minGapEvidence: 2,
      clusters: [
        {
          id: "g-a",
          proposedInstruction: "Bootstrap context once",
          representativeQuote: GAP_QUOTE,
          mistake: "m",
          sources: ["s1", "s2"],
          count: 2,
          eligible: true,
          perSource: { s1: { quote: GAP_QUOTE, mistake: "m" }, s2: { quote: GAP_QUOTE, mistake: "m" } },
        },
        {
          id: "g-b",
          proposedInstruction: "Do another thing",
          representativeQuote: GAP_QUOTE,
          mistake: "m",
          sources: ["s1", "s2"],
          count: 2,
          eligible: true,
          perSource: { s1: { quote: GAP_QUOTE, mistake: "m" }, s2: { quote: GAP_QUOTE, mistake: "m" } },
        },
      ],
    };
    const synth = synthesizeWithAcpx(ledger, {
      evidenceIndex: new Map(),
      invoke: ({ ledger: led }) => ({ status: "ok", candidates: [candidateForLedger(led)] }),
      stateDir: badState,
      runId: "run-PP1",
    });
    assert.equal(synth.edits.length, 1);
    assert.ok(/persistence failed/i.test(synth.note || ""));
    const cons = consolidateLedger(ledger, {
      invoke: () => ({ status: "ok", merges: [] }),
      stateDir: badState,
      runId: "run-PP2",
    });
    assert.ok(/persistence failed/i.test(cons.note || ""));
  });
});
