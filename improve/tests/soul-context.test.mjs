import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { createHash } from "node:crypto";

import {
  defaultSoulPath,
  resolveSoulPath,
  readSoulSnapshot,
  SOUL_SNAPSHOT_MAX_CHARS,
} from "../src/soul.js";
import { buildSynthesisPrompt } from "../src/synthesize.js";
import { renderAnnotatePrompt } from "../src/annotate.js";
import { runPipeline } from "../src/pipeline.js";
import { runSynthesizeResume } from "../src/synthesize-resume.js";

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "ca-ctx-"));
}

function repoRoot() {
  return path.resolve(path.dirname(new URL(import.meta.url).pathname), "..", "..");
}

function seedResumeState() {
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

function homeWithTranscripts(n = 2) {
  const home = tmpDir();
  const dir = path.join(home, ".codex", "sessions");
  fs.mkdirSync(dir, { recursive: true });
  for (let i = 0; i < n; i += 1) {
    const payload = JSON.stringify({ role: "user", text: `bootstrap context please ${i}` });
    const tools = ["read", "search", "test"].map((name) =>
      JSON.stringify({ kind: "tool", name, input: { name } }),
    );
    fs.writeFileSync(path.join(dir, `2026-01-0${i + 1}T00-00-00Z.jsonl`), `${[payload, ...tools].join("\n")}\n`, "utf8");
  }
  return home;
}

const GAP_QUOTE = "sessions re-derive project context from scratch";

function gapEvidence() {
  return {
    status: "ok",
    positive: [],
    negative: [],
    gaps: [
      {
        proposedInstruction: "Bootstrap context once",
        mistake: GAP_QUOTE,
        quote: GAP_QUOTE,
        recurrenceRisk: "every new session pays the same cost",
      },
    ],
  };
}

describe("active SOUL contextualization", () => {
  it("canonical default resolves to repo-root SOUL.md independent of CWD", () => {
    const expected = path.join(repoRoot(), "workspaces", "alignment", "artifacts", "SOUL.md");
    assert.equal(defaultSoulPath(), expected);
    const cwd = process.cwd();
    try {
      process.chdir(os.tmpdir());
      assert.equal(defaultSoulPath(), expected);
    } finally {
      process.chdir(cwd);
    }
  });

  it("explicit --soul-path overrides the canonical default", () => {
    const custom = path.join(tmpDir(), "CUSTOM_SOUL.md");
    fs.writeFileSync(custom, "# custom\n", "utf8");
    assert.equal(resolveSoulPath(custom), path.resolve(custom));
    assert.equal(resolveSoulPath(null), defaultSoulPath());
  });

  it("missing SOUL snapshot fails closed", () => {
    assert.throws(
      () => readSoulSnapshot(path.join(tmpDir(), "missing-SOUL.md")),
      /SOUL/,
    );
  });

  it("empty SOUL snapshot fails closed", () => {
    const empty = path.join(tmpDir(), "empty-SOUL.md");
    fs.writeFileSync(empty, "   \n", "utf8");
    assert.throws(() => readSoulSnapshot(empty), /SOUL/);
  });

  it("snapshot carries bounded text plus stable sha256", () => {
    const snap = readSoulSnapshot(null);
    const full = fs.readFileSync(defaultSoulPath(), "utf8");
    assert.equal(snap.sha256, createHash("sha256").update(full).digest("hex"));
    assert.ok(snap.text.length <= SOUL_SNAPSHOT_MAX_CHARS);
    assert.ok(snap.text.length > 0);
    assert.equal(snap.chars, full.length);
  });

  it("synthesis prompt carries SOUL text and hash with baseline non-conflict", () => {
    const snap = readSoulSnapshot(null);
    const prompt = buildSynthesisPrompt(
      { clusters: [] },
      {
        evidenceIndex: new Map(),
        soulSnapshot: snap.text,
        soulSha256: snap.sha256,
      },
    );
    assert.ok(prompt.includes(snap.text.slice(0, 64)));
    assert.ok(prompt.includes(snap.sha256));
    assert.match(prompt, /non-conflict|must not conflict/i);
  });

  it("annotation prompt carries SOUL text and hash with tension/counterevidence", () => {
    const snap = readSoulSnapshot(null);
    const prompt = renderAnnotatePrompt([], {
      runId: "run-SOUL",
      soulSnapshot: snap.text,
      soulSha256: snap.sha256,
    });
    assert.ok(prompt.includes(snap.text.slice(0, 64)));
    assert.ok(prompt.includes(snap.sha256));
    assert.match(prompt, /tension|counterevidence/i);
  });

  it("improve-run proposal carries soul provenance and never writes SOUL", async () => {
    const home = homeWithTranscripts(2);
    const stateDir = tmpDir();
    const soulFile = defaultSoulPath();
    const before = fs.readFileSync(soulFile, "utf8");
    const proposal = await runPipeline({
      home,
      stateDir,
      analyzer: "mock",
      analyzeInvoke: () => ({ status: "ok", evidence: gapEvidence() }),
      consolidateInvoke: () => ({ status: "ok", result: { merges: [] } }),
    });
    assert.ok(proposal.soul);
    assert.equal(proposal.soul.path, soulFile);
    assert.equal(proposal.soul.sha256, createHash("sha256").update(before).digest("hex"));
    assert.equal(proposal.soul.chars, before.length);
    assert.equal(fs.readFileSync(soulFile, "utf8"), before);
  });

  it("improve-run fails closed when the default SOUL is unavailable", async () => {
    const home = homeWithTranscripts(2);
    const stateDir = tmpDir();
    await assert.rejects(
      () =>
        runPipeline({
          home,
          stateDir,
          analyzer: "mock",
          soulPath: path.join(tmpDir(), "missing-SOUL.md"),
          analyzeInvoke: () => ({ status: "ok", evidence: gapEvidence() }),
          consolidateInvoke: () => ({ status: "ok", result: { merges: [] } }),
        }),
      /SOUL/,
    );
    assert.ok(!fs.existsSync(path.join(stateDir, "proposal.json")));
  });

  it("improve-synthesize proposal carries soul provenance", async () => {
    const { stateDir, quote } = seedResumeState();
    const soulFile = defaultSoulPath();
    const before = fs.readFileSync(soulFile, "utf8");
    const { buildMockFinalAnnotation } = await import("../src/annotate.js");
    const proposal = await runSynthesizeResume({
      stateDir,
      consolidateInvoke: () => ({ status: "ok", result: { merges: [] } }),
      synthesizeInvoke: (args) => {
        const cluster = (args?.ledger?.clusters || []).find((c) => c.eligible);
        const cwd = args?.cwd || args?.workspace;
        fs.writeFileSync(
          path.join(String(cwd), `${cluster.id}.md`),
          `---\nclusterId: ${cluster.id}\nprovisionalSources:\n${cluster.sources.map((s) => `  - ${s}`).join("\n")}\n---\n# ${cluster.proposedInstruction}\n\nRecurring gap.\n`,
          "utf8",
        );
        return { status: "ok", result: "edit-turn" };
      },
      annotateInvoke: (args) => {
        if (args?.stage === "annotate-preface") return { status: "ok", ready: true };
        return {
          status: "ok",
          annotations: (args?.staged || []).map((p) =>
            buildMockFinalAnnotation(p, {
              ledger: args?.ledger,
              evidenceIndex: new Map([
                ["s1", [{ quote, effect: "made progress" }]],
                ["s2", [{ quote, effect: "made progress" }]],
              ]),
            }),
          ),
        };
      },
    });
    assert.ok(proposal.soul);
    assert.equal(proposal.soul.sha256, createHash("sha256").update(before).digest("hex"));
    assert.equal(fs.readFileSync(soulFile, "utf8"), before);
  });

  it("improve-synthesize fails closed when SOUL is unavailable", async () => {
    const { stateDir } = seedResumeState();
    await assert.rejects(
      () =>
        runSynthesizeResume({
          stateDir,
          soulPath: path.join(tmpDir(), "missing-SOUL.md"),
        }),
      /SOUL/,
    );
  });

  it("improvement runtime never writes SOUL", () => {
    const forbidden = ["writeFileSync(SOUL", "writeFileSync(soul", "SOUL.md\", \"w", "SOUL.md', 'w"];
    for (const file of ["soul.js", "pipeline.js", "synthesize-resume.js", "synthesize.js", "annotate.js", "stage.js"]) {
      const src = fs.readFileSync(new URL(`../src/${file}`, import.meta.url), "utf8");
      for (const pattern of forbidden) {
        assert.ok(!src.includes(pattern), `${file} must never write SOUL (${pattern})`);
      }
    }
  });
});
