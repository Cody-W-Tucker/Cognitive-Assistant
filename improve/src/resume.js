// `ca-improve synthesize`: propose again from the evidence and ledger a
// previous run saved, without discovering or analyzing any session. Saved
// state is validated before anything is written; missing, corrupt, or
// ineligible state fails with a message naming the fix.

import fs from "node:fs";
import path from "node:path";

import { consolidateLedger, saveOpenGaps } from "./consolidate.js";
import { assertModelConfigured, modelInvoke } from "./model.js";
import { propose } from "./propose.js";
import { readSoulSnapshot } from "./soul.js";
import { assertMinGapEvidence, initStateDir, readEvidenceRecords, readJson, timestampId, writeJson } from "./state.js";

const RERUN = "run `python -m core improve-run --headless`";

export async function runSynthesizeResume({ stateDir, soulPath, minGapEvidence = 2, invoke = null, progress = null }) {
  const emit = (event, data = {}) => progress?.(event, data);
  if (!stateDir) throw new Error("improve-synthesize: --state-dir is required");
  const floor = assertMinGapEvidence(minGapEvidence, "improve-synthesize: --min-gap-evidence");
  const resolvedState = path.resolve(stateDir);

  const evidenceRecords = readEvidenceRecords(resolvedState);
  if (!evidenceRecords.length) {
    throw new Error(`improve-synthesize: no successful evidence in ${resolvedState}/evidence; ${RERUN} first to populate state`);
  }
  const ledgerFile = path.join(resolvedState, "ledger.json");
  if (!fs.existsSync(ledgerFile)) throw new Error(`improve-synthesize: no persisted ledger at ${ledgerFile}; ${RERUN} first`);
  const saved = readJson(ledgerFile);
  if (!Array.isArray(saved?.clusters)) {
    throw new Error(`improve-synthesize: corrupt ledger at ${ledgerFile} (no clusters array); ${RERUN} to rebuild state`);
  }
  const soul = readSoulSnapshot(soulPath);
  const runId = timestampId("run");
  if (!invoke) {
    assertModelConfigured();
    invoke = modelInvoke(resolvedState);
  }

  emit("fold:start");
  const consolidation = await consolidateLedger(
    {
      version: 1,
      minGapEvidence: floor,
      clusters: saved.clusters.map((c) => ({ ...c, eligible: new Set((c?.sources || []).map(String)).size >= floor })),
    },
    { invoke, stateDir: resolvedState, runId, minGapEvidence: floor },
  );
  const { ledger } = consolidation;
  const eligible = ledger.clusters.filter((c) => c.eligible);
  emit("fold:done", { clusters: ledger.clusters.length, eligible: eligible.length });
  if (!eligible.length) {
    throw new Error(
      `improve-synthesize: no eligible gap clusters in ${ledgerFile} (${ledger.clusters.length} cluster(s), floor ${floor}); ${RERUN} to gather more evidence`,
    );
  }

  initStateDir(resolvedState);
  writeJson(ledgerFile, ledger);
  saveOpenGaps(resolvedState, consolidation.openGaps);
  return propose({
    stateDir: resolvedState,
    runId,
    ledger,
    evidenceRecords,
    soul,
    floor,
    invoke,
    analyzer: "model",
    consolidation,
    harnessSummary: "resume",
    emit,
    extra: { resume: true },
    stats: { transcripts: evidenceRecords.length, analyzed: evidenceRecords.length, skipped: 0, failed: 0 },
  });
}
