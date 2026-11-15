import test from "node:test";
import assert from "node:assert/strict";

import { distill } from "../src/distill.js";

const ATTACHED_MARKER = "--- Attached Context ---";

test("long sessions retain both the beginning and the outcome", () => {
  const events = [
    { kind: "message", role: "user", text: "START" },
    ...Array.from({ length: 50 }, (_, i) => ({ kind: "message", role: "assistant", text: `${i} ${"x".repeat(1000)}` })),
    { kind: "message", role: "assistant", text: "FINAL OUTCOME" },
  ];
  const trace = distill(events, { id: "long" });
  assert.ok(trace.includes("START"));
  assert.ok(trace.includes("FINAL OUTCOME"));
  assert.match(trace, /\[\.\.\. \d+ chars elided \.\.\.\]/);
  assert.ok(trace.length <= 24000);
});

function liveEvents() {
  const pageBody = `page-body-marker-${"lorem ipsum dolor sit amet ".repeat(40)}`;
  const userContent = `What is nix.dev?\n\n${ATTACHED_MARKER}\nSkip to main content\n${pageBody}`;
  const toolPayload = JSON.stringify({
    action: "fetch",
    url: "https://nix.dev",
    body: `tool-body-marker-${"x".repeat(500)}`,
  });
  return {
    pageBody,
    toolPayload,
    events: [
      { kind: "message", role: "user", text: userContent },
      { kind: "message", role: "assistant", text: "" },
      { kind: "tool", name: "tool", input: toolPayload },
      { kind: "message", role: "assistant", text: "nix.dev is the official documentation site." },
    ],
  };
}

test("CA live shape: intent + reply kept, attachment dump excluded, tool summarized, empty assistant dropped", () => {
  const { pageBody, toolPayload, events } = liveEvents();
  const trace = distill(events, { id: "ca-live", harness: "test" });

  // User intent + assistant reply preserved.
  assert.ok(trace.includes("What is nix.dev?"), "distilled trace keeps pre-marker user intent");
  assert.ok(
    trace.includes("nix.dev is the official documentation site."),
    "distilled trace keeps short assistant reply",
  );

  // Attachment dump never leaks as page body.
  assert.ok(!trace.includes("Skip to main content"), "attached page boilerplate excluded");
  assert.ok(!trace.includes("page-body-marker-"), "attached page body excluded");
  assert.ok(!trace.includes(pageBody.slice(0, 200)), "original attachment dump excluded");

  // Attachment represented as a short one-line summary, not the dump.
  const contextLines = trace.split("\n").filter((l) => l.startsWith("- tool") && /context/i.test(l));
  assert.ok(contextLines.length >= 1, `expected one-line tool/context summary, got:\n${trace}`);
  for (const line of contextLines) {
    assert.ok(line.length < 300, `context summary stays short, got ${line.length} chars`);
    assert.ok(!line.includes("Skip to main content"), "context summary is not the page dump");
  }

  // Tool JSON is one summarized one-line tool event, not the raw dump.
  const toolLines = trace.split("\n").filter((l) => l.startsWith("- tool"));
  assert.ok(toolLines.length >= 2, `expected attachment + tool JSON events, got:\n${trace}`);
  for (const line of toolLines) {
    assert.equal(line.trim().split("\n").length, 1, "tool event stays one line");
  }
  assert.ok(!trace.includes(toolPayload), "raw tool JSON dump excluded");
  assert.ok(!trace.includes("x".repeat(100)), "long tool body truncated to one-line summary");

  // Empty assistant message absent: only the short reply renders as an agent block.
  const agentBlocks = trace.match(/## agent/g) || [];
  assert.equal(agentBlocks.length, 1, `empty assistant dropped, expected 1 agent block, got ${agentBlocks.length}`);
  const humanBlocks = trace.match(/## human/g) || [];
  assert.equal(humanBlocks.length, 1, `expected 1 human block, got ${humanBlocks.length}`);
});

test("tool event renders as one summarized line, empty assistant messages dropped", () => {
  const toolPayload = JSON.stringify({
    action: "fetch",
    url: "https://nix.dev",
    body: `tool-body-marker-${"x".repeat(500)}`,
  });
  const events = [
    { kind: "message", role: "user", text: "What is nix.dev?" },
    { kind: "message", role: "assistant", text: "" },
    { kind: "message", role: "assistant", text: "   " },
    { kind: "tool", name: "tool", input: toolPayload },
  ];

  const trace = distill(events, { id: "ca-prenorm", harness: "test" });
  assert.equal((trace.match(/## agent/g) || []).length, 0, "empty assistant messages dropped");
  assert.ok(!trace.includes("## human") || (trace.match(/## human/g) || []).length === 1, "tool payload does not render as extra human block");
  assert.ok(!trace.includes(toolPayload), "raw tool payload excluded");
  assert.ok(!trace.includes("x".repeat(100)), "long tool body truncated to one-line summary");
  const toolLines = trace.split("\n").filter((l) => l.startsWith("- tool"));
  assert.equal(toolLines.length, 1, `expected 1 one-line tool event, got:\n${trace}`);
  assert.equal(toolLines[0].trim().split("\n").length, 1, "tool event stays one line");
  assert.ok(!trace.includes("## human\n" + toolPayload.slice(0, 20)), "tool content never renders as human block");
});

test("tool results survive distillation in bounded form", () => {
  const trace = distill([{ kind: "tool", name: "test", input: { command: "npm test" }, result: `FAIL regression ${"x".repeat(500)}` }]);
  assert.match(trace, /tool test: npm test => FAIL regression/);
  assert.ok(!trace.includes("x".repeat(250)));
});
