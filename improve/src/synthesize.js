// SPDX: MIT (Backpass MIT (c) 2026 Kun Chen) — see improve/LICENSE.NOTICE.
// Synthesis adapted from Backpass src/synthesize.js + src/proposal.js
// (commit 0268201), narrowed to this slice's contract: text-only ACPX
// proposer of narrow staged change plans plus deterministic code
// materialization under stateDir/synthesis-workspace. The SOUL baseline
// is read-only context — synthesis never patches SOUL, memory files, or
// skills. The apply gate owns all durable writes.

import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";

import { renderPrompt } from "./prompts.js";
import { persistPrompt, resolveAcpxBin } from "./analyze.js";
import { parseWorkspaceFileProvenance } from "./workspace-frontmatter.js";
import { runAcpxPromptFile } from "./acpx-text.js";
import { parseStrictBoundedSynthesisStdout } from "./synthesis-parser.js";
import { modelForRole } from "./models.js";
import { readSoulSnapshot } from "./soul.js";
import { assertMinGapEvidence } from "./state.js";
// Private writable synthesis workspace under stateDir (synthesis-workspace).
// ACPX synthesis is text-only (no workspace cwd); validated narrow plans
// are materialized deterministically by code inside it. Synthesis must
// refuse/forbid/deny any durable write to the source repo, SOUL.md,
// skills, or Hermes; apply remains the only durable experience
// destination writer.
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
 * carries no workspace cwd (text-only). Fail-closed (throw) on escape.
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
 * Production never calls this and never passes a workspace/cwd to ACPX —
 * production synthesis is a text-only proposer (no workspace cwd) and
 * deterministic code materializes validated plans inside the private
 * workspace. Containment is enforced before any write. No synthetic
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
  // No synthetic fallback: with no eligible plans the mock authors nothing.
  // Empty evidence yields zero workspace files and zero edits downstream.
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
  for (const forbidden of ["file", "path", "workspace", "workspaceRoot", "cwd", "sources"]) {
    if (plan[forbidden] !== undefined) errors.push(`filesystem/source field ${forbidden} must not appear on a staged change plan (deterministic code assigns storage)`);
  }
  const allowedPlanKeys = new Set(["id", "kind", "clusterId", "provisionalIntent", "intent", "provisionalSources", "provisionalCount", "corroboratedOpenGap", "openGapPromotedSingleton", "reverted"]);
  for (const key of Object.keys(plan)) {
    if (!allowedPlanKeys.has(key)) errors.push(`unexpected field ${JSON.stringify(key)} on staged change plan`);
  }
  if (plan.id !== undefined) {
    const sid = String(plan.id);
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(sid) || sid.includes("..") || sid.includes("/") || sid.includes("\\")) {
      errors.push(`plan id is not a safe label (got ${JSON.stringify(plan.id)})`);
    }
  }
  if (Array.isArray(provisionalSources)) {
    for (const s of provisionalSources) {
      const ss = String(s);
      if (!ss.trim() || ss.includes("/") || ss.includes("\\") || ss.includes("..")) {
        errors.push(`provisional source is path-like or empty (${JSON.stringify(s)})`);
        break;
      }
    }
  }
  if (plan.clusterId !== undefined) {
    const cid = String(plan.clusterId);
    if (cid.includes("/") || cid.includes("\\") || cid.includes("..")) {
      errors.push(`clusterId is path-like (${JSON.stringify(plan.clusterId)})`);
    }
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

// --- strict provisional-plan constants (Option 2 text-only) ------------------

/** Max raw ACPX stdout chars accepted for the synthesis payload. */
export const SYNTHESIS_STDOUT_MAX_CHARS = 20000;
/** Max provisional plans accepted per run (bounded payload). */
export const SYNTHESIS_MAX_PLANS = 16;
/** Max chars for one provisional intent. */
export const PROVISIONAL_INTENT_MAX_CHARS = 500;
/** Safe plan label: no slashes, no traversal, bounded. */
export const SAFE_PLAN_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;
/** Whitelisted provisional plan keys (text-only stdout contract). */
export const ALLOWED_PLAN_KEYS = ["id", "kind", "clusterId", "provisionalIntent", "provisionalSources", "provisionalCount"];
/** Authoritative final fields that must never appear on provisional plans. */
export const AUTHORITATIVE_PLAN_FIELDS = ["record", "evidence", "title", "body", "counterevidence", "compilerImplication", "stagedArtifact", "diff", "rationale", "instructions"];
/** Filesystem/path fields that must never appear (no model-controlled target). */
export const PATH_LIKE_PLAN_FIELDS = ["file", "path", "workspace", "workspaceRoot", "cwd", "sources", "target", "dir", "directory"];

function isPathLike(value) {
  const s = String(value || "");
  return !s.trim() ? true : s.includes("/") || s.includes("\\") || s.includes("..") || s.startsWith("~") || /^[A-Za-z]:/.test(s);
}

/**
 * Strict fail-closed validation of the raw ACPX stdout payload against the
 * eligible ledger. Rejects: malformed (missing/non-array plans,
 * candidates/edits keys), unknown/ineligible clusters, <2 distinct known
 * sources, authoritative final fields, path-like or unexpected fields,
 * duplicate or unsafe ids. Returns { ok, plans, errors } where plans are
 * normalized narrow plans only.
 */
export function validateProvisionalPlans(raw, { ledger, floor = 2 } = {}) {
  const errors = [];
  const f = Number(floor);
  const minSources = Number.isInteger(f) && f >= 2 ? f : 2;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return { ok: false, plans: [], errors: ["synthesis payload must be an object with a plans array"] };
  }
  if (raw.candidates !== undefined || raw.edits !== undefined) {
    return { ok: false, plans: [], errors: ["synthesis payload must use {plans:[...]} only (candidates/edits rejected)"] };
  }
  const rootKeys = Object.keys(raw);
  if (rootKeys.length !== 1 || rootKeys[0] !== "plans") {
    return { ok: false, plans: [], errors: ["synthesis payload must use {plans:[...]} only (no extra top-level fields)"] };
  }
  if (!Array.isArray(raw.plans)) {
    return { ok: false, plans: [], errors: ["synthesis payload must carry plans array"] };
  }
  if (raw.plans.length > SYNTHESIS_MAX_PLANS) {
    return { ok: false, plans: [], errors: [`synthesis payload exceeds ${SYNTHESIS_MAX_PLANS} plans (got ${raw.plans.length})`] };
  }
  const eligibleById = new Map((ledger?.clusters || []).filter((c) => c?.eligible).map((c) => [String(c.id), c]));
  const seenIds = new Set();
  const plans = [];
  raw.plans.forEach((plan, i) => {
    const tag = `plans[${i}]`;
    if (!plan || typeof plan !== "object" || Array.isArray(plan)) {
      errors.push(`${tag} is malformed (object required)`);
      return;
    }
    for (const key of Object.keys(plan)) {
      if (!ALLOWED_PLAN_KEYS.includes(key)) {
        if (AUTHORITATIVE_PLAN_FIELDS.includes(key)) errors.push(`${tag} carries authoritative field ${key} (annotation owns it)`);
        else if (PATH_LIKE_PLAN_FIELDS.includes(key)) errors.push(`${tag} carries filesystem field ${key} (no model-controlled path target)`);
        else errors.push(`${tag} carries unexpected field ${JSON.stringify(key)}`);
      }
    }
    if (plan.kind !== undefined && plan.kind !== "add") errors.push(`${tag} kind must be "add"`);
    const cid = String(plan.clusterId || "").trim();
    if (!cid) {
      errors.push(`${tag} clusterId is required`);
      return;
    }
    if (isPathLike(cid)) {
      errors.push(`${tag} clusterId is path-like`);
      return;
    }
    const cluster = eligibleById.get(cid);
    if (!cluster) {
      const known = (ledger?.clusters || []).some((c) => String(c?.id) === cid);
      errors.push(known ? `${tag} cluster ${JSON.stringify(cid)} is not eligible` : `${tag} unknown cluster ${JSON.stringify(cid)}`);
      return;
    }
    const intentRaw = plan.provisionalIntent ?? plan.intent;
    const intent = String(intentRaw || "").trim();
    if (!intent) {
      errors.push(`${tag} provisionalIntent is required`);
      return;
    }
    if (intent.length > PROVISIONAL_INTENT_MAX_CHARS) {
      errors.push(`${tag} provisionalIntent exceeds ${PROVISIONAL_INTENT_MAX_CHARS} chars`);
      return;
    }
    const srcRaw = plan.provisionalSources;
    if (!Array.isArray(srcRaw)) {
      errors.push(`${tag} provisionalSources array is required`);
      return;
    }
    const distinct = [...new Set(srcRaw.map((s) => String(s).trim()).filter(Boolean))];
    if (distinct.length < minSources) {
      errors.push(`${tag} provisionalSources needs >=${minSources} distinct sessions`);
      return;
    }
    const clusterSources = new Set((cluster.sources || []).map(String));
    for (const s of distinct) {
      if (isPathLike(s)) {
        errors.push(`${tag} provisional source is path-like (${JSON.stringify(s)})`);
        return;
      }
      if (!clusterSources.has(String(s))) {
        errors.push(`${tag} provisional source ${JSON.stringify(s)} is not evidence from cluster ${cluster.id}`);
        return;
      }
    }
    if (plan.provisionalCount !== undefined && Number(plan.provisionalCount) !== distinct.length) {
      errors.push(`${tag} provisionalCount must equal distinct source count`);
      return;
    }
    let pid = plan.id !== undefined ? String(plan.id).trim() : `e${plans.length + 1}`;
    if (!SAFE_PLAN_ID_PATTERN.test(pid) || pid.includes("..")) {
      errors.push(`${tag} id is not a safe label (got ${JSON.stringify(plan.id)})`);
      return;
    }
    const safeFile = pid.replace(/[^a-zA-Z0-9._-]/g, "_");
    if (seenIds.has(safeFile)) {
      errors.push(`${tag} duplicate plan id ${JSON.stringify(pid)}`);
      return;
    }
    seenIds.add(safeFile);
    plans.push({
      id: pid,
      kind: "add",
      clusterId: String(cluster.id),
      provisionalIntent: intent.slice(0, PROVISIONAL_INTENT_MAX_CHARS),
      provisionalSources: distinct,
      provisionalCount: distinct.length,
    });
  });
  if (errors.length) return { ok: false, plans: [], errors };
  return { ok: true, plans, errors: [] };
}

