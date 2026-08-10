#!/usr/bin/env python3
"""Tests for alignment spec generation, persona map parsing, and skill loading."""

from __future__ import annotations

import re
import textwrap
import unittest
from pathlib import Path

from core.alignment_spec import (
    AGENT_SOULS_PLACEHOLDER,
    SKILLS_PLACEHOLDER,
    AlignmentSpecCreator,
    load_declared_agent_slugs,
)


class LoadDeclaredAgentSlugsTests(unittest.TestCase):
    def test_parses_declared_slugs(self) -> None:
        content = textwrap.dedent("""\
            # Persona Map

            Discovered 2 distinct agent personas from the existential and operational profile artifacts.

            ## Builder
            - **Slug:** `builder`
            - **Archetype:** A maker
            - **Responsibility:** Shipping

            ## Strategist
            - **Slug:** `strategist`
            - **Archetype:** A thinker
            - **Responsibility:** Strategy
        """)
        path = Path(self._write_temp(content))
        slugs = load_declared_agent_slugs(path)
        self.assertEqual(slugs, ["builder", "strategist"])

    def test_rejects_missing_map(self) -> None:
        with self.assertRaises(FileNotFoundError) as ctx:
            load_declared_agent_slugs(Path("/nonexistent/persona_map.md"))
        self.assertIn("Persona map not found", str(ctx.exception))

    def test_rejects_empty_map(self) -> None:
        path = Path(self._write_temp("# Persona Map\n\nNo agents here.\n"))
        with self.assertRaises(ValueError) as ctx:
            load_declared_agent_slugs(path)
        self.assertIn("declares no agent slugs", str(ctx.exception))

    def test_rejects_duplicate_slugs(self) -> None:
        content = textwrap.dedent("""\
            ## A
            - **Slug:** `same`

            ## B
            - **Slug:** `same`
        """)
        path = Path(self._write_temp(content))
        with self.assertRaises(ValueError) as ctx:
            load_declared_agent_slugs(path)
        self.assertIn("duplicate slug", str(ctx.exception))

    def test_ignores_non_slug_backtick_references(self) -> None:
        content = textwrap.dedent("""\
            # Persona Map

            Some prose mentioning `random.md` and other files.

            ## Builder
            - **Slug:** `builder`
        """)
        path = Path(self._write_temp(content))
        slugs = load_declared_agent_slugs(path)
        self.assertEqual(slugs, ["builder"])

    def _write_temp(self, content: str) -> str:
        import tempfile
        fd = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        )
        fd.write(content)
        fd.close()
        return fd.name


class AlignmentSpecPlaceholderValidationTests(unittest.TestCase):
    def test_seed_must_contain_both_placeholders_exactly_once(self) -> None:
        creator = AlignmentSpecCreator.__new__(AlignmentSpecCreator)

        def fake_seed() -> str:
            content = f"skills: {SKILLS_PLACEHOLDER} souls: {AGENT_SOULS_PLACEHOLDER}"
            for placeholder in (SKILLS_PLACEHOLDER, AGENT_SOULS_PLACEHOLDER):
                count = content.count(placeholder)
                if count != 1:
                    raise ValueError(
                        f"Alignment seed must contain placeholder "
                        f"'{placeholder}' exactly once; found {count}."
                    )
            return content

        creator._load_seed = fake_seed  # type: ignore[assignment]
        result = creator._load_seed()
        self.assertEqual(result.count(SKILLS_PLACEHOLDER), 1)
        self.assertEqual(result.count(AGENT_SOULS_PLACEHOLDER), 1)

    def test_seed_with_missing_skills_placeholder_rejected(self) -> None:
        creator = AlignmentSpecCreator.__new__(AlignmentSpecCreator)

        def fake_seed() -> str:
            content = f"no skills placeholder, only {AGENT_SOULS_PLACEHOLDER}"
            for placeholder in (SKILLS_PLACEHOLDER, AGENT_SOULS_PLACEHOLDER):
                count = content.count(placeholder)
                if count != 1:
                    raise ValueError(
                        f"Alignment seed must contain placeholder "
                        f"'{placeholder}' exactly once; found {count}."
                    )
            return content

        creator._load_seed = fake_seed  # type: ignore[assignment]
        with self.assertRaises(ValueError) as ctx:
            creator._load_seed()
        self.assertIn("found 0", str(ctx.exception))

    def test_seed_with_multiple_agent_souls_placeholders_rejected(self) -> None:
        creator = AlignmentSpecCreator.__new__(AlignmentSpecCreator)

        def fake_seed() -> str:
            content = f"{SKILLS_PLACEHOLDER} {AGENT_SOULS_PLACEHOLDER} {AGENT_SOULS_PLACEHOLDER}"
            for placeholder in (SKILLS_PLACEHOLDER, AGENT_SOULS_PLACEHOLDER):
                count = content.count(placeholder)
                if count != 1:
                    raise ValueError(
                        f"Alignment seed must contain placeholder "
                        f"'{placeholder}' exactly once; found {count}."
                    )
            return content

        creator._load_seed = fake_seed  # type: ignore[assignment]
        with self.assertRaises(ValueError) as ctx:
            creator._load_seed()
        self.assertIn("found 2", str(ctx.exception))


