import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";

import {
  analyzeTraces,
  mockInvoke,
  buildAnalysisPrompt,
  loadDefaultContexts,
  persistPrompt,
} from "../src/analyze.js";
import { SELF_SESSION_SENTINEL } from "../src/sentinel.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ANALYSIS_MD = path.join(HERE, "..", "prompts", "analysis.md");
const NOTICE = path.join(HERE, "..", "LICENSE.NOTICE");

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "ca-analyze-"));
}

function trace(overrides = {}) {
  return {
    transcriptId: "pi-1",
    harness: "pi",
    distilled: "## human\nfix the bug\n\n## agent\nfixed\n",
    ...overrides,
  };
}

describe("analysis.md contract (CA-native, Backpass 0268201 operational source)", () => {
  it("maps exact provenance in LICENSE.NOTICE (prompt carries no license comments)", () => {
    const notice = fs.readFileSync(NOTICE, "utf8");
    assert.ok(notice.includes("Backpass"), "NOTICE must name Backpass");
    assert.ok(notice.includes("0268201"), "NOTICE must pin commit 0268201");
    assert.ok(notice.includes("src/prompts/analysis.md"), "NOTICE must name the upstream module");
    assert.ok(notice.includes("improve/prompts/analysis.md"), "NOTICE must map the CA prompt file");
    const text = fs.readFileSync(ANALYSIS_MD, "utf8");
    assert.ok(!text.includes("Backpass"), "prompt body carries no license comments");
    assert.ok(!text.includes("0268201"), "prompt body carries no pinned commit");
  });

  it("declares exactly the six supported placeholders and nothing else", () => {
    const text = fs.readFileSync(ANALYSIS_MD, "utf8");
    const tokens = [...text.matchAll(/\{\{([A-Za-z0-9_]+)\}\}/g)].map((m) => m[1]);
    const unique = [...new Set(tokens)].sort();
    assert.deepEqual(unique, [
      "EXPERIENCE_RECORDS",
      "HARNESS",
      "INTERACTION_POSTURE",
      "SOUL_BASELINE",
      "TRACE",
      "TRANSCRIPT_ID",
    ]);
  });

  it("does not bake in the sentinel (the loader prepends it FIRST)", () => {
    const text = fs.readFileSync(ANALYSIS_MD, "utf8");
    assert.ok(!text.includes("ca-improve:self-session"), "sentinel lives in the loader, not the file");
  });

  it("audits one distilled trace against SOUL, posture, and accepted experience", () => {
    const text = fs.readFileSync(ANALYSIS_MD, "utf8");
    assert.ok(/SOUL/i.test(text));
    assert.ok(/posture/i.test(text));
    assert.ok(/experience/i.test(text));
    assert.ok(/distilled/i.test(text));
  });

  it("requires strict JSON with positive/negative/gaps/changed_context/usedRawTranscript", () => {
    const text = fs.readFileSync(ANALYSIS_MD, "utf8");
    for (const key of ["positive", "negative", "gaps", "changed_context", "usedRawTranscript"]) {
      assert.ok(text.includes(`"${key}"`), `contract must name ${key}`);
    }
    assert.ok(/verbatim/i.test(text) && /quote/i.test(text), "every observation needs a verbatim trace quote");
  });

  it("distinguishes non-compliance from guidance-caused harm", () => {
    const text = fs.readFileSync(ANALYSIS_MD, "utf8");
    assert.ok(text.includes("non-compliance"));
    assert.ok(text.includes("harm"));
  });

  it("frames gaps as recurring-use experience candidates, never direct SOUL edits", () => {
    const text = fs.readFileSync(ANALYSIS_MD, "utf8");
    assert.ok(/never.*SOUL|not.*SOUL.*edit/i.test(text));
  });
});

describe("default artifact contexts", () => {
  it("degrades explicitly when baselines are absent", () => {
    const contexts = loadDefaultContexts({ repoRoot: tmpDir() });
    for (const key of ["soulBaseline", "interactionPosture", "experienceRecords"]) {
      assert.ok(typeof contexts[key] === "string" && contexts[key].length > 0);
      assert.ok(/unavailable/i.test(contexts[key]), `${key} must say it is unavailable`);
    }
  });

  it("loads the active CA baselines from the real repo root", () => {
    const repoRoot = path.join(HERE, "..", "..");
    const contexts = loadDefaultContexts({ repoRoot });
    assert.ok(!/unavailable/i.test(contexts.soulBaseline), "SOUL.md exists in this repo");
    assert.ok(contexts.soulBaseline.includes("Who I am at rest"));
    assert.ok(!/unavailable/i.test(contexts.interactionPosture));
  });
});

