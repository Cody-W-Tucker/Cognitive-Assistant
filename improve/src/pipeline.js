// Full headless pipeline: discover -> collect -> distill -> analyze
// (acpx-only, injectable) -> fold (deterministic) -> consolidate (one
// judged acpx call, fail-soft to exact observation identity) -> synthesize (mock deterministic
// or production acpx, fail-closed) -> proposal. Writes private state only;
// never touches the CA repo, tracked files, or live Hermes.

import fs from "node:fs";
import path from "node:path";

import { discoverTranscripts } from "./discovery.js";
import { distill, recordToEvents } from "./distill.js";
import { analyzeTracesAsync, mockInvoke, assertAcpxAvailable } from "./analyze.js";
import { foldEvidence } from "./fold.js";
import { consolidateLedger } from "./consolidate.js";
import { synthesizeCandidates, synthesizeWithAcpx, measuredIdsForPlan } from "./synthesize.js";
import { stageCandidates, buildFinalProposal } from "./stage.js";
import { measureStaging } from "./measure.js";
import { annotateStaging, applyRejectionSuppression, buildMockFinalAnnotation, acpxAnnotatePrefaceInvoke, acpxAnnotateInvoke } from "./annotate.js";
import { checkpointKey, initStateDir, readEvidenceRecords, readSessionCheckpoint, writeJson, assertMinGapEvidence } from "./state.js";
import { readSoulSnapshot } from "./soul.js";
import { prepareExperienceWorkspace, measureExperienceWorkspace } from "./experience-workspace.js";
import { readOpencodeExportAsync } from "./opencode-export.js";

function readJsonlEvents(file) {
  const events = [];
  let text;
  try {
    text = fs.readFileSync(file, "utf8");
  } catch {
    return events;
  }
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      events.push(...recordToEvents(JSON.parse(trimmed)));
    } catch {
      // skip unparseable lines; the raw file stays referenced in the trace
    }
  }
  return events;
}

async function readSqliteMessages(dbPath, sessionId) {
  let sqlite;
  try {
    sqlite = await import("node:sqlite");
  } catch {
    return [];
  }
  const events = [];
  let db;
  try {
    db = new sqlite.DatabaseSync(dbPath, { readOnly: true });
    const tables = new Set(
      db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all().map((r) => r.name),
    );
    let rows = [];
    if (tables.has("session_message")) {
      rows = db
        .prepare("SELECT data FROM session_message WHERE session_id = ? ORDER BY seq ASC")
        .all(sessionId)
        .map((r) => r.data);
    } else if (tables.has("messages")) {
      let mcols = new Set();
      try {
        mcols = new Set(
          db.prepare("SELECT name FROM pragma_table_info('messages')").all().map((r) => r.name),
        );
      } catch {
        mcols = new Set();
      }
      const hasSessionId = mcols.has("session_id");
      const textCol = mcols.has("text") ? "text" : mcols.has("content") ? "content" : null;
      const roleCol = mcols.has("role") ? "role" : null;
      if (hasSessionId && textCol) {
        const roleSelect = roleCol ? "role" : "NULL AS role";
        rows = db
          .prepare(`SELECT ${roleSelect}, ${textCol} FROM messages WHERE session_id = ? ORDER BY rowid ASC`)
          .all(sessionId)
          .map((r) => ({ role: r.role, text: Buffer.isBuffer(r[textCol]) ? r[textCol].toString("utf8") : r[textCol] }));
      }
    }
    for (const row of rows) {
      if (typeof row === "string") {
        try {
          events.push(...recordToEvents(JSON.parse(row)));
        } catch {
          events.push({ kind: "message", role: "user", text: row });
        }
      } else {
        events.push(...recordToEvents(row));
      }
    }
  } catch {
    // unreadable here mirrors discovery fail-soft: trace carries no events
  } finally {
    try {
      db?.close();
    } catch {
      // ignore
    }
  }
  return events;
}

