#!/usr/bin/env python3
"""Tests for crystallization artifact management and rule rendering."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core import adaptation_rules
from core.config import Config


class AdaptationRulesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = Config.from_profile("operational")

    def test_normalize_input_payload_accepts_object_wrapper(self) -> None:
        payload = {"adaptations": [{"id": "adapt-1", "precision_weight": 0.9}]}
        normalized = adaptation_rules.normalize_input_payload(payload)
        self.assertEqual(normalized[0]["id"], "adapt-1")

    def test_merge_adaptations_marks_recurrence_after_capture(self) -> None:
        existing = [
            {
                "id": "adapt-1",
                "precision_weight": 0.9,
                "captured_upstream": True,
                "status": "applied",
                "times_seen": 1,
            }
        ]
        incoming = [{"id": "adapt-1", "precision_weight": 0.95}]
        merged = adaptation_rules.merge_adaptations(
            existing, incoming, profile="operational"
        )
        self.assertEqual(merged[0]["status"], "confirmed")
        self.assertFalse(merged[0]["captured_upstream"])
        self.assertEqual(merged[0]["times_seen"], 2)
        self.assertTrue(merged[0]["recurred_after_capture"])

    def test_render_rule_overlay_includes_active_rule_details(self) -> None:
        overlay = adaptation_rules.render_rule_overlay(
            [
                {
                    "id": "adapt-1",
                    "type": "skill_override",
                    "source": "Hermes",
                    "observed_need": "Need narrower file handling guidance",
                    "precision_weight": 0.91,
                    "proposed_update": {"target": "skills", "value": "Prefer explicit file constraints"},
                }
            ]
        )
        self.assertIn("<adaptation_rules>", overlay)
        self.assertIn("adapt-1", overlay)
        self.assertIn("Need narrower file handling guidance", overlay)

    def test_build_skill_adaptations_groups_by_skill(self) -> None:
        payload = adaptation_rules.build_skill_adaptations(
            self.config,
            [
                {
                    "id": "adapt-1",
                    "precision_weight": 0.91,
                    "proposed_update": {
                        "target": "skill",
                        "skill": "gws-drive",
                        "action": "prepend",
                        "content": "Prefer explicit read-only store handling.",
                    },
                },
                {
                    "id": "adapt-2",
                    "precision_weight": 0.88,
                    "proposed_update": {
                        "target": "global_skill_preamble",
                        "content": "Runtime-learned constraints override generic defaults when they conflict.",
                    },
                },
            ],
        )
        self.assertEqual(payload["profile"], "operational")
        self.assertEqual(
            payload["skills"]["gws-drive"]["prepend"],
            ["Prefer explicit read-only store handling."],
        )
        self.assertEqual(
            payload["global"]["prepend"],
            [
                "Runtime-learned constraints override generic defaults when they conflict."
            ],
        )

    def test_write_skill_adaptations_writes_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "skill_adaptations.json"
            original = adaptation_rules.skill_adaptations_path_for_config
            try:
                adaptation_rules.skill_adaptations_path_for_config = lambda _config: out_path
                written = adaptation_rules.write_skill_adaptations(
                    self.config,
                    [
                        {
                            "id": "adapt-1",
                            "precision_weight": 0.9,
                            "proposed_update": {
                                "target": "skill",
                                "skill": "gws-drive",
                                "content": "Prefer explicit read-only store handling.",
                            },
                        }
                    ],
                )
            finally:
                adaptation_rules.skill_adaptations_path_for_config = original

            self.assertEqual(written, out_path)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertIn("gws-drive", payload["skills"])

    def test_mark_adaptations_captured_updates_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_path = Path(tmp_dir) / "crystallization.json"
            artifact = {
                "version": 1,
                "profile": "operational",
                "updated_at": None,
                "adaptations": [
                    {
                        "id": "adapt-1",
                        "precision_weight": 0.8,
                        "status": "confirmed",
                        "captured_upstream": False,
                    }
                ],
            }
            adaptation_rules.write_artifact(artifact_path, artifact)

            original = adaptation_rules.artifact_path_for_config
            try:
                adaptation_rules.artifact_path_for_config = lambda _config: artifact_path
                adaptation_rules.mark_adaptations_captured(
                    self.config,
                    ["adapt-1"],
                    captured_in="build-prompts",
                )
            finally:
                adaptation_rules.artifact_path_for_config = original

            updated = json.loads(artifact_path.read_text(encoding="utf-8"))
            entry = updated["adaptations"][0]
            self.assertTrue(entry["captured_upstream"])
            self.assertEqual(entry["captured_in"], "build-prompts")
            self.assertEqual(entry["status"], "applied")


if __name__ == "__main__":
    unittest.main()
