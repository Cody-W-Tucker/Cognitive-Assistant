// Resume-only synthesis: loads persisted successful evidence + folded
// ledger/open-gap state, consolidates only if required, checks
// eligibility/evidence floors, then fixed raw-stdout production synthesis
// -> workspace measure -> annotation -> fresh reviewable proposal JSON.
//
// Resume never invokes discovery/export/ACPX analysis: no transcript
// discovery, no OpenCode export, no per-trace analyze (acpx or mock).
// State absent/incomplete/corrupt fails closed with an actionable error.
// Writes land only under stateDir; apply remains the sole durable
// experience writer.

import fs from "node:fs";
import path from "node:path";

import { consolidateLedger, saveOpenGaps, loadOpenGaps, corroborateOpenGaps } from "./consolidate.js";
import { synthesizeWithAcpx, measuredIdsForPlan } from "./synthesize.js";
import { stageCandidates, buildFinalProposal } from "./stage.js";
import { measureStaging } from "./measure.js";
import {
  annotateStaging,
  applyRejectionSuppression,
  acpxAnnotatePrefaceInvoke,
  acpxAnnotateInvoke,
} from "./annotate.js";
import {
  initStateDir,
  readEvidenceRecords,
  readJson,
  writeJson,
} from "./state.js";
import {
  prepareExperienceWorkspace,
  measureExperienceWorkspace,
} from "./experience-workspace.js";
import { readSoulSnapshot } from "./soul.js";

function fail(message) {
  throw new Error(String(message));
}