function assertNotSymlink(p, label) {
  let st = null;
  try {
    st = fs.lstatSync(String(p));
  } catch {
    return;
  }
  if (st && typeof st.isSymbolicLink === "function" && st.isSymbolicLink()) {
    throw new Error(`materialize refused: ${label} is a symlink (${JSON.stringify(String(p))})`);
  }
}

function assertNoSymlinkComponents(base, root) {
  assertNotSymlink(base, "stateDir/synthesis-workspace root");
  if (root === base) return;
  const rel = path.relative(base, root);
  if (!rel || rel.startsWith("..") || path.isAbsolute(rel)) return;
  let cur = base;
  for (const part of rel.split(path.sep).filter(Boolean)) {
    cur = path.join(cur, part);
    assertNotSymlink(cur, "synthesis-workspace component");
  }
}

function requiredFdPrimitives() {
  const O = fs.constants || {};
  if (process.platform !== "linux") return "platform is not linux (descriptor-relative traversal requires Linux)";
  if (typeof O.O_NOFOLLOW !== "number") return "O_NOFOLLOW unavailable";
  if (typeof O.O_DIRECTORY !== "number") return "O_DIRECTORY unavailable";
  try {
    const st = fs.statSync("/proc/self/fd");
    if (typeof st.isDirectory === "function" && !st.isDirectory()) return "/proc/self/fd unavailable";
  } catch {
    return "/proc/self/fd unavailable";
  }
  return null;
}

