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
import { validateCandidate, isSuppressedByRejection, isValidRecordId, renderStagedArtifact, renderDiff } from "./synthesize.js";
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
export function buildMockFinalAnnotation(plan, { ledger, evidenceIndex = new Map(), soulBaseline = "", measuredChanges = null, workspace = null } = {}) {
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
    reason: plan?.corroboratedOpenGap ? `open-gap corroborated singleton: ${mistake || intent}` : mistake || intent,
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

function stagedCandidatesBlock(list, { ledger = null, evidenceIndex = null } = {}) {
  if (list.length === 0) return "(no staged change plans)";
  const idx = evidenceIndex instanceof Map ? evidenceIndex : null;
  const clustersById = new Map(((ledger && ledger.clusters) || []).map((c) => [String(c?.id), c]));
  const MAX_SOURCES_PER_CANDIDATE = 8;
  const MAX_QUOTES_PER_SOURCE = 2;
  // Bounded whole-quote rendering policy: only complete unmodified quotes are
  // ever emitted. Total prompt budget is enforced by skipping whole quotes,
  // never by slicing/rewriting text (byte-for-byte contract).
  const MAX_TOTAL_QUOTE_CHARS = 8000;
  let budgetUsed = 0;
  const allowedQuotesFor = (cluster, source) => {
    const seen = new Set();
    const out = [];
    const push = (q) => {
      if (typeof q !== "string") return;
      const text = q;
      if (!text || seen.has(text)) return;
      seen.add(text);
      if (out.length >= MAX_QUOTES_PER_SOURCE) return;
      if (budgetUsed + text.length > MAX_TOTAL_QUOTE_CHARS) return;
      budgetUsed += text.length;
      out.push(text);
    };
    if (idx) {
      for (const entry of idx.get(String(source)) || []) {
        if (out.length >= MAX_QUOTES_PER_SOURCE) break;
        if (entry && typeof entry.quote === "string") push(entry.quote);
      }
    }
    const perQuote = cluster?.perSource?.[String(source)]?.quote;
    if (out.length < MAX_QUOTES_PER_SOURCE && typeof perQuote === "string") push(perQuote);
    return out;
  };
  return list
    .map((c) => {
      const sources = c?.provisionalSources || [];
      const cluster = clustersById.get(String(c?.clusterId || "")) || null;
      let allowedLines = "    allowed evidence: (no ledger context)";
      if (ledger && idx) {
        const scoped = [...new Set(sources.map(String))].slice(0, MAX_SOURCES_PER_CANDIDATE);
        if (scoped.length === 0) {
          allowedLines = "    allowed evidence: (none)";
        } else {
          allowedLines = scoped
            .map((s) => {
              const quotes = allowedQuotesFor(cluster, s);
              if (quotes.length === 0) return `    - [${s}] (no staged quote)`;
              return quotes.map((q) => `    - [${s}] ${JSON.stringify(q)}`).join("\n");
            })
            .join("\n");
          allowedLines = `    allowed evidence (copy byte-for-byte; same-source only):\n${allowedLines}`;
        }
      }
      return `- [${c.id}] ${c.provisionalIntent || c.intent || "untitled"}\n    cluster=${c.clusterId || "unknown"} eligibleSources=${sources.join(", ") || "(none)"}\n    provisional intent (untrusted): ${c.provisionalIntent || c.intent || "(missing)"}\n${allowedLines}`;
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
export function renderAnnotatePrompt(candidates, { runId = "run-unknown", promptsDir, ledger = null, evidenceIndex = null } = {}) {
  const list = asList(candidates);
  return renderPrompt(
    "annotate",
    {
      COUNT: String(list.length),
      STAGED_CANDIDATES: stagedCandidatesBlock(list, { ledger, evidenceIndex }),
      RUN_ID: String(runId),
    },
    { ...(promptsDir ? { promptsDir } : {}) },
  );
}

function specificMeasuredChanges(planId, workspaceChanges) {
  const want = String(planId || "");
  if (!want) return [];
  return (Array.isArray(workspaceChanges) ? workspaceChanges : []).filter((m) => {
    const rid = String(m?.recordId || "");
    const file = String(m?.file || m?.path || "");
    const mid = String(m?.id || "");
    return rid === want || file === `${want}.md` || mid === `m-${want}`;
  });
}

function measuredSourcesOf(m) {
  const raw = m?.provisionalSources || m?.eligibleSources || m?.sources || null;
  if (!Array.isArray(raw)) return null;
  const distinct = [...new Set(raw.map((s) => String(s).trim()).filter(Boolean))];
  return distinct.length ? distinct : null;
}

function validMeasuredProvenance(specific) {
  for (const m of specific) {
    const clusterId = String(m?.clusterId || "").trim();
    const sources = measuredSourcesOf(m);
    if (clusterId && sources && sources.length >= 2) {
      return { change: m, clusterId, sources };
    }
  }
  return null;
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
 * annotation must carry the complete durable record (id/title/body/
 * clusterId/sources/evidence/counterevidence/compilerImplication/
 * rationale); staged plans contribute no record/evidence. Mechanical
 * validation (exact session-bound quotes) applies to annotation finals;
 * production fails closed and invents nothing. Fail-closed: invalid/
 * failure (including prompt render failure) marks staging
 * (annotate.failed, candidates cleared) and returns no edits.
 */
export async function annotateStaging(
  staged,
  { stateDir = null, invoke = null, runId = null, ledger = null, evidenceIndex = null, promptsDir = null, soulBaseline = "", measuredChanges = null, workspace = null } = {},
) {
  const workspaceChanges = Array.isArray(measuredChanges) ? measuredChanges : [];
  const provenanceWorkspace = workspace ? String(workspace).split("/").slice(-1)[0] || "synthesis-workspace" : "synthesis-workspace";
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
    annotatePrompt = renderAnnotatePrompt(list, { runId: String(resolvedRun), ...(promptsDir ? { promptsDir } : {}), ledger, evidenceIndex });
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
    prefaceOutcome = await invoke({ stage: "annotate-preface", prompt: prefacePrompt, promptFile: prefaceFile, staged: list, runId: String(resolvedRun), measuredChanges: workspaceChanges });
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
    outcome = await invoke({ stage: "annotate", prompt: annotatePrompt, promptFile: annotateFile, staged: list, preface: prefaceOutcome, runId: String(resolvedRun), measuredChanges: workspaceChanges });
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
    // Provenance gate: actual changed workspace files are the source of
    // provenance. When measured workspace changes exist, every staged
    // candidate must match its own specific measured change with valid
    // explicit frontmatter (cluster id + >=2 distinct sources) AND bind the
    // stable measured ID (m-<id>). A malformed/missing measured change or an
    // unmatched candidate (no specific measured change) rejects that
    // candidate individually; valid siblings proceed. Never auto-assigned:
    // missing linkage never borrows a cluster and no candidate progresses
    // absent a valid stable measured ID linkage.
    const specificEarly = specificMeasuredChanges(c?.id, workspaceChanges);
    if (workspaceChanges.length > 0) {
      const earlyProv = validMeasuredProvenance(specificEarly);
      if (!earlyProv) {
        continue;
      }
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
    // Keep MUST carry a valid annotation-authored record id: a safe,
    // stable, deterministic `exp-<slug>-<hash>` bound to the candidate
    // identity. Run-local staged plan ids (e1, eN) and paths are never
    // valid; synthesis never authors this id. No fallback downstream.
    if (!finalRecord.id || !String(finalRecord.id).trim()) {
      return fail(`annotation invalid for ${String(c?.id)} (record.id is required; annotation authors the deterministic experience-record id)`);
    }
    if (!isValidRecordId(finalRecord.id)) {
      return fail(`annotation invalid for ${String(c?.id)} (record.id must be a safe stable id exp-<slug>-<hash>; got ${JSON.stringify(finalRecord.id)})`);
    }
    if (String(finalRecord.id) === String(c?.id)) {
      return fail(`annotation invalid for ${String(c?.id)} (record.id must not reuse the run-local staged plan id)`);
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
    // When measured provenance is present, the final record must match the
    // measured file provenance (same cluster, sources within measured set);
    // mismatches reject only that change.
    const measuredForRecord = specificMeasuredChanges(c?.id, workspaceChanges);
    const measuredValid = workspaceChanges.length > 0 && measuredForRecord.length > 0 ? validMeasuredProvenance(measuredForRecord) : null;
    if (measuredValid) {
      const recordSources = Array.isArray(finalRecord.sources) ? [...new Set(finalRecord.sources.map((s) => String(s)))] : [];
      const measuredSet = new Set((measuredValid.sources || []).map((s) => String(s)));
      if (String(finalRecord.clusterId || "") !== String(measuredValid.clusterId) || !recordSources.length || !recordSources.every((s) => measuredSet.has(String(s)))) {
        continue;
      }
    }
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
    // Render the staged artifact/diff from the annotation final record id.
    // No fallback: record.id was validated above as the sole origin.
    try {
      merged.stagedArtifact = renderStagedArtifact(finalRecord, soulBaseline);
      merged.diff = renderDiff(finalRecord.id, merged.stagedArtifact);
    } catch (err) {
      return fail(`annotation invalid for ${String(c?.id)} (artifact render failed: ${err?.message || err})`);
    }
    try {
      // Bind each annotation to its SPECIFIC measured change(s) only —
      // matched by staged plan id (recordId / `<id>.md` / `m-<id>`). Never
      // the blanket "all IDs" set; plans with no authored change bind none.
      // Measured IDs, file provenance, exact diffs, and eligible quote
      // context travel with the annotation.
      const want = String(c?.id || "");
      const specific = specificMeasuredChanges(want, workspaceChanges);
      if (specific.length) {
        const ids = specific.map((m) => String(m.id)).filter(Boolean);
        const prov = validMeasuredProvenance(specific);
        const diffs = specific.map((m) => String(m.diff || m.text || "")).filter(Boolean);
        merged.measuredIds = ids;
        merged.workspaceProvenance = {
          measuredIds: ids,
          workspace: provenanceWorkspace,
          ...(prov ? { clusterId: prov.clusterId, provisionalSources: prov.sources, eligibleSources: prov.sources } : {}),
          ...(diffs.length ? { diffs } : {}),
        };
        merged.measuredProvenance = merged.workspaceProvenance;
        if (prov) {
          merged.measuredClusterId = prov.clusterId;
          merged.measuredSources = prov.sources;
        }
        if (diffs.length) merged.measuredDiffs = diffs;
      }
    } catch {}
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
