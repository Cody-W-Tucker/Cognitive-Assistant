// OpenCode 1.18 may retain session metadata in SQLite while serving message
// parts only through its export command. This adapter recovers those parts
// without a model call; malformed exports remain an empty, skippable trace.
import { spawn, spawnSync } from "node:child_process";

export function opencodeExportToEvents(exported) {
  const events = [];
  const messages = Array.isArray(exported?.messages) ? exported.messages : [];
  for (const message of messages) {
    const role = message?.info?.role === "assistant" ? "assistant" : message?.info?.role === "user" ? "user" : null;
    if (!role) continue;
    for (const part of Array.isArray(message?.parts) ? message.parts : []) {
      if (part?.type === "text" && typeof part.text === "string" && part.text.trim()) {
        events.push({ kind: "message", role, text: part.text });
      } else if (role === "assistant" && part?.type === "tool") {
        const state = part.state && typeof part.state === "object" ? part.state : {};
        const output = typeof state.output === "string" ? state.output : "";
        const error = typeof state.error?.message === "string" ? state.error.message : "";
        events.push({
          kind: "tool",
          name: String(part.tool || part.name || "tool"),
          input: state.input,
          ...(output || error ? { result: [error, output].filter(Boolean).join("\n") } : {}),
          ...(state.status ? { status: state.status } : {}),
        });
      }
    }
  }
  return { events, model: exported?.info?.model?.id || exported?.info?.model?.modelID || null };
}

export function readOpencodeExport(sessionId, { bin = process.env.CA_IMPROVE_OPENCODE_BIN || "opencode", spawnFn = spawnSync } = {}) {
  const result = spawnFn(bin, ["export", String(sessionId)], { encoding: "utf8", timeout: 30_000, maxBuffer: 16 * 1024 * 1024 });
  if (result?.error) return { events: [], model: null, error: `opencode export failed: ${result.error.message}` };
  if (result?.status !== 0) return { events: [], model: null, error: `opencode export exited ${result?.status ?? "unknown"}` };
  try {
    return opencodeExportToEvents(JSON.parse(result.stdout));
  } catch {
    return { events: [], model: null, error: "opencode export returned invalid JSON" };
  }
}

/** Non-blocking export for the bounded collection worker pool. */
export async function readOpencodeExportAsync(sessionId, { bin = process.env.CA_IMPROVE_OPENCODE_BIN || "opencode" } = {}) {
  return await new Promise((resolve) => {
    let child;
    try { child = spawn(bin, ["export", String(sessionId)], { stdio: ["ignore", "pipe", "pipe"] }); }
    catch (err) { resolve({ events: [], model: null, error: `opencode export failed: ${err.message}` }); return; }
    let stdout = "", stderr = "";
    const timer = setTimeout(() => child.kill("SIGTERM"), 30_000);
    child.stdout.on("data", (part) => { stdout += part; });
    child.stderr.on("data", (part) => { stderr += part; });
    child.on("error", (err) => { clearTimeout(timer); resolve({ events: [], model: null, error: `opencode export failed: ${err.message}` }); });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) { resolve({ events: [], model: null, error: `opencode export exited ${code ?? "unknown"}: ${stderr.trim()}` }); return; }
      try { resolve(opencodeExportToEvents(JSON.parse(stdout))); }
      catch { resolve({ events: [], model: null, error: "opencode export returned invalid JSON" }); }
    });
  });
}
