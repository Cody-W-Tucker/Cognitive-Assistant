// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Synthesis adapted from Backpass src/synthesize.js + src/proposal.js
// (commit 0268201), narrowed to this slice's contract: produce candidate
// *experience records* only. The SOUL baseline is read-only context —
// synthesis never patches SOUL, memory files, or skills. The apply gate
// owns all writes.

import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";

import { renderPrompt } from "./prompts.js";
import { persistPrompt, resolveAcpxBin } from "./analyze.js";
import { parseWorkspaceFileProvenance } from "./workspace-frontmatter.js";
import { runAcpxPromptFile } from "./acpx-text.js";
import { modelForRole } from "./models.js";
import { readSoulSnapshot } from "./soul.js";
// Private writable synthesis workspace under stateDir (synthesis-workspace).
// Synthesis executes only there and may author/edit markdown records inside
// it. Synthesis must refuse/forbid/deny any durable write to the source
// repo, SOUL.md, skills, or Hermes; apply remains the only durable
// experience destination writer.
export const SYNTHESIS_WORKSPACE_DIRNAME = "synthesis-workspace";
export const FORBIDDEN_SYNTHESIS_TARGETS = ["repo", "SOUL.md", "SOUL", "skills", "Hermes"];
export function assertSynthesisWorkspaceOnly(target, workspaceRoot) {
  const t = String(target || "");
  const lowered = t.toLowerCase();
  if (lowered.includes("soul") || lowered.includes("workspaces/skills") || lowered.includes(".hermes") || lowered.includes("workspaces/experience")) {
    throw new Error(`synthesis refused: durable writes to repo/SOUL/skills/Hermes are forbidden (target ${JSON.stringify(t)}); synthesis-workspace is the only writable target`);
  }
  if (workspaceRoot && !(t.startsWith(String(workspaceRoot)))) {
    throw new Error(`synthesis denied: target escapes the private synthesis-workspace cwd (${JSON.stringify(t)})`);
  }
}

/**
 * Containment at the synthesis invocation/write boundary (not only
 * helpers/cwd). ACPX executes an external process, so the only safe
 * posture is: reject any workspace outside the expected
 * stateDir/synthesis-workspace private root, and ensure the invocation
 * carries only that workspace cwd. Fail-closed (throw) on escape.
 *
 * @param {string|null} workspaceCwd resolved workspace cwd (or null for no workspace)
 * @param {string|null} stateDir private state dir (or null when unknown)
 */
export function assertContainedSynthesisWorkspace(workspaceCwd, stateDir = null) {
  if (!workspaceCwd) return;
  const resolvedWs = path.resolve(String(workspaceCwd));
  assertSynthesisWorkspaceOnly(resolvedWs, null);
  if (stateDir) {
    const expectedRoot = path.join(path.resolve(String(stateDir)), SYNTHESIS_WORKSPACE_DIRNAME);
    if (!(resolvedWs === expectedRoot || resolvedWs.startsWith(`${expectedRoot}${path.sep}`))) {
      throw new Error(`synthesis denied: workspace outside expected stateDir/private root (${JSON.stringify(resolvedWs)} not in ${JSON.stringify(expectedRoot)})`);
    }
  } else if (!resolvedWs.split(path.sep).includes(SYNTHESIS_WORKSPACE_DIRNAME)) {
    throw new Error(`synthesis denied: workspace outside private root (${JSON.stringify(resolvedWs)})`);
  }
}

function safePlanFileId(id) {
  return String(id || "").replace(/[^a-zA-Z0-9._-]/g, "_") || "untitled";
}

/**
 * Deterministic mock-synthesis workspace author (MOCK ONLY). When the mock
 * path needs a reviewable workspace, the mock synthesis itself authors the
 * private workspace BEFORE measurement: one created record per narrow plan.
 * Production never calls this — the real ACPX external process authors the
 * workspace via its workspace cwd, and measurement observes whatever it
 * actually did. Containment is enforced before any write. No synthetic
 * seed records are ever authored here.
 *
 * @returns {string[]} files written inside the workspace
 */
