#!/usr/bin/env python3
"""Regression tests for `python -m core improve-synthesize` (resume-only).

Resume loads persisted successful evidence + ledger/open-gap state,
consolidates only if required, checks eligibility/evidence floors, then
fixed raw-stdout production synthesis -> workspace measure -> annotation ->
fresh reviewable proposal JSON. It never invokes discovery/export/ACPX
analysis; absent/incomplete/corrupt state fails closed actionable.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from core import improve

REPO_ROOT = Path(__file__).resolve().parents[1]
RESUME_SRC = REPO_ROOT / "improve" / "src" / "synthesize-resume.js"


def _git_tracked_status() -> str:
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


class ImproveSynthesizeCliTests(unittest.TestCase):
    def test_improve_synthesize_is_registered_with_state_dir(self) -> None:
        from core.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(
            ["improve-synthesize", "--state-dir", "/tmp/ca-state"]
        )
        self.assertEqual(args.command, "improve-synthesize")
        self.assertEqual(str(args.state_dir), "/tmp/ca-state")
        self.assertEqual(args.min_gap_evidence, 2)

    def test_improve_synthesize_accepts_min_gap_evidence(self) -> None:
        from core.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(
            ["improve-synthesize", "--min-gap-evidence", "3"]
        )
        self.assertEqual(args.min_gap_evidence, 3)

    def test_headless_stdout_is_single_json_document(self) -> None:
        import io
        from contextlib import redirect_stderr, redirect_stdout

        from core import cli as cli_mod
        from unittest import mock

        fake = {"id": "prop-resume-1", "edits": [], "stats": {"transcripts": 2}}
        with mock.patch(
            "core.improve.synthesize_resume", return_value=fake
        ) as resume_mock:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                rc = cli_mod.main(["improve-synthesize", "--state-dir", "/tmp/x"])
        self.assertEqual(rc, 0)
        resume_mock.assert_called_once()
        lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["id"], "prop-resume-1")


class ImproveSynthesizeStateTests(unittest.TestCase):
    def test_absent_state_fails_closed_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory) / "empty-state"
            with self.assertRaisesRegex(RuntimeError, "no successful evidence|no persisted ledger|improve-run"):
                improve.synthesize_resume(state_dir=state_dir)
            self.assertFalse((state_dir / "proposal.json").exists())

    def test_corrupt_ledger_fails_closed_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir = root / "state"
            (state_dir / "evidence").mkdir(parents=True)
            (state_dir / "evidence" / "s1.json").write_text(
                json.dumps({
                    "transcriptId": "s1",
                    "status": "ok",
                    "positive": [{"quote": "q", "effect": "e"}],
                    "gaps": [],
                }),
                encoding="utf-8",
            )
            (state_dir / "ledger.json").write_text("{not-json", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "ledger|improve-run"):
                improve.synthesize_resume(state_dir=state_dir)

    def test_incomplete_state_without_eligible_clusters_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir = root / "state"
            (state_dir / "evidence").mkdir(parents=True)
            (state_dir / "evidence" / "s1.json").write_text(
                json.dumps({
                    "transcriptId": "s1",
                    "status": "ok",
                    "positive": [{"quote": "q", "effect": "e"}],
                    "gaps": [],
                }),
                encoding="utf-8",
            )
            (state_dir / "ledger.json").write_text(
                json.dumps({"version": 1, "clusters": []}), encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "eligible|evidence"):
                improve.synthesize_resume(state_dir=state_dir)

    def test_resume_never_invokes_discovery_or_analysis(self) -> None:
        text = RESUME_SRC.read_text(encoding="utf-8")
        for forbidden in (
            "discoverTranscripts",
            "readOpencodeExport",
            "analyzeTraces",
            "mockInvoke",
            "assertAcpxAvailable",
            "collectTraces",
            "distill(",
        ):
            self.assertNotIn(
                forbidden, text,
                f"resume pipeline must never invoke {forbidden}",
            )
        for required in (
            "readEvidenceRecords",
            "synthesizeWithAcpx",
            "measureExperienceWorkspace",
            "annotateStaging",
            "buildFinalProposal",
            "consolidateLedger",
        ):
            self.assertIn(
                required, text,
                f"resume pipeline must use {required}",
            )

    def test_synthesize_boundary_calls_synthesize_subcommand(self) -> None:
        from unittest import mock

        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory) / "state"
            with mock.patch("core.improve.subprocess.run") as run_mock, mock.patch(
                "core.improve.node_bin", return_value="node"
            ):
                run_mock.return_value = mock.Mock(
                    returncode=0,
                    stdout=json.dumps({"id": "p", "edits": []}),
                    stderr="",
                )
                improve.synthesize_resume(state_dir=state_dir)
                argv = run_mock.call_args[0][0]
                self.assertIn("synthesize", argv)
                self.assertNotIn("discover", argv)
                # The full run pipeline entry is never used here.
                self.assertNotIn("run", [a for a in argv if a in ("run", "discover")])

    def test_saved_state_gets_synthesis_annotation_proposal_without_analysis(self) -> None:
        from tests.test_improve import _add_eligible_codex_sessions, _make_fixture_home

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = _make_fixture_home(root)
            _add_eligible_codex_sessions(home)
            state_dir = root / "state"
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            before = _git_tracked_status()
            # Populate persisted successful evidence + ledger via the mock run.
            improve.run_headless(
                home=home, cwd=elsewhere, state_dir=state_dir, analyzer="mock"
            )
            self.assertTrue((state_dir / "ledger.json").exists())
            self.assertGreaterEqual(len(list((state_dir / "evidence").glob("*.json"))), 1)
            # Resume via injected production doubles: the fake ACPX synthesis
            # returns stdout-only provisional plans; deterministic code
            # materializes the workspace and annotation supplies finals.
            probe = root / "resume-probe.mjs"
            resume_url = (REPO_ROOT / "improve" / "src" / "synthesize-resume.js").as_uri()
            annotate_url = (REPO_ROOT / "improve" / "src" / "annotate.js").as_uri()
            probe.write_text(
                f"import {{ runSynthesizeResume }} from '{resume_url}';\n"
                f"import {{ buildMockFinalAnnotation }} from '{annotate_url}';\n"
                "import fs from 'node:fs';\n"
                "import path from 'node:path';\n"
                "const stateDir = process.argv[2];\n"
                "const ledger = JSON.parse(fs.readFileSync(path.join(stateDir, 'ledger.json'), 'utf8'));\n"
                "const proposal = await runSynthesizeResume({\n"
                "  stateDir,\n"
                "  consolidateInvoke: () => ({ status: 'ok', result: { merges: [] } }),\n"
                "  synthesizeInvoke: (args) => {\n"
                "    const led = args?.ledger;\n"
                "    const cluster = (led?.clusters || []).find((c) => c.eligible);\n"
                "    if (!cluster) return { status: 'failed', error: 'no eligible' };\n"
                "    const sources = [...new Set((cluster.sources || []).map(String))].slice(0, 2);\n"
                "    const plan = { clusterId: cluster.id, provisionalIntent: String(cluster.proposedInstruction || 'improve').slice(0, 500), provisionalSources: sources };\n"
                "    return { status: 'ok', plans: [plan] };\n"
                "  },\n"
                "  annotateInvoke: (args) => {\n"
                "    if (args?.stage === 'annotate-preface') return { status: 'ok', ready: true };\n"
                "    const staged = args?.staged || [];\n"
                "    const idx = args?.ledger ? new Map() : new Map();\n"
                "    return { status: 'ok', annotations: staged.map((p) => buildMockFinalAnnotation(p, { ledger: args?.ledger || ledger, evidenceIndex: idx })) };\n"
                "  },\n"
                "});\n"
                "console.log(JSON.stringify(proposal));\n",
                encoding="utf-8",
            )
            # Build the evidence index the same way resume does so the mock
            # finals carry exact session-bound quotes.
            proc = subprocess.run(
                ["node", str(probe), str(state_dir)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, f"stderr: {proc.stderr}")
            proposal = json.loads(proc.stdout.strip().splitlines()[-1])
            self.assertIn("edits", proposal)
            self.assertGreaterEqual(len(proposal["edits"]), 1)
            edit = proposal["edits"][0]
            self.assertEqual(edit.get("annotation", {}).get("verdict"), "keep")
            for key in ("record", "stagedArtifact", "diff", "evidence"):
                self.assertIn(key, edit, f"resume edit missing {key}")
            # Fresh reviewable proposal: unreviewed, unconsumed, persisted.
            self.assertFalse(proposal.get("reviewed", True))
            self.assertIsNone(proposal.get("appliedAt"))
            stored = json.loads((state_dir / "proposal.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["id"], proposal["id"])
            # No tracked repo writes from the resume path.
            self.assertEqual(_git_tracked_status(), before)


if __name__ == "__main__":
    unittest.main()
