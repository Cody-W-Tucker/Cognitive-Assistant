#!/usr/bin/env python3
"""Phase-2 RED tests: required outcomes not yet implemented (TDD phase 1 ONLY).

No production source is changed here. Each test encodes a required outcome
and is expected to FAIL until the implementation lands:

1. consolidation evaluates/merges open singleton gaps before minGapEvidence
   floor and persists eligible open-gap state for future corroboration.
2. private writable synthesis workspace under stateDir is measured for actual
   created/modified/deleted markdown files with stable anchored diffs.
3. annotation consumes measured IDs and final proposal records/diffs come
   from measured workspace changes, not annotation invented artifacts.
4. synthesis cannot durably write repo/SOUL/skills/Hermes, and apply is sole
   durable writer.
5. ACPX synthesis invocation gets explicit workspace cwd without breaking
   relevant existing invocation behavior.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from core import improve

REPO_ROOT = Path(__file__).resolve().parents[1]


def _git_tracked_status() -> str:
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


class ConsolidationOpenGapsTests(unittest.TestCase):
    def test_open_singleton_gaps_merge_before_floor_and_persist(self) -> None:
        """Open singleton gaps must be evaluated/merged before the floor."""
        import sqlite3
        import time as _time

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "fakehome"
            now = int(_time.time())
            # Minimal Hermes store with one repeatable signal across sessions.
            h_db = home / ".hermes" / "state.db"
            h_db.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(h_db)
            conn.execute(
                "CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT, source TEXT,"
                " created_at INTEGER, updated_at INTEGER)"
            )
            conn.execute(
                "CREATE TABLE messages (id TEXT PRIMARY KEY, session_id TEXT,"
                " role TEXT, text BLOB)"
            )
            for i in range(2):
                conn.execute(
                    "INSERT INTO sessions VALUES (?, '/tmp/proj', 'cli', ?, ?)",
                    (f"hermes-{i}", now, now),
                )
                conn.execute(
                    "INSERT INTO messages VALUES (?, ?, 'user', 'bootstrap context once')",
                    (f"hm{i}", f"hermes-{i}"),
                )
            conn.commit()
            conn.close()
            state_dir = root / "state"
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            # First pass with floor=2 persists eligible open-gap state.
            improve.run_headless(
                home=home,
                cwd=elsewhere,
                state_dir=state_dir,
                analyzer="mock",
                min_gap_evidence=2,
            )
            open_gaps = state_dir / "open-gaps.json"
            self.assertTrue(
                open_gaps.exists(),
                "consolidation must persist eligible open-gap state for future corroboration",
            )
            persisted = json.loads(open_gaps.read_text(encoding="utf-8"))
            gaps = persisted.get("gaps", persisted if isinstance(persisted, list) else [])
            self.assertGreaterEqual(len(gaps), 1, "expected at least one persisted open gap")
            # Second pass must merge a corroborated singleton into an eligible gap.
            proposal = improve.run_headless(
                home=home,
                cwd=elsewhere,
                state_dir=state_dir,
                analyzer="mock",
                min_gap_evidence=2,
            )
            merged = [
                e
                for e in proposal.get("edits", [])
                if "open-gap" in str(e.get("rationale", "")).lower()
                or "singleton" in str(e.get("rationale", "")).lower()
                or e.get("corroboratedOpenGap")
            ]
            self.assertGreaterEqual(
                len(merged),
                1,
                "consolidation must evaluate/merge open singleton gaps before applying floor",
            )


class SynthesisWorkspaceMeasurementTests(unittest.TestCase):
    def test_private_workspace_measured_created_modified_deleted(self) -> None:
        """Workspace under stateDir must report real file changes with diffs."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            from tests.test_improve import _add_eligible_codex_sessions, _make_fixture_home

            home = _make_fixture_home(root)
            _add_eligible_codex_sessions(home)
            state_dir = root / "state"
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            proposal = improve.run_headless(
                home=home, cwd=elsewhere, state_dir=state_dir, analyzer="mock"
            )
            workspace = state_dir / "synthesis-workspace"
            self.assertTrue(
                workspace.exists() and workspace.is_dir(),
                "private writable synthesis workspace must live under stateDir",
            )
            self.assertEqual(
                workspace.resolve().relative_to(state_dir.resolve()).parts[0],
                "synthesis-workspace",
                "workspace must stay inside stateDir",
            )
            measured_path = state_dir / "measured-changes.json"
            self.assertTrue(measured_path.exists(), "measured workspace changes must be persisted")
            measured = json.loads(measured_path.read_text(encoding="utf-8"))
            pipeline_changes = measured.get("changes", measured if isinstance(measured, list) else [])
            # Production pipeline starts empty: no synthetic seed records.
            pipeline_ids = json.dumps(pipeline_changes)
            self.assertNotIn("seed-keep", pipeline_ids)
            self.assertNotIn("seed-remove", pipeline_ids)
            self.assertGreaterEqual(len(pipeline_changes), 1)
            for change in pipeline_changes:
                self.assertTrue(str(change.get("path", "")).endswith(".md"))
                self.assertIn("diff", change, "each measured change needs a stable anchored diff")
                self.assertTrue(str(change.get("diff", "")).strip(), "diff must be non-empty")
            # Test-owned lifecycle: the test creates its own baseline markdown
            # itself (never pipeline seeds) then verifies created/modified/deleted
            # via the JS helper API.
            lifecycle_state = root / "lifecycle-state"
            lifecycle_script = (
                "import fs from 'node:fs';"
                "import path from 'node:path';"
                "import { prepareExperienceWorkspace, measureExperienceWorkspace }"
                " from './improve/src/experience-workspace.js';"
                "const stateDir = process.argv[1];"
                "const ws = prepareExperienceWorkspace({ stateDir, records: ["
                "{ id: 'keep', text: 'baseline' },"
                "{ id: 'gone', text: 'bye' },"
                "]});"
                "fs.writeFileSync(path.join(ws.root, 'keep.md'), 'baseline\\namended\\n', 'utf8');"
                "fs.rmSync(path.join(ws.root, 'gone.md'), { force: true });"
                "fs.writeFileSync(path.join(ws.root, 'fresh.md'), '# fresh\\n\\nnew\\n', 'utf8');"
                "const m = measureExperienceWorkspace(ws);"
                "console.log(JSON.stringify(m));"
            )
            proc = subprocess.run(
                ["node", "--input-type=module", "-e", lifecycle_script, str(lifecycle_state)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=True,
            )
            lifecycle_changes = json.loads(proc.stdout.strip().splitlines()[-1])
            by_kind = {m.get("kind") for m in lifecycle_changes}
            for want in ("created", "modified", "deleted"):
                self.assertIn(want, by_kind, f"measured changes must include {want} markdown files")
            for change in lifecycle_changes:
                self.assertTrue(str(change.get("path", "")).endswith(".md"))
                self.assertIn("diff", change, "each measured change needs a stable anchored diff")
                self.assertTrue(str(change.get("diff", "")).strip(), "diff must be non-empty")
                self.assertIn(str(change.get("id", "")), str(change.get("diff", "")))
            # Proposal edits must reference measured change IDs.
            self.assertGreaterEqual(len(proposal.get("edits", [])), 1)
            for edit in proposal["edits"]:
                self.assertIn("measuredIds", edit, "edits must carry measured workspace IDs")
                self.assertTrue(edit["measuredIds"], "measuredIds must be non-empty")


class AnnotationMeasuredProvenanceTests(unittest.TestCase):
    def test_records_and_diffs_come_from_measured_workspace(self) -> None:
        """Final records/diffs must derive from measured changes, not invention."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            from tests.test_improve import _add_eligible_codex_sessions, _make_fixture_home

            home = _make_fixture_home(root)
            _add_eligible_codex_sessions(home)
            state_dir = root / "state"
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            proposal = improve.run_headless(
                home=home, cwd=elsewhere, state_dir=state_dir, analyzer="mock"
            )
            measured_path = state_dir / "measured-changes.json"
            self.assertTrue(measured_path.exists(), "needs measured-changes.json from workspace")
            measured = json.loads(measured_path.read_text(encoding="utf-8"))
            by_id = {m.get("id"): m for m in measured.get("changes", [])}
            self.assertTrue(by_id, "measured changes must have IDs")
            for edit in proposal.get("edits", []):
                measured_ids = edit.get("measuredIds") or []
                self.assertTrue(measured_ids, "annotation must consume measured IDs")
                for mid in measured_ids:
                    self.assertIn(mid, by_id, f"measured ID {mid!r} must resolve to workspace change")
                # Record/diff provenance: must match measured workspace content.
                provenance = edit.get("workspaceProvenance") or edit.get("measuredProvenance") or {}
                self.assertTrue(provenance, "edit must record workspace provenance, not invented artifacts")
                self.assertNotIn("invented", json.dumps(provenance).lower())
                self.assertIn("diff", edit)
                anchor_hits = [mid for mid in measured_ids if mid in str(edit.get("diff", "")) or mid in json.dumps(provenance)]
                self.assertTrue(anchor_hits, "diff/provenance must anchor to measured IDs")


class SynthesisContainmentTests(unittest.TestCase):
    def test_synthesis_cannot_write_repo_soul_skills_hermes(self) -> None:
        """Synthesis workspace is the only durable target; apply is sole writer."""
        before = _git_tracked_status()
        soul_path = REPO_ROOT / "workspaces" / "alignment" / "artifacts" / "SOUL.md"
        soul_before = soul_path.read_text(encoding="utf-8") if soul_path.exists() else None
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            from tests.test_improve import _add_eligible_codex_sessions, _make_fixture_home

            home = _make_fixture_home(root)
            _add_eligible_codex_sessions(home)
            state_dir = root / "state"
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            improve.run_headless(
                home=home, cwd=elsewhere, state_dir=state_dir, analyzer="mock"
            )
            # No repo/SOUL/skills/Hermes writes from synthesis.
            self.assertEqual(_git_tracked_status(), before, "synthesis must not durably write the repo")
            if soul_before is not None:
                self.assertEqual(soul_path.read_text(encoding="utf-8"), soul_before)
            skills_hits = list((state_dir).rglob("*"))
            for hit in skills_hits:
                self.assertNotIn("workspaces/skills", str(hit))
            # Synthesize module must declare containment (guard rails in source).
            synth_src = (REPO_ROOT / "improve" / "src" / "synthesize.js").read_text(encoding="utf-8")
            self.assertIn("synthesis-workspace", synth_src, "synthesize must target the private workspace")
            lowered = synth_src.lower()
            self.assertTrue(
                ("forbid" in lowered or "deny" in lowered or "refus" in lowered)
                and ("soul" in lowered or "repo" in lowered or "hermes" in lowered),
                "synthesize must encode durable-write refusal for repo/SOUL/skills/Hermes",
            )
            # Apply remains the sole durable writer of experience records.
            # Fail-closed runs may legitimately yield zero edits; the
            # containment assertions above still hold and apply must then
            # report an empty (not crashing) result.
            proposal = json.loads((state_dir / "proposal.json").read_text(encoding="utf-8"))
            if not proposal.get("edits"):
                result = improve.apply(
                    state_dir=state_dir,
                    experience_root=root / "exp",
                    decisions={},
                )
                self.assertEqual(result["accepted"], [])
                return
            edit = proposal["edits"][0]
            result = improve.apply(
                state_dir=state_dir,
                experience_root=root / "exp",
                decisions={edit["id"]: "accepted"},
            )
            self.assertEqual(result["accepted"], [edit["id"]])
            self.assertTrue((root / "exp" / "authored").exists())


class AcpxWorkspaceCwdTests(unittest.TestCase):
    def test_acpx_synthesis_gets_explicit_workspace_cwd(self) -> None:
        """ACPX path must receive the workspace cwd without breaking callers."""
        acpx_src = (REPO_ROOT / "improve" / "src" / "acpx-text.js").read_text(encoding="utf-8")
        synth_src = (REPO_ROOT / "improve" / "src" / "synthesize.js").read_text(encoding="utf-8")
        pipe_src = (REPO_ROOT / "improve" / "src" / "pipeline.js").read_text(encoding="utf-8")
        # Explicit workspace cwd threading through synthesis -> ACPX.
        self.assertIn("workspace", synth_src.lower(), "synthesize must accept a workspace cwd")
        self.assertIn("workspace", acpx_src.lower(), "acpx-text must accept a workspace cwd")
        self.assertIn("workspace", pipe_src.lower(), "pipeline must thread the workspace cwd")
        # Existing invocation behavior preserved: analyzer/mock entry still works.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            from tests.test_improve import _add_eligible_codex_sessions, _make_fixture_home

            home = _make_fixture_home(root)
            _add_eligible_codex_sessions(home)
            state_dir = root / "state"
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            proposal = improve.run_headless(
                home=home, cwd=elsewhere, state_dir=state_dir, analyzer="mock"
            )
            self.assertIn("edits", proposal)


if __name__ == "__main__":
    unittest.main()
