// A fake Langfuse v2 observations endpoint over fixture observations, shaped
// like the real harness traces (io fields arrive as JSON strings). Serves as
// an injectable `fetch` and, for CLI tests, as an HTTP server.

import http from "node:http";

import { langfuseClient } from "../src/langfuse.js";

const ROOT_NAMES = { hermes: "Hermes turn", claude: "Conversational Turn", opencode: "opencode.turn" };
const HOUR = 3600_000;
let counter = 0;
const nextId = () => `obs${String((counter += 1)).padStart(6, "0")}`;
const iso = (ms) => new Date(ms).toISOString();

function rootIo(harness, user, assistant) {
  if (harness === "hermes") {
    return { input: JSON.stringify({ role: "user", content: [{ type: "input_text", text: user }] }), output: JSON.stringify({ content: assistant, tool_calls: [] }) };
  }
  if (harness === "opencode") {
    return {
      input: JSON.stringify([{ role: "user", content: [{ type: "text", text: user }] }]),
      output: JSON.stringify([{ role: "assistant", content: [{ type: "text", text: assistant }] }]),
    };
  }
  return { input: JSON.stringify({ role: "user", content: user }), output: JSON.stringify({ role: "assistant", content: assistant }) };
}

function toolIo(harness, input, output) {
  if (harness === "opencode") return { input: JSON.stringify(input), output: JSON.stringify({ role: "tool", content: output }) };
  if (harness === "hermes") return { input: JSON.stringify(input), output: JSON.stringify({ output }) };
  return { input: JSON.stringify(input), output: JSON.stringify(output) };
}

/**
 * Observations for one session. Each turn is `{user, assistant, tools}`;
 * turns start at `start` and are `turnMs` apart. Hermes carries `platform`,
 * Claude carries `cwd`.
 */
export function sessionObservations(harness, id, {
  turns = [{ user: "bootstrap context please", assistant: "done", tools: [["read", { file_path: "a" }, "ok"], ["search", { query: "b" }, "ok"], ["test", { command: "c" }, "ok"]] }],
  start = Date.now() - 48 * HOUR,
  turnMs = 10 * 60_000,
  platform = "desktop",
  cwd = "/tmp/proj",
  source = "claude-code",
  environment = "default",
} = {}) {
  const out = [];
  turns.forEach((turn, index) => {
    const begin = start + index * turnMs;
    const rootId = nextId();
    const traceId = `trace-${rootId}`;
    const metadata = harness === "hermes" ? { platform, capture_mode: "sanitized" } : harness === "claude" ? { source, cwd } : {};
    out.push({
      id: rootId, traceId, sessionId: id, type: harness === "opencode" ? "AGENT" : "CHAIN", name: ROOT_NAMES[harness],
      isRootObservation: true, environment, startTime: iso(begin), endTime: iso(begin + 60_000), metadata,
      ...rootIo(harness, turn.user ?? "", turn.assistant ?? ""),
    });
    (turn.tools || []).forEach(([name, input, output], t) => {
      out.push({
        id: nextId(), traceId, sessionId: id, type: "TOOL", name: harness === "opencode" ? name : `Tool: ${name}`,
        isRootObservation: false, parentObservationId: rootId, environment, startTime: iso(begin + 1000 * (t + 1)), endTime: iso(begin + 1000 * (t + 1) + 500),
        metadata: {}, ...toolIo(harness, input, output),
      });
    });
    out.push({ id: nextId(), traceId, sessionId: id, type: "GENERATION", name: "LLM call 1", isRootObservation: false, parentObservationId: rootId, environment, startTime: iso(begin + 100), endTime: iso(begin + 200), metadata: {}, input: "[]", output: "null" });
  });
  return out;
}

/** A fake endpoint over a mutable observation list; `calls` records each request's query. */
export function fakeLangfuse(observations = [], { pageSize = null } = {}) {
  const calls = [];
  const state = { observations, failNext: [] };

  function handle(urlText, headers = {}) {
    const url = new URL(urlText);
    const q = Object.fromEntries(url.searchParams);
    calls.push(q);
    const status = state.failNext.shift();
    if (status) return { status, body: { message: "induced failure" } };
    if (!String(headers.authorization || headers.Authorization || "").startsWith("Basic ")) return { status: 401, body: { message: "unauthorized" } };
    if (url.pathname !== "/api/public/v2/observations") return { status: 404, body: { message: "not found" } };
    const fields = String(q.fields || "core,basic").split(",");
    let rows = state.observations.filter((o) =>
      (q.sessionId === undefined || o.sessionId === q.sessionId)
      && (q.name === undefined || o.name === q.name)
      && (q.traceId === undefined || o.traceId === q.traceId)
      && (q.isRootObservation === undefined || String(Boolean(o.isRootObservation)) === q.isRootObservation)
      && (q.fromStartTime === undefined || Date.parse(o.startTime) >= Date.parse(q.fromStartTime)));
    rows = [...rows].sort((a, b) => Date.parse(b.startTime) - Date.parse(a.startTime) || String(b.id).localeCompare(String(a.id)));
    const limit = Math.min(Number(q.limit || 50), pageSize ?? Infinity);
    const offset = Number(q.cursor || 0);
    const page = rows.slice(offset, offset + limit).map((o) => {
      const copy = { ...o };
      if (!fields.includes("io")) { delete copy.input; delete copy.output; }
      if (!fields.includes("metadata")) delete copy.metadata;
      if (!fields.includes("basic")) delete copy.isRootObservation;
      return copy;
    });
    return { status: 200, body: { data: page, meta: offset + limit < rows.length ? { cursor: String(offset + limit) } : {} } };
  }

  const fetch = async (url, init = {}) => {
    const { status, body } = handle(String(url), init.headers || {});
    return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
  };

  const client = langfuseClient({ baseUrl: "http://langfuse.test", publicKey: "pk", secretKey: "sk", fetch, retryDelayMs: 1 });

  /** Serve over HTTP for CLI tests; resolves to {url, close, env}. */
  async function serve() {
    const server = http.createServer((req, res) => {
      const { status, body } = handle(`http://localhost${req.url}`, req.headers);
      res.writeHead(status, { "content-type": "application/json" });
      res.end(JSON.stringify(body));
    });
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    const url = `http://127.0.0.1:${server.address().port}`;
    return {
      url,
      env: { LANGFUSE_BASE_URL: url, LANGFUSE_PUBLIC_KEY: "pk", LANGFUSE_SECRET_KEY: "sk" },
      close: () => new Promise((resolve) => server.close(resolve)),
    };
  }

  return {
    observations: state.observations,
    calls,
    client,
    fetch,
    serve,
    failNext: (...statuses) => state.failNext.push(...statuses),
    add: (harness, id, options) => { state.observations.push(...sessionObservations(harness, id, options)); },
  };
}
