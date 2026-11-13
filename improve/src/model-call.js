// Model boundary for the CA improvement runtime: one prompt in, text out.
//
// Every model call is a single OpenAI-compatible chat completion request made
// by improve/bin/model-call.js. Nothing here is an agent: the request carries
// no tools, the child gets no workspace, and the model's text is only ever
// parsed as data by the strict validators below. Code, not the model, decides
// every path and every field that is written.
//
// Configuration (environment, never model-controlled):
//   CA_LLM_BASE_URL            OpenAI-compatible base, e.g. http://nas:8080/v1
//   CA_LLM_MODEL               model for every role
//   CA_LLM_MODEL_<ROLE>        per-role override (ANALYSIS, CONSOLIDATE, SYNTHESIS, ANNOTATE)
//   CA_LLM_API_KEY_FILE        optional file holding a bearer key (inference-only)
//
// Reproducibility: temperature 0, fixed seed, JSON-only output, and every
// validated reply is cached under sha256(request) beside the persisted prompt,
// so re-running an unchanged prompt returns the identical reply without a call.

import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { parseStrictBoundedSynthesisStdout } from "./synthesis-parser.js";

export const ANALYSIS_TIMEOUT_SEC = 180;
export const SYNTHESIS_TIMEOUT_SEC = 300;
export const ROLE_TIMEOUT_SEC = {
  analysis: ANALYSIS_TIMEOUT_SEC,
  consolidate: ANALYSIS_TIMEOUT_SEC,
  synthesis: SYNTHESIS_TIMEOUT_SEC,
  annotate: SYNTHESIS_TIMEOUT_SEC,
};
const ROLE_MAX_TOKENS = { analysis: 4000, consolidate: 4000, synthesis: 6000, annotate: 8000 };
const CHILD_TIMEOUT_BUFFER_MS = 15_000;
export const SEED = 0;

const CALL_SCRIPT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "bin", "model-call.js");

/** Timeout seconds for one pipeline role. Unknown roles fail closed. */
export function timeoutForRole(role) {
  const secs = ROLE_TIMEOUT_SEC[String(role)];
  if (!secs) throw new Error(`unknown model role: ${role}`);
  return secs;
}

/** Endpoint and model for a role, from the environment only. */
export function modelConfig(role, env = process.env) {
  const roleKey = String(role || "");
  if (!ROLE_TIMEOUT_SEC[roleKey]) throw new Error(`unknown model role: ${role}`);
  const baseUrl = String(env.CA_LLM_BASE_URL || "").replace(/\/+$/, "");
  const model = env[`CA_LLM_MODEL_${roleKey.toUpperCase()}`] || env.CA_LLM_MODEL || "";
  if (!baseUrl) throw new Error("CA_LLM_BASE_URL is not set (OpenAI-compatible endpoint, e.g. http://host:8080/v1)");
  if (!model) throw new Error(`no model for role ${roleKey}: set CA_LLM_MODEL or CA_LLM_MODEL_${roleKey.toUpperCase()}`);
  return { role: roleKey, baseUrl, model, apiKeyFile: env.CA_LLM_API_KEY_FILE || null };
}

/** Preflight for the production run path: config present, no model traffic. */
export function checkModelConfigured(env = process.env) {
  try {
    for (const role of Object.keys(ROLE_TIMEOUT_SEC)) modelConfig(role, env);
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
  return result;
}

/** The exact request body: no tools, no functions, deterministic sampling. */
export function buildChatRequest({ role, model, prompt }) {
  return {
    model,
    messages: [{ role: "user", content: String(prompt) }],
    temperature: 0,
    seed: SEED,
    max_tokens: ROLE_MAX_TOKENS[String(role)] || 4000,
    response_format: { type: "json_object" },
    stream: false,
  };
}

export function requestKey(config, body) {
  return createHash("sha256").update(JSON.stringify({ url: config.baseUrl, body })).digest("hex");
}

function cachePath(promptFile, key) {
  // Only prompts persisted under <stateDir>/prompts are cached, in
  // <stateDir>/model-cache; an ad-hoc prompt elsewhere is never cached.
  const dir = path.dirname(path.resolve(promptFile));
  if (path.basename(dir) !== "prompts") return null;
  return path.join(dir, "..", "model-cache", `${key}.txt`);
}

function readCache(file) {
  if (!file) return null;
  try {
    return fs.readFileSync(file, "utf8");
  } catch {
    return null;
  }
}

function writeCache(file, text) {
  if (!file) return;
  try {
    fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
    fs.writeFileSync(file, text, { encoding: "utf8", mode: 0o600 });
  } catch {
    // cache is an optimization; a write failure never fails the call
  }
}

/**
 * Pull exactly one JSON object out of a model reply: the whole reply, a
 * fenced block, or the span from the first `{` to the last `}`.
 */
export function extractFinalJson(text) {
  if (typeof text !== "string") return null;
  let body = text.charCodeAt(0) === 0xfeff ? text.slice(1) : text;
  body = body.trim();
  if (!body) return null;
  const fenced = /```(?:json)?\s*([\s\S]*?)```/i.exec(body);
  const candidates = fenced ? [fenced[1], body] : [body];
  for (const raw of candidates) {
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
        // try the next form
      }
    }
  }
  return null;
}

