// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Analyzer boundary adapted from Backpass src/acpx.js + src/analyze.js
// (commit 0268201): every model call goes through the `acpx` binary only —
// this runtime owns no API keys and makes no direct model calls. The invoke
// function is injectable so tests (and headless CI) can substitute a mock
// with zero model traffic. The model prompt itself is the checked-in
// improve/prompts/analysis.md (adapted from Backpass
// src/prompts/analysis.md), rendered by improve/src/prompts.js with the
// self-session sentinel FIRST; no inline prompt text lives here.

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { renderPrompt } from "./prompts.js";
import { buildAcpxArgs, extractAcpxFinalJson } from "./acpx-text.js";

export const ACPX_BIN = process.env.CA_IMPROVE_ACPX_BIN || process.env.BACKPASS_ACPX_BIN || "acpx";

/** Resolve the acpx binary fresh from the environment (selection order). */
export function resolveAcpxBin() {
  return process.env.CA_IMPROVE_ACPX_BIN || process.env.BACKPASS_ACPX_BIN || "acpx";
}

/**
 * Focused availability preflight for the real production run path.
 * Respects CA_IMPROVE_ACPX_BIN / BACKPASS_ACPX_BIN selection; never reads
 * machine config, never replaces acpx. Returns { ok, bin, path } or
 * { ok: false, bin, error } with remediation. No model traffic, no traces.
 */
export function checkAcpxAvailable({ bin } = {}) {
  const target = bin || resolveAcpxBin();
  const isPath = String(target).includes("/");
  const candidates = [];
  if (isPath) {
    candidates.push(path.resolve(String(target)));
  } else {
    const pathEnv = String(process.env.PATH || "");
    for (const dir of pathEnv.split(path.delimiter)) {
      if (!dir) continue;
      candidates.push(path.join(dir, String(target)));
    }
    if (!candidates.length) candidates.push(String(target));
  }
  for (const candidate of candidates) {
    try {
      fs.accessSync(candidate, fs.constants.X_OK);
      return { ok: true, bin: target, path: candidate };
    } catch {
      // try next PATH entry
    }
  }
  return {
    ok: false,
    bin: target,
    error:
      `acpx binary not available (looked for ${JSON.stringify(target)}` +
      ` via CA_IMPROVE_ACPX_BIN/BACKPASS_ACPX_BIN/PATH): install acpx on PATH` +
      ` or set CA_IMPROVE_ACPX_BIN=/path/to/acpx (BACKPASS_ACPX_BIN also honored).` +
      ` No traces were analyzed and no evidence was written.`,
  };
}

/** Throwing variant for the production run path (before trace analysis). */
export function assertAcpxAvailable(options = {}) {
  const result = checkAcpxAvailable(options);
  if (!result.ok) throw new Error(result.error);
  return result;
}

/** Repo root resolved relative to the runtime, never CWD. */
export function defaultRepoRoot() {
  return path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
}

function readBaselineFile(file) {
  try {
    const text = fs.readFileSync(file, "utf8");
    if (text.trim()) return text.slice(0, 6000);
  } catch {
    // fall through to the explicit-degradation marker below
  }
  return null;
}

function unavailable(label, lookedIn) {
  return `(${label} unavailable: looked in ${lookedIn}; audit the trace alone and note the gap in changed_context.)`;
}

function readExperienceRecords(experienceRoot) {
  const roots = [];
  if (experienceRoot) roots.push(path.resolve(experienceRoot));
  else roots.push(path.join(defaultRepoRoot(), "workspaces", "experience"));
  const blocks = [];
  for (const root of roots) {
    for (const sub of ["authored", "staged"]) {
      let entries = [];
      try {
        entries = fs.readdirSync(path.join(root, sub)).filter((f) => f.endsWith(".md")).sort();
      } catch {
        continue;
      }
      for (const entry of entries.slice(0, 20)) {
        try {
          const text = fs.readFileSync(path.join(root, sub, entry), "utf8");
          blocks.push(`--- ${sub}/${entry} ---\n${text.slice(0, 2000)}`);
        } catch {
          // skip unreadable records; absence is reported explicitly below
        }
      }
    }
    if (blocks.length) return blocks.join("\n\n").slice(0, 6000);
  }
  return null;
}

/**
 * Active artifact context for the analysis prompt. Every key degrades to an
 * explicit "(... unavailable ...)" marker when its source is absent, so the
 * model audits the trace alone instead of confabulating guidance.
 */
