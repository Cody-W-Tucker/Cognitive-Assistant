// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Synthesis adapted from Backpass src/synthesize.js + src/proposal.js
// (commit 0268201), narrowed to this slice's contract: produce candidate
// *experience records* only. The SOUL baseline is read-only context —
// synthesis never patches SOUL, memory files, or skills. The apply gate
// owns all writes.

import { spawnSync } from "node:child_process";
import path from "node:path";
import { createHash } from "node:crypto";

import { renderPrompt } from "./prompts.js";
import { persistPrompt, resolveAcpxBin } from "./analyze.js";
import { buildAcpxArgs, extractAcpxFinalJson } from "./acpx-text.js";
import { modelForRole } from "./models.js";

export const BODY_MAX_CHARS = 2000;

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
 * Render the staged (generated) artifact for one candidate record.
 * Pure function of (record, soulBaseline): the compiler consumes this.
 */
export function renderStagedArtifact(record, soulBaseline = "") {
  const baselineNote = soulBaseline
    ? `Baseline: SOUL.md excerpt (${soulBaseline.length} chars, read-only).`
    : "Baseline: SOUL.md unavailable; record stands alone.";
  const counter = record.counterevidence || "none observed";
  const implication = record.compilerImplication || "compiler appends this record to the experience block.";
  return (
    `---\n` +
    `id: ${record.id}\n` +
    `sources: ${record.sources.join(", ")}\n` +
    `---\n\n` +
    `# ${record.title}\n\n` +
    `${record.body}\n\n` +
    `## Evidence\n\n` +
    record.evidence.map((e) => `- (${e.source}) ${e.text}`).join("\n") +
    `\n\n## Counterevidence\n\n${counter}\n\n` +
    `## Compiler implication\n\n${implication}\n\n` +
    `_${baselineNote}_\n`
  );
}

/** Informational diff of the staged artifact against the read-only baseline. */
export function renderDiff(recordId, stagedArtifact) {
  const lines = [`--- SOUL.md (baseline, read-only)`, `+++ staged/${recordId}.md`];
  for (const line of stagedArtifact.split("\n")) lines.push(`+${line}`);
  return lines.join("\n");
}

/**
 * @param {{clusters}} ledger — folded ledger (eligible clusters only become plans)
 * @param {{positiveBySession: Map}} evidenceIndex — sessionId -> positive entries
 * @param {string} soulBaseline — SOUL.md text (read-only context, unused for plans)
 * @returns plans [{id, kind, clusterId, provisionalIntent, provisionalSources, provisionalCount}]
 *
 * Narrow staged change plans ONLY. Plans may hold the untrusted provisional
 * proposal/cluster ref/intent and eligible source ids for private
 * stage/measure context. They NEVER carry authoritative final fields:
 * no record, title, body, evidence, session quote mappings,
 * counterevidence, compilerImplication, stagedArtifact, or diff.
 * Annotation is the sole full-record origin.
 */
export function synthesizeCandidates(ledger, { evidenceIndex = new Map(), soulBaseline = "" } = {}) {
  void evidenceIndex;
  void soulBaseline;
  const plans = [];
  let index = 0;
  for (const cluster of ledger.clusters || []) {
    if (!cluster.eligible) continue;
    index += 1;
    plans.push({
      id: `e${index}`,
      kind: "add",
      clusterId: cluster.id,
      provisionalIntent: cluster.proposedInstruction,
      provisionalSources: [...(cluster.sources || [])],
      provisionalCount: cluster.count || (cluster.sources || []).length,
    });
  }
  return plans;
}

/**
 * Validate a narrow staged change plan. Plans must reference an eligible
 * ledger cluster and carry only provisional intent/context. Any authoritative
 * final field (record/title/body/evidence/counterevidence/
 * compilerImplication/stagedArtifact/diff) fails the plan.
 */
