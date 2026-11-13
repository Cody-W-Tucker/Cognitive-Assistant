// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Analyzer boundary adapted from Backpass src/analyze.js (commit 0268201).
// Every model call is one tool-free chat completion through model-call.js;
// the invoke function is injectable so tests (and headless CI) can substitute
// a mock with zero model traffic. The model prompt itself is the checked-in
// improve/prompts/analysis.md (adapted from Backpass
// src/prompts/analysis.md), rendered by improve/src/prompts.js with the
// self-session sentinel FIRST; no inline prompt text lives here.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { renderPrompt } from "./prompts.js";
import { runModelPromptFile, runModelPromptFileAsync } from "./model-call.js";
import { defaultExperienceRoot } from "./state.js";
import { defaultSoulPath } from "./soul.js";

export { checkModelConfigured, assertModelConfigured } from "./model-call.js";

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
  else roots.push(defaultExperienceRoot());
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
  const soulFile = soulPath || (repoRoot ? path.join(root, "workspaces", "alignment", "artifacts", "SOUL.md") : defaultSoulPath());
  const postureFile =
    posturePath || path.join(root, "workspaces", "alignment", "artifacts", "INTERACTION_POSTURE.md");
  const soulBaseline = readBaselineFile(soulFile) || unavailable("SOUL baseline", soulFile);
  const interactionPosture =
    readBaselineFile(postureFile) || unavailable("interaction posture", postureFile);
  const experienceRecords =
    readExperienceRecords(experienceRoot) ||
    unavailable(
      "accepted experience records",
      experienceRoot || defaultExperienceRoot(),
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

// Backpass's trivial-run gate, applied to CA's already-distilled trace. A
// single-turn user sessions stay eligible when it has meaningful agent/tool
// work; only genuinely tiny shells skip the model call.
export function distilledTraceStats(distilled) {
  const text = String(distilled || "");
  return {
    userTurns: (text.match(/^## human\s*$/gm) || []).length,
    assistantTurns: (text.match(/^## agent\s*$/gm) || []).length,
    toolCalls: (text.match(/^- tool\s+/gm) || []).length,
  };
}

export function isTrivialTrace(distilled) {
  const { userTurns, assistantTurns, toolCalls } = distilledTraceStats(distilled);
  return userTurns < 1 && assistantTurns < 4 && toolCalls < 3;
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
 * Default invoke: one tool-free model call per distilled trace on its persisted
 * prompt. Any failure is fail-soft (status "failed") so one bad transcript
 * never stops a run.
 */
export function modelInvoke(options = {}) {
  const { trace, model = null, timeoutSec = null, timeoutMs = null, prompt = null, promptFile = null, contexts, promptsDir, spawnFn = null } = options;
  void prompt;
  void contexts;
  void promptsDir;
  void trace;
  const file = promptFile ? String(promptFile) : "";
  if (!file) {
    return { status: "failed", error: "model prompt file is required (reuse persisted prompt)" };
  }
  const out = runModelPromptFile({
    role: "analysis",
    promptFile: file,
    ...(model ? { model } : {}),
    timeoutSec: timeoutSec ?? 180,
    ...(timeoutMs !== null && timeoutMs !== undefined ? { timeoutMs } : {}),
    ...(spawnFn ? { spawnFn } : {}),
  });
  if (out.status !== "ok") {
    return { status: "failed", error: out.error };
  }
  return { status: "ok", evidence: out.result };
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
    invoke = modelInvoke,
    contexts,
    promptsDir,
    stateDir = null,
    runId = null,
    repoRoot,
    soulPath,
    posturePath,
    experienceRoot,
    onRecord = null,
  } = {},
) {
  const merged = {
    ...loadDefaultContexts({ repoRoot, soulPath, posturePath, experienceRoot }),
    ...(contexts || {}),
  };
  const resolvedState = stateDir ? path.resolve(stateDir) : null;
  const resolvedRun = runId || `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
  const analyzeOne = (trace) => {
    const activity = trace.activity || null;
    if (activity && activity.userTurns < 1 && activity.assistantTurns < 4 && activity.toolCalls < 3) {
      return {
        transcriptId: trace.transcriptId,
        harness: trace.harness,
        status: "skipped",
        error: `trivial session (${activity.userTurns} user turn(s), ${activity.assistantTurns} agent turn(s), ${activity.toolCalls} tool call(s))`,
        positive: [],
        negative: [],
        gaps: [],
      };
    }
    const prompt = buildAnalysisPrompt(trace, merged, { promptsDir });
    let promptFile = null;
    if (resolvedState) {
      try {
        promptFile = persistPrompt(resolvedState, {
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
      outcome = invoke({ trace, prompt, promptFile, contexts: merged, promptsDir });
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
  };
  const records = [];
  for (const trace of traces) {
    const record = analyzeOne(trace);
    records.push(record);
    try {
      onRecord?.(record);
    } catch {
      // Progress is observational only; a renderer cannot break analysis.
    }
  }
  return records;
}

/** Async, bounded worker-pool form of analyzeTraces (Backpass jobs shape). */
export async function analyzeTracesAsync(traces, options = {}) {
  const { invoke = null, jobs = 4, onRecord = null, stateDir = null, runId = null, promptsDir, repoRoot, soulPath, posturePath, experienceRoot, contexts } = options;
  const merged = { ...loadDefaultContexts({ repoRoot, soulPath, posturePath, experienceRoot }), ...(contexts || {}) };
  const useInvoke = invoke || (async ({ promptFile }) => { const out = await runModelPromptFileAsync({ role: "analysis", promptFile }); return out.status === "ok" ? { status: "ok", evidence: out.result } : { status: "failed", error: out.error }; });
  let next = 0;
  const records = new Array(traces.length);
  async function one(trace) {
    const activity = trace.activity || distilledTraceStats(trace.distilled);
    if (activity.userTurns < 1 && activity.assistantTurns < 4 && activity.toolCalls < 3) return { transcriptId: trace.transcriptId, harness: trace.harness, status: "skipped", error: `trivial session (${activity.userTurns} user turn(s), ${activity.assistantTurns} agent turn(s), ${activity.toolCalls} tool call(s))`, positive: [], negative: [], gaps: [] };
    const prompt = buildAnalysisPrompt(trace, merged, { promptsDir });
    let promptFile = null;
    if (stateDir) { try { promptFile = persistPrompt(path.resolve(stateDir), { runId: runId || "run-unknown", transcriptId: trace.transcriptId, harness: trace.harness, prompt }); } catch {} }
    let outcome;
    try { outcome = await useInvoke({ trace, prompt, promptFile, contexts: merged, promptsDir }); } catch (err) { outcome = { status: "failed", error: err?.message || String(err) }; }
    const evidence = outcome?.evidence;
    const valid = outcome?.status === "ok" && evidence && Array.isArray(evidence.positive) && Array.isArray(evidence.negative) && Array.isArray(evidence.gaps) && (evidence.status === undefined || evidence.status === "ok");
    return valid ? { transcriptId: trace.transcriptId, harness: trace.harness, status: "ok", positive: evidence.positive, negative: evidence.negative, gaps: evidence.gaps } : { transcriptId: trace.transcriptId, harness: trace.harness, status: "failed", error: outcome?.error || "analyzer failed", positive: [], negative: [], gaps: [] };
  }
  async function worker() { while (true) { const index = next++; if (index >= traces.length) return; const record = await one(traces[index]); records[index] = record; try { onRecord?.(record); } catch {} } }
  await Promise.all(Array.from({ length: Math.max(1, Math.min(Number(jobs) || 4, traces.length)) }, worker));
  return records;
}
