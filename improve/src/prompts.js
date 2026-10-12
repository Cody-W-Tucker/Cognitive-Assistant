// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Prompt loading adapted from Backpass src/prompts.js (commit 0268201):
// same dependency-free shape (load from disk, explicit {{TOKEN}}
// substitution, sentinel prepended FIRST), repointed at CA paths. The
// strict render (missing/unused/unexpected failures) is CA-native: a
// half-rendered analysis prompt must fail loudly, never reach a model.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { SELF_SESSION_SENTINEL } from "./sentinel.js";

const DEFAULT_PROMPT_DIR = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "prompts",
);

const cache = new Map();

function resolvePromptDir(promptsDir) {
  return promptsDir || DEFAULT_PROMPT_DIR;
}

function promptPath(name, promptsDir) {
  if (!/^[a-z0-9-]+$/.test(name)) {
    throw new Error(`invalid prompt name ${JSON.stringify(name)} (want [a-z0-9-]+)`);
  }
  return path.join(path.resolve(resolvePromptDir(promptsDir)), `${name}.md`);
}

/** Load a checked-in prompt by name, resolved relative to the runtime (not CWD). */
export function loadPrompt(name, { promptsDir } = {}) {
  const file = promptPath(name, promptsDir);
  if (!cache.has(file)) {
    let text;
    try {
      text = fs.readFileSync(file, "utf8");
    } catch {
      throw new Error(`prompt not found: ${name} (looked in ${file})`);
    }
    cache.set(file, text);
  }
  return cache.get(file);
}

const TOKEN_PATTERN = /\{\{([A-Za-z0-9_]+)\}\}/g;
const DECLARED_PATTERN = /^[A-Z][A-Z0-9_]*$/;

/** Unique {{TOKEN}} names in first-appearance order. */
export function declaredPlaceholders(template) {
  const seen = [];
  for (const match of String(template).matchAll(TOKEN_PATTERN)) {
    if (!seen.includes(match[1])) seen.push(match[1]);
  }
  return seen;
}

/**
 * Strict {{TOKEN}} substitution — no template engine, no surprises.
 *
 * Fails loudly on: a template token with no provided value (missing), a
 * provided value the template never declares (unused), and unexpected token
 * or key shapes (anything outside UPPER_SNAKE). Repeated occurrences of one
 * token all render the same value.
 */
export function render(template, values) {
  const text = String(template);
  const provided = values && typeof values === "object" ? values : {};
  for (const key of Object.keys(provided)) {
    if (!DECLARED_PATTERN.test(key)) {
      throw new Error(`unexpected placeholder value ${JSON.stringify(key)} (want UPPER_SNAKE)`);
    }
  }
  const tokens = declaredPlaceholders(text);
  for (const token of tokens) {
    if (!DECLARED_PATTERN.test(token)) {
      throw new Error(`unexpected template token {{${token}}} (want UPPER_SNAKE)`);
    }
    if (!Object.prototype.hasOwnProperty.call(provided, token)) {
      throw new Error(`missing placeholder value for {{${token}}}`);
    }
  }
  for (const key of Object.keys(provided)) {
    if (!tokens.includes(key)) {
      throw new Error(`unused placeholder value {{${key}}} (not declared by this prompt)`);
    }
  }
  const out = text.replace(TOKEN_PATTERN, (match, key) => String(provided[key]));
  const leftover = out.match(/\{\{[^}]*\}\}/);
  if (leftover) {
    throw new Error(`unrendered placeholder ${leftover[0]} left in prompt`);
  }
  return out;
}

/**
 * Re-exported so every prompt-facing caller keeps one import. The constant itself lives
 * in `src/sentinel.js`, which has no dependencies, because discovery's self-exclusion
 * check needs it without prompt loading.
 */
export { SELF_SESSION_SENTINEL };

/** Load, render, and prefix with the self-session sentinel FIRST. */
export function renderPrompt(name, values, { promptsDir } = {}) {
  return `${SELF_SESSION_SENTINEL}\n${render(loadPrompt(name, { promptsDir }), values)}`;
}
