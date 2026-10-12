// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Analyzer boundary adapted from Backpass src/acpx.js + src/analyze.js
// (commit 0268201): every model call goes through the `acpx` binary only —
// this runtime owns no API keys and makes no direct model calls. The invoke
// function is injectable so tests (and headless CI) can substitute a mock
// with zero model traffic.

import { spawnSync } from "node:child_process";

export const ACPX_BIN = process.env.CA_IMPROVE_ACPX_BIN || process.env.BACKPASS_ACPX_BIN || "acpx";

/**
 * Default invoke: one acpx call per distilled trace. The prompt is passed on
 * stdin; JSON evidence is expected on stdout. Any failure is fail-soft
 * (status "failed") so one bad transcript never stops a run.
 */
export function acpxInvoke({ trace, agent = null, timeoutMs = 120_000 }) {
  const args = [];
  if (agent) args.push(agent);
  const extra = (process.env.CA_IMPROVE_ACPX_ARGS || "").trim();
  if (extra) args.push(...extra.split(/\s+/));
  const prompt =
    `${SELF_PROMPT_PREFIX}\n\n` +
    `Read this distilled agent session and return JSON evidence ` +
    `{status, positive[], negative[], gaps[]} only.\n\n${trace.distilled}\n`;
  const result = spawnSync(ACPX_BIN, args, {
    input: prompt,
    encoding: "utf8",
    timeout: timeoutMs,
  });
  if (result.error || result.status !== 0) {
    return { status: "failed", error: result.error?.message || `acpx exit ${result.status}` };
  }
  try {
    return { status: "ok", evidence: JSON.parse(result.stdout) };
  } catch {
    return { status: "failed", error: "acpx returned unparseable output" };
  }
}

const SELF_PROMPT_PREFIX =
  "<!-- ca-improve:self-session --> you are grading a past agent session.";

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
 * @param {{invoke?: (args) => object}} [options]
 * @returns evidence records [{transcriptId, harness, status, positive, negative, gaps}]
 */
export function analyzeTraces(traces, { invoke = acpxInvoke } = {}) {
  return traces.map((trace) => {
    let outcome;
    try {
      outcome = invoke({ trace });
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
    return {
      transcriptId: trace.transcriptId,
      harness: trace.harness,
      status: evidence.status === "ok" ? "ok" : "failed",
      positive: Array.isArray(evidence.positive) ? evidence.positive : [],
      negative: Array.isArray(evidence.negative) ? evidence.negative : [],
      gaps: Array.isArray(evidence.gaps) ? evidence.gaps : [],
    };
  });
}
