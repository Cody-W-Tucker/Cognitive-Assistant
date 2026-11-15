#!/usr/bin/env python3
"""Outcome check and the autonomous adopt / judge / revert cycle."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone

from core import experience, improve, living_soul, outcome
from core.paths import improve_dir, soul_dir
from tests.fixtures import CAHomeTestCase

T0 = datetime(2026, 11, 1, tzinfo=timezone.utc)
FIVE = outcome.OutcomePolicy(min_sessions=5)


def _iso(when: datetime) -> str:
    return when.isoformat(timespec="seconds")


def _ms(when: datetime) -> int:
    return int(when.timestamp() * 1000)


def _write_evidence(
    name: str, when: datetime, miss: bool, harness: str = "hermes",
    source: str | None = "cli", rubric: dict | None = None,
    label: str | None = None, scored: bool = True,
) -> None:
    negative = [{"class": "harm", "quote": "q"}] if miss else []
    payload = {
        "transcriptId": name,
        "harness": harness,
        "status": "ok",
        "positive": [],
        "negative": negative,
        "gaps": [],
        "sessionAt": _ms(when),
        "source": source,
        "rubric": rubric,
    }
    if scored:
        payload["outcome"] = {"label": label or ("stalled" if miss else "advanced"), "rubric": rubric}
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

    def test_miss_uses_outcome_labels_only(self) -> None:
        for label in ("stalled", "regressed"):
            self.assertIs(outcome.is_miss({"outcome": {"label": label}}), True)
        self.assertIs(outcome.is_miss({"outcome": {"label": "advanced"}, "gaps": [1]}), False)
        for evidence in ({"outcome": {"label": "unclear"}}, {"outcome": {"label": "answered"}},
                         {"negative": [{"class": "harm"}]},
                         {"outcome": {"label": "invalid"}}):
            self.assertIsNone(outcome.is_miss(evidence))


class AutoCycleTests(CAHomeTestCase):
    def _set_activations(self, rows: list[tuple[datetime, int]]) -> None:
        path = soul_dir() / "activations.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(json.dumps({"at": _iso(at), "generation": g}) + "\n" for at, g in rows),
            encoding="utf-8",
        )

    def _adopt_after_baseline(self, proposal: dict, misses: int) -> dict:
        """First run builds a baseline; adoption happens once it has sessions."""
        first = improve.auto_cycle(proposal=proposal, policy=FIVE)
        self.assertEqual(first["action"], "baseline")
        self._set_activations([(T0, 1)])
        _fill("base", T0, total=10, misses=misses)
        adopted = improve.auto_cycle(proposal=proposal, policy=FIVE)
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
        waiting = improve.auto_cycle(proposal=proposal, policy=FIVE)
        self.assertEqual(waiting["action"], "wait")

        # Sessions under the new generation go clearly worse: revert it.
        _fill("after", start, total=10, misses=8)
        reverted = improve.auto_cycle(proposal=proposal, policy=FIVE)
        self.assertEqual(reverted["verdict"]["verdict"], "revert")
        self.assertEqual(reverted["action"], "revert")
        self.assertNotIn(adopted[0], living_soul.current_generation()["records"])
        self.assertIn(adopted[0], experience.reverted_ids())
        # The reverted text is generation 1's, so generation 1 is reactivated
        # and its sessions remain the baseline for the next change.
        self.assertEqual(reverted["generation"], 1)
        self.assertEqual(living_soul.current_generation()["generation"], 1)
        self.assertEqual(len(living_soul.list_generations()), 2)
        self.assertEqual(living_soul.activations()[-1]["generation"], 1)

        # The next run must not bring the withdrawn change straight back.
        again = improve.run(analyzer="mock")
        self.assertNotIn(adopted[0], [edit["record"]["id"] for edit in again["edits"]])
        self.assertNotEqual(improve.auto_cycle(proposal=again, policy=FIVE).get("records"), adopted)

    def test_change_that_does_not_hurt_is_kept(self) -> None:
        proposal = self.run_mock_proposal()
        self._adopt_after_baseline(proposal, misses=4)
        current = living_soul.current_generation()
        start = T0 + timedelta(days=7)
        self._set_activations([(T0, 1), (start, current["generation"])])
        _fill("after", start, total=10, misses=3)
        verdict = outcome.evaluate(FIVE)
        self.assertEqual(verdict["verdict"], "keep")
        # Settled verdicts are final and recorded once.
        again = outcome.evaluate(FIVE)
        self.assertTrue(again.get("settled"))
        self.assertEqual(len(outcome.verdicts()), 2)

    def test_wrapper_change_does_not_end_the_test_of_the_change_before_it(self) -> None:
        proposal = self.run_mock_proposal()
        adopted = self._adopt_after_baseline(proposal, misses=1)["records"]
        tested = living_soul.current_generation()["generation"]
        prefix = self.ca_home / "prefix.md"
        prefix.write_text("Be brief.", encoding="utf-8")
        living_soul.write_compose_config(str(prefix), None)
        wrapped = living_soul.compile_soul(reason="activation")
        self.assertEqual((wrapped["added"], wrapped["parent"]), ([], tested))

        start = T0 + timedelta(days=7)
        self._set_activations([(T0, 1), (start, tested), (start + timedelta(days=1), wrapped["generation"])])
        _fill("under-test", start, total=3, misses=3)
        self.assertEqual(outcome.evaluate(FIVE)["verdict"], "pending")
        _fill("wrapped", start + timedelta(days=1), total=7, misses=5)
        verdict = outcome.evaluate(FIVE)
        self.assertEqual((verdict["verdict"], verdict["generation"], verdict["added"]), ("revert", tested, adopted))
        self.assertEqual(verdict["current"], {"sessions": 10, "misses": 8})
        # The wrapper-only generation is then kept untested, as before.
        self.assertEqual(outcome.evaluate(FIVE)["reason"], "untested: no records added")

    def test_other_harness_sessions_do_not_count(self) -> None:
        proposal = self.run_mock_proposal()
        improve.auto_cycle(proposal=proposal, policy=FIVE)
        start = T0 + timedelta(days=7)
        self._set_activations([(T0, 1)])
        before = outcome.session_outcomes()
        for i in range(10):
            _write_evidence(f"codex{i}", start + timedelta(minutes=i), miss=True, harness="codex")
        self.assertEqual(outcome.session_outcomes(), before)

    def test_source_allowlist_excludes_unknown_and_missing(self) -> None:
        self._set_activations([(T0, 1)])
        for source in ("desktop", "tui", "cli", "cron", "api_server", "subagent", None):
            _write_evidence(str(source), T0, miss=True, source=source)
        self.assertEqual(outcome.session_outcomes(), {1: {"sessions": 3, "misses": 3}})
        self.assertEqual(outcome.session_outcomes(sources={"cron"}), {1: {"sessions": 1, "misses": 1}})
        self.assertEqual(outcome.session_outcomes(sources=set()), {})

    def test_qualified_evidence_wins_over_legacy_before_filtering(self) -> None:
        self._set_activations([(T0, 1)])
        _write_evidence("same", T0, miss=True)
        path = improve_dir() / "evidence" / "hermes:same.json"
        legacy = json.loads((path.parent / "same.json").read_text(encoding="utf-8"))
        path.write_text(json.dumps({**legacy, "outcome": {**legacy["outcome"], "label": "advanced"}}), encoding="utf-8")
        self.assertEqual(outcome.session_outcomes(), {1: {"sessions": 1, "misses": 0}})
        path.write_text(json.dumps({**legacy, "source": "cron"}), encoding="utf-8")
        self.assertEqual(outcome.session_outcomes(), {})
        path.write_text(json.dumps({**legacy, "status": "failed"}), encoding="utf-8")
        self.assertEqual(outcome.session_outcomes(), {1: {"sessions": 1, "misses": 1}})
    def test_unclear_and_unscored_do_not_count(self) -> None:
        self._set_activations([(T0, 1)])
        _write_evidence("unclear", T0, True, label="unclear")
        _write_evidence("unscored", T0, True, scored=False)
        self.assertEqual(outcome.session_outcomes(), {})
        _write_evidence("advanced", T0, True, label="advanced")
        _write_evidence("regressed", T0, False, label="regressed")
        self.assertEqual(outcome.session_outcomes(), {1: {"sessions": 2, "misses": 1}})

    def test_unscored_generations_are_pending(self) -> None:
        proposal = self.run_mock_proposal()
        self._adopt_after_baseline(proposal, misses=0)
        current = living_soul.current_generation()
        start = T0 + timedelta(days=7)
        self._set_activations([(T0, 1), (start, current["generation"])])
        for i in range(10):
            _write_evidence(f"after{i}", start + timedelta(minutes=i), True, scored=False)
        result = outcome.evaluate(FIVE, record=False)
        self.assertEqual(result["verdict"], "pending")
        self.assertEqual(result["current"]["sessions"], 0)

    def test_improved_is_reported_without_changing_keep_rule(self) -> None:
        proposal = self.run_mock_proposal()
        self._adopt_after_baseline(proposal, misses=8)
        current = living_soul.current_generation()
        start = T0 + timedelta(days=7)
        self._set_activations([(T0, 1), (start, current["generation"])])
        _fill("after", start, total=10, misses=1)
        result = outcome.evaluate(FIVE)
        self.assertEqual(result["verdict"], "keep")
        self.assertTrue(result["improved"])
        self.assertTrue(outcome.verdicts()[current["generation"]]["improved"])

    def test_rubric_mismatch_blocks_verdict(self) -> None:
        proposal = self.run_mock_proposal()
        self._adopt_after_baseline(proposal, misses=0)
        current = living_soul.current_generation()
        start = T0 + timedelta(days=7)
        self._set_activations([(T0, 1), (start, current["generation"])])
        stamp = {"promptSha": "p1", "model": "m1", "contextSha": "c1"}
        for i in range(10):
            _write_evidence(f"base{i}", T0 + timedelta(minutes=i + 1), False, rubric=stamp)
            _write_evidence(f"after{i}", start + timedelta(minutes=i + 1), False,
                            rubric={**stamp, "contextSha": "c2"})
        self.assertEqual(outcome.evaluate(FIVE, record=False)["verdict"], "keep")
        for rubric, reason in [({**stamp, "promptSha": "p2"}, "promptSha"),
                               ({**stamp, "model": "m2"}, "model"),
                               ({**stamp, "matureDays": 3}, "matureDays"), (None, "promptSha")]:
            _write_evidence("after0", start + timedelta(minutes=1), False, rubric=rubric)
            verdict = outcome.evaluate(FIVE, record=False)
            self.assertEqual(verdict["verdict"], "pending")
            self.assertIn(reason, verdict["reason"])
        self.assertNotIn(current["generation"], outcome.verdicts())


if __name__ == "__main__":
    unittest.main()
