// Model boundary: one prompt in, one JSON object out.
//
// Every model call is a single OpenAI-compatible chat completion with no
// tools; the reply is only ever parsed as data and validated by the stage
// that asked for it. Code, not the model, decides every path and field that
// is written.
//
// Configuration (environment, never model-controlled):
//   CA_LLM_BASE_URL            OpenAI-compatible base, e.g. http://nas:8080/v1
//   CA_LLM_MODEL               model for every role
//   CA_LLM_MODEL_<ROLE>        per-role override (ANALYSIS, CONSOLIDATE, SYNTHESIS, ANNOTATE)
//   CA_LLM_API_KEY_FILE        optional file holding a bearer key (inference-only)
//   CA_LLM_RETRY_DELAYS_MS     retry backoff for 429/5xx/network errors (default 5000,20000)
//
// Reproducibility: temperature 0, fixed seed, JSON-only output, and every
// parseable reply is cached under sha256(request), so re-running an
// unchanged prompt returns the identical reply without a call.

import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const ROLES = {
  analysis: { timeoutSec: 180, maxTokens: 4000 },
  consolidate: { timeoutSec: 180, maxTokens: 4000 },
  synthesis: { timeoutSec: 300, maxTokens: 6000 },
  annotate: { timeoutSec: 300, maxTokens: 8000 },
};

/** Endpoint and model for a role, from the environment only. */
export function modelConfig(role, env = process.env) {
  if (!ROLES[role]) throw new Error(`unknown model role: ${role}`);
  const baseUrl = String(env.CA_LLM_BASE_URL || "").replace(/\/+$/, "");
  const model = env[`CA_LLM_MODEL_${role.toUpperCase()}`] || env.CA_LLM_MODEL || "";
  if (!baseUrl) throw new Error("CA_LLM_BASE_URL is not set (OpenAI-compatible endpoint, e.g. http://host:8080/v1)");
  if (!model) throw new Error(`no model for role ${role}: set CA_LLM_MODEL or CA_LLM_MODEL_${role.toUpperCase()}`);
  return { baseUrl, model, apiKeyFile: env.CA_LLM_API_KEY_FILE || null };
}

/** Preflight for a real run: every role is configured; no model traffic. */
export function checkModelConfigured(env = process.env) {
  try {
    for (const role of Object.keys(ROLES)) modelConfig(role, env);
  } catch (err) {
    return { ok: false, error: `${err.message}. No traces were analyzed and no evidence was written.` };
  }
  if (env.CA_LLM_API_KEY_FILE) {
    try {
      fs.accessSync(env.CA_LLM_API_KEY_FILE, fs.constants.R_OK);
    } catch {
      return { ok: false, error: `CA_LLM_API_KEY_FILE is not readable: ${env.CA_LLM_API_KEY_FILE}` };
    }
  }
  return { ok: true };
}

export function assertModelConfigured(env = process.env) {
  const result = checkModelConfigured(env);
  if (!result.ok) throw new Error(result.error);
}

/** The exact request body: no tools, no functions, deterministic sampling. */
export function buildChatRequest({ role, model, prompt }) {
  return {
    model,
    messages: [{ role: "user", content: String(prompt) }],
    temperature: 0,
    seed: 0,
    max_tokens: ROLES[role].maxTokens,
    response_format: { type: "json_object" },
    stream: false,
  };
}

/**
 * Pull exactly one JSON object out of a model reply: the whole reply, a
 * fenced block, or the span from the first `{` to the last `}`.
 */
export function extractFinalJson(text) {
  if (typeof text !== "string") return null;
  const body = (text.charCodeAt(0) === 0xfeff ? text.slice(1) : text).trim();
  if (!body) return null;
  const fenced = /```(?:json)?\s*([\s\S]*?)```/i.exec(body);
  for (const raw of fenced ? [fenced[1], body] : [body]) {
    const candidate = raw.trim();
    const forms = [candidate];
    const first = candidate.indexOf("{");
    const last = candidate.lastIndexOf("}");
    if (first !== -1 && last > first) forms.push(candidate.slice(first, last + 1));
    for (const form of forms) {
      try {
        const parsed = JSON.parse(form);
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed;
      } catch {
        continue;
      }
    }
  }
  return null;
}