async function collectTraces(transcripts, jobs = 4) {
  const traces = new Array(transcripts.length);
  let next = 0;
  async function collectOne(transcript) {
    let events = [];
    if (transcript.path) events = readJsonlEvents(transcript.path);
    else if (transcript.db) events = await readSqliteMessages(transcript.db, transcript.id);
    // OpenCode's current legacy SQLite store can retain only session headers.
    // Its supported export command is the authoritative read path in that
    // layout; only invoke it when SQLite produced no usable events.
    if (transcript.harness === "opencode" && events.length === 0) {
      const recovered = await readOpencodeExportAsync(transcript.id);
      events = recovered.events;
    }
    return {
      transcriptId: transcript.id,
      harness: transcript.harness,
      activity: {
        userTurns: events.filter((event) => event?.kind === "message" && event.role === "user").length,
        assistantTurns: events.filter((event) => event?.kind === "message" && event.role === "assistant").length,
        toolCalls: events.filter((event) => event?.kind === "tool").length,
      },
      distilled: distill(events, transcript),
    };
  }
  async function worker() {
    while (true) {
      const index = next++;
      if (index >= transcripts.length) return;
      traces[index] = await collectOne(transcripts[index]);
    }
  }
  await Promise.all(Array.from({ length: Math.max(1, Math.min(Number(jobs) || 4, transcripts.length)) }, worker));
  return traces;
}

function readRejections(stateDir) {
  const out = [];
  try {
    const text = fs.readFileSync(path.join(path.resolve(stateDir), "rejections.jsonl"), "utf8");
    for (const line of text.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        out.push(JSON.parse(trimmed));
      } catch {
        // skip malformed rejection lines; the raw file stays for audit
      }
    }
  } catch {
    // no rejections yet
  }
  return out;
}

function harnessSummaryOf(transcripts) {
  const counts = new Map();
  for (const t of transcripts || []) counts.set(t.harness, (counts.get(t.harness) || 0) + 1);
  const parts = [...counts.entries()].map(([h, n]) => `${h} ${n}`);
  return parts.join(", ") || "none";
}


/**
 * Run the headless pass. All writes land under `stateDir`.
 *
 * Injectable model invokes (no real acpx in tests): `analyzeInvoke`
 * overrides the per-trace analyzer, `consolidateInvoke` the one judged
 * consolidation call, `synthesizeInvoke` the production synthesis call.
 * Each defaults to the analyzer selection (`mock` double vs real acpx).
 *
 * @returns the proposal object (also written to stateDir/proposal.json)
 */
