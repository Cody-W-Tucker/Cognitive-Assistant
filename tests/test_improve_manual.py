"""Focused TDD tests for improve-run manual (TTY) vs headless routes."""

from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

from core.cli import _build_parser


def _fake_proposal() -> dict:
    return {"id": "p1", "edits": [], "stats": {"transcripts": 0}}


class TestImproveRunRoutes(unittest.TestCase):
    def test_default_allowed_without_headless_flag(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["improve-run"])
        self.assertEqual(args.command, "improve-run")
        self.assertFalse(args.headless)

    def test_default_manual_presents_stage_labels_and_directs_review_apply(self) -> None:
        from core import cli as cli_mod

        argv = ["improve-run"]
        with mock.patch(
            "core.improve.run_headless", return_value=_fake_proposal()
        ) as run_mock, mock.patch(
            "core.improve.apply"
        ) as apply_mock, mock.patch(
            "core.improve.default_state_dir", return_value=Path("/tmp/ca-improve-test")
        ), mock.patch.object(sys.stdin, "isatty", return_value=True):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr), mock.patch.object(
                sys.stdout, "isatty", return_value=True
            ):
                rc = cli_mod.main(argv)
        self.assertEqual(rc, 0)
        # Uses the exact existing CA JS pipeline/state/proposal path.
        run_mock.assert_called_once()
        combined = stdout.getvalue() + stderr.getvalue()
        for label in (
            "collect samples",
            "calculate loss",
            "aggregate gradients",
            "gradient descent",
        ):
            self.assertIn(label, combined)
        self.assertIn("review", combined.lower())
        self.assertIn("improve-apply", combined)
        apply_mock.assert_not_called()

    def test_default_without_headless_rejects_non_tty_before_pipeline(self) -> None:
        from core import cli as cli_mod

        argv = ["improve-run"]
        with mock.patch(
            "core.improve.run_headless", return_value=_fake_proposal()
        ) as run_mock, mock.patch(
            "core.improve.default_state_dir", return_value=Path("/tmp/ca-improve-test")
        ), mock.patch.object(sys.stdin, "isatty", return_value=False):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                rc = cli_mod.main(argv)
        self.assertNotEqual(rc, 0)
        run_mock.assert_not_called()
        self.assertIn("--headless", stderr.getvalue())

    def test_headless_emits_exactly_one_json_stdout_object_no_progress(self) -> None:
        from core import cli as cli_mod

        argv = ["improve-run", "--headless"]
        with mock.patch(
            "core.improve.run_headless", return_value=_fake_proposal()
        ) as run_mock, mock.patch(
            "core.improve.default_state_dir", return_value=Path("/tmp/ca-improve-test")
        ):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                rc = cli_mod.main(argv)
        self.assertEqual(rc, 0)
        run_mock.assert_called_once()
        out = stdout.getvalue()
        # Exactly one JSON object on stdout, no extra lines/progress.
        lines = [line for line in out.splitlines() if line.strip() != ""]
        self.assertEqual(len(lines), 1)
        parsed = json.loads(lines[0])
        self.assertEqual(parsed["id"], "p1")
        for label in (
            "collect samples",
            "calculate loss",
            "aggregate gradients",
            "gradient descent",
        ):
            self.assertNotIn(label, out)

    def test_both_paths_use_existing_js_pipeline_state_proposal_path(self) -> None:
        from core import improve as improve_runtime

        # Exact existing pipeline entry points must exist and agree.
        self.assertTrue(improve_runtime.RUNTIME_BIN.name == "ca-improve.js")
        self.assertTrue(hasattr(improve_runtime, "run_headless"))
        self.assertTrue(hasattr(improve_runtime, "default_state_dir"))
        self.assertTrue(hasattr(improve_runtime, "read_proposal"))
        import inspect

        src = inspect.getsource(improve_runtime.run_headless)
        self.assertIn('"run"', src)
        self.assertIn('"--headless"', src)
        self.assertIn("proposal", inspect.getsource(improve_runtime.read_proposal))


if __name__ == "__main__":
    unittest.main()