function parseStageReply(role, text) {
  if (role !== "synthesis") return extractFinalJson(text);
  try {
    const parsed = JSON.parse(text);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function retryDelays() {
  return String(process.env.CA_LLM_RETRY_DELAYS_MS ?? "5000,20000")
    .split(",")
    .filter((part) => part.trim())
    .map(Number)
    .filter((ms) => Number.isFinite(ms) && ms >= 0);
}

/**
 * A shared local endpoint can drop a request while it swaps models, and hosted
 * ones rate-limit. Network errors, 429 and 5xx are retried a bounded number of
 * times inside the same deadline; any other status is final.
 */
async function postWithRetry(url, init, deadline) {
  const delays = retryDelays();
  let lastError = null;
  for (let attempt = 0; attempt <= delays.length; attempt += 1) {
    const remaining = deadline - Date.now();
    if (remaining <= 0) break;
    try {
      const response = await fetch(url, { ...init, signal: AbortSignal.timeout(remaining) });
      const text = await response.text();
      const retryable = response.status === 429 || response.status >= 500;
      if (!retryable || attempt === delays.length) return { status: response.status, text };
      lastError = new Error(`HTTP ${response.status}`);
    } catch (err) {
      lastError = err;
      if (err?.name === "TimeoutError") break;
    }
    const delay = delays[attempt];
    if (delay === undefined || Date.now() + delay >= deadline) break;
    await new Promise((resolve) => setTimeout(resolve, delay));
  }
  throw new Error(`model endpoint unreachable: ${lastError?.cause?.code || lastError?.message || "deadline exceeded"}`);
}

/**
 * One chat completion for `role`. Resolves to the reply's JSON object; throws
 * on transport, HTTP, or parse failure. Replies are cached in `cacheDir`.
 */
export async function invokeStage(role, prompt, { cacheDir = null } = {}) {
  const config = modelConfig(role);
  const body = buildChatRequest({ role, model: config.model, prompt });
  const key = createHash("sha256").update(JSON.stringify({ url: config.baseUrl, body })).digest("hex");
  const cacheFile = cacheDir ? path.join(cacheDir, `${key}.txt`) : null;
  if (cacheFile && fs.existsSync(cacheFile)) {
    const hit = parseStageReply(role, fs.readFileSync(cacheFile, "utf8"));
    if (hit) return hit;
  }
  const headers = { "content-type": "application/json" };
  if (config.apiKeyFile) headers.authorization = `Bearer ${fs.readFileSync(config.apiKeyFile, "utf8").trim()}`;
  const { status, text } = await postWithRetry(
    `${config.baseUrl}/chat/completions`,
    { method: "POST", headers, body: JSON.stringify(body) },
    Date.now() + ROLES[role].timeoutSec * 1000,
  );
  if (status < 200 || status >= 300) throw new Error(`model endpoint returned HTTP ${status}: ${text.slice(0, 300)}`);
  let content;
  try {
    content = JSON.parse(text)?.choices?.[0]?.message?.content;
  } catch {
    content = null;
  }
  if (typeof content !== "string" || !content.trim()) throw new Error("model endpoint returned no message content");
  const parsed = parseStageReply(role, content);
  if (!parsed) throw new Error(`${role} model returned unparseable output`);
  if (cacheFile) {
    try {
      fs.mkdirSync(cacheDir, { recursive: true, mode: 0o700 });
      fs.writeFileSync(cacheFile, content, { encoding: "utf8", mode: 0o600 });
    } catch {
      // The cache only saves a repeat call; the reply in hand is still good.
    }
  }
  return parsed;
}

/** The production invoke for one state dir: `(role, prompt) => Promise<object>`. */
export function modelInvoke(stateDir) {
  const cacheDir = path.join(stateDir, "model-cache");
  return (role, prompt) => invokeStage(role, prompt, { cacheDir });
}
