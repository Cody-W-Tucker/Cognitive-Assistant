import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import { runSynthesizeResume } from "../src/resume.js";
import { readJson } from "../src/state.js";
import { invokeWith, tmpDir, writeJson, writeSoul } from "./helpers.mjs";

const QUOTE = "sessions re-derive project context from scratch";

function seedState({ clusters } = {}) {
  const root = tmpDir();
  const stateDir = path.join(root, "state");
  for (const id of ["s1", "s2"]) {
    writeJson(path.join(stateDir, "evidence", `${id}.json`), {
      transcriptId: id,
      harness: "codex",
      status: "ok",
      positive: [{ quote: QUOTE, effect: "made progress" }],
      negative: [],
      gaps: [{ proposedInstruction: "Bootstrap context once", mistake: QUOTE, quote: QUOTE }],
    });
  }
  const cluster = {
    id: "g-abc",
    proposedInstruction: "Bootstrap context once",
    representativeQuote: QUOTE,
    mistake: QUOTE,
    sources: ["s1", "s2"],
    count: 2,
    eligible: true,
    perSource: { s1: { quote: QUOTE, mistake: QUOTE }, s2: { quote: QUOTE, mistake: QUOTE } },
  };
  writeJson(path.join(stateDir, "ledger.json"), { version: 1, minGapEvidence: 2, clusters: clusters || [cluster] });
  return { stateDir, soulPath: writeSoul(root) };
}

describe("synthesize (resume from saved state)", () => {
  it("proposes from saved evidence and ledger without analyzing any session", async () => {
    const env = seedState();
    const invoke = invokeWith();
    const proposal = await runSynthesizeResume({ ...env, invoke });
    assert.deepEqual(invoke.calls.map((c) => c.role), ["synthesis", "annotate"]);
    assert.equal(proposal.resume, true);
    assert.equal(proposal.edits.length, 1);
    assert.equal(proposal.edits[0].record.clusterId, "g-abc");
    assert.equal(proposal.stats.transcripts, 2);
    assert.match(proposal.consolidation.note, /fewer than two open gaps/);
    assert.deepEqual(readJson(path.join(env.stateDir, "proposal.json")), proposal);
  });

  it("re-checks eligibility against the requested floor", async () => {
    const env = seedState();
    await assert.rejects(runSynthesizeResume({ ...env, minGapEvidence: 3, invoke: invokeWith() }), /no eligible gap clusters.*floor 3/);
  });

  it("fails with an actionable message when saved state is missing, corrupt, or ineligible", async () => {
    const empty = { stateDir: path.join(tmpDir(), "state"), soulPath: writeSoul(tmpDir()) };
    await assert.rejects(runSynthesizeResume({ ...empty, invoke: invokeWith() }), /no successful evidence.*improve-run/);

    const noLedger = seedState();
    fs.rmSync(path.join(noLedger.stateDir, "ledger.json"));
    await assert.rejects(runSynthesizeResume({ ...noLedger, invoke: invokeWith() }), /no persisted ledger.*improve-run/);

    const corrupt = seedState();
    fs.writeFileSync(path.join(corrupt.stateDir, "ledger.json"), "{not-json");
    await assert.rejects(runSynthesizeResume({ ...corrupt, invoke: invokeWith() }), /corrupt ledger/);

    const ineligible = seedState({ clusters: [] });
    await assert.rejects(runSynthesizeResume({ ...ineligible, invoke: invokeWith() }), /no eligible gap clusters/);
    assert.equal(fs.existsSync(path.join(ineligible.stateDir, "open-gaps.json")), false, "nothing is written before state proves eligible");
    assert.equal(fs.existsSync(path.join(ineligible.stateDir, "proposal.json")), false);
  });

  it("fails without a proposal when the SOUL is missing or empty", async () => {
    const env = seedState();
    await assert.rejects(runSynthesizeResume({ ...env, soulPath: path.join(env.stateDir, "missing.md"), invoke: invokeWith() }), /SOUL/);
    fs.writeFileSync(env.soulPath, "\n\t\n");
    await assert.rejects(runSynthesizeResume({ ...env, invoke: invokeWith() }), /SOUL baseline .* is empty/);
    assert.equal(fs.existsSync(path.join(env.stateDir, "proposal.json")), false);
  });
});