function closeQuiet(fd) {
  try {
    if (typeof fd === "number" && fd >= 0) fs.closeSync(fd);
  } catch {}
}

function procChildFdPath(parentFd, name) {
  return `/proc/self/fd/${Number(parentFd)}/${String(name)}`;
}

function throwSymlink(label, p) {
  throw new Error(`materialize refused: ${label} is a symlink (${JSON.stringify(String(p))})`);
}

// Open an existing child directory relative to a held directory fd.
// Uses O_DIRECTORY|O_NOFOLLOW so a symlinked child never resolves through
// the link. A symlink-to-directory surfaces as ENOTDIR under O_DIRECTORY,
// so disambiguate with a no-DIRECTORY probe: ELOOP there means symlink,
// success means a non-directory exists.
function openChildDirFd(parentFd, comp, displayPath, label) {
  const O = fs.constants;
  const childPath = procChildFdPath(parentFd, comp);
  try {
    return fs.openSync(childPath, O.O_RDONLY | O.O_DIRECTORY | O.O_NOFOLLOW);
  } catch (err) {
    if (err?.code === "ELOOP") throwSymlink(label, displayPath);
    if (err?.code === "ENOTDIR") {
      try {
        const probe = fs.openSync(childPath, O.O_RDONLY | O.O_NOFOLLOW);
        closeQuiet(probe);
        throw new Error(`materialize refused: ${label} is not a directory (${JSON.stringify(String(displayPath))})`);
      } catch (probeErr) {
        if (probeErr?.code === "ELOOP" || /is a symlink/.test(probeErr?.message || "")) {
          throwSymlink(label, displayPath);
        }
        if (probeErr?.message?.startsWith("materialize refused")) throw probeErr;
        throw new Error(`materialize refused: cannot open ${label} (${JSON.stringify(String(displayPath))}; ${probeErr?.message || probeErr})`);
      }
    }
    throw err;
  }
}

