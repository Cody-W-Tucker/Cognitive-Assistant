// CA-native annotate: fresh logical invocation sequencing
// annotate-preface -> annotate, strict final validation, fail-closed with
// staging marked and no final proposal edits on invalid/failure.
// Prompts are checked in under improve/prompts/ (annotate-preface.md,
// annotate.md) and rendered through the existing prompt loader/renderer so
// the self-session sentinel is FIRST; no inline substitute content.

import fs from "node:fs";
import path from "node:path";

import { renderPrompt } from "./prompts.js";
import { persistPrompt } from "./analyze.js";
import { validateCandidate, isSuppressedByRejection } from "./synthesize.js";
import { validateStaged } from "./stage.js";

function asList(input) {
  if (Array.isArray(input)) return input;
  if (input && typeof input === "object") return [input];
  return [];
}

function stagedSummary(list) {
  if (list.length === 0) return "(no staged candidates)";
  return list
    .map((c) => `- ${c.id}: ${c.title || c.record?.title || "untitled"} (sources=${(c.record?.sources || []).length})`)
    .join("\n");
}

function stagedCandidatesBlock(list) {
  if (list.length === 0) return "(no staged candidates)";
  return list
    .map((c) => {
      const record = c?.record || {};
      const evidence = Array.isArray(c?.evidence) ? c.evidence : Array.isArray(record.evidence) ? record.evidence : [];
      const lines = evidence.map((e) => `    - (${e.source}) ${e.text}`).join("\n");
      return `- [${c.id}] ${c.title || record.title || "untitled"}\n    record: ${record.id || "unknown"} cluster=${record.clusterId || "unknown"} sources=${(record.sources || []).join(", ")}\n${lines || "    - (no evidence rows)"}`;
    })
    .join("\n");
}

/**
 * Render the annotate preface from the checked-in prompt file via the
 * existing strict loader/renderer (sentinel FIRST). Accepts a single staged
 * candidate or a list.
 */
export function renderAnnotatePreface(candidates, { runId = "run-unknown", promptsDir } = {}) {
  const list = asList(candidates);
  return renderPrompt(
    "annotate-preface",
    {
      COUNT: String(list.length),
      STAGED_SUMMARY: stagedSummary(list),
      RUN_ID: String(runId),
    },
    { ...(promptsDir ? { promptsDir } : {}) },
  );
}

/**
 * Render the final annotate prompt from the checked-in prompt file via the
 * existing strict loader/renderer (sentinel FIRST). Accepts a single staged
 * candidate or a list.
 */
export function renderAnnotatePrompt(candidates, { runId = "run-unknown", promptsDir } = {}) {
  const list = asList(candidates);
  return renderPrompt(
    "annotate",
    {
      COUNT: String(list.length),
      STAGED_CANDIDATES: stagedCandidatesBlock(list),
      RUN_ID: String(runId),
    },
    { ...(promptsDir ? { promptsDir } : {}) },
  );
}

function stagingDir(stateDir) {
  return path.join(path.resolve(stateDir), "staging");
}

function markAnnotateFailed(stateDir, error) {
  if (!stateDir) return;
  try {
    const dir = stagingDir(stateDir);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(
      path.join(dir, "annotate.failed"),
      `${JSON.stringify({ version: 1, error: String(error || "annotate failed"), at: new Date().toISOString() }, null, 2)}\n`,
      "utf8",
    );
    try {
      fs.unlinkSync(path.join(dir, "candidates.json"));
    } catch {
      // marker alone satisfies the cleared-or-marked contract
    }
  } catch {
    // fail-closed return value already carries the failure
  }
}

function annotationsFrom(outcome) {
  if (!outcome || typeof outcome !== "object") return null;
  if (Array.isArray(outcome.annotations)) return outcome.annotations;
  if (outcome.result && Array.isArray(outcome.result.annotations)) return outcome.result.annotations;
  return null;
}

/**
 * Run annotate-preface then annotate as two fresh logical invocations.
 * Persists both rendered prompts privately (run/stage naming, 0600).
 * Strict: measurement coverage is enforced downstream by buildFinalProposal;
 * here every non-reverted staged candidate needs a verdict annotation with
 * exact quote/session binding when ledger context is available.
 * Fail-closed: invalid/failure (including prompt render failure) marks
 * staging (annotate.failed, candidates cleared) and returns no edits.
 */
