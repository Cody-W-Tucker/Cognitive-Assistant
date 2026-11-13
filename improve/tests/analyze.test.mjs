import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import { analyzeTraces, buildAnalysisPrompt, loadContexts } from "../src/analyze.js";
import { SELF_SESSION_SENTINEL } from "../src/sentinel.js";
import { readSoulSnapshot } from "../src/soul.js";
import { tmpDir, writeSoul } from "./helpers.mjs";

const ACTIVE = { userTurns: 1, assistantTurns: 1, toolCalls: 0 };
const trace = (id, extra = {}) => ({ transcriptId: id, harness: "codex", activity: ACTIVE, distilled: `# session ${id}\n## human\nhello\n`, ...extra });

async function analyzeOne(reply, t = trace("t1")) {
  const stateDir = tmpDir();
  const [record] = await analyzeTraces([t], { invoke: async () => reply(), contexts: loadContexts(), stateDir, runId: "run-1" });
  return { record, stateDir };
}

describe("analysis contexts", () => {
  it("each context degrades to an explicit marker when its source is absent", () => {
    const contexts = loadContexts({ soulPath: "/nonexistent/SOUL.md" });
    assert.match(contexts.soulBaseline, /SOUL baseline unavailable: looked in \/nonexistent\/SOUL\.md/);
    assert.match(contexts.interactionPosture, /interaction posture unavailable/);
    assert.match(contexts.experienceRecords, /accepted experience records unavailable/);
  });

  it("reads SOUL, posture, and the active experience records", () => {
    const dir = tmpDir();
    fs.writeFileSync(path.join(dir, "experience.md"), '<record id="exp-a">\naccepted record body\n</record>');
    fs.writeFileSync(path.join(dir, "posture.md"), "posture text");
    const contexts = loadContexts({ soulPath: writeSoul(dir, "soul text"), posturePath: path.join(dir, "posture.md"), experiencePath: path.join(dir, "experience.md") });
    assert.equal(contexts.soulBaseline, "soul text");
    assert.equal(contexts.interactionPosture, "posture text");
    assert.match(contexts.experienceRecords, /<record id="exp-a">\naccepted record body/);
  });

  it("unreadable optional contexts degrade locally while the required SOUL fails closed", (t) => {
    const dir = tmpDir();
    const files = {
      soulPath: writeSoul(dir, "soul text"),
      posturePath: path.join(dir, "posture.md"),
      experiencePath: path.join(dir, "experience.md"),
    };
    fs.writeFileSync(files.posturePath, "posture text");
    fs.writeFileSync(files.experiencePath, "experience text");
    const read = fs.readFileSync;
    let blocked;
    t.mock.method(fs, "readFileSync", (file, ...args) => {
      if (file === blocked) throw Object.assign(new Error("access denied"), { code: "EACCES" });
      return read(file, ...args);
    });
    for (const [input, output, label] of [
      ["soulPath", "soulBaseline", "SOUL baseline"],
      ["posturePath", "interactionPosture", "interaction posture"],
      ["experiencePath", "experienceRecords", "accepted experience records"],
    ]) {
      blocked = files[input];
      const contexts = loadContexts(files);
      assert.equal(contexts[output], `(${label} unavailable: looked in ${blocked}; audit the trace alone and note the gap in changed_context.)`);
      if (input === "soulPath") assert.throws(() => readSoulSnapshot(files.soulPath), /refusing to propose/);
      else {
        assert.equal(readSoulSnapshot(files.soulPath).text, "soul text");
        assert.equal(contexts.soulBaseline, "soul text");
      }
    }
  });

  it("the prompt carries the trace and contexts behind the sentinel", () => {
    const prompt = buildAnalysisPrompt(trace("t1"), { soulBaseline: "S", interactionPosture: "P", experienceRecords: "E" });
    assert.ok(prompt.startsWith(SELF_SESSION_SENTINEL));
    assert.ok(prompt.includes("## human\nhello"));
  });
});

describe("evidence normalization", () => {
  it("accepts an omitted status with well-formed collections", async () => {
    const gaps = [{ quote: "q", mistake: "m" }];
    const { record } = await analyzeOne(() => ({ positive: [], negative: [], gaps }));
    assert.equal(record.status, "ok");
    assert.deepEqual(record.gaps, gaps);
  });

  it("an explicit non-ok status, malformed collections, or a thrown call fail that trace only", async () => {
    for (const reply of [
      () => ({ status: "excluded", positive: [], negative: [], gaps: [] }),
      () => ({ positive: [], negative: "x", gaps: [] }),
      () => ({ gaps: [] }),
      () => {
        throw new Error("endpoint down");
      },
    ]) {
      const { record } = await analyzeOne(reply);
      assert.equal(record.status, "failed");
      assert.deepEqual(record.gaps, []);
    }
  });

  it("skips trivial sessions without a model call, keeping single-request sessions with real tool work", async () => {
    let calls = 0;
    const invoke = async () => {
      calls += 1;
      return { positive: [], negative: [], gaps: [] };
    };
    const records = await analyzeTraces(
      [
        trace("empty", { activity: { userTurns: 0, assistantTurns: 0, toolCalls: 0 } }),
        trace("autonomous", { activity: { userTurns: 0, assistantTurns: 0, toolCalls: 3 } }),
      ],
      { invoke, contexts: loadContexts(), stateDir: tmpDir(), runId: "run-1" },
    );
    assert.equal(records[0].status, "skipped");
    assert.match(records[0].error, /trivial session \(0 user turn\(s\), 0 agent turn\(s\), 0 tool call\(s\)\)/);
    assert.equal(records[1].status, "ok");
    assert.equal(calls, 1);
  });

  it("an unreadable session fails (and so is retried) instead of passing as trivial", async () => {
    const { record } = await analyzeOne(() => ({ positive: [], negative: [], gaps: [] }), { transcriptId: "t1", harness: "hermes", readError: "unreadable session: locked" });
    assert.deepEqual([record.status, record.error], ["failed", "unreadable session: locked"]);
  });

  it("archives one prompt per session under the state dir, with hostile ids made safe", async () => {
    const { stateDir } = await analyzeOne(() => ({ positive: [], negative: [], gaps: [] }), trace("../../evil id"));
    const files = fs.readdirSync(path.join(stateDir, "prompts"));
    assert.deepEqual(files.sort(), ["run-1__.._.._evil_id.json", "run-1__.._.._evil_id.md"]);
  });

  it("reports each record as it finishes", async () => {
    const seen = [];
    await analyzeTraces([trace("a"), trace("b")], {
      invoke: async () => ({ positive: [], negative: [], gaps: [] }),
      contexts: loadContexts(),
      stateDir: tmpDir(),
      runId: "run-1",
      jobs: 1,
      onRecord: (r) => seen.push(r.transcriptId),
    });
    assert.deepEqual(seen, ["a", "b"]);
  });
});