function mkdirChildFd(parentFd, comp, displayPath, label) {
  const childPath = procChildFdPath(parentFd, comp);
  try {
    fs.mkdirSync(childPath, { mode: 0o755 });
  } catch (err) {
    // EEXIST is a racy create (possibly a symlink planted between the
    // failed open and the mkdir): the caller re-opens with NOFOLLOW checks.
    if (err?.code === "EEXIST") return;
    throw new Error(`materialize refused: cannot create ${label} (${JSON.stringify(String(displayPath))}; ${err?.message || err})`);
  }
}

// Traverse/create a directory chain relative to a held directory fd.
// Never resolves a full pathname: every component is opened/created via
// the parent directory descriptor (/proc/self/fd). Does not close startFd;
// closes each intermediate as it descends; the caller owns the leaf fd.
function walkDirChainFd(startFd, startPath, endPath, label) {
  const O = fs.constants;
  const rel = path.relative(String(startPath), String(endPath));
  if (!rel) {
    // Independent fd for the same directory so ownership stays simple.
    // The trailing "/." matters: opening /proc/self/fd/N directly with
    // O_DIRECTORY|O_NOFOLLOW rejects the magic symlink itself (ENOTDIR);
    // "/." resolves to the pinned directory.
    try {
      return fs.openSync(`/proc/self/fd/${Number(startFd)}/.`, O.O_RDONLY | O.O_DIRECTORY | O.O_NOFOLLOW);
    } catch (err) {
      if (err?.code === "ELOOP") throwSymlink(label, String(startPath));
      throw new Error(`materialize refused: cannot open ${label} (${JSON.stringify(String(startPath))}; ${err?.message || err})`);
    }
  }
  if (rel.startsWith("..") || path.isAbsolute(rel)) {
    throw new Error(`materialize refused: target outside stateDir/synthesis-workspace (${JSON.stringify(String(endPath))})`);
  }
  let cur = startFd;
  let ownsCur = false;
  let curPath = String(startPath);
  try {
    for (const part of rel.split(path.sep).filter(Boolean)) {
      if (part === "." || part === ".." || part.includes("\0")) {
        throw new Error(`materialize refused: unsafe path component (${JSON.stringify(part)})`);
      }
      curPath = path.join(curPath, part);
      let next = null;
      try {
        next = openChildDirFd(cur, part, curPath, label);
      } catch (err) {
        if (err?.code !== "ENOENT") throw err;
        mkdirChildFd(cur, part, curPath, label);
        next = openChildDirFd(cur, part, curPath, label);
      }
      if (ownsCur) closeQuiet(cur);
      cur = next;
      ownsCur = true;
    }
    const leaf = cur;
    cur = null;
    ownsCur = false;
    return leaf;
  } finally {
    if (cur !== null && ownsCur) closeQuiet(cur);
  }
}

// Open/create the final markdown relative to the held workspace directory
// fd with O_NOFOLLOW: a pre-planted symlink fails with ELOOP and the
// outside target is never created or truncated. The full pathname is used
// only for messages and a post-write lstat tripwire, never for the open.
function writeFileViaDirFd(dirFd, name, body, rootDisplay) {
  const O = fs.constants;
  const fname = String(name);
  if (!fname || fname.includes("/") || fname.includes("\\") || fname.includes("\0") || fname !== path.basename(fname)) {
    throw new Error(`materialize refused: unsafe file name (${JSON.stringify(fname)})`);
  }
  const display = path.join(String(rootDisplay), fname);
  assertNotSymlink(display, "synthesis target");
  const childPath = procChildFdPath(dirFd, fname);
  let fd = -1;
  try {
    fd = fs.openSync(childPath, O.O_WRONLY | O.O_CREAT | O.O_TRUNC | O.O_NOFOLLOW, 0o644);
  } catch (err) {
    throw new Error(`materialize refused: symlink or unsafe target (${JSON.stringify(display)}; code=${err?.code || "unknown"}; ${err?.message || err})`, { cause: err });
  }
  try {
    const st = fs.fstatSync(fd);
    if (typeof st.isFile === "function" && !st.isFile()) {
      throw new Error(`materialize refused: symlink or unsafe target (${JSON.stringify(display)}; not a regular file)`);
    }
    fs.writeSync(fd, String(body), null, "utf8");
  } finally {
    closeQuiet(fd);
  }
  assertNotSymlink(display, "synthesis target");
}

