import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { initialState, reduceEvent, renderFrame, startTui, tuiEligible } from "../src/tui.js";

describe("live progress view", () => {
  it("renders the four stages with live counts", () => {
    const state = initialState({ since: "30d", analyzer: "mock" });
    reduceEvent(state, "discover:start", { harnesses: ["codex", "hermes"] });
    reduceEvent(state, "discover:done", { transcripts: 3, perHarness: { codex: 2, hermes: 1 } });
    reduceEvent(state, "analyze:start", { total: 3, pending: 2, analyzer: "mock" });
    reduceEvent(state, "analyze:tick", { done: 1, ok: 1, failed: 0 });
    const text = renderFrame(state, { width: 90, now: 3500, spin: "⠋" }).join("\n");
    for (const label of ["cognitive assistant", "collect samples", "calculate loss", "aggregate gradients", "gradient descent", "1/2"]) {
      assert.ok(text.includes(label), label);
    }
    reduceEvent(state, "synthesize:done", { plans: 2, annotated: 2, edits: 1 });
    assert.match(renderFrame(state, { width: 90, spin: "⠋" }).join("\n"), /1 candidate edit\(s\) · 2\/2 annotated/);
  });

  it("only starts on a usable interactive terminal", () => {
    assert.equal(tuiEligible({ env: { TERM: "xterm-256color" }, stderr: { isTTY: true, columns: 80 } }), true);
    assert.equal(tuiEligible({ env: { TERM: "dumb" }, stderr: { isTTY: true, columns: 80 } }), false);
    assert.equal(tuiEligible({ env: { CI: "1" }, stderr: { isTTY: true, columns: 80 } }), false);
    assert.equal(tuiEligible({ env: {}, stderr: { isTTY: false, columns: 80 } }), false);
    assert.equal(tuiEligible({ env: {}, stderr: { isTTY: true, columns: 40 } }), false);
    assert.equal(startTui({}, { env: {}, stderr: { isTTY: false } }), null);
  });

  it("paints only stderr and restores the cursor on stop", () => {
    const written = [];
    const stderr = { isTTY: true, columns: 80, write: (s) => written.push(s) };
    const tui = startTui({ since: "30d" }, { env: { TERM: "xterm-256color" }, stderr });
    tui.event("discover:start", { harnesses: ["codex"] });
    tui.stop();
    assert.equal(written[0], "\x1b[?25l");
    assert.equal(written.at(-1), "\x1b[?25h");
    assert.ok(written.some((s) => s.includes("collect samples")));
  });
});
