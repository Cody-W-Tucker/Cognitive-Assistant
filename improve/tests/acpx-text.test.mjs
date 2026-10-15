import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

import {
  ACPX_TEXT_FORMAT_ARGS,
  buildAcpxArgs,
  extractAcpxFinalJson,
  isJsonRpcEnvelope,
  runAcpxPromptFile,
  stripAcpxFraming,
  stripPiQuietPreamble,
} from "../src/acpx-text.js";
import { ANALYSIS_MODEL, SYNTHESIS_MODEL, modelForRole } from "../src/models.js";

function withEnv(patch, fn) {
  const prev = new Map();
  for (const key of Object.keys(patch)) {
    prev.set(key, process.env[key]);
    if (patch[key] === undefined) delete process.env[key];
    else process.env[key] = patch[key];
  }
  try {
    return fn();
  } finally {
    for (const [key, value] of prev) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
}

describe("ACPX text-output argv (not JSON-RPC, agent + env preserved)", () => {
  it("requests text-output by default", () => {
    withEnv({ CA_IMPROVE_ACPX_ARGS: undefined }, () => {
      assert.deepEqual(buildAcpxArgs({}), [...ACPX_TEXT_FORMAT_ARGS, "pi"]);
      assert.ok(ACPX_TEXT_FORMAT_ARGS.includes("quiet"));
    });
  });

  it("uses the fixed Pi executor as trailing callable positional (after globals/format)", () => {
    withEnv({ CA_IMPROVE_ACPX_ARGS: undefined }, () => {
      const args = buildAcpxArgs({});
      assert.deepEqual(args, [...ACPX_TEXT_FORMAT_ARGS, "pi"]);
      assert.equal(args[args.length - 1], "pi");
      assert.ok(args.includes("--format") && args.includes("quiet"));
    });
  });

  it("rejects any caller-supplied agent (Pi is the fixed executor)", () => {
    withEnv({ CA_IMPROVE_ACPX_ARGS: undefined }, () => {
      assert.throws(() => buildAcpxArgs({ agent: "pi" }), /fixed to pi/);
      assert.throws(() => buildAcpxArgs({ agent: "codex" }), /fixed to pi/);
      assert.throws(
        () => runAcpxPromptFile({ role: "analysis", promptFile: "/tmp/x.md", agent: "pi" }),
        /fixed to pi/,
      );
    });
  });

  it("rejects env executors other than pi exec", () => {
    withEnv({ CA_IMPROVE_ACPX_ARGS: "codex" }, () => {
      assert.throws(() => buildAcpxArgs({}), /fixed to pi/);
    });
    withEnv({ CA_IMPROVE_ACPX_ARGS: "pi exec codex" }, () => {
      assert.throws(() => buildAcpxArgs({}), /fixed to pi/);
    });
  });

  it("preserves CA_IMPROVE_ACPX_ARGS global extra args before format (fixed pi executor)", () => {
    withEnv({ CA_IMPROVE_ACPX_ARGS: "--timeout 30 --model x" }, () => {
      const args = buildAcpxArgs({});
      assert.deepEqual(args, ["--timeout", "30", "--model", "x", "--format", "quiet", "pi"]);
      assert.ok(args.indexOf("--timeout") < args.indexOf("--format"));
      assert.equal(args[args.length - 1], "pi");
    });
  });

  it("supports Pi via ACPX with globals before executor (valid CLI shape, spawn-ready)", () => {
    withEnv({ CA_IMPROVE_ACPX_ARGS: "--env KEY=value" }, () => {
      const args = buildAcpxArgs({});
      // Valid: `acpx --env KEY=value --format quiet pi ...` (... = --file appended downstream).
      assert.deepEqual(args, ["--env", "KEY=value", "--format", "quiet", "pi"]);
      // Guard the invalid old ordering: `acpx pi --format quiet --env KEY=value ...`.
      assert.notDeepEqual(args, ["pi", "--format", "quiet", "--env", "KEY=value"]);
      // Builder return is suitable for spawn where downstream appends --file.
      assert.deepEqual([...args, "--file", "PROMPT"], ["--env", "KEY=value", "--format", "quiet", "pi", "--file", "PROMPT"]);
    });
  });

  it("places bare `pi exec` subcommand after text-output format (exact order)", () => {
    withEnv({ CA_IMPROVE_ACPX_ARGS: "pi exec" }, () => {
      assert.deepEqual(buildAcpxArgs({}), ["--format", "quiet", "pi", "exec"]);
    });
  });

  it("rejects explicit --format/--output overrides fail-closed (text output required)", () => {
    for (const override of ["--format json", "--format=json", "--output json", "--format quiet"]) {
      withEnv({ CA_IMPROVE_ACPX_ARGS: override }, () => {
        assert.throws(() => buildAcpxArgs({}), /must not override.*--format quiet/);
      });
    }
  });

  it("assigns Backpass cheap and strong models by role", () => {
    withEnv({ CA_IMPROVE_ACPX_ARGS: "pi exec" }, () => {
      assert.equal(modelForRole("analysis"), ANALYSIS_MODEL);
      assert.equal(modelForRole("consolidate"), ANALYSIS_MODEL);
      assert.equal(modelForRole("synthesis"), SYNTHESIS_MODEL);
      assert.equal(modelForRole("annotate"), SYNTHESIS_MODEL);
      assert.deepEqual(buildAcpxArgs({ model: modelForRole("analysis") }), [
        "--format",
        "quiet",
        "--model",
        ANALYSIS_MODEL,
        "pi",
        "exec",
      ]);
      assert.deepEqual(buildAcpxArgs({ model: modelForRole("synthesis") }), [
        "--format",
        "quiet",
        "--model",
        SYNTHESIS_MODEL,
        "pi",
        "exec",
      ]);
    });
  });

  it("never requests JSON-RPC by default", () => {
    withEnv({ CA_IMPROVE_ACPX_ARGS: undefined }, () => {
      const args = buildAcpxArgs({});
      assert.ok(!args.includes("json") || args.includes("quiet"));
      assert.ok(args.includes("quiet"));
    });
  });

  it("builds file-mode argv: --format quiet --timeout N --model M pi exec --file P (timeout before executor)", () => {
    withEnv({ CA_IMPROVE_ACPX_ARGS: "pi exec" }, () => {
      const args = buildAcpxArgs({
        model: ANALYSIS_MODEL,
        timeoutSec: 180,
        promptFile: "/tmp/prompt.md",
      });
      assert.deepEqual(args, [
        "--format",
        "quiet",
        "--timeout",
        "180",
        "--model",
        ANALYSIS_MODEL,
        "pi",
        "exec",
        "--file",
        "/tmp/prompt.md",
      ]);
      assert.ok(args.indexOf("--timeout") < args.indexOf("pi"));
      assert.ok(args.indexOf("--format") < args.indexOf("--timeout"));
      assert.equal(args[args.indexOf("--file") + 1], "/tmp/prompt.md");
    });
  });

  it("keeps configured CA_IMPROVE_ACPX_ARGS globals before format in file mode (Pi executor remains)", () => {
    withEnv({ CA_IMPROVE_ACPX_ARGS: "--env KEY=value pi exec" }, () => {
      const args = buildAcpxArgs({
        model: SYNTHESIS_MODEL,
        timeoutSec: 300,
        promptFile: "/tmp/synth.md",
      });
      assert.deepEqual(args.slice(0, 2), ["--env", "KEY=value"]);
      assert.ok(args.includes("--format") && args.includes("quiet"));
      assert.ok(args.includes("pi") && args.includes("exec"));
      assert.equal(args[args.indexOf("--file") + 1], "/tmp/synth.md");
      assert.ok(args.indexOf("--timeout") < args.indexOf("pi"));
      assert.equal(args[args.indexOf("--timeout") + 1], "300");
      assert.equal(args[args.indexOf("--model") + 1], SYNTHESIS_MODEL);
    });
  });

  it("explicit role timeout/model/file win over env globals (ACPX timeout mandatory)", () => {
    withEnv({ CA_IMPROVE_ACPX_ARGS: "--timeout 30 --model env-model pi exec" }, () => {
      const args = buildAcpxArgs({
        model: ANALYSIS_MODEL,
        timeoutSec: 180,
        promptFile: "/tmp/p.md",
      });
      // Env --timeout/--model are replaced, not duplicated.
      assert.equal(args.filter((t) => t === "--timeout").length, 1);
      assert.equal(args.filter((t) => t === "--model").length, 1);
      assert.equal(args.filter((t) => t === "--file").length, 1);
      assert.equal(args[args.indexOf("--timeout") + 1], "180");
      assert.equal(args[args.indexOf("--model") + 1], ANALYSIS_MODEL);
    });
  });
});

describe("strict deterministic extractor (exactly one final object)", () => {
  it("accepts actual ACPX framing: [acpx] lines before/after + whitespace", () => {
    const out = `[acpx] tokens: input=10 output=47 total=57\n{"plans": []}\n[acpx] done in 1.2s\n`;
    assert.deepEqual(extractAcpxFinalJson(out), { plans: [] });
    assert.equal(stripAcpxFraming(out).trim(), `{"plans": []}`);
  });

  it("accepts one ```json fenced block with known framing outside stripped", () => {
    const out = `[acpx] tokens: input=1 output=2\n\`\`\`json\n{"merges": []}\n\`\`\`\n`;
    assert.deepEqual(extractAcpxFinalJson(out), { merges: [] });
  });

  it("accepts plain final object with surrounding whitespace", () => {
    assert.deepEqual(extractAcpxFinalJson(`\n  {"ready": true}  \n`), { ready: true });
  });

  it("handles braces inside strings without splitting candidates", () => {
    const out = `{"body": "a { b } c", "plans": []}`;
    assert.deepEqual(extractAcpxFinalJson(out), { body: "a { b } c", plans: [] });
  });

  it("rejects JSON-RPC envelopes fail-closed", () => {
    const rpc = `{"jsonrpc": "2.0", "id": 1, "result": {"plans": []}}`;
    assert.equal(extractAcpxFinalJson(rpc), null);
    assert.equal(isJsonRpcEnvelope(JSON.parse(rpc)), true);
    assert.equal(extractAcpxFinalJson(`{"jsonrpc":"2.0","method":"prompt","params":{}}`), null);
  });

  it("rejects ambiguity: two top-level objects fail closed", () => {
    assert.equal(extractAcpxFinalJson(`{"a": 1}\n{"b": 2}`), null);
  });

  it("rejects absent/malformed/unbalanced output", () => {
    assert.equal(extractAcpxFinalJson(""), null);
    assert.equal(extractAcpxFinalJson("   \n  "), null);
    assert.equal(extractAcpxFinalJson("not json at all"), null);
    assert.equal(extractAcpxFinalJson(`{"plans": [`), null);
    assert.equal(extractAcpxFinalJson(`{"a": 1} extra }`), null);
  });

  it("rejects top-level arrays and scalars", () => {
    assert.equal(extractAcpxFinalJson(`[1, 2, 3]`), null);
    assert.equal(extractAcpxFinalJson(`"just a string"`), null);
    assert.equal(extractAcpxFinalJson(`42`), null);
    assert.deepEqual(extractAcpxFinalJson(`[{"plans": []}]`), { plans: [] });
  });

  it("matches Backpass by accepting OpenCode prose around one JSON object", () => {
    assert.deepEqual(extractAcpxFinalJson(`Here is your result: {"plans": []} hope this helps`), { plans: [] });
    assert.deepEqual(
      extractAcpxFinalJson(`Sure! {"plans": [{"clusterId": "g-a"}]} Let me explain...`),
      { plans: [{ clusterId: "g-a" }] },
    );
    assert.deepEqual(
      extractAcpxFinalJson(`\`\`\`json\n{"a": 1}\n\`\`\`\n\`\`\`json\n{"b": 2}\n\`\`\`\n`),
      { a: 1 },
    );
  });

  it("matches Backpass by accepting a fenced JSON object with surrounding text", () => {
    assert.deepEqual(extractAcpxFinalJson("```python\n{\"a\": 1}\n```\n"), { a: 1 });
    assert.deepEqual(extractAcpxFinalJson("prefix\n```json\n{\"a\": 1}\n```\n"), { a: 1 });
  });

  it("uses no loose regex brace heuristic (nested + escaped strings stay exact)", () => {
    const out = `{"text": "quote \\"with\\" braces {not json}", "n": 1}`;
    assert.deepEqual(extractAcpxFinalJson(out), { text: 'quote "with" braces {not json}', n: 1 });
  });

  it("accepts real-shaped Pi quiet preamble before exactly one final object", () => {
    const out = [
      "pi v0.5.1",
      "----------",
      "",
      "Context",
      "  - /repo/SOUL.md",
      "  - /repo/INTERACTION_POSTURE.md",
      "",
      "Skills",
      "  - skill-a: does x",
      "  - skill-b: does y",
      "",
      '{"status": "ok", "positive": [], "negative": [], "gaps": []}',
      "",
    ].join("\n");
    assert.deepEqual(extractAcpxFinalJson(out), {
      status: "ok",
      positive: [],
      negative: [],
      gaps: [],
    });
    assert.ok(stripPiQuietPreamble(out).trimStart().startsWith("{"));
  });

  it("accepts live Pi header with level-2 Markdown headings before exactly one final object", () => {
    const out = [
      "pi v0.5.1",
      "----------",
      "",
      "## Context",
      "  - /repo/SOUL.md",
      "  - /repo/INTERACTION_POSTURE.md",
      "",
      "## Skills",
      "  - skill-a: does x",
      "  - skill-b: does y",
      "",
      '{"status": "ok", "positive": [], "negative": [], "gaps": []}',
      "",
    ].join("\n");
    assert.deepEqual(extractAcpxFinalJson(out), {
      status: "ok",
      positive: [],
      negative: [],
      gaps: [],
    });
    assert.ok(stripPiQuietPreamble(out).trimStart().startsWith("{"));
  });

  it("accepts Pi preamble with [acpx] framing and a single fenced object", () => {
    const out = [
      "[acpx] tokens: input=3 output=9",
      "pi v0.5.1",
      "----------",
      "",
      "Context",
      "  - ctx-one",
      "",
      "Skills",
      "  - skill-one",
      "",
      "```json",
      '{"ready": true}',
      "```",
      "",
    ].join("\n");
    assert.deepEqual(extractAcpxFinalJson(out), { ready: true });
  });

  it("matches Backpass when Pi/OpenCode adds arbitrary preamble prose", () => {
    const out = [
      "pi v0.5.1 extra prose",
      "----------",
      "",
      "Context",
      "  - /repo/SOUL.md",
      "  - /repo/INTERACTION_POSTURE.md",
      "",
      "Skills",
      "  - skill-a: does x",
      "  - skill-b: does y",
      "",
      '{"status": "ok", "positive": [], "negative": [], "gaps": []}',
      "",
    ].join("\n");
    assert.deepEqual(extractAcpxFinalJson(out), { status: "ok", positive: [], negative: [], gaps: [] });
    assert.equal(stripPiQuietPreamble(out), out);
  });

  it("accepts generic preambles the same way Backpass does", () => {
    assert.deepEqual(extractAcpxFinalJson(`Hello from Pi\n\n{"ready": true}\n`), { ready: true });
    assert.deepEqual(
      extractAcpxFinalJson(`pi v0.5.1\nSome intro prose\n\n{"ready": true}\n`),
      { ready: true },
    );
    assert.deepEqual(extractAcpxFinalJson(`Version pi v1\n\n{"ready": true}\n`), { ready: true });
  });

  it("accepts malformed Pi-like wrappers when they still contain one final JSON object", () => {
    const base = (head) => `${head}\n{"ready": true}\n`;
    assert.deepEqual(extractAcpxFinalJson(base(`pi v0.5.1\n----------\n\nContext\n  - a`)), { ready: true });
    assert.deepEqual(
      extractAcpxFinalJson(base(`pi v0.5.1\n----------\n\nContext\n  - a\n\nSkills\n  - b\n\nTools\n  - c`)),
      { ready: true },
    );
  });

  it("keeps JSON-RPC and multiple-object output rejected while recovering wrapper prose", () => {
    const head = `pi v0.5.1\n----------\n\nContext\n  - a\n\nSkills\n  - b\n\n`;
    assert.equal(
      extractAcpxFinalJson(`${head}{"jsonrpc": "2.0", "id": 1, "result": {}}\n`),
      null,
    );
    // Backpass's first-to-last brace span is not valid JSON for two objects.
    assert.equal(extractAcpxFinalJson(`${head}{"a": 1}\n{"b": 2}\n`), null);
    assert.equal(extractAcpxFinalJson(`${head}[1, 2, 3]\n`), null);
    assert.deepEqual(extractAcpxFinalJson(`${head}{"a": 1} trailing prose\n`), { a: 1 });
  });

  it("accepts exact live Pi shape with upgrade-notice tail before one final object", () => {
    const out = [
      "pi v1.1.0",
      "---",
      "",
      "Context",
      "  - /repo/SOUL.md",
      "  - /repo/INTERACTION_POSTURE.md",
      "",
      "Skills",
      "  - skill-a: does x",
      "  - skill-b: does y",
      "",
      "---",
      "New version available: v1.1.0 -> v1.2.0 (run `pi upgrade`)",
      '{"plans":[]}',
      "",
    ].join("\n");
    assert.deepEqual(extractAcpxFinalJson(out), { plans: [] });
    assert.ok(stripPiQuietPreamble(out).trimStart().startsWith("{"));
  });

  it("accepts upgrade notices with explanatory prose the same way Backpass does", () => {
    const out = [
      "pi v1.1.0",
      "---",
      "",
      "Context",
      "  - /repo/SOUL.md",
      "  - /repo/INTERACTION_POSTURE.md",
      "",
      "Skills",
      "  - skill-a: does x",
      "  - skill-b: does y",
      "",
      "---",
      "New version available: v1.1.0 -> v1.2.0 (run `pi upgrade`)",
      "Please upgrade soon",
      '{"plans":[]}',
      "",
    ].join("\n");
    assert.deepEqual(extractAcpxFinalJson(out), { plans: [] });
  });
});

describe("real ACPX calls use text-output + strict extraction (no direct client/fallback)", () => {
  let tmp;
  let prevBin;
  let prevArgs;
  beforeEach(() => {
    tmp = fs.mkdtempSync(path.join(os.tmpdir(), "ca-acpx-text-"));
    prevBin = process.env.CA_IMPROVE_ACPX_BIN;
    prevArgs = process.env.CA_IMPROVE_ACPX_ARGS;
    delete process.env.CA_IMPROVE_ACPX_ARGS;
  });
  afterEach(() => {
    if (prevBin === undefined) delete process.env.CA_IMPROVE_ACPX_BIN;
    else process.env.CA_IMPROVE_ACPX_BIN = prevBin;
    if (prevArgs === undefined) delete process.env.CA_IMPROVE_ACPX_ARGS;
    else process.env.CA_IMPROVE_ACPX_ARGS = prevArgs;
    fs.rmSync(tmp, { recursive: true, force: true });
  });

  function fakeBin({ stdout, exitCode = 0, recordArgs }) {
    const bin = path.join(tmp, `fake-acpx-${Math.random().toString(36).slice(2)}`);
    const script =
      `#!/bin/sh\n` +
      `echo "$@" > ${JSON.stringify(`${recordArgs}`)}\n` +
      `cat ${JSON.stringify(`${tmp}/out.txt`)}\n` +
      (exitCode === 0 ? "" : `exit ${exitCode}\n`);
    fs.writeFileSync(`${tmp}/out.txt`, stdout);
    fs.writeFileSync(bin, script, { mode: 0o755 });
    fs.chmodSync(bin, 0o755);
    return bin;
  }

  function recordedArgs(file) {
    return fs.readFileSync(file, "utf8").trim().split(/\s+/).filter(Boolean);
  }

  function assertFileArgv(argv, { promptFile, timeoutSec, model }) {
    const fileIdx = argv.indexOf("--file");
    assert.notEqual(fileIdx, -1, `argv must include --file (got ${argv.join(" ")})`);
    assert.equal(argv[fileIdx + 1], promptFile);
    const timeoutIdx = argv.indexOf("--timeout");
    assert.notEqual(timeoutIdx, -1, `argv must include --timeout (got ${argv.join(" ")})`);
    assert.equal(argv[timeoutIdx + 1], String(timeoutSec));
    assert.ok(timeoutIdx < argv.indexOf("pi"), "--timeout must precede the pi agent");
    assert.ok(argv.indexOf("--format") < timeoutIdx, "--format quiet must precede --timeout");
    const modelIdx = argv.indexOf("--model");
    assert.notEqual(modelIdx, -1, `argv must include --model (got ${argv.join(" ")})`);
    assert.equal(argv[modelIdx + 1], model);
    assert.ok(argv.includes("pi") && argv.includes("exec"), `argv must run pi exec (got ${argv.join(" ")})`);
    assert.ok(argv.includes("--format") && argv.includes("quiet"));
  }

  function assertNoStdinInputInSources() {
    const { fileURLToPath } = process.env.CA_TEST_NOOP ? {} : {};
    void fileURLToPath;
    // Static proof: the five stage call sites must not pass stdin `input:` to
    // spawnSync; prompts travel via persisted --file only. The single shared
    // helper owns the one spawnSync call.
    return import("node:url").then(async ({ fileURLToPath: toPath }) => {
      const here = path.dirname(toPath(import.meta.url));
      const stageFiles = ["../src/analyze.js", "../src/consolidate.js", "../src/synthesize.js", "../src/annotate.js"];
      for (const rel of stageFiles) {
        const text = fs.readFileSync(path.join(here, rel), "utf8");
        assert.ok(/runAcpxPromptFile/.test(text), `${rel} must use the shared runAcpxPromptFile helper`);
        assert.ok(!/\binput\s*:/.test(text), `${rel} must not pass stdin input to spawnSync (use --file)`);
      }
      const helperText = fs.readFileSync(path.join(here, "../src/acpx-text.js"), "utf8");
      assert.ok(/runAcpxPromptFile/.test(helperText), "acpx-text.js must own runAcpxPromptFile");
      assert.ok(!/\binput\s*:/.test(helperText), "shared helper must not use stdin input (use --file)");
      const pipeText = fs.readFileSync(path.join(here, "../src/pipeline.js"), "utf8");
      assert.ok(/promptFile/.test(pipeText), "pipeline must forward persisted promptFile");
    });
  }

  it("analysis real call uses persisted --file + --timeout 180/luna before pi (no stdin)", async () => {
    const { acpxInvoke } = await import("../src/analyze.js");
    const argFile = path.join(tmp, "args.txt");
    const promptFile = path.join(tmp, "analysis-prompt.md");
    fs.writeFileSync(promptFile, "PROMPT", "utf8");
    const stdout = `[acpx] tokens: input=3 output=9\n{"status": "ok", "positive": [], "negative": [], "gaps": []}\n`;
    process.env.CA_IMPROVE_ACPX_BIN = fakeBin({ stdout, recordArgs: argFile });
    process.env.CA_IMPROVE_ACPX_ARGS = "pi exec";
    const out = acpxInvoke({
      trace: { transcriptId: "t1", harness: "pi", distilled: "hi" },
      prompt: "PROMPT",
      promptFile,
    });
    assert.equal(out.status, "ok");
    assert.deepEqual(out.evidence, { status: "ok", positive: [], negative: [], gaps: [] });
    const argv = recordedArgs(argFile);
    assertFileArgv(argv, { promptFile, timeoutSec: 180, model: ANALYSIS_MODEL });
    await assertNoStdinInputInSources();
  });

  it("consolidation real call uses persisted --file + --timeout 180/luna before pi (no stdin)", async () => {
    const { acpxConsolidateInvoke } = await import("../src/consolidate.js");
    const argFile = path.join(tmp, "args3.txt");
    const promptFile = path.join(tmp, "consolidate-prompt.md");
    fs.writeFileSync(promptFile, "P", "utf8");
    process.env.CA_IMPROVE_ACPX_BIN = fakeBin({
      stdout: `{"merges": []}\n{"merges": []}\n`,
      recordArgs: argFile,
    });
    process.env.CA_IMPROVE_ACPX_ARGS = "pi exec";
    const out = acpxConsolidateInvoke({ prompt: "P", promptFile });
    assert.equal(out.status, "failed");
    const argv = recordedArgs(argFile);
    assertFileArgv(argv, { promptFile, timeoutSec: 180, model: ANALYSIS_MODEL });
    await assertNoStdinInputInSources();
  });

  it("synthesis real call uses persisted --file + --timeout 300/sol before pi, strictly parses bounded plans payload", async () => {
    const { acpxSynthesisInvoke } = await import("../src/synthesize.js");
    const argFile = path.join(tmp, "args2.txt");
    const promptFile = path.join(tmp, "synthesis-prompt.md");
    fs.writeFileSync(promptFile, "P", "utf8");
    const raw = `{"plans": [{"id": "e1", "kind": "add", "clusterId": "g-1", "provisionalIntent": "do x", "provisionalSources": ["s1", "s2"]}]}\n`;
    process.env.CA_IMPROVE_ACPX_BIN = fakeBin({
      stdout: raw,
      recordArgs: argFile,
    });
    process.env.CA_IMPROVE_ACPX_ARGS = "pi exec";
    const out = acpxSynthesisInvoke({ prompt: "P", promptFile });
    assert.equal(out.status, "ok");
    assert.ok(
      Array.isArray(out.plans) && out.plans.length === 1,
      `synthesis exit 0 must strictly parse bounded plans payload (got ${JSON.stringify(out)})`,
    );
    const argv = recordedArgs(argFile);
    assertFileArgv(argv, { promptFile, timeoutSec: 300, model: SYNTHESIS_MODEL });
    await assertNoStdinInputInSources();
  });

  it("annotate real calls use persisted --file + --timeout 300/sol before pi (preface + final)", async () => {
    const { acpxAnnotatePrefaceInvoke, acpxAnnotateInvoke, annotateStaging } = await import(
      "../src/annotate.js"
    );
    const prePromptFile = path.join(tmp, "preface-prompt.md");
    fs.writeFileSync(prePromptFile, "PREFACE", "utf8");
    const preFile = path.join(tmp, "pre.txt");
    process.env.CA_IMPROVE_ACPX_BIN = fakeBin({
      stdout: `[acpx] tokens: input=1 output=1\n{"ready": true}\n`,
      recordArgs: preFile,
    });
    process.env.CA_IMPROVE_ACPX_ARGS = "pi exec";
    const pre = acpxAnnotatePrefaceInvoke({ prompt: "PREFACE", promptFile: prePromptFile });
    assert.equal(pre.status, "ok");
    assert.deepEqual(pre.result, { ready: true });
    assertFileArgv(recordedArgs(preFile), {
      promptFile: prePromptFile,
      timeoutSec: 300,
      model: SYNTHESIS_MODEL,
    });

    const annPromptFile = path.join(tmp, "annotate-prompt.md");
    fs.writeFileSync(annPromptFile, "ANNOTATE", "utf8");
    const annFile = path.join(tmp, "ann.txt");
    process.env.CA_IMPROVE_ACPX_BIN = fakeBin({
      stdout: `{"annotations": [{"id": "e1", "verdict": "drop", "reason": "x"}]}\n`,
      recordArgs: annFile,
    });
    const ann = acpxAnnotateInvoke({ prompt: "ANNOTATE", promptFile: annPromptFile });
    assert.equal(ann.status, "ok");
    assertFileArgv(recordedArgs(annFile), {
      promptFile: annPromptFile,
      timeoutSec: 300,
      model: SYNTHESIS_MODEL,
    });
    await assertNoStdinInputInSources();

    // Stage schema validation stays authoritative downstream: drop yields no finals.
    const { buildFinalProposal } = await import("../src/stage.js");
    const staged = [{ id: "e1", kind: "add", clusterId: "g-aaa", provisionalIntent: "i", provisionalSources: ["s1", "s2"], provisionalCount: 2 }];
    const out = await annotateStaging(staged, {
      invoke: (args) => {
        if (args.stage === "annotate-preface") return { status: "ok", result: { ready: true } };
        return { status: "ok", result: { annotations: [{ id: "e1", verdict: "drop", reason: "x" }] } };
      },
    });
    assert.equal(out.failed, false);
    assert.deepEqual(buildFinalProposal(out.annotated, {}), []);
  });

  it("all five stage invokes reject caller-supplied agent (Pi fixed)", async () => {
    const promptFile = path.join(tmp, "fixed-pi-prompt.md");
    fs.writeFileSync(promptFile, "X", "utf8");
    const { acpxInvoke } = await import("../src/analyze.js");
    const { acpxConsolidateInvoke } = await import("../src/consolidate.js");
    const { acpxSynthesisInvoke } = await import("../src/synthesize.js");
    const { acpxAnnotatePrefaceInvoke, acpxAnnotateInvoke } = await import("../src/annotate.js");
    assert.throws(() => acpxInvoke({ promptFile, agent: "pi" }), /fixed to pi/);
    assert.throws(() => acpxInvoke({ promptFile, agent: "codex" }), /fixed to pi/);
    assert.throws(() => acpxConsolidateInvoke({ promptFile, agent: "pi" }), /fixed to pi/);
    assert.throws(() => acpxSynthesisInvoke({ promptFile, agent: "codex" }), /fixed to pi/);
    assert.throws(() => acpxAnnotatePrefaceInvoke({ promptFile, agent: "pi" }), /fixed to pi/);
    assert.throws(() => acpxAnnotateInvoke({ promptFile, agent: "pi" }), /fixed to pi/);
  });

  it("shared helper never uses stdin input and keeps node spawn timeout above ACPX --timeout", async () => {
    const promptFile = path.join(tmp, "helper-prompt.md");
    fs.writeFileSync(promptFile, "HELPER", "utf8");
    let seenArgs;
    let seenOpts;
    const spawnFn = (bin, args, opts) => {
      seenArgs = args;
      seenOpts = opts;
      assert.ok(!("input" in (opts || {})), "spawn options must not carry stdin input");
      return { status: 0, stdout: `{"ok":true}\n` };
    };
    withEnv({ CA_IMPROVE_ACPX_ARGS: "pi exec" }, () => {
      const out = runAcpxPromptFile({
        role: "analysis",
        promptFile,
        spawnFn,
      });
      assert.equal(out.status, "ok");
    });
    assertFileArgv(seenArgs, { promptFile, timeoutSec: 180, model: ANALYSIS_MODEL });
    assert.ok(seenOpts && typeof seenOpts.timeout === "number", "node spawn timeout must be set");
    assert.ok(seenOpts.timeout > 180 * 1000, "node spawn timeout must exceed ACPX --timeout");
    assert.ok(!("input" in seenOpts), "spawn options must not use stdin input");

    const synthFile = path.join(tmp, "helper-synth.md");
    fs.writeFileSync(synthFile, "S", "utf8");
    const synthSpawnFn = (bin, args, opts) => {
      seenArgs = args;
      seenOpts = opts;
      assert.ok(!("input" in (opts || {})), "spawn options must not carry stdin input");
      return { status: 0, stdout: `{"plans":[]}\n` };
    };
    withEnv({ CA_IMPROVE_ACPX_ARGS: "pi exec" }, () => {
      const out = runAcpxPromptFile({ role: "synthesis", promptFile: synthFile, spawnFn: synthSpawnFn });
      assert.equal(out.status, "ok");
      assert.deepEqual(out.result, { plans: [] });
    });
    assertFileArgv(seenArgs, { promptFile: synthFile, timeoutSec: 300, model: SYNTHESIS_MODEL });
    assert.ok(seenOpts.timeout > 300 * 1000, "synthesis spawn timeout must exceed ACPX --timeout");
  });

  it("stage schema validation remains authoritative over extracted finals", async () => {
    const { validateCandidate } = await import("../src/synthesize.js");
    const ledger = {
      version: 1,
      minGapEvidence: 2,
      clusters: [
        {
          id: "g-aaa",
          proposedInstruction: "Do X",
          representativeQuote: "quote-a",
          mistake: "m",
          sources: ["s1", "s2"],
          count: 2,
          eligible: true,
          perSource: { s1: { quote: "quote-a", mistake: "m" }, s2: { quote: "quote-a", mistake: "m" } },
        },
      ],
    };
    const idx = new Map([
      ["s1", [{ quote: "quote-a", effect: "e" }]],
      ["s2", [{ quote: "quote-a", effect: "e" }]],
    ]);
    const extracted = extractAcpxFinalJson(`{"title": "x", "plans": []}\n`);
    assert.ok(extracted);
    // An extracted envelope with no record still fails stage validation.
    assert.equal(validateCandidate({ record: {} }, { ledger, evidenceIndex: idx }).ok, false);
    // A fully-evidenced extracted record with its annotation id passes.
    const good = {
      id: "exp-do-x-a1b2c3d4e5f6",
      title: "Do X",
      body: "Recurring gap",
      sources: ["s1", "s2"],
      clusterId: "g-aaa",
      evidence: [
        { text: "quote-a", source: "s1" },
        { text: "quote-a", source: "s2" },
      ],
      counterevidence: "none observed",
      compilerImplication: "compiler appends",
    };
    assert.equal(validateCandidate({ record: good }, { ledger, evidenceIndex: idx }).ok, true);
  });

  it("async helper passes explicit workspace cwd to spawn like sync (existing callers preserved)", async () => {
    const { runAcpxPromptFileAsync } = await import("../src/acpx-text.js");
    const promptFile = path.join(tmp, "async-cwd-prompt.md");
    fs.writeFileSync(promptFile, "HELPER", "utf8");
    const wsDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-acpx-async-cwd-"));
    const cwdFile = path.join(tmp, "async-cwd.txt");
    const argFile = path.join(tmp, "async-args.txt");
    fs.writeFileSync(`${tmp}/async-out.txt`, `{"ok":true}\n`);
    const bin = path.join(tmp, `fake-acpx-async-${Math.random().toString(36).slice(2)}`);
    fs.writeFileSync(
      bin,
      `#!/bin/sh\npwd > ${JSON.stringify(cwdFile)}\necho "$@" > ${JSON.stringify(argFile)}\ncat ${JSON.stringify(`${tmp}/async-out.txt`)}\n`,
      { mode: 0o755 },
    );
    fs.chmodSync(bin, 0o755);
    const prevArgs = process.env.CA_IMPROVE_ACPX_ARGS;
    process.env.CA_IMPROVE_ACPX_ARGS = "pi exec";
    try {
      const out = await runAcpxPromptFileAsync({ role: "analysis", promptFile, bin, workspace: wsDir });
      assert.equal(out.status, "ok");
      assert.deepEqual(out.result, { ok: true });
      const seenCwd = fs.readFileSync(cwdFile, "utf8").trim();
      assert.equal(fs.realpathSync(seenCwd), fs.realpathSync(wsDir), "async spawn must run with explicit workspace cwd");
      const argv = fs.readFileSync(argFile, "utf8").trim().split(/\s+/).filter(Boolean);
      assert.ok(argv.includes("pi") && argv.includes("exec"));
      // Existing callers without workspace still work (no cwd forced).
      const out2 = await runAcpxPromptFileAsync({ role: "analysis", promptFile, bin });
      assert.equal(out2.status, "ok");
      // cwd alias is honored too.
      const out3 = await runAcpxPromptFileAsync({ role: "analysis", promptFile, bin, cwd: wsDir });
      assert.equal(out3.status, "ok");
      assert.equal(fs.realpathSync(fs.readFileSync(cwdFile, "utf8").trim()), fs.realpathSync(wsDir));
    } finally {
      if (prevArgs === undefined) delete process.env.CA_IMPROVE_ACPX_ARGS;
      else process.env.CA_IMPROVE_ACPX_ARGS = prevArgs;
      fs.rmSync(wsDir, { recursive: true, force: true });
    }
  });

  it("runtime owns no direct model client or OpenCode fallback", async () => {
    const files = [
      "../src/acpx-text.js",
      "../src/analyze.js",
      "../src/consolidate.js",
      "../src/synthesize.js",
      "../src/annotate.js",
      "../src/pipeline.js",
    ];
    const { fileURLToPath } = await import("node:url");
    const here = path.dirname(fileURLToPath(import.meta.url));
    for (const rel of files) {
      const text = fs.readFileSync(path.join(here, rel), "utf8");
      assert.ok(!/fetch\s*\(/.test(text), `${rel} must not call fetch`);
      assert.ok(!/ANTHROPIC_API_KEY|OPENAI_API_KEY|apiKey\s*[:=]/i.test(text), `${rel} must own no API keys`);
      assert.ok(!/spawnSync\(\s*["']opencode/.test(text), `${rel} must not spawn opencode as a model fallback`);
      assert.ok(!/opencodeInvoke|directModelClient/i.test(text), `${rel} must not contain a direct model fallback`);
    }
  });
});

describe("synthesis strict text-only regression (Option 2)", () => {
  const RAW_SYNTHESIS_STDOUT = "Synthesis draft:\n\nThis is prose with no JSON object.\n";

  function makePromptFile() {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-synth-raw-"));
    const promptFile = path.join(dir, "prompt.md");
    fs.writeFileSync(promptFile, "PROMPT", "utf8");
    return { dir, promptFile };
  }

  it("sync synthesis blocks workspace before spawn", () => {
    const { dir, promptFile } = makePromptFile();
    const wsDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-synth-ws-"));
    try {
      let called = false;
      const spawnFn = () => {
        called = true;
        return { status: 0, stdout: `{"plans":[]}` };
      };
      const out = withEnv({ CA_IMPROVE_ACPX_ARGS: "pi exec" }, () =>
        runAcpxPromptFile({ role: "synthesis", promptFile, workspace: wsDir, spawnFn }),
      );
      assert.equal(out.status, "failed");
      assert.ok(/text-only/.test(out.error));
      assert.equal(called, false);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
      fs.rmSync(wsDir, { recursive: true, force: true });
    }
  });

  it("sync synthesis blocks cwd before spawn", () => {
    const { dir, promptFile } = makePromptFile();
    const wsDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-synth-ws-"));
    try {
      let called = false;
      const spawnFn = () => {
        called = true;
        return { status: 0, stdout: `{"plans":[]}` };
      };
      const out = withEnv({ CA_IMPROVE_ACPX_ARGS: "pi exec" }, () =>
        runAcpxPromptFile({ role: "synthesis", promptFile, cwd: wsDir, spawnFn }),
      );
      assert.equal(out.status, "failed");
      assert.ok(/text-only/.test(out.error));
      assert.equal(called, false);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
      fs.rmSync(wsDir, { recursive: true, force: true });
    }
  });

  it("async synthesis blocks workspace before spawn", async () => {
    const { runAcpxPromptFileAsync } = await import("../src/acpx-text.js");
    const { dir, promptFile } = makePromptFile();
    const wsDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-synth-ws-"));
    const prevArgs = process.env.CA_IMPROVE_ACPX_ARGS;
    process.env.CA_IMPROVE_ACPX_ARGS = "pi exec";
    try {
      let called = false;
      const spawnFn = () => {
        called = true;
        throw new Error("must not spawn");
      };
      const out = await runAcpxPromptFileAsync({ role: "synthesis", promptFile, workspace: wsDir, spawnFn });
      assert.equal(out.status, "failed");
      assert.ok(/text-only/.test(out.error));
      assert.equal(called, false);
    } finally {
      if (prevArgs === undefined) delete process.env.CA_IMPROVE_ACPX_ARGS;
      else process.env.CA_IMPROVE_ACPX_ARGS = prevArgs;
      fs.rmSync(dir, { recursive: true, force: true });
      fs.rmSync(wsDir, { recursive: true, force: true });
    }
  });

  it("async synthesis blocks cwd before spawn", async () => {
    const { runAcpxPromptFileAsync } = await import("../src/acpx-text.js");
    const { dir, promptFile } = makePromptFile();
    const wsDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-synth-ws-"));
    const prevArgs = process.env.CA_IMPROVE_ACPX_ARGS;
    process.env.CA_IMPROVE_ACPX_ARGS = "pi exec";
    try {
      let called = false;
      const spawnFn = () => {
        called = true;
        throw new Error("must not spawn");
      };
      const out = await runAcpxPromptFileAsync({ role: "synthesis", promptFile, cwd: wsDir, spawnFn });
      assert.equal(out.status, "failed");
      assert.ok(/text-only/.test(out.error));
      assert.equal(called, false);
    } finally {
      if (prevArgs === undefined) delete process.env.CA_IMPROVE_ACPX_ARGS;
      else process.env.CA_IMPROVE_ACPX_ARGS = prevArgs;
      fs.rmSync(dir, { recursive: true, force: true });
      fs.rmSync(wsDir, { recursive: true, force: true });
    }
  });

  it("sync synthesis rejects prose/fenced/trailing", () => {
    const { dir, promptFile } = makePromptFile();
    try {
      const cases = [
        RAW_SYNTHESIS_STDOUT,
        "```json\n{\"plans\":[]}\n```\n",
        "[acpx] tokens: input=1 output=2\n{\"plans\":[]}\n",
        `{"plans":[]} trailing prose`,
        `Here is your result: {"plans":[]} hope this helps`,
        JSON.stringify({ plans: [], extra: 1 }),
      ];
      for (const stdout of cases) {
        const out = withEnv({ CA_IMPROVE_ACPX_ARGS: "pi exec" }, () =>
          runAcpxPromptFile({ role: "synthesis", promptFile, spawnFn: () => ({ status: 0, stdout }) }),
        );
        assert.equal(out.status, "failed", `must reject ${JSON.stringify(stdout.slice(0, 40))}`);
        assert.ok(/malformed/.test(out.error));
      }
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it("async synthesis rejects prose/fenced/trailing", async () => {
    const { runAcpxPromptFileAsync } = await import("../src/acpx-text.js");
    const { dir, promptFile } = makePromptFile();
    const prevArgs = process.env.CA_IMPROVE_ACPX_ARGS;
    process.env.CA_IMPROVE_ACPX_ARGS = "pi exec";
    try {
      const binDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-synth-raw-bin-"));
      try {
        const bin = path.join(binDir, "fake-acpx");
        fs.writeFileSync(bin, `#!/bin/sh\ncat ${JSON.stringify(path.join(binDir, "out.txt"))}\n`, { mode: 0o755 });
        fs.chmodSync(bin, 0o755);
        const cases = [
          RAW_SYNTHESIS_STDOUT,
          "```json\n{\"plans\":[]}\n```\n",
          `{"plans":[]} trailing prose`,
          JSON.stringify({ plans: [], extra: 1 }),
        ];
        for (const stdout of cases) {
          fs.writeFileSync(path.join(binDir, "out.txt"), stdout);
          const out = await runAcpxPromptFileAsync({ role: "synthesis", promptFile, bin });
          assert.equal(out.status, "failed", `must reject ${JSON.stringify(stdout.slice(0, 40))}`);
          assert.ok(/malformed/.test(out.error));
        }
      } finally {
        fs.rmSync(binDir, { recursive: true, force: true });
      }
    } finally {
      if (prevArgs === undefined) delete process.env.CA_IMPROVE_ACPX_ARGS;
      else process.env.CA_IMPROVE_ACPX_ARGS = prevArgs;
      delete process.env.CA_IMPROVE_ACPX_BIN;
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it("sync/async synthesis accept exact plans JSON", async () => {
    const { runAcpxPromptFileAsync } = await import("../src/acpx-text.js");
    const { dir, promptFile } = makePromptFile();
    try {
      const out = withEnv({ CA_IMPROVE_ACPX_ARGS: "pi exec" }, () =>
        runAcpxPromptFile({
          role: "synthesis",
          promptFile,
          spawnFn: () => ({ status: 0, stdout: `  {"plans":[]}  \n` }),
        }),
      );
      assert.equal(out.status, "ok");
      assert.deepEqual(out.result, { plans: [] });
      const prevArgs = process.env.CA_IMPROVE_ACPX_ARGS;
      process.env.CA_IMPROVE_ACPX_ARGS = "pi exec";
      try {
        const binDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-synth-exact-bin-"));
        try {
          fs.writeFileSync(path.join(binDir, "out.txt"), `  {"plans":[]}  \n`);
          const bin = path.join(binDir, "fake-acpx");
          fs.writeFileSync(bin, `#!/bin/sh\ncat ${JSON.stringify(path.join(binDir, "out.txt"))}\n`, { mode: 0o755 });
          fs.chmodSync(bin, 0o755);
          const aout = await runAcpxPromptFileAsync({ role: "synthesis", promptFile, bin });
          assert.equal(aout.status, "ok");
          assert.deepEqual(aout.result, { plans: [] });
        } finally {
          fs.rmSync(binDir, { recursive: true, force: true });
        }
      } finally {
        if (prevArgs === undefined) delete process.env.CA_IMPROVE_ACPX_ARGS;
        else process.env.CA_IMPROVE_ACPX_ARGS = prevArgs;
      }
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it("non-synthesis extractor framing unchanged", () => {
    assert.deepEqual(extractAcpxFinalJson(`[acpx] tokens: input=10 output=47\n{"ok":true}\n[acpx] done\n`), { ok: true });
    assert.deepEqual(extractAcpxFinalJson(`Here is your result: {"ok":true} hope this helps`), { ok: true });
  });

  it("analysis/consolidate/annotate still fail strict JSON extraction on synthesis raw stdout", () => {
    const { dir, promptFile } = makePromptFile();
    try {
      for (const role of ["analysis", "consolidate", "annotate"]) {
        const out = withEnv({ CA_IMPROVE_ACPX_ARGS: "pi exec" }, () =>
          runAcpxPromptFile({
            role,
            promptFile,
            spawnFn: () => ({ status: 0, stdout: RAW_SYNTHESIS_STDOUT }),
          }),
        );
        assert.equal(out.status, "failed", `role=${role} must stay strict`);
        assert.ok(/unparseable/.test(out.error), `role=${role} must fail strict extraction`);
      }
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it("acpxSynthesisInvoke is text-only: rejects workspace/cwd and parses bounded plans", async () => {
    const { acpxSynthesisInvoke } = await import("../src/synthesize.js");
    const { dir, promptFile } = makePromptFile();
    const wsDir = fs.mkdtempSync(path.join(os.tmpdir(), "ca-synth-ws-"));
    try {
      let seenArgs;
      const plansStdout = JSON.stringify({ plans: [{ id: "e1", kind: "add", clusterId: "g-1", provisionalIntent: "do x", provisionalSources: ["s1", "s2"] }] });
      const spawnFn = (bin, args, opts) => {
        seenArgs = args;
        assert.equal(opts?.cwd, undefined, "text-only invoke must not forward cwd to spawn");
        return { status: 0, stdout: plansStdout };
      };
      assert.throws(() => withEnv({ CA_IMPROVE_ACPX_ARGS: "pi exec" }, () =>
        acpxSynthesisInvoke({ prompt: "P", promptFile, workspace: wsDir, spawnFn }),
      ), /text-only/);
      assert.throws(() => withEnv({ CA_IMPROVE_ACPX_ARGS: "pi exec" }, () =>
        acpxSynthesisInvoke({ prompt: "P", promptFile, cwd: wsDir, spawnFn }),
      ), /text-only/);
      const out = withEnv({ CA_IMPROVE_ACPX_ARGS: "pi exec" }, () =>
        acpxSynthesisInvoke({ prompt: "P", promptFile, spawnFn }),
      );
      assert.ok(seenArgs.includes("pi") && seenArgs.includes("exec"), "must run via shared pi exec argv");
      assert.equal(seenArgs[seenArgs.indexOf("--timeout") + 1], "300");
      assert.equal(seenArgs[seenArgs.indexOf("--model") + 1], SYNTHESIS_MODEL);
      assert.equal(out.status, "ok");
      assert.ok(Array.isArray(out.plans) && out.plans.length === 1);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
      fs.rmSync(wsDir, { recursive: true, force: true });
    }
  });
});