/**
 * Deterministic materialization of text-only ACPX synthesis plans: write
 * only validated narrow plans as Markdown under the existing
 * stateDir/synthesis-workspace root. Filenames derive solely from
 * validated safe ids (no model-controlled path target); content is the
 * two-key provenance frontmatter plus heading/prose. Returns the written
 * files. Containment-guarded; throws fail-closed on escape or on any
 * symlink in the workspace root, intermediate components, or target.
 *
 * TOCTOU design: after the string containment checks, every directory
 * component is traversed/created relative to a held Linux directory
 * descriptor (O_DIRECTORY|O_NOFOLLOW via /proc/self/fd) anchored on the
 * trusted stateDir, and each final markdown is opened/created relative to
 * the held workspace directory fd with O_NOFOLLOW. No unchecked full path
 * is ever resolved for an open/mkdir after validation. Fails closed when
 * the platform primitives (Linux, O_NOFOLLOW, O_DIRECTORY, /proc/self/fd)
 * are unavailable. All descriptors close on success and on errors.
 *
 * Test seam (narrow, test-only): pass `_beforeFinalOpen` with
 * NODE_ENV === 'test' to run a synchronous hook after the workspace
 * directories are pinned but before the final opens. Used by the fd-race
 * regression test to swap a checked intermediate for a symlink and assert
 * rejection with no outside create/truncate. The hook receives only minimal
 * pathname data ({ root }) — never a file descriptor. Supplying the seam
 * outside NODE_ENV === 'test' is rejected fail-closed.
 */