describe("analyzer prompt integration", () => {
  it("builds the model prompt from the checked-in file (no generic inline prompt)", () => {
    const prompt = buildAnalysisPrompt(trace(), {
      soulBaseline: "SOUL-BASELINE",
      interactionPosture: "POSTURE",
      experienceRecords: "RECORDS",
    });
    assert.ok(prompt.startsWith(`${SELF_SESSION_SENTINEL}\n`));
    assert.ok(prompt.includes("SOUL-BASELINE"));
    assert.ok(prompt.includes("## human\nfix the bug"));
    assert.ok(!prompt.includes("return JSON evidence"), "generic inline prompt must be gone");
  });

  it("analyzeTraces passes the rendered prompt to invoke and persists it privately", () => {
    const stateDir = tmpDir();
    let seen = null;
    const invoke = (args) => {
      seen = args;
      return mockInvoke({ trace: args.trace });
    };
    const records = analyzeTraces([trace()], {
      invoke,
      stateDir,
      runId: "run-TEST",
      contexts: {
        soulBaseline: "SOUL-BASELINE",
        interactionPosture: "POSTURE",
        experienceRecords: "RECORDS",
      },
    });
    assert.equal(records[0].status, "ok");
    assert.ok(seen.prompt && seen.prompt.includes("SOUL-BASELINE"), "invoke must receive the rendered prompt");
    const promptFile = path.join(stateDir, "prompts", "run-TEST__pi-1.md");
    assert.ok(fs.existsSync(promptFile), "rendered prompt must be persisted under stateDir/prompts");
    assert.ok(fs.readFileSync(promptFile, "utf8").includes("SOUL-BASELINE"));
    const metaFile = path.join(stateDir, "prompts", "run-TEST__pi-1.json");
    const meta = JSON.parse(fs.readFileSync(metaFile, "utf8"));
    assert.equal(meta.runId, "run-TEST");
    assert.equal(meta.transcriptId, "pi-1");
    assert.equal(meta.harness, "pi");
    assert.equal(meta.promptFile, "run-TEST__pi-1.md");
    if (process.platform !== "win32") {
      for (const file of [promptFile, metaFile]) {
        assert.equal(fs.statSync(file).mode & 0o777, 0o600, `${file} must be 0600`);
      }
    }
  });

  it("persists one prompt per session with run/session naming (no raw transcript file)", () => {
    const stateDir = tmpDir();
    analyzeTraces([trace(), trace({ transcriptId: "claude-9", harness: "claude" })], {
      invoke: (args) => mockInvoke({ trace: args.trace }),
      stateDir,
      runId: "run-MULTI",
    });
    const dir = path.join(stateDir, "prompts");
    const names = fs.readdirSync(dir).sort();
    assert.deepEqual(names, [
      "run-MULTI__claude-9.json",
      "run-MULTI__claude-9.md",
      "run-MULTI__pi-1.json",
      "run-MULTI__pi-1.md",
    ]);
    assert.ok(!fs.existsSync(path.join(stateDir, "raw-transcript-pi-1.txt")));
  });

  it("mock invoke path is unchanged (no live calls, same evidence shape)", () => {
    const outcome = mockInvoke({ trace: trace() });
    assert.equal(outcome.status, "ok");
    assert.ok(Array.isArray(outcome.evidence.positive));
    assert.ok(Array.isArray(outcome.evidence.gaps));
    const records = analyzeTraces([trace()], { invoke: mockInvoke });
    assert.equal(records[0].status, "ok");
    assert.equal(records[0].transcriptId, "pi-1");
  });

  it("persistPrompt sanitizes hostile transcript ids", () => {
    const stateDir = tmpDir();
    const file = persistPrompt(stateDir, {
      runId: "run-X",
      transcriptId: "../../evil",
      harness: "pi",
      prompt: "PROMPT",
    });
    assert.ok(file.startsWith(path.join(stateDir, "prompts") + path.sep));
    assert.ok(fs.readFileSync(file, "utf8").includes("PROMPT"));
  });
});

describe("evidence status normalization (ACPX omitted-status default)", () => {
  const gap = {
    proposedInstruction: "exp-context-bootstrap",
    mistake: "sessions re-derive project context from scratch",
    quote: "sessions re-derive project context from scratch",
    recurrenceRisk: "every new session pays the same bootstrap cost",
  };

  it("accepts omitted status with well-formed collections and passes gaps through", () => {
    const records = analyzeTraces([trace()], {
      invoke: () => ({
        status: "ok",
        evidence: { positive: [], negative: [], gaps: [gap] },
      }),
    });
    assert.equal(records[0].status, "ok");
    assert.deepEqual(records[0].gaps, [gap]);
    assert.deepEqual(records[0].positive, []);
    assert.deepEqual(records[0].negative, []);
  });

  it("keeps explicit non-ok evidence.status failed/excluded", () => {
    for (const status of ["failed", "error", "partial", ""]) {
      const records = analyzeTraces([trace()], {
        invoke: () => ({
          status: "ok",
          evidence: { status, positive: [], negative: [], gaps: [gap] },
        }),
      });
      assert.equal(records[0].status, "failed", `explicit status ${JSON.stringify(status)} must stay failed`);
      assert.deepEqual(records[0].gaps, [gap]);
    }
  });

  it("fails closed on malformed/missing/non-array evidence lists", () => {
    const badEvidences = [
      { positive: [], negative: [] },
      { positive: "x", negative: [], gaps: [] },
      { positive: [], negative: null, gaps: [] },
      { positive: [], negative: [], gaps: {} },
      { positive: [], negative: [] , gaps: null },
    ];
    for (const evidence of badEvidences) {
      const records = analyzeTraces([trace()], {
        invoke: () => ({ status: "ok", evidence }),
      });
      assert.equal(
        records[0].status,
        "failed",
        `omitted status with malformed evidence ${JSON.stringify(evidence)} must fail closed`,
      );
    }
  });
});

describe("analysis progress", () => {
  it("reports each finished trace before the next synchronous invoke starts", () => {
    const reported = [];
    const calls = [];
    analyzeTraces([trace({ transcriptId: "one" }), trace({ transcriptId: "two" })], {
      invoke: ({ trace: item }) => {
        calls.push(item.transcriptId);
        return { status: "ok", evidence: { positive: [], negative: [], gaps: [] } };
      },
      onRecord: (record) => reported.push(record.transcriptId),
    });
    assert.deepEqual(calls, ["one", "two"]);
    assert.deepEqual(reported, ["one", "two"]);
  });
});
