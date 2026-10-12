import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";

import {
  loadPrompt,
  render,
  renderPrompt,
  SELF_SESSION_SENTINEL,
} from "../src/prompts.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RUNTIME_SRC = path.join(HERE, "..", "src");

describe("prompts loader (Backpass src/prompts.js shape, CA paths)", () => {
  it("loads checked-in prompts relative to the runtime, not CWD", () => {
    const elsewhere = fs.mkdtempSync(path.join(os.tmpdir(), "ca-prompts-cwd-"));
    const previous = process.cwd();
    process.chdir(elsewhere);
    try {
      const text = loadPrompt("analysis");
      assert.ok(text.includes("{{TRACE}}"), "analysis prompt must declare {{TRACE}}");
    } finally {
      process.chdir(previous);
    }
  });

  it("rejects missing prompt files with a clear error", () => {
    assert.throws(() => loadPrompt("consolidate"), /not found|no such file/i);
  });

  it("rejects path traversal in prompt names", () => {
    assert.throws(() => loadPrompt("../LICENSE"), /invalid prompt name/i);
  });

  it("replaces every declared {{PLACEHOLDER}} occurrence (duplicates render alike)", () => {
    const out = render("a {{X}} b {{X}} c", { X: "zee" });
    assert.equal(out, "a zee b zee c");
  });

  it("fails on a missing placeholder value", () => {
    assert.throws(() => render("a {{MISSING}} b", {}), /MISSING/);
  });

  it("fails on an unused value", () => {
    assert.throws(() => render("a {{X}}", { X: "x", EXTRA: "e" }), /EXTRA/);
  });

  it("fails on unexpected (non-UPPER_SNAKE) template tokens", () => {
    assert.throws(() => render("a {{lowercase}}", { lowercase: "x" }), /unexpected/i);
  });

  it("fails on unexpected value keys", () => {
    assert.throws(() => render("a {{X}}", { X: "x", "bad-key": "y" }), /unexpected|invalid/i);
  });

  it("renderPrompt keeps the self-session sentinel FIRST", () => {
    const out = renderPrompt(
      "analysis",
      {
        TRANSCRIPT_ID: "t1",
        HARNESS: "pi",
        SOUL_BASELINE: "soul",
        INTERACTION_POSTURE: "posture",
        EXPERIENCE_RECORDS: "records",
        TRACE: "trace",
      },
    );
    assert.ok(out.startsWith(`${SELF_SESSION_SENTINEL}\n`), "sentinel must be the first line");
    assert.equal(SELF_SESSION_SENTINEL, "<!-- ca-improve:self-session -->");
  });

  it("analysis.md is the only checked-in prompt (no consolidate/synthesis/annotate)", () => {
    const promptDir = path.join(HERE, "..", "prompts");
    const names = fs.readdirSync(promptDir).filter((f) => f.endsWith(".md")).sort();
    assert.deepEqual(names, ["analysis.md"]);
    void RUNTIME_SRC;
  });
});