export function materializeValidatedPlans(plans, { stateDir, workspaceRoot = null, ledger = null, floor = 2, _beforeFinalOpen = null } = {}) {
  if (!stateDir) throw new Error("materializeValidatedPlans requires stateDir");
  const anchor = path.resolve(String(stateDir));
  // Ancestry symlink guard: reject when any existing prefix of stateDir
  // resolves through a symlink (e.g. /tmp/link-parent/state where
  // link-parent -> real-parent). Compares the realpath of the nearest
  // existing ancestor to its lexical absolute form; any difference means
  // a symlink in the chain. Runs before any mkdir so nothing is created
  // via the link target. Direct stateDir/target checks below are retained.
  {
    let existing = anchor;
    while (true) {
      try {
        fs.lstatSync(existing);
        break;
      } catch (err) {
        if (err?.code !== "ENOENT") throw err;
        const parent = path.dirname(existing);
        if (parent === existing) break;
        existing = parent;
      }
    }
    try {
      const real = fs.realpathSync(existing);
      if (real !== existing) {
        throw new Error(`materialize refused: stateDir ancestry resolves through a symlink (${JSON.stringify(anchor)} resolves via ${JSON.stringify(real)})`);
      }
    } catch (err) {
      if (err?.message?.includes("stateDir ancestry resolves through a symlink")) throw err;
    }
  }
  let anchorSt = null;
  try {
    anchorSt = fs.lstatSync(anchor);
  } catch {
    anchorSt = null;
  }
  if (!anchorSt) {
    throw new Error(`materialize refused: stateDir does not exist (${JSON.stringify(anchor)})`);
  }
  if (typeof anchorSt.isSymbolicLink === "function" && anchorSt.isSymbolicLink()) {
    throw new Error(`materialize refused: stateDir is a symlink (${JSON.stringify(anchor)})`);
  }
  if (typeof anchorSt.isDirectory === "function" && !anchorSt.isDirectory()) {
    throw new Error(`materialize refused: stateDir is not a directory (${JSON.stringify(anchor)})`);
  }
  const base = path.join(anchor, SYNTHESIS_WORKSPACE_DIRNAME);
  const root = workspaceRoot ? path.resolve(String(workspaceRoot)) : base;
  if (!(root === base || root.startsWith(`${base}${path.sep}`))) {
    throw new Error(`materialize refused: target outside stateDir/synthesis-workspace (${JSON.stringify(root)})`);
  }
  assertNoSymlinkComponents(base, root);
  assertContainedSynthesisWorkspace(root, stateDir);
  if (!Array.isArray(plans)) {
    throw new Error("materialize refused: plans array is required (unvalidated payload)");
  }
  const missingPrimitive = requiredFdPrimitives();
  if (missingPrimitive) {
    throw new Error(`materialize refused: descriptor-relative traversal unavailable (${missingPrimitive})`);
  }
  const eligibleById = ledger
    ? new Map((ledger?.clusters || []).filter((c) => c?.eligible).map((c) => [String(c.id), c]))
    : null;
  const f = Number(floor);
  const minSources = Number.isInteger(f) && f >= 2 ? f : 2;
  const entries = [];
  const seen = new Set();
  for (const plan of plans || []) {
    if (!plan || typeof plan !== "object" || Array.isArray(plan)) {
      throw new Error("materialize refused: plan object is required (unvalidated payload)");
    }
    if (plan.kind !== undefined && plan.kind !== "add") {
      throw new Error(`materialize refused: kind must be "add" (got ${JSON.stringify(plan.kind)})`);
    }
    for (const key of AUTHORITATIVE_PLAN_FIELDS) {
      if (plan[key] !== undefined) {
        throw new Error(`materialize refused: authoritative field ${key} (unvalidated payload; annotation owns it)`);
      }
    }
    for (const key of PATH_LIKE_PLAN_FIELDS) {
      if (plan[key] !== undefined) {
        throw new Error(`materialize refused: filesystem field ${key} (unvalidated payload; no model-controlled path target)`);
      }
    }
    const cid = String(plan.clusterId || "").trim();
    if (!cid || isPathLike(cid)) {
      throw new Error(`materialize refused: unsafe or missing clusterId ${JSON.stringify(plan.clusterId)}`);
    }
    if (eligibleById && !eligibleById.has(cid)) {
      throw new Error(`materialize refused: cluster ${JSON.stringify(cid)} is not eligible (unvalidated payload)`);
    }
    const intent = String(plan.provisionalIntent || "").trim();
    if (!intent || intent.length > PROVISIONAL_INTENT_MAX_CHARS) {
      throw new Error("materialize refused: provisionalIntent is required and bounded (unvalidated payload)");
    }
    const srcRaw = plan.provisionalSources;
    if (!Array.isArray(srcRaw)) {
      throw new Error("materialize refused: provisionalSources array is required (unvalidated payload)");
    }
    const distinct = [...new Set(srcRaw.map((s) => String(s).trim()).filter(Boolean))];
    if (distinct.length < minSources) {
      throw new Error(`materialize refused: provisionalSources needs >=${minSources} distinct sessions (unvalidated payload)`);
    }
    for (const s of distinct) {
      if (isPathLike(s)) {
        throw new Error(`materialize refused: provisional source is path-like (${JSON.stringify(s)})`);
      }
    }
    if (eligibleById) {
      const clusterSources = new Set((eligibleById.get(cid)?.sources || []).map(String));
      for (const s of distinct) {
        if (!clusterSources.has(String(s))) {
          throw new Error(`materialize refused: provisional source ${JSON.stringify(s)} is not evidence from cluster ${cid}`);
        }
      }
    }
    if (plan.provisionalCount !== undefined && Number(plan.provisionalCount) !== distinct.length) {
      throw new Error("materialize refused: provisionalCount must equal distinct source count (unvalidated payload)");
    }
    const pid = safePlanFileId(plan?.id);
    if (!SAFE_PLAN_ID_PATTERN.test(pid) || seen.has(pid)) {
      throw new Error(`materialize refused: duplicate or unsafe plan id ${JSON.stringify(plan?.id)}`);
    }
    seen.add(pid);
    const file = `${pid}.md`;
    const target = path.join(root, file);
    assertSynthesisWorkspaceOnly(target, root);
    const title = String(plan?.provisionalIntent || "untitled").slice(0, PROVISIONAL_INTENT_MAX_CHARS);
    const clusterId = String(plan?.clusterId || "unknown");
    const sources = [...(plan?.provisionalSources || []).map(String)];
    const sourceLines = sources.map((s) => `  - ${s}`).join("\n");
    const body = `---\nclusterId: ${clusterId}\nprovisionalSources:\n${sourceLines}\n---\n# ${title}\n\nRecurring gap (${clusterId}): ${title}\n\nSources: ${sources.join(", ")}\n`;
    entries.push({ file, body });
  }
  // Descriptor-relative traversal: anchor stateDir, then walk to the
  // workspace root using only held directory descriptors. No mkdir/open
  // resolves an unchecked full path from here on.
  const O = fs.constants;
  let anchorFd = -1;
  let baseFd = -1;
  let rootFd = -1;
  try {
    try {
      anchorFd = fs.openSync(anchor, O.O_RDONLY | O.O_DIRECTORY | O.O_NOFOLLOW);
    } catch (err) {
      if (err?.code === "ELOOP") {
        throw new Error(`materialize refused: stateDir is a symlink (${JSON.stringify(anchor)})`);
      }
      throw new Error(`materialize refused: cannot anchor stateDir (${JSON.stringify(anchor)}; ${err?.message || err})`);
    }
    baseFd = walkDirChainFd(anchorFd, anchor, base, "stateDir/synthesis-workspace root");
    rootFd = walkDirChainFd(baseFd, base, root, "synthesis-workspace component");
    // Narrow test-only seam: run the deterministic race hook (if any) while
    // the workspace directories are pinned by held descriptors.
    if (typeof _beforeFinalOpen === "function" && process.env.NODE_ENV !== "test") {
      throw new Error("materialize refused: _beforeFinalOpen test seam requires NODE_ENV=test");
    }
    if (typeof _beforeFinalOpen === "function") {
      _beforeFinalOpen({ root });
    }
    // Post-hook re-verification: the pathname must still resolve to the
    // pinned directory. A swapped intermediate (symlink) changes what the
    // pathname resolves to, so stat/dev/ino diverge from the held fd.
    assertNoSymlinkComponents(base, root);
    let pinned = false;
    try {
      const pathStat = fs.statSync(root);
      const fdStat = fs.fstatSync(rootFd);
      pinned =
        pathStat.dev === fdStat.dev &&
        pathStat.ino === fdStat.ino &&
        (typeof pathStat.isDirectory !== "function" || pathStat.isDirectory());
    } catch {
      pinned = false;
    }
    if (!pinned) {
      throw new Error(`materialize refused: synthesis-workspace component is a symlink (${JSON.stringify(root)})`);
    }
    const written = [];
    for (const entry of entries) {
      assertSynthesisWorkspaceOnly(path.join(root, entry.file), root);
      writeFileViaDirFd(rootFd, entry.file, entry.body, root);
      written.push(entry.file);
    }
    return { root, written };
  } finally {
    closeQuiet(rootFd);
    closeQuiet(baseFd);
    closeQuiet(anchorFd);
  }
}

