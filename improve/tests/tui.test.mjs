import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { initialState, reduceEvent, renderFrame, startTuiProcess, tuiEligible } from "../src/tui.js";

describe("CA improvement live TUI", () => {
  it("uses the Backpass-shaped four-stage rail without touching JSON output", () => {
    const state = initialState({ since: "30d", analyzer: "mock" });
    reduceEvent(state, "discover:start", { harnesses: ["codex", "hermes"] }, 1000);
    reduceEvent(state, "discover:done", { transcripts: 3, perHarness: { codex: 2, hermes: 1 } }, 2000);
    reduceEvent(state, "analyze:start", { total: 3, pending: 2, cached: 1, analyzer: "mock" }, 2000);
    reduceEvent(state, "analyze:tick", { done: 1, ok: 1, failed: 0 }, 3000);

    const lines = renderFrame(state, { width: 90, now: 3500, spin: "⠋" });
    const text = lines.join("\n");
    assert.match(text, /cognitive assistant/);
    assert.match(text, /collect samples/);
    assert.match(text, /calculate loss/);
    assert.match(text, /aggregate gradients/);
    assert.match(text, /gradient descent/);
    assert.match(text, /1\/2/);
  });

  it("only starts on a usable interactive terminal", () => {
    assert.equal(tuiEligible({ env: { TERM: "xterm-256color" }, stderr: { isTTY: true, columns: 80 } }), true);
    assert.equal(tuiEligible({ env: { TERM: "dumb" }, stderr: { isTTY: true, columns: 80 } }), false);
    assert.equal(tuiEligible({ env: { CI: "1" }, stderr: { isTTY: true, columns: 80 } }), false);
    assert.equal(tuiEligible({ env: {}, stderr: { isTTY: false, columns: 80 } }), false);
  });

  it("runs rendering in a separate event loop so synchronous ACPX calls cannot freeze it", () => {
    const written = [];
    let killed = false;
    const child = { stdin: { write: (line) => written.push(line), end: () => written.push("END") }, kill: () => { killed = true; } };
    const tui = startTuiProcess({ since: "30d" }, { env: { TERM: "xterm-256color" }, stderr: { isTTY: true, columns: 80 }, spawnFn: () => child });
    tui.event("discover:start", { harnesses: ["codex"] });
    tui.stop();
    assert.match(written[0], /"type":"start"/);
    assert.match(written[1], /"event":"discover:start"/);
    assert.equal(written.at(-1), "END");
    assert.equal(killed, false, "graceful stdin close lets the renderer erase itself");
  });
});
