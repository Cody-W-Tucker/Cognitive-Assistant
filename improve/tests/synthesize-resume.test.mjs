import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

import { runSynthesizeResume } from "../src/synthesize-resume.js";
import { buildMockFinalAnnotation } from "../src/annotate.js";

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "ca-resume-"));
}

function seedState() {
  const stateDir = tmpDir();
  fs.mkdirSync(path.join(stateDir, "evidence"), { recursive: true });
  const quote = "sessions re-derive project context from scratch";
  for (const id of ["s1", "s2"]) {
    fs.writeFileSync(
      path.join(stateDir, "evidence", `${id}.json`),
      `${JSON.stringify({
        transcriptId: id,
        harness: "codex",
        status: "ok",
        positive: [{ quote, effect: "made progress" }],
        negative: [],
        gaps: [
          {
            proposedInstruction: "Bootstrap context once",
            mistake: quote,
            quote,
            recurrenceRisk: "every session pays",
          },
        ],
      })}\n`,
      "utf8",
    );
  }
  const cluster = {
    id: "g-abc",
    proposedInstruction: "Bootstrap context once",
    representativeQuote: quote,
    mistake: quote,
    sources: ["s1", "s2"],
    count: 2,
    eligible: true,
    perSource: {
      s1: { quote, mistake: quote },
      s2: { quote, mistake: quote },
    },
  };
  fs.writeFileSync(
    path.join(stateDir, "ledger.json"),
    `${JSON.stringify({ version: 1, minGapEvidence: 2, clusters: [cluster] }, null, 2)}\n`,
    "utf8",
  );
  return { stateDir, cluster, quote };
}

