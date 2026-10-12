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

  it("loads consolidate/synthesis/annotate prompts via the same strict loader", () => {
    for (const name of ["consolidate", "synthesis", "annotate", "annotate-preface"]) {
      const text = loadPrompt(name);
      assert.ok(text.length > 0, `${name} must load`);
    }
  });

  it("rejects missing prompt files with a clear error", () => {
    assert.throws(() => loadPrompt("nonexistent-prompt-xyz"), /not found|no such file/i);
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

  it("analysis/consolidate/synthesis/annotate/annotate-preface are the checked-in prompts", () => {
    const promptDir = path.join(HERE, "..", "prompts");
    const names = fs.readdirSync(promptDir).filter((f) => f.endsWith(".md")).sort();
    assert.deepEqual(names, ["analysis.md", "annotate-preface.md", "annotate.md", "consolidate.md", "synthesis.md"]);
    void RUNTIME_SRC;
  });

  it("annotate.md declares exactly its placeholders and required contract text", () => {
    const text = fs.readFileSync(path.join(HERE, "..", "prompts", "annotate.md"), "utf8");
    const tokens = [...text.matchAll(/\{\{([A-Za-z0-9_]+)\}\}/g)].map((m) => m[1]);
    assert.deepEqual([...new Set(tokens)].sort(), ["COUNT", "RUN_ID", "STAGED_CANDIDATES"]);
    assert.ok(!text.includes("ca-improve:self-session"), "sentinel lives in the loader, not the file");
    assert.ok(/Backpass/.test(text) && /0268201/.test(text) && /src\/prompts\/annotate\.md/.test(text));
    assert.ok(/annotations/.test(text) && /coverage/i.test(text) && /revert/i.test(text));
    assert.ok(/verbatim/i.test(text) && /quote/i.test(text) && /source/i.test(text));
    assert.ok(/counterevidence/i.test(text) && /none observed/i.test(text));
    assert.ok(/compilerImplication/i.test(text));
    assert.ok(/never/i.test(text) && /SOUL/.test(text) && /Hermes/.test(text));
  });

  it("annotate-preface.md declares exactly its placeholders and required contract text", () => {
    const text = fs.readFileSync(path.join(HERE, "..", "prompts", "annotate-preface.md"), "utf8");
    const tokens = [...text.matchAll(/\{\{([A-Za-z0-9_]+)\}\}/g)].map((m) => m[1]);
    assert.deepEqual([...new Set(tokens)].sort(), ["COUNT", "RUN_ID", "STAGED_SUMMARY"]);
    assert.ok(!text.includes("ca-improve:self-session"), "sentinel lives in the loader, not the file");
    assert.ok(/staged/i.test(text) && /fresh logical/i.test(text) && /revert/i.test(text));
  });

  it("renderPrompt renders annotate prompts with sentinel FIRST and strict placeholders", () => {
    const preface = renderPrompt("annotate-preface", { COUNT: "1", STAGED_SUMMARY: "s", RUN_ID: "run-T" });
    assert.ok(preface.startsWith(`${SELF_SESSION_SENTINEL}\n`));
    assert.ok(preface.includes("run-T"));
    const annotate = renderPrompt("annotate", { COUNT: "1", STAGED_CANDIDATES: "c", RUN_ID: "run-T" });
    assert.ok(annotate.startsWith(`${SELF_SESSION_SENTINEL}\n`));
    assert.ok(annotate.includes("run-T"));
    assert.throws(() => renderPrompt("annotate", { COUNT: "1", STAGED_CANDIDATES: "c" }), /RUN_ID/);
    assert.throws(
      () => renderPrompt("annotate-preface", { COUNT: "1", STAGED_SUMMARY: "s", RUN_ID: "r", EXTRA: "x" }),
      /EXTRA/,
    );
  });
});