export function loadDefaultContexts({ repoRoot, soulPath, posturePath, experienceRoot } = {}) {
  const root = repoRoot || defaultRepoRoot();
  const soulFile = soulPath || path.join(root, "workspaces", "alignment", "artifacts", "SOUL.md");
  const postureFile =
    posturePath || path.join(root, "workspaces", "alignment", "artifacts", "INTERACTION_POSTURE.md");
  const soulBaseline = readBaselineFile(soulFile) || unavailable("SOUL baseline", soulFile);
  const interactionPosture =
    readBaselineFile(postureFile) || unavailable("interaction posture", postureFile);
  const experienceRecords =
    readExperienceRecords(experienceRoot) ||
    unavailable(
      "accepted experience records",
      experienceRoot || path.join(root, "workspaces", "experience"),
    );
  return { soulBaseline, interactionPosture, experienceRecords };
}

/**
 * Render the analysis model prompt for one distilled trace. Missing context
 * keys fall back to the active defaults (with explicit degradation); an
 * explicit `contexts: null` renders the trace alone with markers.
 */
export function buildAnalysisPrompt(trace, contexts = {}, { promptsDir, repoRoot } = {}) {
  const provided = contexts || {};
  const defaults = loadDefaultContexts({ repoRoot });
  return renderPrompt(
    "analysis",
    {
      TRANSCRIPT_ID: String(trace.transcriptId || "unknown"),
      HARNESS: String(trace.harness || "unknown"),
      SOUL_BASELINE: provided.soulBaseline ?? defaults.soulBaseline,
      INTERACTION_POSTURE: provided.interactionPosture ?? defaults.interactionPosture,
      EXPERIENCE_RECORDS: provided.experienceRecords ?? defaults.experienceRecords,
      TRACE: String(trace.distilled || ""),
    },
    { promptsDir },
  );
}

function safeName(text) {
  const clean = String(text || "unknown").replace(/[^a-zA-Z0-9-_.]+/g, "_").slice(0, 80);
  return clean || "unknown";
}

/**
 * Persist one rendered model prompt under private state (never the repo):
 * `<stateDir>/prompts/<runId>__<transcriptId|stage>.md` plus a `.json`
 * sidecar naming the run/session (or run/stage) relation. Both are 0600
 * where supported. The raw transcript is never written separately — the
 * distilled trace travels only inside the rendered prompt. Stage prompts
 * (consolidate/synthesis) pass `stage` for run/stage identifying metadata.
 *
 * @returns the prompt file path
 */
export function persistPrompt(
  stateDir,
  { runId = "run-unknown", transcriptId = "unknown", harness = "unknown", prompt = "", stage = null } = {},
) {
  const dir = path.join(path.resolve(stateDir), "prompts");
  fs.mkdirSync(dir, { recursive: true });
  const leaf = stage ? String(stage) : String(transcriptId);
  const base = `${safeName(runId)}__${safeName(leaf)}`;
  const promptFile = path.join(dir, `${base}.md`);
  const metaFile = path.join(dir, `${base}.json`);
  fs.writeFileSync(promptFile, prompt, "utf8");
  fs.writeFileSync(
    metaFile,
    `${JSON.stringify(
      {
        version: 1,
        runId: String(runId),
        transcriptId: String(transcriptId),
        harness: String(harness),
        ...(stage ? { stage: String(stage) } : {}),
        promptFile: `${base}.md`,
        createdAt: new Date().toISOString(),
      },
      null,
      2,
    )}\n`,
    "utf8",
  );
  try {
    fs.chmodSync(promptFile, 0o600);
    fs.chmodSync(metaFile, 0o600);
  } catch {
    // mode bits unsupported here (e.g. Windows ACLs); private dir already scopes access
  }
  return promptFile;
}

/**
 * Default invoke: one acpx call per distilled trace. The rendered analysis
 * prompt is passed on stdin; ACPX text-output (`--format quiet`, never
 * JSON-RPC) is requested on stdout and the single final JSON object is
 * extracted strictly. Any failure is fail-soft (status "failed") so one
 * bad transcript never stops a run. Explicit caller `agent` stays the
 * optional first positional; extra args come from CA_IMPROVE_ACPX_ARGS.
 */
