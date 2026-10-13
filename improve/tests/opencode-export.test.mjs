import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { opencodeExportToEvents } from "../src/opencode-export.js";

describe("OpenCode export recovery", () => {
  it("normalizes exported messages and parts when SQLite has only session headers", () => {
    const events = opencodeExportToEvents({
      info: { model: { id: "gpt-5.6-terra" } },
      messages: [
        { info: { role: "user" }, parts: [{ type: "text", text: "Investigate the failure" }] },
        { info: { role: "assistant" }, parts: [
          { type: "text", text: "I will inspect the trace." },
          { type: "tool", tool: "read_file", state: { input: { path: "trace.json" }, output: "read ok", status: "completed" } },
        ] },
      ],
    });
    assert.equal(events.model, "gpt-5.6-terra");
    assert.deepEqual(events.events, [
      { kind: "message", role: "user", text: "Investigate the failure" },
      { kind: "message", role: "assistant", text: "I will inspect the trace." },
      { kind: "tool", name: "read_file", input: { path: "trace.json" }, result: "read ok", status: "completed" },
    ]);
  });
});
