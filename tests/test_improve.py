#!/usr/bin/env python3
"""The improvement pass end to end: run, synthesize, review, apply."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from core import experience, improve, journal, living_soul
from core.cli import main
from core.paths import improve_dir
from tests.fixtures import CAHomeTestCase

REPO_ROOT = Path(__file__).resolve().parents[1]


def _git_status() -> str:
    return subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout


def _run_cli(argv: list[str]) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def _seed_resume_state(state: Path) -> None:
    """Evidence and a ledger with one eligible cluster, as a finished run leaves them."""
    quote = "sessions re-derive project context from scratch"
    for sid in ("s1", "s2"):
        path = state / "evidence" / f"{sid}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "transcriptId": sid,
                    "status": "ok",
                    "positive": [{"quote": quote, "effect": "made progress"}],
                    "negative": [],
                    "gaps": [{"proposedInstruction": "Bootstrap context once", "mistake": quote, "quote": quote}],
                }
            ),
            encoding="utf-8",
        )
    cluster = {
        "id": "g-abc",
        "proposedInstruction": "Bootstrap context once",
        "representativeQuote": quote,
        "mistake": quote,
        "sources": ["s1", "s2"],
        "count": 2,
        "eligible": True,
        "perSource": {sid: {"quote": quote, "mistake": quote} for sid in ("s1", "s2")},
    }
    (state / "ledger.json").write_text(json.dumps({"version": 1, "clusters": [cluster]}), encoding="utf-8")


class RunTests(CAHomeTestCase):
    def test_headless_cli_prints_one_proposal_and_writes_only_ca_home(self) -> None:
        from tests.fixtures import add_eligible_codex_sessions

        add_eligible_codex_sessions(self.user_home)
        before = _git_status()
        with mock.patch.dict(os.environ, {"CA_IMPROVE_HOME": str(self.user_home)}):
            code, out, err = _run_cli(["improve-run", "--headless", "--analyzer", "mock"])
        self.assertEqual(code, 0, err)
        lines = [line for line in out.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        proposal = json.loads(lines[0])
        self.assertGreaterEqual(len(proposal["edits"]), 1)
        self.assertIn(f"--proposal {proposal['id']}", err)
        self.assertEqual(_git_status(), before)
        self.assertEqual(improve.read_proposal()["id"], proposal["id"])

    def test_proposal_is_grounded_in_the_soul_hermes_runs(self) -> None:
        proposal = self.run_mock_proposal()
        text = self.bootstrap.read_text(encoding="utf-8")
        self.assertEqual(Path(proposal["soul"]["path"]), self.bootstrap)
        self.assertEqual(proposal["soul"]["sha256"], hashlib.sha256(text.encode()).hexdigest())

        living_soul.compile_soul()
        again = improve.run(home=self.user_home, analyzer="mock")
        self.assertEqual(Path(again["soul"]["path"]), living_soul.current_path())
        self.assertEqual(self.bootstrap.read_text(encoding="utf-8"), text)

    def test_manual_route_requires_a_terminal(self) -> None:
        with mock.patch.object(improve, "run") as run, mock.patch.object(sys.stdin, "isatty", return_value=False):
            code, _, err = _run_cli(["improve-run"])
        self.assertEqual(code, 2)
        self.assertIn("--headless", err)
        run.assert_not_called()

    def test_auto_requires_headless(self) -> None:
        with mock.patch.object(improve, "run") as run:
            code, _, err = _run_cli(["improve-run", "--auto"])
        self.assertEqual(code, 2)
        self.assertIn("--auto requires --headless", err)
        run.assert_not_called()

    def test_a_named_harness_with_no_store_fails_the_run(self) -> None:
        with mock.patch.dict(os.environ, {"HERMES_HOME": str(self.root / "no-hermes-here")}):
            with self.assertRaisesRegex(RuntimeError, "hermes: store missing"):
                improve.run(harnesses=["hermes"], analyzer="mock")


class SynthesizeTests(CAHomeTestCase):
    def test_no_saved_state_fails_without_a_proposal(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "improve-run"):
            improve.synthesize_resume()
        self.assertFalse((improve_dir() / "proposal.json").exists())

    def test_corrupt_ledger_fails(self) -> None:
        _seed_resume_state(improve_dir())
        (improve_dir() / "ledger.json").write_text("{not-json", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "ledger"):
            improve.synthesize_resume()

    def test_no_eligible_cluster_fails(self) -> None:
        _seed_resume_state(improve_dir())
        (improve_dir() / "ledger.json").write_text(json.dumps({"version": 1, "clusters": []}), encoding="utf-8")
        unreachable = {"CA_LLM_BASE_URL": "http://127.0.0.1:9/v1", "CA_LLM_MODEL": "never-called"}
        with mock.patch.dict(os.environ, unreachable), self.assertRaisesRegex(RuntimeError, "eligible"):
            improve.synthesize_resume()

    def test_no_model_configured_fails_before_touching_the_proposal(self) -> None:
        _seed_resume_state(improve_dir())
        with mock.patch.dict(os.environ, {"CA_LLM_BASE_URL": ""}), self.assertRaisesRegex(RuntimeError, "CA_LLM_BASE_URL"):
            improve.synthesize_resume()
        self.assertFalse((improve_dir() / "proposal.json").exists())

    def test_empty_soul_fails_without_a_proposal(self) -> None:
        _seed_resume_state(improve_dir())
        self.bootstrap.write_text("   \n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "SOUL"):
            improve.synthesize_resume()
        self.assertFalse((improve_dir() / "proposal.json").exists())


class DecisionParsingTests(unittest.TestCase):
    def test_vector_with_reasons(self) -> None:
        decisions, reasons = improve.parse_decisions(["e1=accepted e2=rejected:too-narrow", "e3=rejected"])
        self.assertEqual(decisions, {"e1": "accepted", "e2": "rejected", "e3": "rejected"})
        self.assertEqual(reasons, {"e2": "too-narrow"})

    def test_bad_vectors(self) -> None:
        for vector in ("e1", "e1=maybe", "e1=accepted:too-narrow", "e1=rejected:because", "e1=accepted e1=rejected"):
            with self.subTest(vector=vector), self.assertRaises(RuntimeError):
                improve.parse_decisions([vector])


class ApplyTests(CAHomeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.proposal = self.run_mock_proposal()
        self.edits = self.proposal["edits"]
        self.first = self.edits[0]

    def _only_first(self, verdict: str) -> dict:
        decisions = {edit["id"]: "deferred" for edit in self.edits}
        decisions[self.first["id"]] = verdict
        return decisions

    def test_accepted_record_joins_the_living_soul(self) -> None:
        result = improve.apply(decisions=self._only_first("accepted"))
        record = self.first["record"]
        self.assertEqual(result["accepted"], [self.first["id"]])
        self.assertIn(record["id"], result["generation"]["records"])
        soul = living_soul.current_path().read_text(encoding="utf-8")
        self.assertIn(record["title"], soul)
        types = [event["type"] for event in journal.read_events(improve_dir())]
        self.assertIn("experience_accepted", types)
        self.assertIn("soul_compiled", types)

    def test_rejection_writes_no_record_and_closes_the_proposal(self) -> None:
        vector = " ".join(f"{edit['id']}=rejected:too-narrow" for edit in self.edits)
        code, out, err = _run_cli(["improve-apply", "--proposal", self.proposal["id"], "--decisions", vector])
        self.assertEqual(code, 0, err)
        self.assertIn(f"0 accepted - {len(self.edits)} rejected", out)
        self.assertEqual(experience.active(exclude=set()), [])
        self.assertIsNone(living_soul.current_generation())
        self.assertIn("proposal_rejected", [event["type"] for event in journal.read_events(improve_dir())])
        with self.assertRaisesRegex(RuntimeError, "already applied"):
            improve.apply(decisions=self._only_first("accepted"))

    def test_every_edit_needs_a_known_verdict(self) -> None:
        if len(self.edits) > 1:
            with self.assertRaisesRegex(RuntimeError, "unreviewed"):
                improve.apply(decisions={self.first["id"]: "accepted"})
        with self.assertRaisesRegex(RuntimeError, "bad verdict"):
            improve.apply(decisions=self._only_first("skipped"))
        with self.assertRaisesRegex(RuntimeError, "unknown edit"):
            improve.apply(decisions={**self._only_first("accepted"), "e-nope": "accepted"})
        self.assertEqual(experience.active(exclude=set()), [])

    def test_decisions_for_a_replaced_proposal_are_refused(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "newer run replaced"):
            improve.apply(decisions=self._only_first("accepted"), expected_proposal_id="prop-the-one-i-read")
        self.assertEqual(experience.active(exclude=set()), [])

    def test_cli_requires_the_proposal_id_with_decisions(self) -> None:
        code, _, err = _run_cli(["improve-apply", "--decisions", f"{self.first['id']}=accepted"])
        self.assertEqual(code, 2)
        self.assertIn(f"--proposal {self.proposal['id']}", err)

    def test_dry_run_writes_nothing(self) -> None:
        result = improve.apply(decisions=self._only_first("accepted"), dry_run=True)
        self.assertEqual(result["accepted"], [self.first["id"]])
        self.assertEqual(experience.active(exclude=set()), [])
        self.assertFalse(improve.read_proposal().get("appliedAt"))

    def test_concurrent_apply_is_refused(self) -> None:
        with open(improve_dir() / ".apply.lock", "a+", encoding="utf-8") as holder:
            fcntl.flock(holder.fileno(), fcntl.LOCK_EX)
            with self.assertRaisesRegex(RuntimeError, "another improve-apply"):
                improve.apply(decisions=self._only_first("accepted"))
        self.assertEqual(experience.active(exclude=set()), [])

    def test_failed_apply_leaves_no_record_behind(self) -> None:
        (improve_dir() / ".apply.lock").touch()
        improve_dir().chmod(0o500)
        try:
            with self.assertRaises(OSError):
                improve.apply(decisions=self._only_first("accepted"))
        finally:
            improve_dir().chmod(0o700)
        self.assertEqual(experience.active(exclude=set()), [])
        self.assertFalse(improve.read_proposal().get("appliedAt"))

    def test_terminal_review_shows_the_record_and_records_answers(self) -> None:
        stdout = io.StringIO()
        answers = iter(["a"] + ["r"] * (len(self.edits) - 1))
        with mock.patch.object(sys.stdin, "isatty", return_value=True), mock.patch(
            "builtins.input", lambda _prompt: next(answers)
        ), contextlib.redirect_stdout(stdout):
            result = improve.apply()
        self.assertIn(self.first["record"]["body"], stdout.getvalue())
        self.assertEqual(result["accepted"], [self.first["id"]])


if __name__ == "__main__":
    unittest.main()
