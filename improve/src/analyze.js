// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Analyzer adapted from Backpass src/analyze.js (commit 0268201): one model
// call per distilled trace against improve/prompts/analysis.md, run through a
// bounded worker pool. Any per-trace failure is recorded, never fatal.

import fs from "node:fs";
import path from "node:path";

import { renderPrompt } from "./prompts.js";
import { persistPrompt } from "./state.js";

const CONTEXT_CHARS = 6000;

function unavailable(label, lookedIn) {
  return `(${label} unavailable: looked in ${lookedIn}; audit the trace alone and note the gap in changed_context.)`;
}

function readBaseline(file, label) {
  if (!file) return unavailable(label, "(no path given)");
  try {
    const text = fs.readFileSync(file, "utf8");
    return text.trim() ? text.slice(0, CONTEXT_CHARS) : unavailable(label, file);
  } catch {
    return unavailable(label, file);
  }
}

/**
 * Active artifact context for the analysis prompt. Each key degrades to an
 * explicit "(... unavailable ...)" marker when its source is absent, so the
 * model audits the trace alone instead of confabulating guidance.
 */
export function loadContexts({ soulPath = null, posturePath = null, experiencePath = null } = {}) {
  return {
    soulBaseline: readBaseline(soulPath, "SOUL baseline"),
    interactionPosture: readBaseline(posturePath, "interaction posture"),
    experienceRecords: readBaseline(experiencePath, "accepted experience records"),
  };
}

export function buildAnalysisPrompt(trace, contexts) {
  return renderPrompt(
    "analysis",
    {
      TRANSCRIPT_ID: String(trace.transcriptId || "unknown"),
      HARNESS: String(trace.harness || "unknown"),
      SOUL_BASELINE: contexts.soulBaseline,
      INTERACTION_POSTURE: contexts.interactionPosture,
      EXPERIENCE_RECORDS: contexts.experienceRecords,
      TRACE: String(trace.distilled || ""),
    },
  );
}

// Backpass's trivial-run gate: a single-request session stays eligible when it
// carries meaningful agent or tool work; only genuinely tiny shells skip.
function trivialReason({ userTurns, assistantTurns, toolCalls }) {
  if (userTurns >= 1 || assistantTurns >= 4 || toolCalls >= 3) return null;
  return `trivial session (${userTurns} user turn(s), ${assistantTurns} agent turn(s), ${toolCalls} tool call(s))`;
}

function isEvidence(reply) {
  return (
    reply &&
    Array.isArray(reply.positive) &&
    Array.isArray(reply.negative) &&
    Array.isArray(reply.gaps) &&
    (reply.status === undefined || reply.status === "ok")
  );
}

/**
 * @param {{transcriptId, harness, distilled, activity}[]} traces
 * @returns evidence records [{transcriptId, harness, status, positive, negative, gaps, error?}]
 */
export async function analyzeTraces(traces, { invoke, contexts, stateDir, runId, jobs = 4, onRecord = null }) {
  const record = (trace, status, extra = {}) => ({
    transcriptId: trace.transcriptId,
    harness: trace.harness,
    status,
    positive: [],
    negative: [],
    gaps: [],
    ...extra,
  });
  const analyzeOne = async (trace) => {
    if (trace.readError) return record(trace, "failed", { error: trace.readError });
    const trivial = trivialReason(trace.activity);
    if (trivial) return record(trace, "skipped", { error: trivial });
    try {
      const prompt = buildAnalysisPrompt(trace, contexts);
      persistPrompt(stateDir, { runId, name: trace.transcriptId, prompt, meta: { transcriptId: String(trace.transcriptId), harness: String(trace.harness) } });
      const reply = await invoke("analysis", prompt, { trace });
      if (!isEvidence(reply)) return record(trace, "failed", { error: "analyzer returned malformed evidence" });
      return record(trace, "ok", { positive: reply.positive, negative: reply.negative, gaps: reply.gaps });
    } catch (err) {
      return record(trace, "failed", { error: err.message });
    }
  };
  const records = new Array(traces.length);
  let next = 0;
  const worker = async () => {
    while (next < traces.length) {
      const index = next++;
      records[index] = await analyzeOne(traces[index]);
      onRecord?.(records[index]);
    }
  };
  await Promise.all(Array.from({ length: Math.max(1, Math.min(Number(jobs) || 4, traces.length)) }, worker));
  return records;
}
