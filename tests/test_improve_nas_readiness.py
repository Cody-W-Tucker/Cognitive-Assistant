#!/usr/bin/env python3
"""Guards for running the improvement loop unattended against a deployed Hermes.

Covers: ambient store env survives the Python boundary, a named harness with a
missing store fails loudly, decisions bind to the proposal they reviewed, the
apply lock refuses concurrent writers, and a packaged runtime can point at a
live workspace checkout.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core import experience, improve
from tests.test_improve import _run_fixture_proposal


class HomeScopingTests(unittest.TestCase):
    def test_run_headless_omits_home_when_unset(self) -> None:
        completed = mock.Mock(returncode=0, stdout=json.dumps({"id": "p", "edits": []}), stderr="")
        with tempfile.TemporaryDirectory() as directory, mock.patch(
            "core.improve.subprocess.run", return_value=completed
        ) as run:
            improve.run_headless(
                home=None,
                cwd=Path(directory),
                state_dir=Path(directory) / "state",
                analyzer="mock",
                harnesses=["hermes"],
            )
        cmd = run.call_args.args[0]
        self.assertNotIn("--home", cmd)
        self.assertEqual(cmd[cmd.index("--harness") + 1], "hermes")

    def test_hermes_home_is_honored_and_missing_named_store_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = {**os.environ, "HERMES_HOME": str(root / "no-hermes-here")}
            with mock.patch.dict(os.environ, env, clear=True):
                with self.assertRaisesRegex(RuntimeError, "hermes: store missing"):
                    improve.discover_transcripts(
                        home=None,
                        cwd=root,
                        state_dir=root / "state",
                        harnesses=["hermes"],
                    )


class ProposalBindingTests(unittest.TestCase):
    def test_apply_refuses_decisions_for_a_replaced_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir, proposal = _run_fixture_proposal(root)
            edit = proposal["edits"][0]
            with self.assertRaisesRegex(RuntimeError, "newer run replaced"):
                improve.apply(
                    state_dir=state_dir,
                    experience_root=root / "exp",
                    decisions={edit["id"]: "accepted"},
                    expected_proposal_id="prop-the-one-i-read",
                )
            self.assertFalse((root / "exp").exists())

    def test_cli_requires_proposal_id_with_decisions(self) -> None:
        from core.cli import main

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir, proposal = _run_fixture_proposal(root)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = main(
                    [
                        "improve-apply",
                        "--state-dir",
                        str(state_dir),
                        "--decisions",
                        f"{proposal['edits'][0]['id']}=accepted",
                    ]
                )
            self.assertEqual(code, 2)
            self.assertIn(f"--proposal {proposal['id']}", stderr.getvalue())


class ApplyLockTests(unittest.TestCase):
    def test_concurrent_apply_is_refused(self) -> None:
        import fcntl

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir, proposal = _run_fixture_proposal(root)
            edit = proposal["edits"][0]
            with open(state_dir / ".apply.lock", "a+", encoding="utf-8") as holder:
                fcntl.flock(holder.fileno(), fcntl.LOCK_EX)
                with self.assertRaisesRegex(RuntimeError, "another improve-apply"):
                    improve.apply(
                        state_dir=state_dir,
                        experience_root=root / "exp",
                        decisions={edit["id"]: "rejected:too-narrow"},
                    )
            self.assertFalse((state_dir / "rejections.jsonl").exists())


class StateRootTests(unittest.TestCase):
    def test_ca_home_holds_improve_state_and_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with mock.patch.dict(os.environ, {"CA_HOME": str(home)}):
                self.assertEqual(improve.default_state_dir(), home / "improve")
                self.assertEqual(experience.experience_root(), home / "experience")


if __name__ == "__main__":
    unittest.main()