export function validateChangePlan(plan, { ledger } = {}) {
  const errors = [];
  if (!plan || typeof plan !== "object") return { ok: false, errors: ["change plan is required"] };
  if (plan.kind !== "add") errors.push(`kind must be "add" (got ${JSON.stringify(plan.kind)})`);
  if (!plan.clusterId || !String(plan.clusterId).trim()) {
    errors.push("clusterId is required");
  } else {
    const cluster = (ledger?.clusters || []).find((c) => String(c?.id) === String(plan.clusterId));
    if (!cluster) errors.push(`unknown cluster ${JSON.stringify(plan.clusterId)}`);
    else if (!cluster.eligible) errors.push(`cluster ${JSON.stringify(plan.clusterId)} is not eligible`);
    else if (Array.isArray(plan.provisionalSources) && plan.provisionalSources.length) {
      const clusterSources = new Set((cluster.sources || []).map(String));
      for (const s of plan.provisionalSources) {
        if (!clusterSources.has(String(s))) errors.push(`provisional source ${JSON.stringify(s)} is not evidence from cluster ${cluster.id}`);
      }
    }
  }
  const intent = plan.provisionalIntent ?? plan.intent;
  if (!intent || !String(intent).trim()) errors.push("provisionalIntent is required (untrusted provisional intent)");
  const provisionalSources = plan.provisionalSources;
  if (!Array.isArray(provisionalSources) || provisionalSources.length < 2) {
    errors.push("provisionalSources needs >=2 distinct sessions of eligible context");
  }
  for (const forbidden of ["record", "evidence", "title", "body", "counterevidence", "compilerImplication", "stagedArtifact", "diff", "rationale", "instructions"]) {
    if (plan[forbidden] !== undefined) errors.push(`authoritative field ${forbidden} must not appear on a staged change plan (annotation owns it)`);
  }
  return { ok: errors.length === 0, errors };
}

// --- production (acpx-only) synthesis -------------------------------------

function oneLine(text, max = 240) {
  const flat = String(text || "").replace(/\s+/g, " ").trim();
  return flat.length > max ? `${flat.slice(0, max)}...` : flat;
}

/** Compact folded evidence rendering for the {{EVIDENCE}} slot. */
export function renderEvidenceForSynthesis(ledger, evidenceIndex = new Map()) {
  const lines = [];
  for (const c of ledger?.clusters || []) {
    if (!c.eligible) continue;
    lines.push(`- [${c.id}] sessions=${c.sources.length} :: ${c.proposedInstruction}`);
    const per = c.perSource || {};
    for (const source of c.sources.slice(0, 4)) {
      const positives = evidenceIndex.get(source) || [];
      const quote = per[source]?.quote || positives[0]?.quote || c.representativeQuote;
      lines.push(`    "${oneLine(quote)}" (${source})`);
    }
  }
  return lines.length ? lines.join("\n") : "(no eligible gap clusters)";
}

/** Render prior rejections for the {{REJECTIONS}} slot. */
export function renderRejectionsForPrompt(rejections) {
  const entries = Array.isArray(rejections) ? rejections : [];
  if (!entries.length) return "(none)";
  return entries
    .map((r) => {
      const bits = [];
      if (r.clusterId) bits.push(`cluster ${r.clusterId}`);
      if (r.title) bits.push(`title "${r.title}"`);
      if (r.sources) bits.push(`sessions=${Array.isArray(r.sources) ? r.sources.length : r.sources}`);
      if (r.reason) bits.push(`reason ${r.reason}`);
      const head = r.edit ? `[${r.edit}]` : "-";
      return `${head} ${r.title || r.clusterId || "rejected candidate"} (${bits.join("; ") || "no detail"})`;
    })
    .join("\n");
}

/** Exact verbatim quotes attributable to one source within its cluster. */
function allowedQuotesForSource(cluster, source, evidenceIndex) {
  const out = new Set();
  const per = (cluster?.perSource || {})[String(source)];
  if (per?.quote) out.add(String(per.quote));
  for (const entry of cluster?.quoteProvenance || []) {
    if (String(entry?.source) === String(source) && entry?.quote) out.add(String(entry.quote));
  }
  for (const p of evidenceIndex?.get?.(String(source)) || []) {
    if (p?.quote) out.add(String(p.quote));
  }
  return out;
}