describe("improve-synthesize resume-only pipeline", () => {
  it("reuses saved evidence+ledger into a synthesis+annotation proposal without discovery/analysis", async () => {
    const { stateDir } = seedState();
    const proposal = await runSynthesizeResume({
      stateDir,
      consolidateInvoke: () => ({ status: "ok", result: { merges: [] } }),
      synthesizeInvoke: (args) => {
        const ledger = args?.ledger;
        const cluster = (ledger?.clusters || []).find((c) => c.eligible);
        assert.ok(cluster);
        const cwd = args?.cwd || args?.workspace;
        assert.ok(cwd);
        const body = `---\nclusterId: ${cluster.id}\nprovisionalSources:\n${cluster.sources.map((s) => `  - ${s}`).join("\n")}\n---\n# ${cluster.proposedInstruction}\n\nRecurring gap: ${cluster.proposedInstruction}\n`;
        fs.writeFileSync(path.join(String(cwd), `${cluster.id}.md`), body, "utf8");
        return { status: "ok", result: "edit-turn" };
      },
      annotateInvoke: (args) => {
        if (args?.stage === "annotate-preface") return { status: "ok", ready: true };
        const staged = args?.staged || [];
        return {
          status: "ok",
          annotations: staged.map((p) =>
            buildMockFinalAnnotation(p, {
              ledger: args?.ledger,
              evidenceIndex: new Map([
                ["s1", [{ quote: "sessions re-derive project context from scratch", effect: "made progress" }]],
                ["s2", [{ quote: "sessions re-derive project context from scratch", effect: "made progress" }]],
              ]),
            }),
          ),
        };
      },
    });
    assert.ok(proposal.edits.length >= 1);
    assert.equal(proposal.edits[0].annotation.verdict, "keep");
    assert.ok(proposal.edits[0].record);
    assert.ok(fs.existsSync(path.join(stateDir, "proposal.json")));
    assert.ok(fs.existsSync(path.join(stateDir, "measured-changes.json")));
  });

  it("consolidates only if required: single gap skips with a visible note", async () => {
    const { stateDir } = seedState();
    let consolidateCalls = 0;
    const proposal = await runSynthesizeResume({
      stateDir,
      consolidateInvoke: () => {
        consolidateCalls += 1;
        return { status: "ok", result: { merges: [] } };
      },
      synthesizeInvoke: (args) => {
        const cluster = (args?.ledger?.clusters || []).find((c) => c.eligible);
        const cwd = args?.cwd || args?.workspace;
        fs.writeFileSync(
          path.join(String(cwd), `${cluster.id}.md`),
          `---\nclusterId: ${cluster.id}\nprovisionalSources:\n${cluster.sources.map((s) => `  - ${s}`).join("\n")}\n---\n# ${cluster.proposedInstruction}\n\nx\n`,
          "utf8",
        );
        return { status: "ok", result: "ok" };
      },
      annotateInvoke: (args) => {
        if (args?.stage === "annotate-preface") return { status: "ok", ready: true };
        return {
          status: "ok",
          annotations: (args?.staged || []).map((p) =>
            buildMockFinalAnnotation(p, {
              ledger: args?.ledger,
              evidenceIndex: new Map([
                ["s1", [{ quote: "sessions re-derive project context from scratch", effect: "x" }]],
                ["s2", [{ quote: "sessions re-derive project context from scratch", effect: "x" }]],
              ]),
            }),
          ),
        };
      },
    });
    assert.equal(consolidateCalls, 0, "single gap must skip the judged call (consolidate only if required)");
    assert.match(String(proposal.consolidation.note || ""), /fewer than two|lexical|no valid merges/i);
  });

  it("absent state fails closed with an actionable error", async () => {
    await assert.rejects(
      () => runSynthesizeResume({ stateDir: path.join(tmpDir(), "missing") }),
      /no successful evidence|improve-run/,
    );
  });

  it("corrupt ledger fails closed with an actionable error", async () => {
    const stateDir = tmpDir();
    fs.mkdirSync(path.join(stateDir, "evidence"), { recursive: true });
    fs.writeFileSync(
      path.join(stateDir, "evidence", "s1.json"),
      `${JSON.stringify({ transcriptId: "s1", status: "ok", positive: [], gaps: [] })}\n`,
      "utf8",
    );
    fs.writeFileSync(path.join(stateDir, "ledger.json"), "{not-json", "utf8");
    await assert.rejects(
      () => runSynthesizeResume({ stateDir }),
      /ledger|improve-run/,
    );
  });

  it("RED: default-judged resume consolidation receives an existing persisted promptFile with no pre-eligibility state writes", async () => {
    const stateDir = tmpDir();
    fs.mkdirSync(path.join(stateDir, "evidence"), { recursive: true });
    const quoteA = "sessions re-derive project context from scratch";
    const quoteB = "sessions never record why a fix was chosen";
    const ev = (id, quote) => ({
      transcriptId: id,
      harness: "codex",
      status: "ok",
      positive: [{ quote, effect: "made progress" }],
      negative: [],
      gaps: [{ proposedInstruction: "Instruction for " + quote.slice(0, 12), mistake: quote, quote, recurrenceRisk: "every session pays" }],
    });
    for (const pair of [["s1", quoteA], ["s2", quoteA], ["s3", quoteB], ["s4", quoteB]]) {
      fs.writeFileSync(path.join(stateDir, "evidence", pair[0] + ".json"), JSON.stringify(ev(pair[0], pair[1])) + "\n", "utf8");
    }
    const mkCluster = (id, quote, sources) => ({
      id,
      proposedInstruction: "Instruction for " + quote.slice(0, 12),
      representativeQuote: quote,
      mistake: quote,
      sources,
      count: sources.length,
      eligible: true,
      perSource: Object.fromEntries(sources.map((s) => [s, { quote, mistake: quote }])),
    });
    const clusters = [mkCluster("g-aaa", quoteA, ["s1", "s2"]), mkCluster("g-bbb", quoteB, ["s3", "s4"])];
    fs.writeFileSync(path.join(stateDir, "ledger.json"), JSON.stringify({ version: 1, minGapEvidence: 2, clusters }, null, 2) + "\n", "utf8");
    const ledgerBefore = fs.readFileSync(path.join(stateDir, "ledger.json"), "utf8");
    const openGapsBefore = fs.existsSync(path.join(stateDir, "open-gaps.json"))
      ? fs.readFileSync(path.join(stateDir, "open-gaps.json"), "utf8")
      : null;
    let seen = null;
    let seenLedgerAtInvoke = null;
    let seenOpenAtInvoke = null;
    const proposal = await runSynthesizeResume({
      stateDir,
      consolidateInvoke: (args) => {
        seen = args;
        seenLedgerAtInvoke = fs.readFileSync(path.join(stateDir, "ledger.json"), "utf8");
        seenOpenAtInvoke = fs.existsSync(path.join(stateDir, "open-gaps.json"))
          ? fs.readFileSync(path.join(stateDir, "open-gaps.json"), "utf8")
          : null;
        return { status: "ok", result: { merges: [] } };
      },
      synthesizeInvoke: (args) => {
        const cluster = (args && args.ledger && args.ledger.clusters || []).find((c) => c.eligible);
        assert.ok(cluster);
        const cwd = args.cwd || args.workspace;
        assert.ok(cwd);
        fs.writeFileSync(
          path.join(String(cwd), cluster.id + ".md"),
          "---\nclusterId: " + cluster.id + "\nprovisionalSources:\n" + cluster.sources.map((s) => "  - " + s).join("\n") + "\n---\n# " + cluster.proposedInstruction + "\n\nRecurring gap.\n",
          "utf8",
        );
        return { status: "ok", result: "edit-turn" };
      },
      annotateInvoke: (args) => {
        if (args && args.stage === "annotate-preface") return { status: "ok", ready: true };
        return {
          status: "ok",
          annotations: (args.staged || []).map((pl) =>
            buildMockFinalAnnotation(pl, {
              ledger: args.ledger,
              evidenceIndex: new Map([
                ["s1", [{ quote: quoteA, effect: "made progress" }]],
                ["s2", [{ quote: quoteA, effect: "made progress" }]],
                ["s3", [{ quote: quoteB, effect: "made progress" }]],
                ["s4", [{ quote: quoteB, effect: "made progress" }]],
              ]),
            }),
          ),
        };
      },
    });
    assert.ok(seen, "judged consolidation must run with >=2 gaps (not skip)");
    assert.ok(seen && seen.promptFile, "resume consolidation must supply an existing persisted promptFile to ACPX (got null with persist:false)");
    assert.ok(fs.existsSync(String(seen.promptFile)), "persisted consolidate promptFile must exist");
    assert.equal(seenLedgerAtInvoke, ledgerBefore, "resume must not write ledger state before eligibility");
    assert.equal(seenOpenAtInvoke, openGapsBefore, "resume must not write open-gap state before eligibility");
    assert.ok(proposal);
  });

  it("workspace Markdown frontmatter provenance travels through annotation to the final proposal", async () => {
    const seed = seedState();
    const stateDir = seed.stateDir;
    const cluster = seed.cluster;
    const quote = seed.quote;
    const workspaceBody = "---\nclusterId: " + cluster.id + "\nprovisionalSources:\n" + cluster.sources.map((s) => "  - " + s).join("\n") + "\n---\n# " + cluster.proposedInstruction + "\n\nRecurring gap: " + cluster.proposedInstruction + "\n";
    const captured = {};
    const proposal = await runSynthesizeResume({
      stateDir,
      consolidateInvoke: () => ({ status: "ok", result: { merges: [] } }),
      synthesizeInvoke: (args) => {
        const cwd = args.cwd || args.workspace;
        assert.ok(cwd);
        fs.writeFileSync(path.join(String(cwd), cluster.id + ".md"), workspaceBody, "utf8");
        return { status: "ok", result: "edit-turn" };
      },
      annotateInvoke: (args) => {
        if (args && args.stage === "annotate-preface") return { status: "ok", ready: true };
        captured.staged = args.staged || [];
        captured.measuredChanges = args.measuredChanges || [];
        const staged = args.staged || [];
        return {
          status: "ok",
          annotations: staged.map((pl) =>
            buildMockFinalAnnotation(pl, {
              ledger: args.ledger,
              evidenceIndex: new Map([
                ["s1", [{ quote, effect: "made progress" }]],
                ["s2", [{ quote, effect: "made progress" }]],
              ]),
            }),
          ),
        };
      },
    });
    const measured = JSON.parse(fs.readFileSync(path.join(stateDir, "measured-changes.json"), "utf8"));
    assert.ok(Array.isArray(measured.changes) && measured.changes.length >= 1, "workspace file must be measured");
    const m0 = measured.changes[0];
    assert.equal(String(m0.clusterId), cluster.id, "measured change must carry workspace clusterId");
    assert.deepEqual((m0.provisionalSources || m0.sources || []).map(String).sort(), cluster.sources.map(String).sort());
    assert.ok(String(m0.text || "").includes("clusterId: " + cluster.id), "measured text must be the workspace file");
    assert.ok(Array.isArray(captured.staged) && captured.staged.length >= 1, "annotation must receive staged candidates");
    assert.equal(String(captured.staged[0].clusterId), cluster.id, "staged candidate must carry workspace clusterId into annotation");
    assert.deepEqual((captured.staged[0].provisionalSources || []).map(String).sort(), cluster.sources.map(String).sort());
    assert.ok(proposal.edits.length >= 1);
    const e0 = proposal.edits[0];
    assert.equal(String(e0.clusterId || (e0.record && e0.record.clusterId)), cluster.id);
    assert.deepEqual(((e0.record && e0.record.sources) || []).map(String).sort(), cluster.sources.map(String).sort());
    assert.ok(String((e0.annotation && e0.annotation.reason) || e0.rationale || "").length > 0);
  });

  it("never imports discovery/export/analysis entry points", async () => {
    const src = fs.readFileSync(new URL("../src/synthesize-resume.js", import.meta.url), "utf8");
    for (const forbidden of [
      "discoverTranscripts",
      "readOpencodeExport",
      "analyzeTraces",
      "mockInvoke",
      "assertAcpxAvailable",
    ]) {
      assert.ok(!src.includes(forbidden), `resume must not reference ${forbidden}`);
    }
  });
});