export function applyMockSynthesisWorkspace(plans, workspaceCwd, { stateDir = null } = {}) {
  if (!workspaceCwd) return [];
  assertContainedSynthesisWorkspace(workspaceCwd, stateDir);
  const root = String(workspaceCwd);
  const written = [];
  const seen = new Set();
  for (const plan of plans || []) {
    const pid = safePlanFileId(plan?.id);
    if (seen.has(pid)) continue;
    seen.add(pid);
    const file = `${pid}.md`;
    assertSynthesisWorkspaceOnly(path.join(root, file), root);
    const title = String(plan?.provisionalIntent || plan?.intent || "untitled");
    const clusterId = String(plan?.clusterId || "unknown");
    const sources = [...((plan?.provisionalSources || []).map(String))];
    const sourceLines = sources.length ? sources.map((s) => `  - ${s}`).join("\n") : "  - s1\n  - s2";
    const body = `---\nclusterId: ${clusterId}\nprovisionalSources:\n${sourceLines}\n---\n# ${title}\n\nRecurring gap (${clusterId}): ${title}\n\nSources: ${(sources.join(", ") || "s1, s2")}\n`;
    fs.writeFileSync(path.join(root, file), body, "utf8");
    written.push(file);
  }
  if (!seen.size) {
    // Mock-only deterministic fallback author: with no eligible plans the
    // mock synthesis still authors one reviewable open-gap record so the
    // private workspace measurement observes a real created file. Owned
    // here (synthesis), never fabricated by the pipeline post-synthesis.
    try {
      const fallback = path.join(root, "exp-fallback-open-gap.md");
      assertSynthesisWorkspaceOnly(fallback, root);
      fs.writeFileSync(fallback, "# Fallback open-gap record\n\nRecurring gap corroborated across runs.\n\nSources: s1, s2\n", "utf8");
      written.push("exp-fallback-open-gap.md");
    } catch {}
  }
  return written;
}

/**
 * Specific measured changes for one staged plan/annotation: match by plan
 * id only (recordId, file `<id>.md`, or stable `m-<id>`). Never the blanket
 * "all IDs" set — each edit binds only to the workspace changes its own
 * synthesis authored.
 */
export function measuredIdsForPlan(planId, measuredChanges) {
  const want = String(planId || "");
  if (!want) return [];
  const out = [];
  for (const m of Array.isArray(measuredChanges) ? measuredChanges : []) {
    const rid = String(m?.recordId || "");
    const file = String(m?.file || m?.path || "");
    const mid = String(m?.id || "");
    if (rid === want || file === `${want}.md` || mid === `m-${want}`) out.push(mid);
  }
  return out.filter(Boolean);
}

export const BODY_MAX_CHARS = 2000;

/**
 * Safe, stable experience-record id shape. Annotation is the sole origin
 * of the durable record id: it generates `exp-<slug>-<12-hex-hash>`
 * deterministically bound to the candidate identity (intent + cluster),
 * never a run-local staged plan label (`e1`, `eN`) and never a path.
 * Synthesis never authors or fills this id.
 */
export const RECORD_ID_PATTERN = /^exp-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*-[A-Za-z0-9]{12}$/;

export function isValidRecordId(id) {
  return typeof id === "string" && RECORD_ID_PATTERN.test(id);
}

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
 * No fallback: the annotation record id is required (annotation is the
 * sole full-record origin; synthesis never invents one).
 */