/**
 * Strict final-record validation for ANNOTATION-origin records only.
 * Checks title, bounded body, >=2 distinct known sources, exact
 * per-source quote binding (the cited text must be an exact quote
 * attributable to the cited source, never a swapped/global quote),
 * exact record.sources/evidence set coherence, required
 * counterevidence/compilerImplication, and cluster linkage (clusterId
 * must resolve an eligible ledger cluster; every cited source/quote
 * must be evidence from that cluster, so the floor cannot be met with
 * global evidenceIndex or ineligible sources). Synth plans never satisfy
 * this: they carry no record/evidence by contract.
 */
export function validateCandidate(candidate, { ledger, evidenceIndex = new Map() } = {}) {
  const errors = [];
  const record = candidate?.record || {};
  const evidence = Array.isArray(candidate?.evidence) ? candidate.evidence : record.evidence;
  if (!record.title || !String(record.title).trim()) errors.push("record.title is required");
  if (!record.body || !String(record.body).trim()) errors.push("record.body is required");
  else if (String(record.body).length > BODY_MAX_CHARS) {
    errors.push(`record.body exceeds ${BODY_MAX_CHARS} chars`);
  }
  if (!record.counterevidence || !String(record.counterevidence).trim()) {
    errors.push("record.counterevidence is required (or 'none observed')");
  }
  if (!record.compilerImplication || !String(record.compilerImplication).trim()) {
    errors.push("record.compilerImplication is required");
  }
  const cluster = (ledger?.clusters || []).find((c) => String(c?.id) === String(record.clusterId || ""));
  if (!record.clusterId || !String(record.clusterId).trim()) {
    errors.push("record.clusterId is required");
  } else if (!cluster) {
    errors.push(`unknown cluster ${JSON.stringify(record.clusterId)}`);
  } else if (!cluster.eligible) {
    errors.push(`cluster ${JSON.stringify(record.clusterId)} is not eligible`);
  }
  const sources = Array.isArray(record.sources) ? [...new Set(record.sources.map(String))] : [];
  if (sources.length < 2) errors.push("record.sources needs >=2 distinct sessions");
  if (cluster) {
    const clusterSources = new Set((cluster.sources || []).map(String));
    for (const s of sources) {
      if (!clusterSources.has(String(s))) errors.push(`source ${JSON.stringify(s)} is not evidence from cluster ${cluster.id}`);
    }
  }
  if (!Array.isArray(evidence) || !evidence.length) {
    errors.push("candidate evidence is required");
  } else {
    const evidenceSources = new Set();
    for (const item of evidence) {
      if (!item || typeof item !== "object") {
        errors.push("malformed evidence item");
        continue;
      }
      evidenceSources.add(String(item.source));
      if (!cluster || !new Set((cluster.sources || []).map(String)).has(String(item.source))) {
        errors.push(`unknown evidence source ${JSON.stringify(item.source)}`);
        continue;
      }
      const allowed = allowedQuotesForSource(cluster, item.source, evidenceIndex);
      if (!allowed.has(String(item.text))) {
        errors.push(`evidence quote is not an exact quote from source ${item.source}`);
      }
    }
    if (evidenceSources.size < 2) errors.push("candidate evidence needs >=2 distinct sessions");
    const recordSet = new Set(sources);
    const coherent = recordSet.size === evidenceSources.size && [...recordSet].every((s) => evidenceSources.has(s));
    if (!coherent) errors.push("record.sources must exactly match the evidence source set");
  }
  return { ok: errors.length === 0, errors };
}

/**
 * Robust rejection identity: only clusterId or title identify a rejected
 * candidate. The per-edit id (e1, e9, ...) is a run-local label, never an
 * identity. Rows without clusterId/title (legacy rows) or without a usable
 * source list carry insufficient metadata and must never suppress — they
 * still render as prior rejections via renderRejectionsForPrompt.
 */
function rejectionKey(r) {
  const clusterId = String(r?.clusterId || "").trim();
  if (clusterId) return clusterId;
  const title = String(r?.title || "").trim();
  if (title) return title;
  return "";
}

function rejectionSources(r) {
  if (!Array.isArray(r?.sources)) return [];
  return [...new Set(r.sources.map(String).filter(Boolean))];
}