/**
 * Strict bounded-synthesis stdout parser (synthesis only; re-exported from
 * the shared lowest-level synthesis-parser module so acpx-text and
 * synthesize share one implementation without a circular dependency).
 * Stdout must be exactly one JSON object with exactly `{plans:[...]}` —
 * no prose, no fenced wrapping, no substring extraction. Other ACPX roles
 * keep their own framing behavior via extractAcpxFinalJson; synthesis does
 * not use it. Returns the parsed object or null.
 */
export { parseStrictBoundedSynthesisStdout };

/**
 * Default acpx invoke for synthesis (text-only): persisted prompt via
 * `--file`, ACPX text-output (`--format quiet`, never JSON-RPC) on stdout.
 * No workspace/cwd is passed: the model is a text-only proposer and never
 * executes with a filesystem cwd. Stdout must hold exactly one final JSON
 * object `{"plans": [...]}` within the bounded payload; it is parsed
 * strictly here and returned unvalidated (validation happens in
 * synthesizeWithAcpx against the eligible ledger). Same executable protocol
 * as analyze acpx (analyze.js): the `acpx` binary, Pi executor, extra args
 * from CA_IMPROVE_ACPX_ARGS, role model sol with ACPX --timeout 300s
 * (mandatory, before the agent).
 */