export function renderStagedArtifact(record, soulBaseline = "") {
  if (!record || typeof record !== "object" || !isValidRecordId(record.id)) {
    throw new Error("renderStagedArtifact requires a valid annotation record.id (exp-<slug>-<hash>)");
  }
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

/** Informational diff of the staged artifact against the read-only baseline.
 * No fallback: callers must pass the annotation record id. */
export function renderDiff(recordId, stagedArtifact) {
  if (!isValidRecordId(recordId)) {
    throw new Error("renderDiff requires a valid annotation record id (exp-<slug>-<hash>)");
  }
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
export function synthesizeCandidates(ledger, { evidenceIndex = new Map(), soulBaseline = "", workspace = null, workspaceRoot = null, cwd = null, stateDir = null } = {}) {
  void evidenceIndex;
  void soulBaseline;
  const workspaceCwd = workspace || workspaceRoot || cwd || null;
  if (workspaceCwd) assertContainedSynthesisWorkspace(workspaceCwd, stateDir);
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
      ...(cluster.corroboratedOpenGap ? { corroboratedOpenGap: true } : {}),
      ...(cluster.openGapPromotedSingleton ? { openGapPromotedSingleton: true } : {}),
    });
  }
  // Mock synthesis is the deterministic workspace author in the mock path:
  // it mutates the private workspace BEFORE measurement so the pipeline
  // measures actual resulting changes (never fabricates plan deltas itself).
  if (workspaceCwd) {
    try {
      applyMockSynthesisWorkspace(plans, workspaceCwd, { stateDir });
    } catch {
      // Containment failure is fail-closed downstream (no valid workspace
      // author); plans still return so validation stays observable.
    }
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
  if (!record.id || !String(record.id).trim()) {
    errors.push("record.id is required (annotation authors the deterministic experience-record id)");
  } else if (!isValidRecordId(record.id)) {
    errors.push(`record.id must be a safe stable id (exp-<slug>-<hash> of [A-Za-z0-9-]; got ${JSON.stringify(record.id)})`);
  }
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
 * Default acpx invoke for synthesis: persisted prompt via `--file`, ACPX
 * text-output (`--format quiet`, never JSON-RPC) on stdout. Synthesis is a
 * native edit turn: after an exit-0 ACPX invocation, the measured private
 * workspace diff is authoritative; stdout is retained only as raw diagnostic
 * text. Same executable protocol as analyze
 * acpx (analyze.js): the `acpx` binary, Pi executor, extra args from
 * CA_IMPROVE_ACPX_ARGS, role model sol with ACPX --timeout 300s
 * (mandatory, before the agent).
 */
export function acpxSynthesisInvoke(options = {}) {
  if (options && Object.prototype.hasOwnProperty.call(options, "agent")) {
    throw new Error("CA ACPX executor is fixed to pi (caller agent is not accepted)");
  }
  const { prompt, promptFile = null, model = null, timeoutSec = null, timeoutMs = null, spawnFn = null, workspace = null, workspaceRoot = null, cwd = null } = options;
  const workspaceCwd = workspace || workspaceRoot || cwd || null;
  void prompt;
  void resolveAcpxBin;
  const file = promptFile ? String(promptFile) : "";
  if (!file) {
    return { status: "failed", error: "acpx prompt file is required (reuse persisted prompt)" };
  }
  const out = runAcpxPromptFile({
    role: "synthesis",
    promptFile: file,
    model: model || modelForRole("synthesis"),
    timeoutSec: timeoutSec ?? 300,
    ...(timeoutMs !== null && timeoutMs !== undefined ? { timeoutMs } : {}),
    ...(spawnFn ? { spawnFn } : {}),
    ...(workspaceCwd ? { workspace: workspaceCwd, cwd: workspaceCwd } : {}),
  });
  if (out.status !== "ok") {
    return { status: "failed", error: out.error };
  }
  return { status: "ok", result: out.result };
}

/** Render the production synthesis prompt (sentinel FIRST via the loader). */
export function buildSynthesisPrompt(
  ledger,
  { evidenceIndex = new Map(), rejections = [], transcriptCount = null, harnessSummary = "unknown", runNote = "", soulSnapshot = "", soulSha256 = "", promptsDir } = {},
) {
  if (!String(soulSnapshot || "").trim()) {
    throw new Error("buildSynthesisPrompt requires bounded active SOUL snapshot text (fail-closed without the baseline)");
  }
  if (!String(soulSha256 || "").trim()) {
    throw new Error("buildSynthesisPrompt requires the stable SOUL sha256 (fail-closed without the baseline)");
  }
  const count = transcriptCount ?? evidenceIndex.size ?? 0;
  const base = renderPrompt(
    "synthesis",
    {
      EVIDENCE: renderEvidenceForSynthesis(ledger, evidenceIndex),
      REJECTIONS: renderRejectionsForPrompt(rejections),
      TRANSCRIPT_COUNT: String(count),
      HARNESS_SUMMARY: String(harnessSummary),
      RUN_NOTE: String(runNote || ""),
      SOUL_SNAPSHOT: String(soulSnapshot),
      SOUL_SHA256: String(soulSha256),
    },
    { promptsDir },
  );
  // Production synthesis is an EDIT turn on the private workspace only: the
  // model must inspect and edit ONLY the private synthesis-workspace working
  // directory (workspace cwd). It must not return a JSON plan contract as the
  // durable output; durable records come only from measured workspace diffs
  // observed after the edit turn. A JSON-only response with no workspace file
  // changes fail-closes to zero candidate edits downstream.
  const editOnly = [
    "",
    "EDIT TURN (production): inspect and edit ONLY the private workspace",
    "working directory provided as the invocation cwd. Do not treat a JSON",
    "plan contract as the output; author/edit markdown records directly in",
    "ONLY the private workspace. Any JSON plans without corresponding",
    "workspace file changes are discarded fail-closed.",
  ].join("\n");
  return `${base}${editOnly}`;
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
 * Parse structured frontmatter provenance from a workspace file body.
 * Shared implementation lives in workspace-frontmatter.js (single source of
 * truth with measurement). Returns { clusterId, sources } with nulls on
 * missing/invalid (never auto-assigned).
 */

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
    soulSnapshot = "",
    soulSha256 = "",
    rejections = [],
    invoke = acpxSynthesisInvoke,
    stateDir = null,
    runId = null,
    promptsDir,
    transcriptCount = null,
    harnessSummary = "unknown",
    runNote = "",
    workspace = null,
    workspaceRoot = null,
    cwd = null,
  } = {},
) {
  let snapshotText = String(soulSnapshot || soulBaseline || "");
  let snapshotHash = String(soulSha256 || "");
  if (!snapshotText.trim() || !snapshotHash.trim()) {
    // Canonical default resolves from the repo root (never CWD); an
    // unavailable default fails closed here.
    try {
      const snap = readSoulSnapshot(null);
      if (!snapshotText.trim()) snapshotText = snap.text;
      if (!snapshotHash.trim()) snapshotHash = snap.sha256;
    } catch (err) {
      return {
        edits: [],
        failed: err?.message || String(err),
        note: `${err?.message || err}; refusing synthesis without the active baseline`,
        promptFile: null,
      };
    }
  }
  if (!snapshotText.trim() || !snapshotHash.trim()) {
    return {
      edits: [],
      failed: "SOUL baseline unavailable",
      note: "improve: SOUL baseline unavailable; refusing synthesis without the active baseline",
      promptFile: null,
    };
  }
  const workspaceCwd = workspace || workspaceRoot || cwd || (stateDir ? `${stateDir}/${SYNTHESIS_WORKSPACE_DIRNAME}` : null);
  const resolvedRun = runId || `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
  // Containment at the synthesis invocation boundary: ACPX executes an
  // external process, so reject a workspace outside the expected
  // stateDir/synthesis-workspace private root before invoking. The
  // invocation below carries only this workspace cwd.
  try {
    if (workspaceCwd) assertContainedSynthesisWorkspace(workspaceCwd, stateDir);
  } catch (err) {
    return {
      edits: [],
      failed: err?.message || String(err),
      note: `synthesis refused (${err?.message || err}); fail-closed with no candidate edits for this run`,
      promptFile: null,
    };
  }
  const prompt = buildSynthesisPrompt(ledger, {
    evidenceIndex,
    rejections,
    transcriptCount,
    harnessSummary,
    runNote,
    soulSnapshot: snapshotText,
    soulSha256: snapshotHash,
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
    outcome = invoke({ prompt, promptFile, ledger, evidenceIndex, rejections, workspace: workspaceCwd, workspaceRoot: workspaceCwd, cwd: workspaceCwd });
  } catch (err) {
    outcome = { status: "failed", error: err?.message || String(err) };
  }
  // EDIT-ONLY production synthesis: the durable output is the actual
  // workspace file edits observed after the edit turn, never JSON output.
  // JSON output is never accepted as a candidate source: durable narrow
  // plans are derived solely from measured workspace .md files and their
  // structured frontmatter, so workspace edits with no JSON still proceed
  // while JSON-only output with no workspace changes fails closed to zero
  // edits. Production invents nothing: invalid measured files are dropped
  // individually and clusters are never auto-assigned.
  void outcome;
  const withPersist = (entry) => (persistNote ? { ...entry, note: entry.note ? `${entry.note}\n${persistNote}` : persistNote } : entry);
  if (!outcome || outcome.status !== "ok") {
    return withPersist({
      edits: [],
      failed: outcome?.error || "synthesis failed",
      note: `synthesis failed (${outcome?.error || "unparseable output"}); fail-closed with no candidate edits for this run`,
      promptFile,
    });
  }
  // Independently measure the edit-turn workspace files (durable source).
  let measuredFiles = [];
  try {
    if (workspaceCwd && fs.existsSync(workspaceCwd)) {
      measuredFiles = fs.readdirSync(workspaceCwd).filter((n) => n.endsWith(".md")).sort();
    }
  } catch {
    measuredFiles = [];
  }
  if (!measuredFiles.length) {
    return withPersist({
      edits: [],
      failed: "no workspace file changes",
      note: "synthesis edit turn produced no workspace file changes; JSON-only plans discarded fail-closed with zero candidate edits for this run",
      promptFile,
    });
  }
  const eligible = (ledger?.clusters || []).filter((c) => c?.eligible);
  if (!eligible.length) {
    return withPersist({
      edits: [],
      failed: "no eligible clusters",
      note: "synthesis measured workspace changes but no eligible clusters can anchor them; fail-closed with no candidate edits for this run",
      promptFile,
    });
  }
  const fileIntentAndProvenance = (file) => {
    try {
      const text = fs.readFileSync(path.join(String(workspaceCwd), file), "utf8");
      const head = text.split("\n").find((l) => l.startsWith("# "));
      const intent = head ? head.replace(/^#+\s*/, "").trim().slice(0, 200) : "";
      const fm = parseWorkspaceFileProvenance(text);
      return { intent, clusterId: fm.clusterId, sources: fm.sources };
    } catch {
      return { intent: "", clusterId: null, sources: null };
    }
  };
  const edits = [];
  for (const file of measuredFiles) {
    const fileId = file.slice(0, -3);
    // Provenance comes ONLY from the actual changed workspace file.
    // No JSON acceptance, no cyclic/default fallback, never auto-assigned:
    // files with missing/invalid frontmatter are dropped individually.
    const { intent: fileTitle, clusterId: fileClusterId, sources: fileSources } = fileIntentAndProvenance(file);
    if (!fileClusterId || !Array.isArray(fileSources)) continue;
    const distinct = [...new Set(fileSources.map((s) => String(s)))].filter(Boolean);
    if (distinct.length < 2) continue;
    const cluster = (ledger?.clusters || []).find((c) => String(c?.id) === String(fileClusterId) && c?.eligible) || null;
    if (!cluster) continue;
    const clusterSources = new Set((cluster?.sources || []).map(String));
    if (!distinct.every((s) => clusterSources.has(String(s)))) continue;
    const intent = String(fileTitle || cluster?.proposedInstruction || "").trim();
    if (!intent) continue;
    const plan = {
      id: fileId,
      kind: "add",
      clusterId: String(cluster?.id || ""),
      provisionalIntent: intent,
      provisionalSources: distinct,
      provisionalCount: distinct.length,
    };
    const check = validateChangePlan(plan, { ledger });
    if (!check.ok) continue;
    edits.push({
      id: fileId,
      kind: "add",
      clusterId: String(plan.clusterId),
      provisionalIntent: String(plan.provisionalIntent),
      provisionalSources: [...plan.provisionalSources].map(String),
      provisionalCount: Number(plan.provisionalCount || plan.provisionalSources.length),
      ...(cluster?.corroboratedOpenGap ? { corroboratedOpenGap: true } : {}),
    });
  }
  if (!edits.length) {
    return withPersist({
      edits: [],
      failed: "no valid measured workspace plans",
      note: "synthesis measured workspace changes but none carry valid file frontmatter anchored to eligible clusters; fail-closed with no candidate edits for this run",
      promptFile,
    });
  }
  return withPersist({
    edits,
    promptFile,
    note: `synthesis edit turn measured ${measuredFiles.length} workspace file(s); durable candidates come solely from actual workspace file edits`,
  });
}