function parseReply(role, text) {
  if (role === "synthesis") {
    const parsed = parseStrictBoundedSynthesisStdout(String(text ?? ""));
    return parsed
      ? { status: "ok", stdout: String(text), result: parsed }
      : { status: "failed", error: "synthesis returned malformed payload (expected {plans:[...]})" };
  }
  const parsed = extractFinalJson(text);
  return parsed ? { status: "ok", result: parsed } : { status: "failed", error: "model returned unparseable output" };
}

function prepare({ role, promptFile, model = null, timeoutSec = null, workspace = null, cwd = null }) {
  const roleKey = String(role || "");
  if (workspace || cwd) {
    return { error: "model calls are text-only: workspace/cwd must not be passed" };
  }
  const secs = timeoutSec ?? ROLE_TIMEOUT_SEC[roleKey];
  if (!secs) return { error: `model timeout is required (unknown role ${JSON.stringify(roleKey)})` };
  const file = promptFile ? String(promptFile) : "";
  try {
    if (!file || !fs.statSync(file).isFile()) return { error: "model prompt file not found" };
  } catch {
    return { error: "model prompt file not found" };
  }
  let config;
  try {
    config = modelConfig(roleKey);
  } catch (err) {
    return { error: err.message };
  }
  if (model) config = { ...config, model: String(model) };
  const body = buildChatRequest({ role: roleKey, model: config.model, prompt: fs.readFileSync(file, "utf8") });
  const key = requestKey(config, body);
  const argv = [CALL_SCRIPT, "--role", roleKey, "--prompt-file", file, "--timeout", String(secs)];
  if (model) argv.push("--model", String(model));
  return { roleKey, secs, file, key, cache: cachePath(file, key), argv };
}

/** Blocking model call (used by consolidation, synthesis, annotation). */
export function runModelPromptFile(options = {}) {
  const prep = prepare(options);
  if (prep.error) return { status: "failed", error: prep.error };
  const cached = readCache(prep.cache);
  if (cached !== null) {
    const hit = parseReply(prep.roleKey, cached);
    if (hit.status === "ok") return { ...hit, cached: true };
  }
  const spawner = options.spawnFn || spawnSync;
  const result = spawner(process.execPath, prep.argv, {
    encoding: "utf8",
    timeout: prep.secs * 1000 + CHILD_TIMEOUT_BUFFER_MS,
  });
  if (result?.error || result?.status !== 0) {
    return { status: "failed", error: String(result?.stderr || "").trim() || result?.error?.message || `model call exit ${result?.status}` };
  }
  const reply = parseReply(prep.roleKey, result.stdout);
  if (reply.status === "ok") writeCache(prep.cache, result.stdout);
  return reply;
}

/** Non-blocking model call for parallel trace analysis. */
export async function runModelPromptFileAsync(options = {}) {
  const prep = prepare(options);
  if (prep.error) return { status: "failed", error: prep.error };
  const cached = readCache(prep.cache);
  if (cached !== null) {
    const hit = parseReply(prep.roleKey, cached);
    if (hit.status === "ok") return { ...hit, cached: true };
  }
  return await new Promise((resolve) => {
    const spawner = options.spawnFn || spawn;
    let child;
    try {
      child = spawner(process.execPath, prep.argv, { stdio: ["ignore", "pipe", "pipe"] });
    } catch (err) {
      resolve({ status: "failed", error: err?.message || String(err) });
      return;
    }
    child.stdout.setEncoding?.("utf8");
    child.stderr.setEncoding?.("utf8");
    let stdout = "";
    let stderr = "";
    let expired = false;
    const timer = setTimeout(() => {
      expired = true;
      child.kill("SIGTERM");
    }, prep.secs * 1000 + CHILD_TIMEOUT_BUFFER_MS);
    child.stdout.on("data", (part) => {
      stdout += part;
    });
    child.stderr.on("data", (part) => {
      stderr += part;
    });
    child.on("error", (err) => {
      clearTimeout(timer);
      resolve({ status: "failed", error: err.message });
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (expired || code !== 0) {
        resolve({ status: "failed", error: expired ? "model call timed out" : stderr.trim() || `model call exit ${code}` });
        return;
      }
      const reply = parseReply(prep.roleKey, stdout);
      if (reply.status === "ok") writeCache(prep.cache, stdout);
      resolve(reply);
    });
  });
}
