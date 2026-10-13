#!/usr/bin/env python3
"""Required active-SOUL contextualization for the CA improvement pass.

Canonical default: repo-root/workspaces/alignment/artifacts/SOUL.md,
independent of CWD; --soul-path explicitly overrides. Snapshot is read-only;
missing/unreadable/empty fails closed before synthesis/annotation/proposal.
Bounded snapshot text + stable sha256 flow to synthesis/annotation contexts;
proposal/state carry provenance (path/hash/chars); SOUL is never written.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core import improve

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SOUL = REPO_ROOT / "workspaces" / "alignment" / "artifacts" / "SOUL.md"


class SoulDefaultTests(unittest.TestCase):
    def test_canonical_default_resolves_independent_of_cwd(self) -> None:
        soul = improve.default_soul_path()
        self.assertEqual(soul, CANONICAL_SOUL)
        with tempfile.TemporaryDirectory() as directory:
            elsewhere = Path(directory)
            env = dict(os.environ)
            env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
            proc = subprocess.run(
                ["python", "-c", "from core import improve; print(improve.default_soul_path())"],
                cwd=str(elsewhere),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(proc.returncode, 0, f"stderr: {proc.stderr}")
            self.assertEqual(Path(proc.stdout.strip()), CANONICAL_SOUL)

    def test_explicit_soul_path_overrides_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory) / "state"
            custom = Path(directory) / "CUSTOM_SOUL.md"
            custom.write_text("# custom soul baseline\n", encoding="utf-8")
            with mock.patch("core.improve.subprocess.run") as run_mock, mock.patch(
                "core.improve.node_bin", return_value="node"
            ):
                run_mock.return_value = mock.Mock(
                    returncode=0, stdout=json.dumps({"id": "p", "edits": []}), stderr=""
                )
                improve.run_headless(
                    home=Path(directory),
                    cwd=Path(directory),
                    state_dir=state_dir,
                    analyzer="mock",
                    soul_path=custom,
                )
                argv = run_mock.call_args[0][0]
                self.assertIn("--soul-path", argv)
                self.assertIn(str(custom), argv)
                self.assertNotIn(str(CANONICAL_SOUL), argv)

    def test_default_soul_path_passed_when_no_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory) / "state"
            with mock.patch("core.improve.subprocess.run") as run_mock, mock.patch(
                "core.improve.node_bin", return_value="node"
            ):
                run_mock.return_value = mock.Mock(
                    returncode=0, stdout=json.dumps({"id": "p", "edits": []}), stderr=""
                )
                improve.run_headless(
                    home=Path(directory),
                    cwd=Path(directory),
                    state_dir=state_dir,
                    analyzer="mock",
                    soul_path=None,
                )
                argv = run_mock.call_args[0][0]
                self.assertIn("--soul-path", argv)
                idx = argv.index("--soul-path")
                self.assertEqual(argv[idx + 1], str(CANONICAL_SOUL))

    def test_synthesize_resume_default_soul_path_passed_when_no_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory) / "state"
            with mock.patch("core.improve.subprocess.run") as run_mock, mock.patch(
                "core.improve.node_bin", return_value="node"
            ):
                run_mock.return_value = mock.Mock(
                    returncode=0, stdout=json.dumps({"id": "p", "edits": []}), stderr=""
                )
                improve.synthesize_resume(state_dir=state_dir, soul_path=None)
                argv = run_mock.call_args[0][0]
                self.assertIn("--soul-path", argv)
                idx = argv.index("--soul-path")
                self.assertEqual(argv[idx + 1], str(CANONICAL_SOUL))


class SoulFailClosedTests(unittest.TestCase):
    def _seed_eligible_state(self, state_dir: Path) -> None:
        (state_dir / "evidence").mkdir(parents=True, exist_ok=True)
        quote = "sessions re-derive project context from scratch"
        for sid in ("s1", "s2"):
            (state_dir / "evidence" / f"{sid}.json").write_text(
                json.dumps({
                    "transcriptId": sid,
                    "status": "ok",
                    "positive": [{"quote": quote, "effect": "made progress"}],
                    "negative": [],
                    "gaps": [{
                        "proposedInstruction": "Bootstrap context once",
                        "mistake": quote,
                        "quote": quote,
                        "recurrenceRisk": "every session pays",
                    }],
                }),
                encoding="utf-8",
            )
        (state_dir / "ledger.json").write_text(
            json.dumps({
                "version": 1,
                "minGapEvidence": 2,
                "clusters": [{
                    "id": "g-abc",
                    "proposedInstruction": "Bootstrap context once",
                    "representativeQuote": quote,
                    "mistake": quote,
                    "sources": ["s1", "s2"],
                    "count": 2,
                    "eligible": True,
                    "perSource": {
                        "s1": {"quote": quote, "mistake": quote},
                        "s2": {"quote": quote, "mistake": quote},
                    },
                }],
            }),
            encoding="utf-8",
        )

    def test_unavailable_soul_fails_closed_synthesize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory) / "state"
            self._seed_eligible_state(state_dir)
            missing = Path(directory) / "missing-SOUL.md"
            with self.assertRaisesRegex(RuntimeError, "SOUL"):
                improve.synthesize_resume(state_dir=state_dir, soul_path=missing)
            self.assertFalse((state_dir / "proposal.json").exists())

    def test_empty_soul_fails_closed_synthesize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory) / "state"
            self._seed_eligible_state(state_dir)
            empty = Path(directory) / "empty-SOUL.md"
            empty.write_text("   \n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "SOUL"):
                improve.synthesize_resume(state_dir=state_dir, soul_path=empty)
            self.assertFalse((state_dir / "proposal.json").exists())


class SoulProposalTests(unittest.TestCase):
    def test_run_headless_proposal_carries_soul_provenance_and_never_writes_soul(self) -> None:
        from tests.test_improve import _make_fixture_home, _add_eligible_codex_sessions

        soul_text = CANONICAL_SOUL.read_text(encoding="utf-8")
        expected_hash = hashlib.sha256(soul_text.encode("utf-8")).hexdigest()
        before = CANONICAL_SOUL.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = _make_fixture_home(root)
            _add_eligible_codex_sessions(home)
            state_dir = root / "xdg" / "improve"
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            proposal = improve.run_headless(
                home=home, cwd=elsewhere, state_dir=state_dir, analyzer="mock"
            )
            soul = proposal.get("soul")
            self.assertIsNotNone(soul, "proposal must carry soul provenance")
            self.assertEqual(Path(soul["path"]), CANONICAL_SOUL)
            self.assertEqual(soul["sha256"], expected_hash)
            self.assertEqual(soul["chars"], len(soul_text))
            self.assertGreaterEqual(len(proposal["edits"]), 1)
        self.assertEqual(CANONICAL_SOUL.read_text(encoding="utf-8"), before)

    def test_synthesize_prompt_carries_soul_text_and_hash(self) -> None:
        proc = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                (
                    "import { buildSynthesisPrompt } from './improve/src/synthesize.js';\n"
                    "import { renderAnnotatePrompt } from './improve/src/annotate.js';\n"
                    "import fs from 'node:fs';\n"
                    "const soul = fs.readFileSync('./workspaces/alignment/artifacts/SOUL.md','utf8');\n"
                    "const { createHash } = await import('node:crypto');\n"
                    "const hash = createHash('sha256').update(soul).digest('hex');\n"
                    "const ledger = { clusters: [] };\n"
                    "const sp = buildSynthesisPrompt(ledger, { evidenceIndex: new Map(), soulSnapshot: soul.slice(0,4000), soulSha256: hash });\n"
                    "const ap = renderAnnotatePrompt([], { runId: 'run-SOUL', soulSnapshot: soul.slice(0,4000), soulSha256: hash });\n"
                    "console.log(JSON.stringify({ spHasText: sp.includes(soul.slice(0,64)), spHasHash: sp.includes(hash), apHasText: ap.includes(soul.slice(0,64)), apHasHash: ap.includes(hash) }));\n"
                ),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, f"stderr: {proc.stderr}")
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertTrue(payload["spHasText"], "synthesis prompt must carry bounded SOUL text")
        self.assertTrue(payload["spHasHash"], "synthesis prompt must carry SOUL sha256")
        self.assertTrue(payload["apHasText"], "annotation prompt must carry bounded SOUL text")
        self.assertTrue(payload["apHasHash"], "annotation prompt must carry SOUL sha256")


class SoulCliTests(unittest.TestCase):
    def test_improve_run_registers_soul_path(self) -> None:
        from core.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["improve-run", "--headless", "--soul-path", "/tmp/SOUL.md"])
        self.assertEqual(args.command, "improve-run")
        self.assertEqual(str(args.soul_path), "/tmp/SOUL.md")

    def test_improve_synthesize_registers_soul_path(self) -> None:
        from core.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["improve-synthesize", "--soul-path", "/tmp/SOUL.md"])
        self.assertEqual(args.command, "improve-synthesize")
        self.assertEqual(str(args.soul_path), "/tmp/SOUL.md")

    def test_improve_run_cli_passes_soul_path_through(self) -> None:
        import io
        from contextlib import redirect_stderr, redirect_stdout
        from unittest import mock as _mock

        from core import cli as cli_mod

        fake = {"id": "prop-soul", "edits": [], "stats": {"transcripts": 0}}
        with _mock.patch("core.improve.run_headless", return_value=fake) as headless_mock:
            stdout, stderr = io.StringIO(), io.StringIO()
            from contextlib import redirect_stderr as _rs, redirect_stdout as _ro

            with _ro(stdout), _rs(stderr):
                rc = cli_mod.main(
                    ["improve-run", "--headless", "--state-dir", "/tmp/x", "--soul-path", "/tmp/SOUL.md"]
                )
        self.assertEqual(rc, 0)
        _, kwargs = headless_mock.call_args
        self.assertEqual(str(kwargs.get("soul_path")), "/tmp/SOUL.md")

    def test_improve_synthesize_cli_passes_soul_path_through(self) -> None:
        import io
        from contextlib import redirect_stderr as _rs, redirect_stdout as _ro
        from unittest import mock as _mock

        from core import cli as cli_mod

        fake = {"id": "prop-resume-soul", "edits": [], "stats": {"transcripts": 0}}
        with _mock.patch("core.improve.synthesize_resume", return_value=fake) as resume_mock:
            stdout, stderr = io.StringIO(), io.StringIO()
            with _ro(stdout), _rs(stderr):
                rc = cli_mod.main(
                    ["improve-synthesize", "--state-dir", "/tmp/x", "--soul-path", "/tmp/SOUL.md"]
                )
        self.assertEqual(rc, 0)
        _, kwargs = resume_mock.call_args
        self.assertEqual(str(kwargs.get("soul_path")), "/tmp/SOUL.md")


if __name__ == "__main__":
    unittest.main()
