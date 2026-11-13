import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import { loadPrompt, render, renderPrompt } from "../src/prompts.js";
import { SELF_SESSION_SENTINEL } from "../src/sentinel.js";
import { tmpDir } from "./helpers.mjs";

describe("prompt loader and strict render", () => {
  it("loads checked-in prompts relative to the runtime, not the cwd", () => {
    const previous = process.cwd();
    process.chdir(tmpDir());
    try {
      for (const name of ["analysis", "consolidate", "synthesis", "annotate"]) assert.ok(loadPrompt(name).length > 0);
    } finally {
      process.chdir(previous);
    }
  });

  it("rejects missing prompts and path traversal", () => {
    assert.throws(() => loadPrompt("nonexistent-prompt-xyz"), /not found/);
    assert.throws(() => loadPrompt("../LICENSE"), /invalid prompt name/);
  });

  it("renders every occurrence and fails on missing, unused, or malformed placeholders", () => {
    assert.equal(render("a {{X}} b {{X}} c", { X: "zee" }), "a zee b zee c");
    assert.throws(() => render("a {{MISSING}} b", {}), /MISSING/);
    assert.throws(() => render("a {{X}}", { X: "x", EXTRA: "e" }), /EXTRA/);
    assert.throws(() => render("a {{lowercase}}", { lowercase: "x" }), /unexpected/);
    assert.throws(() => render("a {{X}}", { X: "x", "bad-key": "y" }), /unexpected/);
  });

  it("does not re-render placeholder-shaped text injected through a value", () => {
    assert.equal(render("a {{X}}", { X: "{{Y}}" }), "a {{Y}}");
  });

  it("puts the self-session sentinel first, so the runtime's own calls are never analyzed", () => {
    const dir = tmpDir();
    fs.writeFileSync(path.join(dir, "probe.md"), "hello {{NAME}}");
    assert.equal(renderPrompt("probe", { NAME: "x" }, { promptsDir: dir }), `${SELF_SESSION_SENTINEL}\nhello x`);
  });
});