export function acpxSynthesisInvoke(options = {}) {
  if (options && Object.prototype.hasOwnProperty.call(options, "agent")) {
    throw new Error("CA ACPX executor is fixed to pi (caller agent is not accepted)");
  }
  if (options && (Object.prototype.hasOwnProperty.call(options, "workspace") || Object.prototype.hasOwnProperty.call(options, "workspaceRoot") || Object.prototype.hasOwnProperty.call(options, "cwd"))) {
    throw new Error("synthesis invoke is text-only: workspace/cwd must not be passed");
  }
  const { prompt, promptFile = null, model = null, timeoutSec = null, timeoutMs = null, spawnFn = null } = options;
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
  });
  if (out.status !== "ok") {
    return { status: "failed", error: out.error };
  }
  const stdout = typeof out.stdout === "string" ? out.stdout : "";
  if (stdout.length > SYNTHESIS_STDOUT_MAX_CHARS) {
    return { status: "failed", error: `acpx synthesis stdout exceeds ${SYNTHESIS_STDOUT_MAX_CHARS} chars` };
  }
  // Consume the helper-validated result directly (already strictly parsed
  // via the shared synthesis-parser at the runAcpxPromptFile boundary);
  // no loose reparse here — a non-object result is malformed.
  const parsed = out.result;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed) || !Array.isArray(parsed.plans)) {
    return { status: "failed", error: "acpx synthesis returned malformed payload (expected {plans:[...]})" };
  }
  if (parsed.candidates !== undefined || parsed.edits !== undefined) {
    return { status: "failed", error: "acpx synthesis returned forbidden candidates/edits key (expected {plans:[...]} only)" };
  }
  if (Object.keys(parsed).length !== 1 || !Object.prototype.hasOwnProperty.call(parsed, "plans")) {
    return { status: "failed", error: "acpx synthesis returned extra top-level fields (expected {plans:[...]} only)" };
  }
  if (parsed.plans.length > SYNTHESIS_MAX_PLANS) {
    return { status: "failed", error: `acpx synthesis returned ${parsed.plans.length} plans (max ${SYNTHESIS_MAX_PLANS})` };
  }
  return { status: "ok", plans: parsed.plans };
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
  return renderPrompt(
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
  if (raw.candidates !== undefined || raw.edits !== undefined) return null;
  const keys = Object.keys(raw);
  if (keys.length !== 1 || keys[0] !== "plans") return null;
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
 * Production synthesis: acpx-only text-only proposer, fail-closed.
 * The model returns a strict bounded stdout payload `{"plans": [...]}`;
 * no workspace/cwd is passed to the invocation and no ACPX filesystem
 * change is authoritative. Validated plans are materialized
 * deterministically by code under existing
 * stateDir/synthesis-workspace (no model-controlled path target); the
 * existing measure->annotate->proposal chain then observes those files.
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
    minGapEvidence = null,
    workspaceRoot = null,
  } = {},
) {
  let snapshotText = String(soulSnapshot || soulBaseline || "");
  let snapshotHash = String(soulSha256 || "");
  if (!snapshotText.trim() || !snapshotHash.trim()) {
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
  let floor = 2;
  try {
    const rawFloor = minGapEvidence ?? ledger?.minGapEvidence ?? 2;
    floor = assertMinGapEvidence(rawFloor, "minGapEvidence");
  } catch (err) {
    return {
      edits: [],
      failed: err?.message || String(err),
      note: `synthesis refused (${err?.message || err}); fail-closed with no candidate edits for this run`,
      promptFile: null,
    };
  }
  const resolvedRun = runId || `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
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
      persistNote = `synthesis prompt persistence failed (${err?.message || String(err)}); prompt not archived for this run`;
    }
  }
  let outcome;
  try {
    outcome = invoke({ prompt, promptFile, ledger, evidenceIndex, rejections });
    if (outcome && (outcome.workspace !== undefined || outcome.workspaceRoot !== undefined || outcome.cwd !== undefined)) {
      throw new Error("synthesis invoke is text-only: workspace/cwd must not be passed");
    }
  } catch (err) {
    outcome = { status: "failed", error: err?.message || String(err) };
  }
  const withPersist = (entry) => (persistNote ? { ...entry, note: entry.note ? `${entry.note}\n${persistNote}` : persistNote } : entry);
  if (!outcome || outcome.status !== "ok") {
    return withPersist({
      edits: [],
      failed: outcome?.error || "synthesis failed",
      note: `synthesis failed (${outcome?.error || "unparseable output"}); fail-closed with no candidate edits for this run`,
      promptFile,
    });
  }
  if (outcome.candidates !== undefined || outcome.edits !== undefined) {
    return withPersist({
      edits: [],
      failed: "forbidden candidates/edits key",
      note: "synthesis returned forbidden candidates/edits key (expected {plans:[...]} only); fail-closed with no candidate edits for this run",
      promptFile,
    });
  }
  const rawPayload = Array.isArray(outcome.plans) ? { plans: outcome.plans } : (outcome.result && typeof outcome.result === "object" ? outcome.result : null);
  if (!rawPayload) {
    return withPersist({
      edits: [],
      failed: "malformed synthesis payload",
      note: "synthesis returned no plans payload; fail-closed with no candidate edits for this run",
      promptFile,
    });
  }
  const check = validateProvisionalPlans(rawPayload, { ledger, floor });
  if (!check.ok) {
    return withPersist({
      edits: [],
      failed: (check.errors || []).join("; ") || "invalid synthesis plans",
      note: `synthesis plans invalid (${(check.errors || []).join("; ") || "validation failed"}); fail-closed with no candidate edits for this run`,
      promptFile,
    });
  }
  if (!check.plans.length) {
    return withPersist({
      edits: [],
      promptFile,
      note: "synthesis returned zero plans; no provisional record warranted for this run",
    });
  }
  for (const plan of check.plans) {
    const staged = validateChangePlan(plan, { ledger });
    if (!staged.ok) {
      return withPersist({
        edits: [],
        failed: (staged.errors || []).join("; "),
        note: `synthesis plans invalid (${(staged.errors || []).join("; ")}); fail-closed with no candidate edits for this run`,
        promptFile,
      });
    }
  }
  if (stateDir) {
    try {
      const { written } = materializeValidatedPlans(check.plans, { stateDir, ...(workspaceRoot ? { workspaceRoot } : {}) });
      return withPersist({
        edits: check.plans,
        promptFile,
        note: `synthesis text-only proposer validated ${check.plans.length} plan(s); deterministic code materialized ${written.length} markdown file(s) under synthesis-workspace`,
      });
    } catch (err) {
      return withPersist({
        edits: [],
        failed: err?.message || String(err),
        note: `synthesis materialization refused (${err?.message || err}); fail-closed with no candidate edits for this run`,
        promptFile,
      });
    }
  }
  return withPersist({
    edits: check.plans,
    promptFile,
    note: `synthesis text-only proposer validated ${check.plans.length} plan(s) (no stateDir materialization)`,
  });
}