export function acpxInvoke({ trace, agent = null, timeoutMs = 120_000, prompt = null, contexts, promptsDir }) {
  const rendered = prompt || buildAnalysisPrompt(trace, contexts, { promptsDir });
  const bin = resolveAcpxBin();
  const args = buildAcpxArgs({ agent });
  const result = spawnSync(bin, args, {
    input: rendered,
    encoding: "utf8",
    timeout: timeoutMs,
  });
  if (result.error || result.status !== 0) {
    return { status: "failed", error: result.error?.message || `acpx exit ${result.status}` };
  }
  const evidence = extractAcpxFinalJson(result.stdout);
  if (!evidence) {
    return { status: "failed", error: "acpx returned unparseable output" };
  }
  return { status: "ok", evidence };
}

/**
 * Deterministic test double: no model traffic. Every trace yields the same
 * canonical gap so the fold floor (minGapEvidence) is exercisable with small
 * fixtures. Never used unless the caller selects `analyzer: "mock"`.
 */
export function mockInvoke({ trace }) {
  const firstUserLine = (trace.distilled || "").split("\n").find((l) => l.trim()) || "";
  return {
    status: "ok",
    evidence: {
      status: "ok",
      positive: [
        {
          instruction: "exp-context-bootstrap",
          quote: firstUserLine.slice(0, 200),
          effect: "session made progress from a standing start",
        },
      ],
      negative: [],
      gaps: [
        {
          proposedInstruction: "exp-context-bootstrap",
          mistake: "sessions re-derive project context from scratch",
          quote: "sessions re-derive project context from scratch",
          recurrenceRisk: "every new session pays the same bootstrap cost",
        },
      ],
    },
  };
}

/**
 * @param {{transcriptId, harness, distilled}[]} traces
 * @param {{invoke?: (args) => object, contexts?: object, promptsDir?: string, stateDir?: string, runId?: string}} [options]
 *   `contexts` partially overrides the active defaults; `stateDir` enables
 *   private prompt persistence (the pipeline always supplies it); `runId`
 *   names the run/session relation on persisted prompts. Extra keys are
 *   forwarded to `invoke` (mocks ignore them), so mock tests are unchanged.
 * @returns evidence records [{transcriptId, harness, status, positive, negative, gaps}]
 */
export function analyzeTraces(
  traces,
  {
    invoke = acpxInvoke,
    contexts,
    promptsDir,
    stateDir = null,
    runId = null,
    repoRoot,
    soulPath,
    posturePath,
    experienceRoot,
  } = {},
) {
  const merged = {
    ...loadDefaultContexts({ repoRoot, soulPath, posturePath, experienceRoot }),
    ...(contexts || {}),
  };
  const resolvedState = stateDir ? path.resolve(stateDir) : null;
  const resolvedRun = runId || `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
  return traces.map((trace) => {
    const prompt = buildAnalysisPrompt(trace, merged, { promptsDir });
    if (resolvedState) {
      try {
        persistPrompt(resolvedState, {
          runId: resolvedRun,
          transcriptId: trace.transcriptId,
          harness: trace.harness,
          prompt,
        });
      } catch {
        // persistence is best-effort next to analysis; a prompt write failure
        // must not fail the trace (evidence still flows to fold)
      }
    }
    let outcome;
    try {
      outcome = invoke({ trace, prompt, contexts: merged, promptsDir });
    } catch (err) {
      outcome = { status: "failed", error: err?.message || String(err) };
    }
    if (outcome.status !== "ok" || !outcome.evidence) {
      return {
        transcriptId: trace.transcriptId,
        harness: trace.harness,
        status: "failed",
        error: outcome.error || "analyzer failed",
        positive: [],
        negative: [],
        gaps: [],
      };
    }
    const evidence = outcome.evidence;
    const collectionsOk =
      Array.isArray(evidence.positive) && Array.isArray(evidence.negative) && Array.isArray(evidence.gaps);
    const statusOk = evidence.status === "ok" || (evidence.status === undefined && collectionsOk);
    return {
      transcriptId: trace.transcriptId,
      harness: trace.harness,
      status: statusOk ? "ok" : "failed",
      positive: Array.isArray(evidence.positive) ? evidence.positive : [],
      negative: Array.isArray(evidence.negative) ? evidence.negative : [],
      gaps: Array.isArray(evidence.gaps) ? evidence.gaps : [],
    };
  });
}
