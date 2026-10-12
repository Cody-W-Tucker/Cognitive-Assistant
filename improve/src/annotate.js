// CA-native annotate: fresh logical invocation sequencing
// annotate-preface -> annotate, strict final validation, fail-closed with
// staging marked and no final proposal edits on invalid/failure.
// Prompts are checked in under improve/prompts/ (annotate-preface.md,
// annotate.md) and rendered through the existing prompt loader/renderer so
// the self-session sentinel is FIRST; no inline substitute content.

import fs from "node:fs";
import path from "node:path";

import { renderPrompt } from "./prompts.js";
import { persistPrompt, resolveAcpxBin } from "./analyze.js";
import { runAcpxPromptFile } from "./acpx-text.js";
import { modelForRole } from "./models.js";
import { validateCandidate, isSuppressedByRejection, renderStagedArtifact, renderDiff } from "./synthesize.js";
import { validateStaged } from "./stage.js";
import { createHash } from "node:crypto";

function shortHash(text) {
  return createHash("sha256").update(text).digest("hex").slice(0, 12);
}

function slugify(text) {
  const slug = String(text || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "untitled";
}

/**
 * Deterministically build a mock-only final annotation record from folded
 * ledger context. MOCK ONLY: production must fail closed and invent
 * nothing. The mock follows the same plan->stage/measure->preface->
 * annotate-final path but is allowed to construct the equivalent final
 * annotation deterministically so the pipeline stays reviewable with
 * zero model traffic.
 */
export function buildMockFinalAnnotation(plan, { ledger, evidenceIndex = new Map(), soulBaseline = "" } = {}) {
  void soulBaseline;
  const cluster = (ledger?.clusters || []).find((c) => String(c?.id) === String(plan?.clusterId));
  const sources = [...(plan?.provisionalSources || cluster?.sources || [])].map(String);
  const intent = String(plan?.provisionalIntent ?? plan?.intent ?? cluster?.proposedInstruction ?? "untitled");
  const mistake = String(cluster?.mistake || "");
  const per = cluster?.perSource || {};
  const evidence = sources.map((source) => {
    const positives = evidenceIndex.get(source) || [];
    const first = positives[0];
    return {
      polarity: "negative",
      text: per[source]?.quote || first?.quote || cluster?.representativeQuote || "",
      effect: per[source]?.mistake || mistake,
      moment: first?.effect || "",
      source,
    };
  });
  const recordId = `exp-${slugify(intent).slice(0, 40)}-${shortHash(String(plan?.clusterId || intent))}`;
  return {
    id: String(plan?.id),
    verdict: "keep",
    reason: mistake || intent,
    record: {
      id: recordId,
      title: intent,
      body: `Recurring gap seen in ${sources.length} session(s): ${mistake}`,
      sources,
      clusterId: String(plan?.clusterId || cluster?.id || ""),
      evidence,
      counterevidence: "none observed",
      compilerImplication: "compiler appends this record to the experience block; no SOUL, skill, or Hermes changes.",
    },
  };
}

function asList(input) {
  if (Array.isArray(input)) return input;
  if (input && typeof input === "object") return [input];
  return [];
}

function stagedSummary(list) {
  if (list.length === 0) return "(no staged change plans)";
  return list
    .map((c) => `- ${c.id}: ${c.provisionalIntent || c.intent || "untitled"} (cluster=${c.clusterId || "unknown"} eligibleSources=${((c.provisionalSources) || []).length})`)
    .join("\n");
}

function stagedCandidatesBlock(list) {
  if (list.length === 0) return "(no staged change plans)";
  return list
    .map((c) => {
      const sources = c?.provisionalSources || [];
      return `- [${c.id}] ${c.provisionalIntent || c.intent || "untitled"}\n    cluster=${c.clusterId || "unknown"} eligibleSources=${sources.join(", ") || "(none)"}\n    provisional intent (untrusted): ${c.provisionalIntent || c.intent || "(missing)"}`;
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
 * Default ACPX invoke for annotate-preface: persisted preface prompt via
 * `--file`, ACPX text-output (`--format quiet`, never JSON-RPC) on stdout,
 * single final `{"ready": true}` object extracted strictly. Pi executor;
 * role model sol with ACPX --timeout 300s (mandatory, before the agent).
 * No direct model client, no fallback.
 */
export function acpxAnnotatePrefaceInvoke(options = {}) {
  if (options && Object.prototype.hasOwnProperty.call(options, "agent")) {
    throw new Error("CA ACPX executor is fixed to pi (caller agent is not accepted)");
  }
  const { prompt, promptFile = null, model = null, timeoutSec = null, timeoutMs = null, spawnFn = null } = options;
  void prompt;
  void resolveAcpxBin;
  const file = promptFile ? String(promptFile) : "";
  if (!file) {
    return { status: "failed", error: "acpx prompt file is required (reuse persisted prompt)" };
  }
  const out = runAcpxPromptFile({
    role: "annotate",
    promptFile: file,
    model: model || modelForRole("annotate"),
    timeoutSec: timeoutSec ?? 300,
    ...(timeoutMs !== null && timeoutMs !== undefined ? { timeoutMs } : {}),
    ...(spawnFn ? { spawnFn } : {}),
  });
  if (out.status !== "ok") {
    return { status: "failed", error: out.error };
  }
  return { status: "ok", result: out.result };
}

/**
 * Default ACPX invoke for annotate: persisted annotate prompt via `--file`,
 * ACPX text-output (`--format quiet`, never JSON-RPC) on stdout, single
 * final `{"annotations": [...]}` object extracted strictly. Same argv
 * contract as the preface invoke (sol/300s, Pi executor).
 */
export function acpxAnnotateInvoke(options = {}) {
  if (options && Object.prototype.hasOwnProperty.call(options, "agent")) {
    throw new Error("CA ACPX executor is fixed to pi (caller agent is not accepted)");
  }
  const { prompt, promptFile = null, model = null, timeoutSec = null, timeoutMs = null, spawnFn = null } = options;
  void prompt;
  void resolveAcpxBin;
  const file = promptFile ? String(promptFile) : "";
  if (!file) {
    return { status: "failed", error: "acpx prompt file is required (reuse persisted prompt)" };
  }
  const out = runAcpxPromptFile({
    role: "annotate",
    promptFile: file,
    model: model || modelForRole("annotate"),
    timeoutSec: timeoutSec ?? 300,
    ...(timeoutMs !== null && timeoutMs !== undefined ? { timeoutMs } : {}),
    ...(spawnFn ? { spawnFn } : {}),
  });
  if (out.status !== "ok") {
    return { status: "failed", error: out.error };
  }
  return { status: "ok", result: out.result };
}

/**
 * Run annotate-preface then annotate as two fresh logical invocations.
 * Persists both rendered prompts privately (run/stage naming, 0600).
 * Annotation is the SOLE full-record origin: for verdict keep the
 * annotation must carry the complete durable record (title/body/
 * clusterId/sources/evidence/counterevidence/compilerImplication/
 * rationale); staged plans contribute no record/evidence. Mechanical
 * validation (exact session-bound quotes) applies to annotation finals;
 * production fails closed and invents nothing. Fail-closed: invalid/
 * failure (including prompt render failure) marks staging
 * (annotate.failed, candidates cleared) and returns no edits.
 */
export async function annotateStaging(
  staged,
  { stateDir = null, invoke = null, runId = null, ledger = null, evidenceIndex = null, promptsDir = null, soulBaseline = "" } = {},
) {
  const list = Array.isArray(staged) ? staged : [];
  const resolvedRun = runId || `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
  const fail = (error) => {
    if (stateDir) markAnnotateFailed(stateDir, error);
    return { failed: String(error || "annotate failed"), error: String(error || "annotate failed"), edits: [], annotated: [] };
  };

  let prefacePrompt;
  let annotatePrompt;
  let prefaceFile = null;
  let annotateFile = null;
  try {
    prefacePrompt = renderAnnotatePreface(list, { runId: String(resolvedRun), ...(promptsDir ? { promptsDir } : {}) });
    annotatePrompt = renderAnnotatePrompt(list, { runId: String(resolvedRun), ...(promptsDir ? { promptsDir } : {}) });
  } catch (err) {
    return fail(`annotate prompt render failed (${err?.message || err})`);
  }
  if (stateDir) {
    try {
      const resolved = path.resolve(stateDir);
      prefaceFile = persistPrompt(resolved, {
        runId: String(resolvedRun),
        transcriptId: "annotate-preface",
        harness: "stage",
        prompt: prefacePrompt,
        stage: "annotate-preface",
      });
      annotateFile = persistPrompt(resolved, {
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
        const pre = await invoke({ stage: "annotate-preface", prompt: prefacePrompt, promptFile: prefaceFile, staged: list, runId: String(resolvedRun) });
        if (pre && pre.status === "ok") {
          await invoke({ stage: "annotate", prompt: annotatePrompt, promptFile: annotateFile, staged: list, preface: pre, runId: String(resolvedRun) });
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
    prefaceOutcome = await invoke({ stage: "annotate-preface", prompt: prefacePrompt, promptFile: prefaceFile, staged: list, runId: String(resolvedRun) });
  } catch (err) {
    return fail(err?.message || String(err));
  }
  if (!prefaceOutcome || prefaceOutcome.status !== "ok") {
    return fail(prefaceOutcome?.error || "annotate-preface failed");
  }
  if (prefaceOutcome.result !== undefined) {
    const preface = prefaceOutcome.result;
    if (!preface || typeof preface !== "object" || preface.ready !== true) {
      return fail("annotate-preface returned invalid readiness (expected {\"ready\": true})");
    }
  }

  let outcome;
  try {
    outcome = await invoke({ stage: "annotate", prompt: annotatePrompt, promptFile: annotateFile, staged: list, preface: prefaceOutcome, runId: String(resolvedRun) });
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
    const verdict = String(ann.verdict).trim();
    if (verdict !== "keep" && verdict !== "drop" && verdict !== "revert") {
      return fail(`annotation invalid for ${String(c?.id)} (verdict must be keep|drop|revert)`);
    }
    if (verdict !== "keep") {
      annotated.push({ ...c, annotation: { verdict, reason: ann.reason || ann.note || "" } });
      continue;
    }
    // Keep MUST carry the complete durable record from annotation.
    // No inherited synth record/evidence: staged plans carry none.
    const finalRecord = ann.record || ann.finalRecord;
    if (!finalRecord || typeof finalRecord !== "object") {
      return fail(`annotation invalid for ${String(c?.id)} (keep requires a complete annotation final record; synth plans carry no record)`);
    }
    if (c?.record !== undefined || c?.evidence !== undefined || c?.title !== undefined) {
      return fail(`annotation invalid for ${String(c?.id)} (synth final record leaked into staging; annotation is the sole full-record origin)`);
    }
    const merged = {
      ...c,
      annotation: {
        verdict: "keep",
        reason: ann.reason || ann.note || ann.rationale || "",
        ...(ann.rationale ? { rationale: ann.rationale } : {}),
        ...(Array.isArray(ann.instructions) ? { instructions: ann.instructions } : {}),
        record: finalRecord,
      },
      finalRecord,
    };
    // Mechanical final-record validation; fail closed on fake quote/session.
    if (ledger) {
      const idx = evidenceIndex instanceof Map ? evidenceIndex : new Map();
      const check = validateCandidate({ record: finalRecord, evidence: finalRecord.evidence }, { ledger, evidenceIndex: idx });
      if (!check.ok) {
        return fail(`annotation invalid for ${String(c?.id)} (${(check.errors || []).join("; ") || "validation failed"})`);
      }
    } else {
      if (!finalRecord.title || !String(finalRecord.title).trim()) return fail(`annotation invalid for ${String(c?.id)} (record.title is required)`);
      if (!finalRecord.body || !String(finalRecord.body).trim()) return fail(`annotation invalid for ${String(c?.id)} (record.body is required)`);
      if (!finalRecord.counterevidence || !String(finalRecord.counterevidence).trim()) return fail(`annotation invalid for ${String(c?.id)} (record.counterevidence is required)`);
      if (!finalRecord.compilerImplication || !String(finalRecord.compilerImplication).trim()) return fail(`annotation invalid for ${String(c?.id)} (record.compilerImplication is required)`);
    }
    // Render the staged artifact/diff from the annotation final record.
    try {
      merged.stagedArtifact = renderStagedArtifact(finalRecord, soulBaseline);
      merged.diff = renderDiff(finalRecord.id || String(c?.id), merged.stagedArtifact);
    } catch (err) {
      return fail(`annotation invalid for ${String(c?.id)} (artifact render failed: ${err?.message || err})`);
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
  return list.filter((c) => {
    // Preserve explicit drop/revert (and any non-keep) annotations:
    // suppression operates only on annotated final keep records.
    if (!c || typeof c !== "object") return true;
    if (c?.annotation?.verdict !== "keep") return true;
    if (!c?.finalRecord && !c?.annotation?.record && !c?.record) return true;
    return !isSuppressedByRejection(c, rej);
  });
}