/**
 * True when an ANNOTATED FINAL candidate repeats a rejected identity
 * without higher/new evidence. Operates only on annotation final records
 * (record/finalRecord plus annotation verdict keep). Higher = more distinct
 * sessions; new = a session id the rejection did not cite. Rejections with
 * insufficient identity or source metadata never suppress (fail-open for
 * reappearance, still rendered).
 */
export function isSuppressedByRejection(candidate, rejections) {
  const record = candidate?.finalRecord || candidate?.record || {};
  const candCluster = String(record.clusterId || candidate?.clusterId || "").trim();
  const candTitle = String(record.title || candidate?.title || "").trim();
  if (!candCluster && !candTitle) return false;
  const candSources = new Set(((record.sources || candidate?.provisionalSources) || []).map(String));
  for (const r of rejections || []) {
    const rejKey = rejectionKey(r);
    if (!rejKey) continue;
    const same = rejKey === candCluster || rejKey === candTitle;
    if (!same) continue;
    const rejSources = rejectionSources(r);
    if (!rejSources.length) continue;
    const hasNew = [...candSources].some((s) => !rejSources.includes(s));
    if (hasNew) continue;
    if (candSources.size > rejSources.length) continue;
    return true;
  }
  return false;
}

/**
 * Default acpx invoke for synthesis: rendered prompt on stdin, ACPX
 * text-output (`--format quiet`, never JSON-RPC) on stdout, single final
 * JSON object extracted strictly. Same executable protocol as analyze
 * acpx (analyze.js): the `acpx` binary, optional agent positional,
 * extra args from CA_IMPROVE_ACPX_ARGS, prompt passed on stdin.
 */
export function acpxSynthesisInvoke({ prompt, agent = null, model = null, timeoutMs = 180_000 } = {}) {
  const args = buildAcpxArgs({ agent, model: model || modelForRole("synthesis") });
  const result = spawnSync(resolveAcpxBin(), args, { input: prompt, encoding: "utf8", timeout: timeoutMs });
  if (result.error || result.status !== 0) {
    return { status: "failed", error: result.error?.message || `acpx exit ${result.status}` };
  }
  const parsed = extractAcpxFinalJson(result.stdout);
  if (!parsed) {
    return { status: "failed", error: "acpx returned unparseable output" };
  }
  return { status: "ok", result: parsed };
}

/** Render the production synthesis prompt (sentinel FIRST via the loader). */
export function buildSynthesisPrompt(
  ledger,
  { evidenceIndex = new Map(), rejections = [], transcriptCount = null, harnessSummary = "unknown", runNote = "", promptsDir } = {},
) {
  const count = transcriptCount ?? evidenceIndex.size ?? 0;
  return renderPrompt(
    "synthesis",
    {
      EVIDENCE: renderEvidenceForSynthesis(ledger, evidenceIndex),
      REJECTIONS: renderRejectionsForPrompt(rejections),
      TRANSCRIPT_COUNT: String(count),
      HARNESS_SUMMARY: String(harnessSummary),
      RUN_NOTE: String(runNote || ""),
    },
    { promptsDir },
  );
}

/**
 * Strict raw-acpx parser: the model must return exactly
 * `{"plans": [...]}` — narrow staged change plans only. Anything else
 * (missing key, non-array, a `candidates`/`edits` key carrying full
 * records, a non-object) is malformed and fails closed. Returns the
 * plan list or null. Production invents nothing.
 */
export function parseAcpxSynthesisResult(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  if (!Array.isArray(raw.plans)) return null;
  return raw.plans;
}

/**
 * Production synthesis: acpx-only, narrow plans, fail-closed.
 * Persists the rendered prompt privately with run/stage metadata.
 * Returns {edits: plans, note?, failed?, promptFile?}; failure yields no
 * plans plus a visible note for the proposal. Plans are NEVER final
 * records: no record/title/body/evidence/counterevidence/
 * compilerImplication/stagedArtifact/diff. Suppression and final-record
 * validation happen only on annotated finals downstream.
 */