export async function runPipeline({
  home,
  stateDir,
  since = "30d",
  harnesses = null,
  analyzer = "acpx",
  soulPath = null,
  posturePath = null,
  experienceRoot = null,
  promptsDir = null,
  runId = null,
  minGapEvidence = 2,
  analyzeInvoke = null,
  consolidateInvoke = null,
  synthesizeInvoke = null,
  annotateInvoke = null,
  progress = null,
  jobs = Number(process.env.CA_IMPROVE_JOBS || 4),
} = {}) {
  const emit = (event, data = {}) => progress?.(event, data);
  const floor = assertMinGapEvidence(minGapEvidence, "minGapEvidence");
  initStateDir(stateDir);
  const resolvedRun = runId || `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
  emit("discover:start", { harnesses: harnesses || ["hermes", "pi", "claude", "codex", "opencode"] });
  const discovery = discoverTranscripts({ home, stateDir, since, harnesses });
  // Current OpenCode legacy stores expose only session headers through SQLite.
  // Exporting every header serially is minutes of opaque work, so process a
  // bounded newest-first batch. Successful and trivial sessions checkpoint;
  // the next run advances to the remaining sessions.
  const maxOpencodeExports = Number(process.env.CA_IMPROVE_MAX_OPENCODE_EXPORTS || 50);
  const opencode = discovery.transcripts
    .filter((transcript) => transcript.harness === "opencode")
    .sort((a, b) => (b.mtimeMs || 0) - (a.mtimeMs || 0));
  if (Number.isInteger(maxOpencodeExports) && maxOpencodeExports > 0 && opencode.length > maxOpencodeExports) {
    const allowed = new Set(opencode.slice(0, maxOpencodeExports).map((transcript) => transcript.id));
    discovery.transcripts = discovery.transcripts.filter((transcript) => transcript.harness !== "opencode" || allowed.has(transcript.id));
  }
  emit("discover:done", { transcripts: discovery.transcripts.length, perHarness: discovery.perHarness });
  const pending = discovery.transcripts.length;
  emit("analyze:start", { total: pending, pending, cached: 0, analyzer });
  const traces = await collectTraces(discovery.transcripts, jobs);
  if (analyzer !== "mock" && !analyzeInvoke) {
    // Real production run path only: fail fast before trace analysis when
    // the acpx binary selected via CA_IMPROVE_ACPX_BIN/BACKPASS_ACPX_BIN is
    // unavailable. Mock runs and injected invokes bypass real acpx entirely.
    assertAcpxAvailable();
  }
  const invoke = analyzeInvoke || (analyzer === "mock" ? mockInvoke : undefined);
  let completed = 0;
  let successful = 0;
  let failed = 0;
  let skipped = 0;
  const records = await analyzeTracesAsync(traces, {
    ...(invoke ? { invoke } : {}),
    stateDir,
    runId: resolvedRun,
    soulPath,
    posturePath,
    experienceRoot,
    promptsDir,
    jobs,
    onRecord: (record) => {
      writeJson(path.join(stateDir, "evidence", `${record.transcriptId}.json`), record);
      completed += 1;
      if (record.status === "ok") successful += 1;
      else if (record.status === "skipped") skipped += 1;
      else failed += 1;
      emit("analyze:tick", { done: completed, ok: successful, failed, skipped });
    },
  });
  emit("analyze:done", {
    done: completed,
    ok: successful,
    failed,
    skipped,
    cached: Math.max(discovery.transcripts.length - records.length, 0),
  });
  const recurrenceRecords = readEvidenceRecords(stateDir);
  emit("fold:start");
  const folded = foldEvidence(recurrenceRecords, { minGapEvidence });
  // Consolidation is acpx-only when >=2 eligible gaps exist; the mock
  // analyzer keeps deterministic exact observation identity with a visible note.
  const consolidation = consolidateLedger(folded, {
    ...(consolidateInvoke ? { invoke: consolidateInvoke } : analyzer === "mock" ? { analyzer: "mock" } : {}),
    stateDir,
    runId: resolvedRun,
    promptsDir,
    minGapEvidence,
  });
  // The open-gap ledger is maintained only from actual analyzer gap
  // observations: consolidateLedger persists folded clusters (including
  // open/singleton observations) to open-gaps.json and corroborates them
  // with distinct-session unions before the floor. No synthetic gaps are
  // ever derived from distilled traces here.
  const ledger = consolidation.ledger;
  emit("fold:done", {
    clusters: ledger.clusters.length,
    eligible: ledger.clusters.filter((cluster) => cluster.eligible).length,
  });
  writeJson(path.join(stateDir, "ledger.json"), ledger);
  const evidenceIndex = new Map(recurrenceRecords.map((r) => [r.transcriptId, r.positive || []]));
  const soulSnapshot = readSoulSnapshot(soulPath);
  const soulBaseline = soulSnapshot.text;
  const soulSha256 = soulSnapshot.sha256;
  const rejections = readRejections(stateDir);
  const harnessSummary = harnessSummaryOf(discovery.transcripts);
  const runNote = consolidation.note || "";
  // Private writable synthesis workspace inside stateDir. ACPX synthesis is
  // text-only (no workspace cwd); validated narrow plans are materialized
  // deterministically by code under synthesis-workspace. Apply remains the
  // only durable experience writer. No synthetic seed records are ever
  // created here: the workspace starts empty and only materialized
  // validated plans are measured.
  let workspace = null;
  try {
    workspace = prepareExperienceWorkspace({
      stateDir,
      records: [],
    });
  } catch {
    workspace = null;
  }
  const workspaceCwd = workspace?.root || null;
  let edits;
  let synthesisNote = "";
  let synthesisFailed = false;
  if (analyzer === "mock") {
    // Deterministic reviewable path: narrow change plans only, no model
    // traffic, no real acpx calls. The mock synthesis itself authored the
    // private workspace BEFORE this point (see synthesizeCandidates /
    // applyMockSynthesisWorkspace); the pipeline never fabricates
    // plan-derived edits. Final records come only from the mock
    // annotate step below (same plan->stage/measure->preface->annotate path).
    edits = synthesizeCandidates(ledger, { evidenceIndex, soulBaseline, soulSnapshot: soulSnapshot.text, soulSha256, workspace: workspaceCwd, workspaceRoot: workspaceCwd, cwd: workspaceCwd, stateDir });
  } else {
    // Production acpx-only synthesis: strict validation, fail-closed.
    const out = synthesizeWithAcpx(ledger, {
      evidenceIndex,
      soulBaseline,
      soulSnapshot: soulSnapshot.text,
      soulSha256,
      rejections,
      ...(synthesizeInvoke ? { invoke: synthesizeInvoke } : {}),
      stateDir,
      runId: resolvedRun,
      promptsDir,
      transcriptCount: discovery.transcripts.length,
      harnessSummary,
      runNote,
      minGapEvidence: floor,
      workspaceRoot: workspaceCwd,
    });
    edits = out.edits;
    synthesisFailed = Boolean(out.failed);
    synthesisNote = out.note || "";
  }
  // Synthesis output is the ONLY author of workspace changes: the mock
  // synthesis authored the workspace before measurement (above) and
  // production deterministic code materialized validated text-only plans
  // under synthesis-workspace (no ACPX filesystem write). Here the pipeline
  // only measures the
  // actual resulting created/modified/deleted files with stable anchored
  // diffs (never synthetic plan deltas). Production never derives durable
  // records/diffs from a JSON plan: plans without corresponding measured
  // workspace changes fail closed to zero candidate edits below.
  let measuredChanges = [];
  try {
    if (workspace) {
      measuredChanges = measureExperienceWorkspace(workspace);
      try {
        fs.mkdirSync(path.resolve(stateDir), { recursive: true });
        fs.writeFileSync(path.join(path.resolve(stateDir), "measured-changes.json"), `${JSON.stringify({ version: 1, runId: String(resolvedRun), workspace: "synthesis-workspace", changes: measuredChanges }, null, 2)}\n`, "utf8");
      } catch {}
    }
  } catch {
    measuredChanges = [];
  }
  if (analyzer !== "mock") {
    // Production gate (Option 2 text-only): deterministic code already
    // materialized only validated plans under synthesis-workspace.
    // Measured files independently confirm them by measured IDs. No
    // synthetic derivation: unbound plans fail closed to zero edits.
    const incoming = [...(edits || [])];
    if (!measuredChanges.length) {
      if (incoming.length) {
        synthesisNote = [synthesisNote, "no workspace file changes measured; validated plans discarded fail-closed with zero candidate edits"].filter(Boolean).join("\n");
      }
      edits = [];
      synthesisFailed = true;
    } else {
      const bound = incoming.filter((plan) => measuredIdsForPlan(plan?.id, measuredChanges).length > 0);
      if (bound.length < incoming.length) {
        synthesisNote = [synthesisNote, "plans without measured workspace changes discarded; measured IDs drive annotation"].filter(Boolean).join("\n");
      }
      if (!bound.length) synthesisFailed = true;
      edits = bound;
    }
  }
  const notes = [runNote, synthesisNote].filter(Boolean);
  emit("synthesize:start");
  // Staged change plan: synth output is never final. Stage narrow plans
  // deterministically, measure with stable change ids/deltas + provisional
  // intent/eligible context, annotate via fresh preface->annotate
  // invocations (sole full-record origin), suppress rejections on
  // annotated finals, then build the terminal proposal from annotated
  // finals only. Fail closed with no edits.
  const staged = stageCandidates(edits, { stateDir, runId: resolvedRun });
  measureStaging(staged, { stateDir, runId: resolvedRun, ledger, evidenceIndex });
  // Mock follows the same plan->private stage/measure->preface->
  // annotate-final path and may deterministically construct the equivalent
  // final annotation (mock only). Production invents nothing: without an
  // annotate invoke that supplies complete final records, annotate fails
  // closed with no edits.
  const mockFinalFor = (plans) =>
    (plans || staged).map((c) => buildMockFinalAnnotation(c, { ledger, evidenceIndex, soulBaseline, soulSnapshot: soulSnapshot.text, soulSha256, measuredChanges }));
  const defaultAnnotate = (args) => {
    if (analyzer === "mock") {
      return { status: "ok", annotations: mockFinalFor(args?.staged || staged) };
    }
    // Production: real ACPX text-output calls (fail-closed, invents nothing).
    if (args?.stage === "annotate-preface") {
      return acpxAnnotatePrefaceInvoke({ prompt: args.prompt, promptFile: args.promptFile });
    }
    if (args?.stage === "annotate") {
      return acpxAnnotateInvoke({ prompt: args.prompt, promptFile: args.promptFile });
    }
    return { status: "failed", error: "annotate invoke unavailable; production invents nothing" };
  };
  const annInvoke = annotateInvoke || defaultAnnotate;
  const annOut = await annotateStaging(staged, {
    stateDir,
    invoke: (args) => annInvoke({ ...args, staged: args?.staged || staged }),
    runId: resolvedRun,
    ledger,
    evidenceIndex,
    soulBaseline,
    soulSnapshot: soulSnapshot.text,
    soulSha256,
    measuredChanges,
    workspace: workspaceCwd,
    ...(promptsDir ? { promptsDir } : {}),
  });
  let finalEdits = [];
  let annotateNote = "";
  let annotateFailed = false;
  if (annOut.failed) {
    annotateFailed = true;
    annotateNote = `annotate failed (${annOut.error || "invalid"}); fail-closed with no candidate edits for this run`;
  } else {
    const kept = applyRejectionSuppression(annOut.annotated || [], rejections, { evidenceIndex });
    try {
      finalEdits = buildFinalProposal(kept, { stateDir, ledger, evidenceIndex, soulBaseline, measuredChanges, workspace: workspaceCwd });
    } catch (err) {
      annotateFailed = true;
      annotateNote = `final proposal blocked (${err?.message || err}); unannotated staging cannot reach apply`;
      finalEdits = [];
    }
  }
  try {
    // Per-edit binding only: each final edit keeps the specific measured
    // change(s) its own synthesis authored (matched by plan id). Never
    // blanket-attach all measured IDs. Stage/annotate already bind
    // specifically; here only ensure the anchor line reflects the edit's
    // own measuredIds and propagate open-gap corroboration.
    if (finalEdits.length) {
      // Propagate open-gap corroboration from plans/ledger onto finals.
      const corroborated = new Set((ledger?.clusters || []).filter((c) => c.corroboratedOpenGap).map((c) => String(c.id)));
      if (corroborated.size) {
        for (const e of finalEdits) {
          const cid = String(e.clusterId || e.record?.clusterId || "");
          if (corroborated.has(cid) && !e.corroboratedOpenGap) {
            e.corroboratedOpenGap = true;
            if (!/open-gap|singleton/i.test(String(e.rationale || ""))) e.rationale = `open-gap corroborated singleton: ${e.rationale || e.title || ""}`;
            if (e.annotation && !/open-gap|singleton/i.test(String(e.annotation.reason || ""))) e.annotation.reason = e.rationale;
          }
        }
      }
    }
    // Pipeline never authors final proposal artifacts: with no annotated
    // finals the proposal stays empty (fail-closed). Upstream mock
    // synthesis/annotation remains the sole legitimate author of
    // annotation-derived final records.
  } catch {}
  if (annotateNote) notes.push(annotateNote);
  const proposal = {
    version: 1,
    id: `prop-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`,
    createdAt: new Date().toISOString(),
    reviewed: false,
    appliedAt: null,
    scope: "global",
    minGapEvidence,
    soul: { path: soulSnapshot.path, sha256: soulSnapshot.sha256, chars: soulSnapshot.chars },
    edits: finalEdits,
    notes,
    consolidation: {
      skipped: Boolean(consolidation.skipped),
      failed: Boolean(consolidation.failed),
      merged: consolidation.merged || 0,
      note: consolidation.note || "",
    },
    synthesis: {
      analyzer,
      failed: synthesisFailed,
      note: synthesisNote,
    },
    staging: {
      staged: staged.length,
      annotated: annOut.annotated ? annOut.annotated.length : 0,
      failed: annotateFailed,
      note: annotateNote,
    },
    stats: {
      transcripts: discovery.transcripts.length,
      analyzed: records.filter((r) => r.status === "ok").length,
      skipped: records.filter((r) => r.status === "skipped").length,
      failed: records.filter((r) => r.status === "failed").length,
      clusters: ledger.clusters.length,
      eligible: ledger.clusters.filter((c) => c.eligible).length,
    },
  };
  writeJson(path.join(stateDir, "proposal.json"), proposal);
  emit("synthesize:done", {
    staged: staged.length,
    annotated: annOut.annotated ? annOut.annotated.length : 0,
    edits: finalEdits.length,
    note: annotateNote || synthesisNote,
  });
  const previousCheckpoint = readSessionCheckpoint(stateDir);
  const processed = { ...previousCheckpoint.processed };
  const processedIds = new Set(records.filter((record) => record.status === "ok" || record.status === "skipped").map((record) => record.transcriptId));
  for (const transcript of discovery.transcripts) {
    if (processedIds.has(transcript.id)) processed[checkpointKey(transcript)] = transcript.mtimeMs ?? null;
  }
  writeJson(path.join(stateDir, "cursor.json"), {
    version: 2,
    lastRun: proposal.createdAt,
    lastProposalId: proposal.id,
    analyzedIds: Object.keys(processed).sort(),
    processed,
    perHarness: discovery.perHarness,
  });
  return proposal;
}
