// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Deterministic distillation adapted from Backpass src/distill.js (commit
// 0268201): keep the human/agent signal, one-line tool shapes, drop
// boilerplate. No model involved.

const TOOL_INPUT_CHARS = 160;
const TOOL_OUTPUT_CHARS = 200;
const MESSAGE_CHARS = 6000;
const ATTACHED_MARKER = "--- Attached Context ---";

function attachedSummary(attachment) {
  const chars = String(attachment ?? "").length;
  return `attached context (${chars} chars elided)`;
}

function splitAttachedContext(text) {
  const raw = String(text ?? "");
  const idx = raw.indexOf(ATTACHED_MARKER);
  if (idx === -1) return null;
  return {
    intent: raw.slice(0, idx).trim(),
    attachment: raw.slice(idx + ATTACHED_MARKER.length).trim(),
  };
}

function oneLine(text, limit) {
  const flat = String(text ?? "").replace(/\s+/g, " ").trim();
  return flat.length > limit ? `${flat.slice(0, limit)}...` : flat;
}

function clampMessage(text) {
  const trimmed = String(text ?? "").trim();
  if (trimmed.length <= MESSAGE_CHARS) return trimmed;
  const head = trimmed.slice(0, MESSAGE_CHARS - 1200);
  const tail = trimmed.slice(-1000);
  return `${head}\n\n[... ${trimmed.length - MESSAGE_CHARS} chars elided ...]\n\n${tail}`;
}

function describeToolInput(input) {
  if (input === null || input === undefined) return "";
  if (typeof input === "string") return oneLine(input, TOOL_INPUT_CHARS);
  for (const key of ["command", "cmd", "file_path", "path", "pattern", "query", "url", "description"]) {
    if (typeof input[key] === "string" && input[key].trim()) {
      return oneLine(input[key], TOOL_INPUT_CHARS);
    }
  }
  try {
    return oneLine(JSON.stringify(input), TOOL_INPUT_CHARS);
  } catch {
    return "";
  }
}

const BOILERPLATE = [
  /^<system-reminder>/,
  /^<user_info>/,
  /^<recommended_plugins>/,
  /^<permissions instructions>/,
  /^<env>/,
  /^Caveat: The messages below were generated/,
];

function isBoilerplate(text) {
  const trimmed = String(text ?? "").trim();
  if (!trimmed) return true;
  return BOILERPLATE.some((re) => re.test(trimmed));
}

/**
 * Normalized events accepted:
 *   { kind: 'message', role: 'user'|'assistant', text }
 *   { kind: 'tool', name, input, result }
 * Thinking/reasoning events are dropped (noise for this purpose).
 */
export function distill(events, meta = {}) {
  const lines = [];
  lines.push(`# session ${meta.id || "unknown"} (${meta.harness || "unknown"})`);
  if (meta.cwd) lines.push(`cwd: ${meta.cwd}`);
  lines.push("");
  for (const event of events || []) {
    if (!event || typeof event !== "object") continue;
    if (event.kind === "message") {
      if (event.role === "assistant" && !String(event.text ?? "").trim()) continue;
      const split = splitAttachedContext(event.text);
      if (split) {
        const intent = clampMessage(split.intent);
        if (intent && !isBoilerplate(intent)) {
          const role = event.role === "assistant" ? "agent" : "human";
          lines.push(`## ${role}`);
          lines.push(intent);
          lines.push("");
        }
        lines.push(`- tool context: ${attachedSummary(split.attachment)}`);
        continue;
      }
      const text = clampMessage(event.text);
      if (isBoilerplate(text)) continue;
      const role = event.role === "assistant" ? "agent" : "human";
      lines.push(`## ${role}`);
      lines.push(text);
      lines.push("");
    } else if (event.kind === "tool") {
      const input = describeToolInput(event.input);
      const result = event.result == null ? "" : oneLine(typeof event.result === "string" ? event.result : JSON.stringify(event.result), TOOL_OUTPUT_CHARS);
      lines.push(`- tool ${event.name || "unknown"}${input ? `: ${input}` : ""}${result ? ` => ${result}` : ""}`);
    }
  }
  lines.push(`source: langfuse session ${meta.id || "unknown"}`);
  const trace = lines.join("\n");
  if (trace.length <= 24000) return trace;
  const head = trace.slice(0, 16000);
  const tail = trace.slice(-7900);
  return `${head}\n\n[... ${trace.length - head.length - tail.length} chars elided ...]\n\n${tail}`;
}