function readRejections(stateDir) {
  const out = [];
  try {
    const text = fs.readFileSync(
      path.join(path.resolve(stateDir), "rejections.jsonl"),
      "utf8",
    );
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

/**
 * Run the resume-only synthesis pass over persisted state.
 *
 * Injectable invokes (no real acpx in tests): `consolidateInvoke` the one
 * judged consolidation call, `synthesizeInvoke` the production synthesis
 * call, `annotateInvoke` the preface->annotate pair. Defaults are the real
 * acpx invokes. There is no analyze/discovery invoke: resume never analyzes.
 *
 * @returns the fresh proposal object (also written to stateDir/proposal.json)
 */
export async function runSynthesizeResume({
  stateDir,
  minGapEvidence = 2,
  runId = null,
  promptsDir = null,
  soulPath = null,
  consolidateInvoke = null,
  synthesizeInvoke = null,
  annotateInvoke = null,
  progress = null,
} = {}) {
  const emit = (event, data = {}) => progress?.(event, data);
  if (!stateDir) fail("improve-synthesize: --state-dir is required");
  const resolvedState = path.resolve(String(stateDir));

  const floor = Number(minGapEvidence);
  if (!Number.isInteger(floor) || floor < 2) {
    fail(
      `improve-synthesize: --min-gap-evidence must be an integer >= 2 (got ${JSON.stringify(minGapEvidence)})`,
    );
  }

  // Read-only validation first: no state directories are created and no
  // persisted ledger/open-gap state is mutated until saved state proves
  // valid AND eligible below.

  // 1. Persisted successful evidence is the recurrence corpus.
  const evidenceRecords = readEvidenceRecords(resolvedState);
  if (!evidenceRecords.length) {
    fail(
      `improve-synthesize: no successful evidence in ${resolvedState}/evidence ` +
        `(0 ok records); run \`python -m core improve-run --headless\` first to populate state`,
    );
  }

  // 2. Persisted folded ledger (+ open-gap state loaded inside consolidate).
  const ledgerRaw = readJson(path.join(resolvedState, "ledger.json"));
  if (!ledgerRaw) {
    fail(
      `improve-synthesize: no persisted ledger at ${resolvedState}/ledger.json; ` +
        `run \`python -m core improve-run --headless\` first`,
    );
  }
  if (!Array.isArray(ledgerRaw.clusters)) {
    fail(
      `improve-synthesize: corrupt ledger at ${resolvedState}/ledger.json ` +
        `(missing clusters array); re-run \`python -m core improve-run --headless\` to rebuild state`,
    );
  }
  const workingLedger = {
    version: 1,
    minGapEvidence: floor,
    clusters: ledgerRaw.clusters.map((c) => ({
      ...c,
      eligible:
        Array.isArray(c?.sources) && c.sources.length >= floor,
    })),
  };

  const evidenceIndex = new Map(
    evidenceRecords.map((r) => [r.transcriptId, r.positive || []]),
  );
  const soulSnapshot = readSoulSnapshot(soulPath);
  const soulBaseline = soulSnapshot.text;
  const soulSha256 = soulSnapshot.sha256;
  const rejections = readRejections(resolvedState);
  const resolvedRun =
    runId ||
    `run-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;

  // 3. Consolidate only if required, without mutating persisted state yet.
  // The helper skips <2 gaps; persistence is deferred until eligibility
  // passes so invalid/ineligible saved state never touches ledger/open-gaps.
  emit("fold:resume");
  const persistedOpen = loadOpenGaps(resolvedState);
  const consolidation = consolidateLedger(workingLedger, {
    ...(consolidateInvoke ? { invoke: consolidateInvoke } : {}),
    stateDir: resolvedState,
    runId: resolvedRun,
    ...(promptsDir ? { promptsDir } : {}),
    minGapEvidence: floor,
    persist: false,
    archivePrompt: true,
  });
  const ledger = consolidation.ledger;
  const eligible = (ledger?.clusters || []).filter((c) => c?.eligible);
  emit("fold:done", {
    clusters: (ledger?.clusters || []).length,
    eligible: eligible.length,
  });

  // 4. Eligibility/evidence floors fail closed with an actionable message.
  // No directories created, no ledger/open-gap writes on this path.
  if (!eligible.length) {
    fail(
      `improve-synthesize: no eligible gap clusters in ${resolvedState}/ledger.json ` +
        `(${(ledger?.clusters || []).length} cluster(s), floor ${floor}); ` +
        `run \`python -m core improve-run --headless\` to gather more evidence`,
    );
  }
  for (const cluster of eligible) {
    const distinct = [...new Set((cluster?.sources || []).map(String))];
    if (distinct.length < floor) {
      fail(
        `improve-synthesize: cluster ${JSON.stringify(cluster?.id)} has only ` +
          `${distinct.length} distinct session(s) (floor ${floor}); ` +
          `run \`python -m core improve-run --headless\` to gather more evidence`,
      );
    }
  }

  // Saved state is valid + eligible: now (and only now) create state dirs
  // and persist the folded ledger + open-gap snapshot.
  initStateDir(resolvedState);
  writeJson(path.join(resolvedState, "ledger.json"), ledger);
  try {
    const gaps = (ledger?.clusters || []).map((c) => ({
      id: String(c.id),
      proposedInstruction: c.proposedInstruction,
      representativeQuote: c.representativeQuote,
      mistake: c.mistake,
      sources: [...(c.sources || []).map(String)],
      count: (c.sources || []).length,
      eligible: Boolean(c.eligible),
    }));
    let snapshot = null;
    try {
      snapshot = corroborateOpenGaps(workingLedger, persistedOpen, { minGapEvidence: floor }).snapshot;
    } catch {
      snapshot = null;
    }
    const merged = new Map((snapshot || persistedOpen?.gaps || []).map((g) => [String(g.id || g.key), { ...g }]));
    for (const g of gaps) merged.set(String(g.id), g);
    saveOpenGaps(resolvedState, [...merged.values()]);
  } catch {
    // persistence best-effort; ledger result still flows downstream
  }

  // 5. Private run-isolated synthesis workspace inside stateDir. Each run
  // gets a clean synthesis-workspace/<runId> root so stale artifacts from
  // prior runs can never be measured/annotated/proposed. Synthesis
  // executes only there; apply remains the only durable experience writer.
  let workspace = null;
  try {
    workspace = prepareExperienceWorkspace({ stateDir: resolvedState, records: [], runId: resolvedRun });
  } catch (err) {
    fail(`improve-synthesize: cannot prepare synthesis workspace (${err?.message || err})`);
  }
  const workspaceCwd = workspace?.root || null;
  const runNote = consolidation.note || "";

  // 6. Fixed raw-stdout production synthesis (never mock, never analysis).
  emit("synthesize:start");
  const out = synthesizeWithAcpx(ledger, {
    evidenceIndex,
    soulBaseline,
    soulSnapshot: soulSnapshot.text,
    soulSha256,
    rejections,
    ...(synthesizeInvoke ? { invoke: synthesizeInvoke } : {}),
    stateDir: resolvedState,
    runId: resolvedRun,
    ...(promptsDir ? { promptsDir } : {}),
    transcriptCount: evidenceRecords.length,
    harnessSummary: "resume",
    runNote,
    workspace: workspaceCwd,
    workspaceRoot: workspaceCwd,
    cwd: workspaceCwd,
  });
  let edits = out.edits || [];
  let synthesisNote = out.note || "";
  let synthesisFailed = Boolean(out.failed);

  // 7. Workspace measure independently drives annotation (same gate as run).
  let measuredChanges = [];
  try {
    if (workspace) {
      measuredChanges = measureExperienceWorkspace(workspace);
      try {
        fs.mkdirSync(resolvedState, { recursive: true });
        fs.writeFileSync(
          path.join(resolvedState, "measured-changes.json"),
          `${JSON.stringify({ version: 1, runId: String(resolvedRun), workspace: `synthesis-workspace/${String(resolvedRun)}`, changes: measuredChanges }, null, 2)}\n`,
          "utf8",
        );
      } catch {}
    }
  } catch {
    measuredChanges = [];
  }
  const incoming = [...(edits || [])];
  if (!measuredChanges.length) {
    if (incoming.length) {
      synthesisNote = [
        synthesisNote,
        "no workspace file changes measured; JSON-only plans discarded fail-closed with zero candidate edits",
      ]
        .filter(Boolean)
        .join("\n");
    }
    edits = [];
    synthesisFailed = true;
  } else {
    const bound = incoming.filter(
      (plan) => measuredIdsForPlan(plan?.id, measuredChanges).length > 0,
    );
    if (bound.length) {
      if (bound.length < incoming.length) {
        synthesisNote = [
          synthesisNote,
          "JSON-only plans without measured workspace changes discarded; measured IDs drive annotation",
        ]
          .filter(Boolean)
          .join("\n");
      }
      edits = bound;
    } else {
      const eligibleById = new Map(
        (ledger?.clusters || []).filter((c) => c?.eligible).map((c) => [String(c.id), c]),
      );
      const derived = [];
      for (const m of measuredChanges) {
        const rid = String(m?.recordId || m?.file || m?.path || "").replace(/\.md$/, "");
        if (!rid) continue;
        const mClusterId = String(m?.clusterId || "").trim();
        const mSourcesRaw = m?.provisionalSources || m?.eligibleSources || m?.sources || null;
        if (!mClusterId || !Array.isArray(mSourcesRaw)) continue;
        const distinct = [...new Set(mSourcesRaw.map((s) => String(s)).filter(Boolean))];
        if (distinct.length < floor) continue;
        const cluster = eligibleById.get(mClusterId) || null;
        if (!cluster) continue;
        const clusterSources = new Set((cluster?.sources || []).map(String));
        if (!distinct.every((s) => clusterSources.has(String(s)))) continue;
        let intent = "";
        try {
          const body = String(m?.text || "");
          const head = body.split("\n").find((l) => l.startsWith("# "));
          if (head) intent = head.replace(/^#+\s*/, "").trim().slice(0, 200);
        } catch {}
        if (!intent) intent = String(cluster?.proposedInstruction || rid).trim();
        if (!intent) continue;
        derived.push({
          id: rid,
          kind: "add",
          clusterId: String(cluster.id),
          provisionalIntent: intent,
          provisionalSources: distinct,
          provisionalCount: distinct.length,
          ...(cluster?.corroboratedOpenGap ? { corroboratedOpenGap: true } : {}),
        });
      }
      if (derived.length) {
        edits = derived;
        synthesisFailed = false;
        synthesisNote = [
          synthesisNote,
          `measured workspace changes independently drive ${derived.length} candidate(s) by measured IDs; JSON plan output never creates durable candidates`,
        ]
          .filter(Boolean)
          .join("\n");
      } else {
        if (incoming.length) {
          synthesisNote = [
            synthesisNote,
            "no plans bound to measured workspace changes; fail-closed with zero candidate edits",
          ]
            .filter(Boolean)
            .join("\n");
        }
        edits = [];
        synthesisFailed = true;
      }
    }
  }

  // 8. Stage -> measure -> fresh preface->annotate -> fresh proposal.
  const staged = stageCandidates(edits, { stateDir: resolvedState, runId: resolvedRun });
  measureStaging(staged, {
    stateDir: resolvedState,
    runId: resolvedRun,
    ledger,
    evidenceIndex,
  });
  const defaultAnnotate = (args) => {
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
    stateDir: resolvedState,
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
      finalEdits = buildFinalProposal(kept, {
        stateDir: resolvedState,
        ledger,
        evidenceIndex,
        soulBaseline,
        measuredChanges,
        workspace: workspaceCwd,
      });
    } catch (err) {
      annotateFailed = true;
      annotateNote = `final proposal blocked (${err?.message || err}); unannotated staging cannot reach apply`;
      finalEdits = [];
    }
  }
  if (finalEdits.length) {
    const corroborated = new Set(
      (ledger?.clusters || []).filter((c) => c.corroboratedOpenGap).map((c) => String(c.id)),
    );
    if (corroborated.size) {
      for (const e of finalEdits) {
        const cid = String(e.clusterId || e.record?.clusterId || "");
        if (corroborated.has(cid) && !e.corroboratedOpenGap) {
          e.corroboratedOpenGap = true;
          if (!/open-gap|singleton/i.test(String(e.rationale || ""))) {
            e.rationale = `open-gap corroborated singleton: ${e.rationale || e.title || ""}`;
          }
          if (e.annotation && !/open-gap|singleton/i.test(String(e.annotation.reason || ""))) {
            e.annotation.reason = e.rationale;
          }
        }
      }
    }
  }

  const notes = [runNote, synthesisNote].filter(Boolean);
  if (annotateNote) notes.push(annotateNote);
  const proposal = {
    version: 1,
    id: `prop-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`,
    createdAt: new Date().toISOString(),
    reviewed: false,
    appliedAt: null,
    scope: "global",
    resume: true,
    minGapEvidence: floor,
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
      analyzer: "acpx",
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
      transcripts: evidenceRecords.length,
      analyzed: evidenceRecords.length,
      skipped: 0,
      failed: 0,
      clusters: (ledger?.clusters || []).length,
      eligible: eligible.length,
    },
  };
  writeJson(path.join(resolvedState, "proposal.json"), proposal);
  emit("synthesize:done", {
    staged: staged.length,
    annotated: annOut.annotated ? annOut.annotated.length : 0,
    edits: finalEdits.length,
    note: annotateNote || synthesisNote,
  });
  return proposal;
}