export function synthesizeWithAcpx(
  ledger,
  {
    evidenceIndex = new Map(),
    soulBaseline = "",
    rejections = [],
    invoke = acpxSynthesisInvoke,
    stateDir = null,
    runId = null,
    promptsDir,
    transcriptCount = null,
    harnessSummary = "unknown",
    runNote = "",
  } = {},
) {
  const resolvedRun = runId || `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
  const prompt = buildSynthesisPrompt(ledger, {
    evidenceIndex,
    rejections,
    transcriptCount,
    harnessSummary,
    runNote,
    promptsDir,
  });
  let promptFile = null;
  let persistNote = "";
  if (stateDir) {
    try {
      promptFile = persistPrompt(path.resolve(stateDir), {
        runId: resolvedRun,
        transcriptId: "synthesis",
        harness: "stage",
        prompt,
        stage: "synthesis",
      });
    } catch (err) {
      // Persistence failure is visible, never silent: synthesis still
      // proceeds, but the proposal/run note carries the warning.
      persistNote = `synthesis prompt persistence failed (${err?.message || String(err)}); prompt not archived for this run`;
    }
  }
  let outcome;
  try {
    outcome = invoke({ prompt, ledger, evidenceIndex, rejections });
  } catch (err) {
    outcome = { status: "failed", error: err?.message || String(err) };
  }
  // Two invoke-output shapes: production invokes return
  // {status:"ok", result:<raw acpx JSON>} (parsed strictly as {plans});
  // injected test doubles may return {status:"ok", plans:[...]}
  // directly (legacy {status:"ok", candidates:[...]} is accepted only
  // when every entry is already a narrow plan). A raw `result` is never
  // read loosely. Production invents nothing: invalid plans are dropped.
  let rawCandidates = null;
  if (outcome && outcome.status === "ok") {
    if (outcome.result !== undefined) rawCandidates = parseAcpxSynthesisResult(outcome.result);
    else if (Array.isArray(outcome.plans)) rawCandidates = outcome.plans;
    else if (Array.isArray(outcome.candidates)) rawCandidates = outcome.candidates;
  }
  const withPersist = (entry) => (persistNote ? { ...entry, note: entry.note ? `${entry.note}\n${persistNote}` : persistNote } : entry);
  if (!outcome || outcome.status !== "ok" || !rawCandidates) {
    return withPersist({
      edits: [],
      failed: outcome?.error || "synthesis failed",
      note: `synthesis failed (${outcome?.error || "unparseable output"}); fail-closed with no candidate edits for this run`,
      promptFile,
    });
  }
  const edits = [];
  let index = 0;
  for (const raw of rawCandidates) {
    // Narrow plans only: accept {clusterId, provisionalIntent, provisionalSources}.
    // Anything carrying authoritative final fields is dropped fail-closed.
    const plan = {
      id: raw?.id || `e${index + 1}`,
      kind: raw?.kind || "add",
      clusterId: raw?.clusterId || raw?.record?.clusterId,
      provisionalIntent: raw?.provisionalIntent ?? raw?.intent ?? raw?.record?.title ?? raw?.title,
      provisionalSources: raw?.provisionalSources ?? raw?.record?.sources ?? raw?.sources,
      provisionalCount: raw?.provisionalCount ?? raw?.count,
    };
    if (raw?.record !== undefined || raw?.evidence !== undefined || raw?.title !== undefined || raw?.body !== undefined || raw?.counterevidence !== undefined || raw?.compilerImplication !== undefined || raw?.stagedArtifact !== undefined || raw?.diff !== undefined) {
      continue;
    }
    const check = validateChangePlan(plan, { ledger });
    if (!check.ok) continue;
    index += 1;
    edits.push({
      id: `e${index}`,
      kind: "add",
      clusterId: String(plan.clusterId),
      provisionalIntent: String(plan.provisionalIntent),
      provisionalSources: [...plan.provisionalSources].map(String),
      provisionalCount: Number(plan.provisionalCount || plan.provisionalSources.length),
    });
  }
  if (!edits.length) {
    return withPersist({
      edits: [],
      failed: "no valid change plans",
      note: "synthesis produced no valid change plans; fail-closed with no candidate edits for this run",
      promptFile,
    });
  }
  return withPersist({ edits, promptFile });
}
