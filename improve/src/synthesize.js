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
import { persistPrompt, ACPX_BIN } from "./analyze.js";

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
 * @param {{clusters}} ledger — folded ledger (eligible clusters only become edits)
 * @param {{positiveBySession: Map}} evidenceIndex — sessionId -> positive entries
 * @param {string} soulBaseline — SOUL.md text (read-only context)
 * @returns edits [{id, kind, title, rationale, instructions, evidence, record, stagedArtifact, diff}]
 */
export function synthesizeCandidates(ledger, { evidenceIndex = new Map(), soulBaseline = "" } = {}) {
  const edits = [];
  let index = 0;
  for (const cluster of ledger.clusters || []) {
    if (!cluster.eligible) continue;
    index += 1;
    const recordId = `exp-${slugify(cluster.proposedInstruction).slice(0, 40)}-${shortHash(cluster.id)}`;
    const evidence = cluster.sources.map((source) => {
      const positives = evidenceIndex.get(source) || [];
      const first = positives[0];
      // Per-source quote-backed evidence: never replicate the cluster's
      // first quote/mistake across all sources. Prefer the folded per-source
      // gap sighting, fall back to this source's positive quote.
      const per = (cluster.perSource || {})[source] || {};
      return {
        polarity: "negative",
        text: per.quote || first?.quote || cluster.representativeQuote,
        effect: per.mistake || cluster.mistake,
        moment: first?.effect || "",
        source,
      };
    });
    const record = {
      id: recordId,
      title: cluster.proposedInstruction,
      body: `Recurring gap seen in ${cluster.count} session(s): ${cluster.mistake}`,
      sources: cluster.sources,
      clusterId: cluster.id,
      evidence,
      counterevidence: "none observed",
      compilerImplication: "compiler appends this record to the experience block; no SOUL, skill, or Hermes changes.",
    };
    const stagedArtifact = renderStagedArtifact(record, soulBaseline);
    edits.push({
      id: `e${index}`,
      kind: "add",
      title: `Experience record: ${cluster.proposedInstruction}`,
      rationale: cluster.mistake,
      instructions: [cluster.proposedInstruction],
      evidence,
      record,
      counterevidence: record.counterevidence,
      compilerImplication: record.compilerImplication,
      stagedArtifact,
      diff: renderDiff(recordId, stagedArtifact),
    });
  }
  return edits;
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
 * Strict candidate validation against folded evidence.
 * Checks title, bounded body, >=2 distinct known sources, exact
 * per-source quote binding (the cited text must be an exact quote
 * attributable to the cited source, never a swapped/global quote),
 * exact record.sources/evidence set coherence, required
 * counterevidence/compilerImplication, and cluster linkage (clusterId
 * must resolve an eligible ledger cluster; every cited source/quote
 * must be evidence from that cluster, so the floor cannot be met with
 * global evidenceIndex or ineligible sources).
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
 * True when a candidate repeats a rejected identity without higher/new
 * evidence. Higher = more distinct sessions; new = a session id the
 * rejection did not cite. Rejections with insufficient identity or source
 * metadata never suppress (fail-open for reappearance, still rendered).
 */
export function isSuppressedByRejection(candidate, rejections) {
  const record = candidate?.record || {};
  const candCluster = String(record.clusterId || "").trim();
  const candTitle = String(record.title || candidate?.title || "").trim();
  if (!candCluster && !candTitle) return false;
  const candSources = new Set((record.sources || []).map(String));
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
 * Default acpx invoke for synthesis: rendered prompt on stdin, JSON on
 * stdout. Same executable protocol as analyze acpx (analyze.js): the
 * `acpx` binary, optional agent positional, extra args from
 * CA_IMPROVE_ACPX_ARGS, prompt passed on stdin.
 */
export function acpxSynthesisInvoke({ prompt, agent = null, timeoutMs = 180_000 } = {}) {
  const args = [];
  if (agent) args.push(agent);
  const extra = (process.env.CA_IMPROVE_ACPX_ARGS || "").trim();
  if (extra) args.push(...extra.split(/\s+/));
  const result = spawnSync(ACPX_BIN, args, { input: prompt, encoding: "utf8", timeout: timeoutMs });
  if (result.error || result.status !== 0) {
    return { status: "failed", error: result.error?.message || `acpx exit ${result.status}` };
  }
  try {
    return { status: "ok", result: JSON.parse(result.stdout) };
  } catch {
    return { status: "failed", error: "acpx returned unparseable output" };
  }
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
 * `{"candidates": [...]}`. Anything else (missing key, non-array, an
 * `edits` key, a non-object) is malformed and fails closed. Returns the
 * candidate list or null.
 */
export function parseAcpxSynthesisResult(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  if (!Array.isArray(raw.candidates)) return null;
  return raw.candidates;
}

/**
 * Production synthesis: acpx-only, strict validation, fail-closed.
 * Persists the rendered prompt privately with run/stage metadata.
 * Returns {edits, note?, failed?, promptFile?}; failure yields no edits
 * plus a visible note for the proposal.
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
  // {status:"ok", result:<raw acpx JSON>} (parsed strictly above);
  // injected test doubles may return {status:"ok", candidates:[...]}
  // directly. A raw `result` is never read loosely.
  let rawCandidates = null;
  if (outcome && outcome.status === "ok") {
    if (outcome.result !== undefined) rawCandidates = parseAcpxSynthesisResult(outcome.result);
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
    // Normalize: model returns record-shaped candidates; wrap into edits.
    const record = raw?.record || raw;
    const edit = raw?.record
      ? raw
      : {
          id: raw.id || `e${index + 1}`,
          kind: "add",
          title: record.title,
          rationale: record.rationale || "",
          instructions: record.instructions || (record.title ? [record.title] : []),
          evidence: record.evidence || [],
          record,
          counterevidence: record.counterevidence,
          compilerImplication: record.compilerImplication,
        };
    const check = validateCandidate(edit, { ledger, evidenceIndex });
    if (!check.ok) continue;
    if (isSuppressedByRejection(edit, rejections)) continue;
    index += 1;
    const recordId = record.id || `exp-${slugify(record.title).slice(0, 40)}-${shortHash(record.clusterId || record.title)}`;
    const fullRecord = { ...record, id: recordId };
    const stagedArtifact = renderStagedArtifact(fullRecord, soulBaseline);
    edits.push({
      id: `e${index}`,
      kind: "add",
      title: record.title?.startsWith("Experience record:") ? record.title : `Experience record: ${record.title}`,
      rationale: record.rationale || edit.rationale || "",
      instructions: edit.instructions?.length ? edit.instructions : [record.title],
      evidence: fullRecord.evidence,
      record: fullRecord,
      counterevidence: fullRecord.counterevidence,
      compilerImplication: fullRecord.compilerImplication,
      stagedArtifact,
      diff: renderDiff(recordId, stagedArtifact),
    });
  }
  if (!edits.length) {
    return withPersist({
      edits: [],
      failed: "no valid candidates",
      note: "synthesis produced no valid candidates; fail-closed with no candidate edits for this run",
      promptFile,
    });
  }
  return withPersist({ edits, promptFile });
}
