import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { analyzeTraces } from "../src/analyze.js";

describe("trivial CA traces", () => {
  it("skips an eventless trace without sending it to ACPX", () => {
    let invoked = false;
    const [record] = analyzeTraces(
      [{ transcriptId: "empty-opencode", harness: "opencode", activity: { userTurns: 0, assistantTurns: 0, toolCalls: 0 }, distilled: "# session empty-opencode (opencode)\ncwd: /repo\n\nsource: /db\n" }],
      { invoke: () => { invoked = true; throw new Error("must not invoke ACPX"); } },
    );
    assert.equal(invoked, false);
    assert.equal(record.status, "skipped");
    assert.match(record.error, /trivial session \(0 user turn\(s\), 0 agent turn\(s\), 0 tool call\(s\)\)/);
  });

  it("retains a one-request autonomous run with substantial tool work", () => {
    let invoked = false;
    const [record] = analyzeTraces(
      [{ transcriptId: "substantial", harness: "opencode", activity: { userTurns: 1, assistantTurns: 0, toolCalls: 3 }, distilled: "# session substantial (opencode)\n\n## human\nship it\n\n- tool read: a\n- tool test: b\n- tool test: c\nsource: /db\n" }],
      { invoke: () => { invoked = true; return { status: "ok", evidence: { positive: [], negative: [], gaps: [] } }; } },
    );
    assert.equal(invoked, true);
    assert.equal(record.status, "ok");
  });
});
