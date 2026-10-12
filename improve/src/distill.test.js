import test from "node:test";
import assert from "node:assert/strict";

import { distill, recordToEvents } from "./distill.js";

const ATTACHED_MARKER = "--- Attached Context ---";

function liveRecords() {
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
    records: [
      { role: "user", content: userContent },
      { role: "assistant", content: "" },
      { role: "tool", content: toolPayload },
      { role: "assistant", content: "nix.dev is the official documentation site." },
    ],
  };
}

function distilledFor(records) {
  const events = records.flatMap((r) => recordToEvents(r));
  return { events, trace: distill(events, { id: "ca-live", harness: "test" }) };
}

test("CA live shape: intent + reply kept, attachment dump excluded, tool summarized, empty assistant dropped", () => {
  const { pageBody, toolPayload, records } = liveRecords();
  const { events, trace } = distilledFor(records);

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

  // Events themselves carry no dump (defense in depth).
  for (const e of events) {
    if (e.kind === "tool") {
      assert.ok(!String(e.input ?? "").includes("Skip to main content"), "tool event input never carries page body");
    }
    if (e.kind === "message") {
      assert.ok(!String(e.text ?? "").includes("Skip to main content"), "message event never carries page body");
    }
  }
});

test("pre-normalized role:'tool' message normalizes to one-line tool event, empty assistant dropped at normalization", () => {
  const toolPayload = JSON.stringify({
    action: "fetch",
    url: "https://nix.dev",
    body: `tool-body-marker-${"x".repeat(500)}`,
  });
  const preNormalized = [
    { kind: "message", role: "user", text: "What is nix.dev?" },
    { kind: "message", role: "assistant", text: "" },
    { kind: "message", role: "assistant", text: "   " },
    { kind: "message", role: "tool", text: toolPayload },
  ];
  const events = preNormalized.flatMap((r) => recordToEvents(r));

  // Empty pre-normalized assistant messages are dropped during normalization.
  assert.ok(
    !events.some((e) => e.kind === "message" && e.role === "assistant" && !String(e.text ?? "").trim()),
    "empty pre-normalized assistant message absent from events",
  );

  // Pre-normalized role:'tool' becomes a tool event, not a message.
  assert.ok(!events.some((e) => e.kind === "message" && e.role === "tool"), "no role:'tool' message survives normalization");
  const toolEvents = events.filter((e) => e.kind === "tool");
  assert.equal(toolEvents.length, 1, `expected 1 normalized tool event, got ${toolEvents.length}`);

  const trace = distill(events, { id: "ca-prenorm", harness: "test" });
  assert.ok(!trace.includes("## human") || (trace.match(/## human/g) || []).length === 1, "tool payload does not render as extra human block");
  assert.ok(!trace.includes(toolPayload), "raw pre-normalized tool payload excluded");
  assert.ok(!trace.includes("x".repeat(100)), "long pre-normalized tool body truncated to one-line summary");
  const toolLines = trace.split("\n").filter((l) => l.startsWith("- tool"));
  assert.equal(toolLines.length, 1, `expected 1 one-line tool event, got:\n${trace}`);
  assert.equal(toolLines[0].trim().split("\n").length, 1, "pre-normalized tool event stays one line");
  assert.ok(!trace.includes("## human\n" + toolPayload.slice(0, 20)), "tool content never renders as human block");
});
