#!/usr/bin/env python3
"""Tests for alignment spec generation and skill loading."""

from __future__ import annotations

import unittest
from pathlib import Path

from core.alignment_spec import (
    SKILLS_PLACEHOLDER,
    AlignmentSpecCreator,
)


class AlignmentSpecPlaceholderValidationTests(unittest.TestCase):
    def test_seed_must_contain_skills_placeholder_exactly_once(self) -> None:
        creator = AlignmentSpecCreator.__new__(AlignmentSpecCreator)

        def fake_seed() -> str:
            content = f"skills: {SKILLS_PLACEHOLDER}"
            count = content.count(SKILLS_PLACEHOLDER)
            if count != 1:
                raise ValueError(
                    f"Alignment seed must contain placeholder "
                    f"'{SKILLS_PLACEHOLDER}' exactly once; found {count}."
                )
            return content

        creator._load_seed = fake_seed  # type: ignore[assignment]
        result = creator._load_seed()
        self.assertEqual(result.count(SKILLS_PLACEHOLDER), 1)

    def test_seed_with_missing_skills_placeholder_rejected(self) -> None:
        creator = AlignmentSpecCreator.__new__(AlignmentSpecCreator)

        def fake_seed() -> str:
            content = "no skills placeholder"
            count = content.count(SKILLS_PLACEHOLDER)
            if count != 1:
                raise ValueError(
                    f"Alignment seed must contain placeholder "
                    f"'{SKILLS_PLACEHOLDER}' exactly once; found {count}."
                )
            return content

        creator._load_seed = fake_seed  # type: ignore[assignment]
        with self.assertRaises(ValueError) as ctx:
            creator._load_seed()
        self.assertIn("found 0", str(ctx.exception))

    def test_seed_with_multiple_skills_placeholders_rejected(self) -> None:
        creator = AlignmentSpecCreator.__new__(AlignmentSpecCreator)

        def fake_seed() -> str:
            content = f"{SKILLS_PLACEHOLDER} {SKILLS_PLACEHOLDER}"
            count = content.count(SKILLS_PLACEHOLDER)
            if count != 1:
                raise ValueError(
                    f"Alignment seed must contain placeholder "
                    f"'{SKILLS_PLACEHOLDER}' exactly once; found {count}."
                )
            return content

        creator._load_seed = fake_seed  # type: ignore[assignment]
        with self.assertRaises(ValueError) as ctx:
            creator._load_seed()
        self.assertIn("found 2", str(ctx.exception))


class CLISubcommandTests(unittest.TestCase):
    def test_skill_commands_registered(self) -> None:
        """Skill and alignment CLI commands must be registered."""
        from core.cli import _build_parser
        parser = _build_parser()
        # Collect registered subcommand names
        subparser_action = None
        for action in parser._subparsers._group_actions:
            if action.dest == "command":
                subparser_action = action
                break
        self.assertIsNotNone(subparser_action)
        registered = set(subparser_action.choices.keys())  # type: ignore[union-attr]
        # Skill commands
        self.assertIn("build-skills", registered)
        self.assertIn("enhance-skill", registered)
        # Alignment command
        self.assertIn("build-alignment-spec", registered)
        # Retired commands
        self.assertNotIn("build-agents", registered)
        self.assertNotIn("build-soul", registered)


class ActualSeedPlaceholderTests(unittest.TestCase):
    def test_seed_file_contains_skills_placeholder_exactly_once(self) -> None:
        """The on-disk seed.md must contain the skills placeholder exactly once."""
        from core.config import ROOT_DIR
        seed_path = ROOT_DIR / "profiles" / "alignment" / "prompts" / "seed.md"
        content = seed_path.read_text(encoding="utf-8")
        self.assertEqual(
            content.count(SKILLS_PLACEHOLDER),
            1,
            f"seed.md must contain '{SKILLS_PLACEHOLDER}' exactly once",
        )

    def test_seed_file_has_no_agent_souls_section(self) -> None:
        """The on-disk seed.md must not reference agent souls."""
        from core.config import ROOT_DIR
        seed_path = ROOT_DIR / "profiles" / "alignment" / "prompts" / "seed.md"
        content = seed_path.read_text(encoding="utf-8").lower()
        self.assertNotIn("agent soul", content)
        self.assertNotIn("agent_souls", content)


class RetainedTranslationLayerTests(unittest.TestCase):
    def test_spec_owns_verification_and_translation_layer_is_retained(self) -> None:
        """The spec no longer consumes agent souls; the translation layer
        artifacts remain owned by build-translation-layer."""
        source = Path("core/alignment_spec.py").read_text(encoding="utf-8")
        self.assertNotIn("AGENTS_DIR", source)
        self.assertNotIn("PLAN_FILE", source)
        self.assertNotIn("agent_plan", source)
        self.assertNotIn("persona_map", source)
        self.assertNotIn("agent_souls", source)
        # Translation layer is not an input to the spec.
        self.assertNotIn("translation_layer_creator", source)
        # But it is still generated and exported by the repo.
        self.assertTrue(
            Path("core/translation_layer_creator.py").exists(),
            "translation layer creator must be retained",
        )
        self.assertTrue(
            Path("profiles/alignment/prompts/soul_seed.md").exists(),
            "soul seed must be retained",
        )
        self.assertTrue(
            Path("profiles/alignment/prompts/interaction_posture_seed.md").exists(),
            "posture seed must be retained",
        )


if __name__ == "__main__":
    unittest.main()
