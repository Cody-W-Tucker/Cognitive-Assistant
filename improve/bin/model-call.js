#!/usr/bin/env node
// One chat completion: read a prompt file, POST it, print the reply text.
//
// This process has no tools to offer the model and does nothing with the
// reply except print it; the parent validates it as data. The bearer key, if
// any, is read from CA_LLM_API_KEY_FILE and never printed.

import fs from "node:fs";

import { buildChatRequest, modelConfig } from "../src/model-call.js";

function flag(args, name) {
  const index = args.indexOf(name);
  return index === -1 ? null : args[index + 1] ?? null;
}

const RETRY_DELAYS_MS = String(process.env.CA_LLM_RETRY_DELAYS_MS || "5000,20000")
  .split(",")
  .map(Number)
  .filter((ms) => Number.isFinite(ms) && ms >= 0);

/**
 * A shared local endpoint can drop a request while it swaps models, and hosted
 * ones rate-limit. Network errors, 429 and 5xx are retried a bounded number of
 * times inside the same deadline; any other status is final.
 */
async function postWithRetry(url, init, deadline) {
  let lastError = null;
  for (let attempt = 0; attempt <= RETRY_DELAYS_MS.length; attempt += 1) {
    const remaining = deadline - Date.now();
    if (remaining <= 0) break;
    try {
      const response = await fetch(url, { ...init, signal: AbortSignal.timeout(remaining) });
      const text = await response.text();
      const retryable = response.status === 429 || response.status >= 500;
      if (!retryable || attempt === RETRY_DELAYS_MS.length) return { status: response.status, text };
      lastError = new Error(`HTTP ${response.status}`);
    } catch (err) {
      lastError = err;
      if (err?.name === "TimeoutError") break;
    }
    const delay = RETRY_DELAYS_MS[attempt];
    if (delay === undefined || Date.now() + delay >= deadline) break;
    await new Promise((resolve) => setTimeout(resolve, delay));
  }
  throw new Error(`model endpoint unreachable: ${lastError?.cause?.code || lastError?.message || "deadline exceeded"}`);
}

async function main(args) {
  const role = flag(args, "--role");
  const promptFile = flag(args, "--prompt-file");
  const timeoutSec = Number(flag(args, "--timeout") || 180);
  const config = modelConfig(role);
  const model = flag(args, "--model") || config.model;
  const body = buildChatRequest({ role, model, prompt: fs.readFileSync(promptFile, "utf8") });
  const headers = { "content-type": "application/json" };
  if (config.apiKeyFile) {
    headers.authorization = `Bearer ${fs.readFileSync(config.apiKeyFile, "utf8").trim()}`;
  }
  const { status, text } = await postWithRetry(`${config.baseUrl}/chat/completions`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  }, Date.now() + timeoutSec * 1000);
  if (status < 200 || status >= 300) {
    throw new Error(`model endpoint returned HTTP ${status}: ${text.slice(0, 300)}`);
  }
  const content = JSON.parse(text)?.choices?.[0]?.message?.content;
  if (typeof content !== "string" || !content.trim()) {
    throw new Error("model endpoint returned no message content");
  }
  process.stdout.write(content);
}

main(process.argv.slice(2)).then(
  () => process.exit(0),
  (err) => {
    process.stderr.write(`model-call: ${err?.message || err}\n`);
    process.exit(1);
  },
);
