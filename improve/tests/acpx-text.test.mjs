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
      assert.deepEqual(buildAcpxArgs({}), [...ACPX_TEXT_FORMAT_ARGS]);
      assert.ok(ACPX_TEXT_FORMAT_ARGS.includes("quiet"));
    });
  });

  it("keeps explicit caller agent as trailing callable positional (after globals/format)", () => {
    withEnv({ CA_IMPROVE_ACPX_ARGS: undefined }, () => {
      const args = buildAcpxArgs({ agent: "codex" });
      assert.deepEqual(args, [...ACPX_TEXT_FORMAT_ARGS, "codex"]);
      assert.equal(args[args.length - 1], "codex");
      assert.ok(args.includes("--format") && args.includes("quiet"));
    });
  });

  it("preserves CA_IMPROVE_ACPX_ARGS global extra args before format/agent", () => {
    withEnv({ CA_IMPROVE_ACPX_ARGS: "--timeout 30 --model x" }, () => {
      const args = buildAcpxArgs({ agent: "codex" });
      assert.deepEqual(args, ["--timeout", "30", "--model", "x", "--format", "quiet", "codex"]);
      assert.ok(args.indexOf("--timeout") < args.indexOf("--format"));
      assert.equal(args[args.length - 1], "codex");
    });
  });

  it("supports Pi via ACPX with globals before agent (valid CLI shape, spawn-ready)", () => {
    withEnv({ CA_IMPROVE_ACPX_ARGS: "--env KEY=value" }, () => {
      const args = buildAcpxArgs({ agent: "pi" });
      // Valid: `acpx --env KEY=value --format quiet pi ...` (... = prompt/input appended downstream).
      assert.deepEqual(args, ["--env", "KEY=value", "--format", "quiet", "pi"]);
      // Guard the invalid old ordering: `acpx pi --format quiet --env KEY=value ...`.
      assert.notDeepEqual(args, ["pi", "--format", "quiet", "--env", "KEY=value"]);
      // Builder return is suitable for spawn where downstream appends prompt/input.
      assert.deepEqual([...args, "PROMPT"], ["--env", "KEY=value", "--format", "quiet", "pi", "PROMPT"]);
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
        "--model",
        ANALYSIS_MODEL,
        "--format",
        "quiet",
        "pi",
        "exec",
      ]);
      assert.deepEqual(buildAcpxArgs({ model: modelForRole("synthesis") }), [
        "--model",
        SYNTHESIS_MODEL,
        "--format",
        "quiet",
        "pi",
        "exec",
      ]);
    });
  });

  it("never requests JSON-RPC by default", () => {
    withEnv({ CA_IMPROVE_ACPX_ARGS: undefined }, () => {
      const args = buildAcpxArgs({ agent: "pi" });
      assert.ok(!args.includes("json") || args.includes("quiet"));
      assert.ok(args.includes("quiet"));
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
    assert.equal(extractAcpxFinalJson(`[{"plans": []}]`), null);
  });

  it("rejects arbitrary embedded JSON and model prose", () => {
    assert.equal(extractAcpxFinalJson(`Here is your result: {"plans": []} hope this helps`), null);
    assert.equal(
      extractAcpxFinalJson(`Sure! {"plans": [{"clusterId": "g-a"}]} Let me explain...`),
      null,
    );
    assert.equal(
      extractAcpxFinalJson(`\`\`\`json\n{"a": 1}\n\`\`\`\n\`\`\`json\n{"b": 2}\n\`\`\`\n`),
      null,
    );
  });

  it("rejects non-json fences and content outside a single fence", () => {
    assert.equal(extractAcpxFinalJson("```python\n{\"a\": 1}\n```\n"), null);
    assert.equal(extractAcpxFinalJson("prefix\n```json\n{\"a\": 1}\n```\n"), null);
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

  it("rejects Pi preamble whose version line has trailing prose (strict version token)", () => {
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
    assert.equal(extractAcpxFinalJson(out), null);
    assert.equal(stripPiQuietPreamble(out), out);
  });

  it("rejects non-Pi prose preambles fail-closed (no generic prose stripping)", () => {
    assert.equal(extractAcpxFinalJson(`Hello from Pi\n\n{"ready": true}\n`), null);
    assert.equal(
      extractAcpxFinalJson(`pi v0.5.1\nSome intro prose\n\n{"ready": true}\n`),
      null,
    );
    assert.equal(extractAcpxFinalJson(`Version pi v1\n\n{"ready": true}\n`), null);
  });

  it("rejects malformed/unknown-section Pi-like preambles fail-closed", () => {
    const base = (head) => `${head}\n{"ready": true}\n`;
    // Missing Skills section.
    assert.equal(
      extractAcpxFinalJson(base(`pi v0.5.1\n----------\n\nContext\n  - a`)),
      null,
    );
    // Unknown extra section after Skills.
    assert.equal(
      extractAcpxFinalJson(
        base(`pi v0.5.1\n----------\n\nContext\n  - a\n\nSkills\n  - b\n\nTools\n  - c`),
      ),
      null,
    );
    // Separator with trailing prose is not the known shape.
    assert.equal(
      extractAcpxFinalJson(base(`pi v0.5.1\n---------- done\n\nContext\n  - a\n\nSkills\n  - b`)),
      null,
    );
    // Empty Context list is malformed.
    assert.equal(
      extractAcpxFinalJson(base(`pi v0.5.1\n----------\n\nContext\n\nSkills\n  - b`)),
      null,
    );
  });

  it("stays fail-closed after a valid Pi preamble (rpc / multiple / array)", () => {
    const head = `pi v0.5.1\n----------\n\nContext\n  - a\n\nSkills\n  - b\n\n`;
    assert.equal(
      extractAcpxFinalJson(`${head}{"jsonrpc": "2.0", "id": 1, "result": {}}\n`),
      null,
    );
    assert.equal(extractAcpxFinalJson(`${head}{"a": 1}\n{"b": 2}\n`), null);
    assert.equal(extractAcpxFinalJson(`${head}[1, 2, 3]\n`), null);
    assert.equal(extractAcpxFinalJson(`${head}{"a": 1} trailing prose\n`), null);
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

  it("rejects live Pi upgrade-notice tail with a second prose line fail-closed", () => {
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
    assert.equal(extractAcpxFinalJson(out), null);
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

  it("analysis real call passes text-output argv and extracts ACPX-framed evidence", async () => {
    const { acpxInvoke } = await import("../src/analyze.js");
    const argFile = path.join(tmp, "args.txt");
    const stdout = `[acpx] tokens: input=3 output=9\n{"status": "ok", "positive": [], "negative": [], "gaps": []}\n`;
    process.env.CA_IMPROVE_ACPX_BIN = fakeBin({ stdout, recordArgs: argFile });
    const out = acpxInvoke({
      trace: { transcriptId: "t1", harness: "pi", distilled: "hi" },
      prompt: "PROMPT",
    });
    assert.equal(out.status, "ok");
    assert.deepEqual(out.evidence, { status: "ok", positive: [], negative: [], gaps: [] });
    const argv = recordedArgs(argFile);
    assert.ok(argv.includes("--format") && argv.includes("quiet"), `argv was ${argv.join(" ")}`);
  });

  it("synthesis real call rejects JSON-RPC stdout fail-closed", async () => {
    const { acpxSynthesisInvoke } = await import("../src/synthesize.js");
    const argFile = path.join(tmp, "args2.txt");
    process.env.CA_IMPROVE_ACPX_BIN = fakeBin({
      stdout: `{"jsonrpc": "2.0", "id": 1, "result": {"plans": []}}\n`,
      recordArgs: argFile,
    });
    const out = acpxSynthesisInvoke({ prompt: "P" });
    assert.equal(out.status, "failed");
    assert.ok(/unparseable/.test(out.error));
  });

  it("consolidation real call rejects ambiguous stdout fail-closed", async () => {
    const { acpxConsolidateInvoke } = await import("../src/consolidate.js");
    const argFile = path.join(tmp, "args3.txt");
    process.env.CA_IMPROVE_ACPX_BIN = fakeBin({
      stdout: `{"merges": []}\n{"merges": []}\n`,
      recordArgs: argFile,
    });
    const out = acpxConsolidateInvoke({ prompt: "P" });
    assert.equal(out.status, "failed");
  });

  it("annotate real calls extract preface + final through the strict path", async () => {
    const { acpxAnnotatePrefaceInvoke, acpxAnnotateInvoke, annotateStaging } = await import(
      "../src/annotate.js"
    );
    const preFile = path.join(tmp, "pre.txt");
    process.env.CA_IMPROVE_ACPX_BIN = fakeBin({
      stdout: `[acpx] tokens: input=1 output=1\n{"ready": true}\n`,
      recordArgs: preFile,
    });
    const pre = acpxAnnotatePrefaceInvoke({ prompt: "PREFACE" });
    assert.equal(pre.status, "ok");
    assert.deepEqual(pre.result, { ready: true });

    const annFile = path.join(tmp, "ann.txt");
    process.env.CA_IMPROVE_ACPX_BIN = fakeBin({
      stdout: `{"annotations": [{"id": "e1", "verdict": "drop", "reason": "x"}]}\n`,
      recordArgs: annFile,
    });
    const ann = acpxAnnotateInvoke({ prompt: "ANNOTATE" });
    assert.equal(ann.status, "ok");

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
    // A fully-evidenced extracted record passes.
    const good = {
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