export async function annotateStaging(
  staged,
  { stateDir = null, invoke = null, runId = null, ledger = null, evidenceIndex = null, promptsDir = null } = {},
) {
  const list = Array.isArray(staged) ? staged : [];
  const resolvedRun = runId || `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
  const fail = (error) => {
    if (stateDir) markAnnotateFailed(stateDir, error);
    return { failed: String(error || "annotate failed"), error: String(error || "annotate failed"), edits: [], annotated: [] };
  };

  let prefacePrompt;
  let annotatePrompt;
  try {
    prefacePrompt = renderAnnotatePreface(list, { runId: String(resolvedRun), ...(promptsDir ? { promptsDir } : {}) });
    annotatePrompt = renderAnnotatePrompt(list, { runId: String(resolvedRun), ...(promptsDir ? { promptsDir } : {}) });
  } catch (err) {
    return fail(`annotate prompt render failed (${err?.message || err})`);
  }
  if (stateDir) {
    try {
      const resolved = path.resolve(stateDir);
      persistPrompt(resolved, {
        runId: String(resolvedRun),
        transcriptId: "annotate-preface",
        harness: "stage",
        prompt: prefacePrompt,
        stage: "annotate-preface",
      });
      persistPrompt(resolved, {
        runId: String(resolvedRun),
        transcriptId: "annotate",
        harness: "stage",
        prompt: annotatePrompt,
        stage: "annotate",
      });
    } catch {
      // prompt persistence best-effort; invocation outcome still decides
    }
  }

  if (list.length === 0) {
    if (typeof invoke === "function") {
      try {
        const pre = await invoke({ stage: "annotate-preface", prompt: prefacePrompt, staged: list, runId: String(resolvedRun) });
        if (pre && pre.status === "ok") {
          await invoke({ stage: "annotate", prompt: annotatePrompt, staged: list, preface: pre, runId: String(resolvedRun) });
        }
      } catch {
        // empty staging never fails the run on invoke errors
      }
    }
    return { failed: false, annotated: [], edits: [] };
  }
  if (typeof invoke !== "function") {
    return fail("annotate invoke unavailable");
  }

  let prefaceOutcome;
  try {
    prefaceOutcome = await invoke({ stage: "annotate-preface", prompt: prefacePrompt, staged: list, runId: String(resolvedRun) });
  } catch (err) {
    return fail(err?.message || String(err));
  }
  if (!prefaceOutcome || prefaceOutcome.status !== "ok") {
    return fail(prefaceOutcome?.error || "annotate-preface failed");
  }

  let outcome;
  try {
    outcome = await invoke({ stage: "annotate", prompt: annotatePrompt, staged: list, preface: prefaceOutcome, runId: String(resolvedRun) });
  } catch (err) {
    return fail(err?.message || String(err));
  }
  if (!outcome || outcome.status !== "ok") {
    return fail(outcome?.error || "annotate failed");
  }
  const annotations = annotationsFrom(outcome);
  if (!annotations) {
    return fail("annotate returned no annotations");
  }
  const byId = new Map(annotations.filter((a) => a && typeof a === "object").map((a) => [String(a.id), a]));
  const annotated = [];
  for (const c of list) {
    if (c?.reverted === true) {
      annotated.push({ ...c });
      continue;
    }
    const ann = byId.get(String(c?.id));
    if (!ann || !ann.verdict || !String(ann.verdict).trim()) {
      return fail(`missing annotation for ${String(c?.id || "unknown")}`);
    }
    const merged = { ...c, annotation: { verdict: String(ann.verdict), reason: ann.reason || ann.note || "", ...(ann.quote ? { quote: ann.quote } : {}) } };
    // Strict binding when ledger context is available; fail closed on fake quote/session.
    if (ledger) {
      const idx = evidenceIndex instanceof Map ? evidenceIndex : new Map();
      const check = c?.record ? validateStaged(merged, { ledger, evidenceIndex: idx }) : validateCandidate(merged, { ledger, evidenceIndex: idx });
      if (!check.ok) {
        return fail(`annotation invalid for ${String(c?.id)} (${(check.errors || []).join("; ") || "validation failed"})`);
      }
    }
    annotated.push(merged);
  }

  if (stateDir) {
    try {
      const dir = stagingDir(stateDir);
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(path.join(dir, "annotated.json"), `${JSON.stringify(annotated, null, 2)}\n`, "utf8");
      fs.writeFileSync(path.join(dir, "candidates.json"), `${JSON.stringify(annotated, null, 2)}\n`, "utf8");
    } catch {
      // annotated return value still carries the result
    }
  }
  return { failed: false, annotated, edits: annotated };
}

/**
 * Final rejection suppression over annotated candidates: same identity
 * without higher/new evidence stays suppressed. Higher = more distinct
 * sessions; new = a session id the rejection did not cite. Rows without
 * usable identity/sources never suppress (still rendered upstream).
 */
export function applyRejectionSuppression(annotated, rejections, { evidenceIndex = new Map() } = {}) {
  const list = Array.isArray(annotated) ? annotated : [];
  const rej = Array.isArray(rejections) ? rejections : [];
  void evidenceIndex;
  return list.filter((c) => !isSuppressedByRejection(c, rej));
}
