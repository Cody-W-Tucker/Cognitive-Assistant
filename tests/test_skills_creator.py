#!/usr/bin/env python3
"""Tests for declared per-skill generation helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.config import Config, SkillSpec
from core.skills_creator import SkillsCreator


class SkillsCreatorContractTests(unittest.TestCase):
    def _creator(self) -> SkillsCreator:
        creator = SkillsCreator.__new__(SkillsCreator)
        creator.config = Config.from_profile("existential")
        return creator

    def test_scoped_context_uses_only_declared_headings(self) -> None:
        creator = self._creator()
        spec = SkillSpec(
            slug="example-skill",
            source_group="example-group",
            source_headings=("Core Frame", "Constraint Map"),
        )
        sections = {
            "Core Frame": "core content",
            "Constraint Map": "constraint content",
            "Open Questions": "excluded content",
        }

        context = creator._build_scoped_bio_content(spec, sections)

        self.assertIn('declared_slug="example-skill"', context)
        self.assertIn("## Core Frame\ncore content", context)
        self.assertIn("## Constraint Map\nconstraint content", context)
        self.assertNotIn("excluded content", context)

    def test_cleanup_removes_only_stale_generated_current_profile_skills(self) -> None:
        creator = self._creator()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            stale = root / "existential" / "stale-skill" / "SKILL.md"
            current = root / "existential" / "current-skill" / "SKILL.md"
            other_profile = root / "operational" / "other-skill" / "SKILL.md"
            for path in (stale, current, other_profile):
                path.parent.mkdir(parents=True, exist_ok=True)
            stale.write_text(
                "---\nname: stale-skill\nsource_profile: existential\n---\n",
                encoding="utf-8",
            )
            current.write_text(
                "---\nname: current-skill\nsource_profile: existential\n---\n",
                encoding="utf-8",
            )
            other_profile.write_text(
                "---\nname: other-skill\nsource_profile: operational\n---\n",
                encoding="utf-8",
            )

            creator._cleanup_stale_generated_skills(root, {"current-skill"})

            self.assertFalse(stale.exists())
            self.assertTrue(current.exists())
            self.assertTrue(other_profile.exists())


if __name__ == "__main__":
    unittest.main()
