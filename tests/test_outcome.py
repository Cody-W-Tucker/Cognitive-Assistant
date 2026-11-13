#!/usr/bin/env python3
"""Outcome check and the autonomous adopt / judge / revert cycle."""

from __future__ import annotations

import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core import experience, improve, living_soul, outcome
from core.paths import improve_dir, soul_dir
from tests.fixtures import CAHomeTestCase

T0 = datetime(2026, 11, 1, tzinfo=timezone.utc)


def _iso(when: datetime) -> str:
    return when.isoformat(timespec="seconds")


def _ms(when: datetime) -> int:
    return int(when.timestamp() * 1000)


def _write_evidence(name: str, when: datetime, miss: bool, harness: str = "hermes") -> None:
    negative = [{"class": "harm", "quote": "q"}] if miss else []
    payload = {
        "transcriptId": name,
        "harness": harness,
        "status": "ok",
        "positive": [],
        "negative": negative,
        "gaps": [],
        "sessionAt": _ms(when),
    }
    path = improve_dir() / "evidence" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fill(prefix: str, start: datetime, total: int, misses: int) -> None:
    for i in range(total):
        _write_evidence(f"{prefix}{i}", start + timedelta(minutes=i + 1), miss=i < misses)


class OutcomeUnitTests(unittest.TestCase):
    def test_generation_at_uses_activation_history(self) -> None:
        history = [
            {"at": _iso(T0), "generation": 1},
            {"at": _iso(T0 + timedelta(days=7)), "generation": 2},
        ]
        self.assertIsNone(outcome.generation_at(_ms(T0 - timedelta(hours=1)), history))
        self.assertEqual(outcome.generation_at(_ms(T0 + timedelta(days=1)), history), 1)
        self.assertEqual(outcome.generation_at(_ms(T0 + timedelta(days=8)), history), 2)

    def test_miss_counts_harm_noncompliance_and_gaps_only(self) -> None:
        self.assertTrue(outcome.is_miss({"negative": [{"class": "harm"}]}))
        self.assertTrue(outcome.is_miss({"negative": [{"class": "non-compliance"}]}))
        self.assertTrue(outcome.is_miss({"gaps": [{"mistake": "x"}]}))
        self.assertFalse(outcome.is_miss({"negative": [{"class": "irrelevant"}], "gaps": []}))


class AutoCycleTests(CAHomeTestCase):
    def _set_activations(self, rows: list[tuple[datetime, int]]) -> None:
        path = soul_dir() / "activations.jsonl"
        path.write_text(
            "".join(json.dumps({"at": _iso(at), "generation": g}) + "\n" for at, g in rows),
            encoding="utf-8",
        )

    def _adopt_after_baseline(self, proposal: dict, misses: int) -> dict:
        """First run builds a baseline; adoption happens once it has sessions."""
        first = improve.auto_cycle(proposal=proposal, min_sessions=5)
        self.assertEqual(first["action"], "baseline")
        self._set_activations([(T0, 1)])
        _fill("base", T0, total=10, misses=misses)
        adopted = improve.auto_cycle(proposal=proposal, min_sessions=5)
        self.assertEqual(adopted["action"], "adopt")
        return adopted

    def test_adopts_one_record_then_waits_then_reverts_on_regression(self) -> None:
        proposal = self.run_mock_proposal()

        first = self._adopt_after_baseline(proposal, misses=1)
        adopted = first["records"]
        self.assertEqual(len(adopted), 1)
        current = living_soul.current_generation()
        self.assertEqual(current["added"], adopted)
        self.assertIn(adopted[0], current["records"])

        # Not enough sessions under the new generation yet: hold, adopt nothing.
        start = T0 + timedelta(days=7)
        self._set_activations([(T0, 1), (start, current["generation"])])
        waiting = improve.auto_cycle(proposal=proposal, min_sessions=5)
        self.assertEqual(waiting["action"], "wait")

        # Sessions under the new generation go clearly worse: revert it.
        _fill("after", start, total=10, misses=8)
        reverted = improve.auto_cycle(proposal=proposal, min_sessions=5)
        self.assertEqual(reverted["verdict"]["verdict"], "revert")
        self.assertEqual(reverted["action"], "revert")
        self.assertNotIn(adopted[0], living_soul.current_generation()["records"])
        self.assertIn(adopted[0], experience.reverted_ids())

        # The next run must not bring the withdrawn change straight back.
        again = improve.run(home=self.user_home, analyzer="mock")
        self.assertNotIn(adopted[0], [edit["record"]["id"] for edit in again["edits"]])
        self.assertNotEqual(improve.auto_cycle(proposal=again, min_sessions=5).get("records"), adopted)

    def test_change_that_does_not_hurt_is_kept(self) -> None:
        proposal = self.run_mock_proposal()
        self._adopt_after_baseline(proposal, misses=4)
        current = living_soul.current_generation()
        start = T0 + timedelta(days=7)
        self._set_activations([(T0, 1), (start, current["generation"])])
        _fill("after", start, total=10, misses=3)
        verdict = outcome.evaluate(min_sessions=5)
        self.assertEqual(verdict["verdict"], "keep")
        # Settled verdicts are final and recorded once.
        again = outcome.evaluate(min_sessions=5)
        self.assertTrue(again.get("settled"))
        self.assertEqual(len(outcome.verdicts()), 2)

    def test_other_harness_sessions_do_not_count(self) -> None:
        proposal = self.run_mock_proposal()
        improve.auto_cycle(proposal=proposal, min_sessions=5)
        start = T0 + timedelta(days=7)
        self._set_activations([(T0, 1)])
        before = outcome.session_outcomes()
        for i in range(10):
            _write_evidence(f"codex{i}", start + timedelta(minutes=i), miss=True, harness="codex")
        self.assertEqual(outcome.session_outcomes(), before)


if __name__ == "__main__":
    unittest.main()