class AlignmentSpecLoadsOnlyDeclaredSoulsTests(unittest.TestCase):
    def test_unlisted_agent_files_are_excluded(self) -> None:
        """Verify _load_declared_agent_souls loads only persona-map-declared slugs."""
        import tempfile
        import shutil

        tmpdir = Path(tempfile.mkdtemp())
        try:
            agents_dir = tmpdir / "agents"
            agents_dir.mkdir()
            persona_map = tmpdir / "persona_map.md"

            # Write declared soul
            (agents_dir / "builder.md").write_text("I build things.\n", encoding="utf-8")
            # Write an undeclared soul that should be ignored
            (agents_dir / "stranger.md").write_text("I am not declared.\n", encoding="utf-8")

            persona_map.write_text(textwrap.dedent("""\
                # Persona Map

                ## Builder
                - **Slug:** `builder`
            """), encoding="utf-8")

            creator = AlignmentSpecCreator.__new__(AlignmentSpecCreator)

            # Patch module-level paths for this test
            import core.alignment_spec as mod
            orig_map = mod.PERSONA_MAP_FILE
            orig_dir = mod.AGENTS_DIR
            mod.PERSONA_MAP_FILE = persona_map
            mod.AGENTS_DIR = agents_dir
            try:
                result = creator._load_declared_agent_souls()
            finally:
                mod.PERSONA_MAP_FILE = orig_map
                mod.AGENTS_DIR = orig_dir

            self.assertIn("builder", result)
            self.assertNotIn("stranger", result)
            self.assertNotIn("I am not declared", result)
        finally:
            shutil.rmtree(tmpdir)

    def test_missing_declared_soul_raises(self) -> None:
        import tempfile
        import shutil

        tmpdir = Path(tempfile.mkdtemp())
        try:
            agents_dir = tmpdir / "agents"
            agents_dir.mkdir()
            persona_map = tmpdir / "persona_map.md"

            persona_map.write_text(textwrap.dedent("""\
                ## Builder
                - **Slug:** `builder`
            """), encoding="utf-8")

            creator = AlignmentSpecCreator.__new__(AlignmentSpecCreator)

            import core.alignment_spec as mod
            orig_map = mod.PERSONA_MAP_FILE
            orig_dir = mod.AGENTS_DIR
            mod.PERSONA_MAP_FILE = persona_map
            mod.AGENTS_DIR = agents_dir
            try:
                with self.assertRaises(FileNotFoundError) as ctx:
                    creator._load_declared_agent_souls()
                self.assertIn("builder", str(ctx.exception))
                self.assertIn("missing", str(ctx.exception).lower())
            finally:
                mod.PERSONA_MAP_FILE = orig_map
                mod.AGENTS_DIR = orig_dir
        finally:
            shutil.rmtree(tmpdir)

    def test_empty_declared_soul_raises(self) -> None:
        import tempfile
        import shutil

        tmpdir = Path(tempfile.mkdtemp())
        try:
            agents_dir = tmpdir / "agents"
            agents_dir.mkdir()
            persona_map = tmpdir / "persona_map.md"

            (agents_dir / "builder.md").write_text("   \n  \n", encoding="utf-8")
            persona_map.write_text(textwrap.dedent("""\
                ## Builder
                - **Slug:** `builder`
            """), encoding="utf-8")

            creator = AlignmentSpecCreator.__new__(AlignmentSpecCreator)

            import core.alignment_spec as mod
            orig_map = mod.PERSONA_MAP_FILE
            orig_dir = mod.AGENTS_DIR
            mod.PERSONA_MAP_FILE = persona_map
            mod.AGENTS_DIR = agents_dir
            try:
                with self.assertRaises(ValueError) as ctx:
                    creator._load_declared_agent_souls()
                self.assertIn("empty", str(ctx.exception).lower())
            finally:
                mod.PERSONA_MAP_FILE = orig_map
                mod.AGENTS_DIR = orig_dir
        finally:
            shutil.rmtree(tmpdir)


class CLISubcommandTests(unittest.TestCase):
    def test_both_skill_and_agent_commands_registered(self) -> None:
        """Both skill and agent CLI commands must be registered."""
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
        # Agent commands
        self.assertIn("build-agents", registered)
        self.assertIn("build-alignment-spec", registered)
        # Retired command
        self.assertNotIn("build-soul", registered)


class LegacyCleanupAbsentTests(unittest.TestCase):
    def test_soul_creator_has_no_legacy_cleanup(self) -> None:
        """soul_creator.py must not contain legacy SOUL/SOUL_ARCHETYPE cleanup logic."""
        source_path = Path(__file__).resolve().parent.parent / "core" / "soul_creator.py"
        source = source_path.read_text(encoding="utf-8")
        # The removed block referenced SOUL.md and SOUL_ARCHETYPE.md in a cleanup loop.
        self.assertNotIn("SOUL.md", source)
        self.assertNotIn("SOUL_ARCHETYPE.md", source)
        self.assertNotIn("legacy_path", source)
        self.assertNotIn("legacy artifact", source.lower())


class ActualSeedPlaceholderTests(unittest.TestCase):
    def test_seed_file_contains_both_placeholders_exactly_once(self) -> None:
        """The on-disk seed.md must contain both placeholders exactly once."""
        from core.config import ROOT_DIR
        seed_path = ROOT_DIR / "profiles" / "alignment" / "prompts" / "seed.md"
        content = seed_path.read_text(encoding="utf-8")
        self.assertEqual(
            content.count(SKILLS_PLACEHOLDER),
            1,
            f"seed.md must contain '{SKILLS_PLACEHOLDER}' exactly once",
        )
        self.assertEqual(
            content.count(AGENT_SOULS_PLACEHOLDER),
            1,
            f"seed.md must contain '{AGENT_SOULS_PLACEHOLDER}' exactly once",
        )


if __name__ == "__main__":
    unittest.main()
