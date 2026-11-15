#!/usr/bin/env python3
"""Living SOUL: bootstrap + lineage compiled into generations under CA home."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from core import journal, living_soul
from core.paths import improve_dir
from tests.fixtures import CAHomeTestCase

RECORD = """---
id: {id}
title: {title}
sources: s1, s2
proposal: prop-1
created: {created}
---

# {title}

{body}

## Evidence

- (s1) quoted evidence that must not reach the SOUL
"""


def _write_record(experience: Path, record_id: str, title: str, body: str, created: str) -> None:
    path = experience / "authored" / f"{record_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(RECORD.format(id=record_id, title=title, body=body, created=created), encoding="utf-8")


class LivingSoulTests(CAHomeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.bootstrap_dir = self.bootstrap.parent
        self.experience = self.ca_home / "experience"

    def test_first_compile_is_bootstrap_and_is_idempotent(self) -> None:
        first = living_soul.compile_soul()
        self.assertEqual(first["generation"], 1)
        self.assertTrue(first["changed"])
        current = living_soul.current_path()
        self.assertEqual(current.read_text(encoding="utf-8"), "# SOUL.md\n\nBootstrap voice.\n")
        again = living_soul.compile_soul()
        self.assertFalse(again["changed"])
        self.assertEqual(len(living_soul.list_generations()), 1)

    def test_records_append_instruction_only_in_acceptance_order(self) -> None:
        _write_record(self.experience, "exp-b", "Second", "Do B.", "2026-11-02T00:00:00+00:00")
        _write_record(self.experience, "exp-a", "First", "Do A.", "2026-11-01T00:00:00+00:00")
        meta = living_soul.compile_soul()
        text = living_soul.current_path().read_text(encoding="utf-8")
        self.assertEqual(meta["records"], ["exp-a", "exp-b"])
        self.assertIn(living_soul.LEARNED_HEADING, text)
        self.assertLess(text.index("### First"), text.index("### Second"))
        self.assertIn("Do A.", text)
        self.assertNotIn("quoted evidence", text)

    def test_generation_never_reads_previous_generation(self) -> None:
        _write_record(self.experience, "exp-a", "First", "Do A.", "2026-11-01T00:00:00+00:00")
        living_soul.compile_soul()
        # Tamper with the active generation; the next compile must not inherit it.
        living_soul.current_path().resolve().write_text("tampered\n", encoding="utf-8")
        _write_record(self.experience, "exp-b", "Second", "Do B.", "2026-11-02T00:00:00+00:00")
        living_soul.compile_soul()
        text = living_soul.current_path().read_text(encoding="utf-8")
        self.assertNotIn("tampered", text)
        self.assertTrue(text.startswith("# SOUL.md"))

    def test_absorbed_and_reverted_records_are_left_out(self) -> None:
        _write_record(self.experience, "exp-a", "Absorbed", "Do A.", "2026-11-01T00:00:00+00:00")
        _write_record(self.experience, "exp-b", "Reverted", "Do B.", "2026-11-02T00:00:00+00:00")
        _write_record(self.experience, "exp-c", "Active", "Do C.", "2026-11-03T00:00:00+00:00")
        (self.bootstrap_dir / "absorbed.json").write_text(json.dumps({"records": ["exp-a"]}), encoding="utf-8")
        (self.experience / "reverted.jsonl").write_text(
            json.dumps({"record": "exp-b", "reason": "metric regressed"}) + "\n", encoding="utf-8"
        )
        meta = living_soul.compile_soul()
        self.assertEqual(meta["records"], ["exp-c"])

    def test_compose_config_wraps_soul_and_persists(self) -> None:
        prefix = Path(self._tmp.name) / "prefix.md"
        suffix = Path(self._tmp.name) / "suffix.md"
        prefix.write_text("Be direct.\n", encoding="utf-8")
        suffix.write_text("# Hermes Environment\n", encoding="utf-8")
        living_soul.write_compose_config(str(prefix), str(suffix))
        living_soul.compile_soul()
        text = living_soul.current_path().read_text(encoding="utf-8")
        self.assertTrue(text.startswith("Be direct.\n\n# SOUL.md"))
        self.assertTrue(text.rstrip().endswith("# Hermes Environment"))

    def test_rollback_and_link_into_hermes_home(self) -> None:
        living_soul.compile_soul()
        _write_record(self.experience, "exp-a", "First", "Do A.", "2026-11-01T00:00:00+00:00")
        living_soul.compile_soul()
        hermes_home = Path(self._tmp.name) / "hermes"
        link = living_soul.link_into(hermes_home)
        self.assertIn("Do A.", link.read_text(encoding="utf-8"))
        living_soul.rollback(1)
        self.assertNotIn("Do A.", link.read_text(encoding="utf-8"))
        self.assertEqual(living_soul.current_generation()["generation"], 1)

    def test_compile_journals_generation_without_soul_text(self) -> None:
        living_soul.compile_soul()
        event = journal.read_events(improve_dir())[-1]
        self.assertEqual(event["type"], "soul_compiled")
        self.assertEqual(event["payload"]["generation"], 1)
        self.assertNotIn("Bootstrap voice", json.dumps(event))


if __name__ == "__main__":
    unittest.main()
