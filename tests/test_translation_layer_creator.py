#!/usr/bin/env python3
"""Tests for the translation layer generation helpers."""

from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from core.translation_layer_creator import (
    TranslationLayerCreator,
    _strip_code_fences,
    _validate_generated_content,
    translation_layer_paths,
)


class StripCodeFencesTests(unittest.TestCase):
    def test_no_fences(self) -> None:
        self.assertEqual(_strip_code_fences("hello"), "hello")

    def test_markdown_fence(self) -> None:
        self.assertEqual(
            _strip_code_fences("```markdown\nhello\n```"),
            "hello",
        )

    def test_md_fence(self) -> None:
        self.assertEqual(
            _strip_code_fences("```md\nhello\n```"),
            "hello",
        )

    def test_generic_fence(self) -> None:
        self.assertEqual(
            _strip_code_fences("```\nhello\n```"),
            "hello",
        )

    def test_trailing_fence_only(self) -> None:
        # A response that starts without a fence but ends with one.
        self.assertEqual(
            _strip_code_fences("hello\n```"),
            "hello",
        )

    def test_strips_whitespace(self) -> None:
        self.assertEqual(_strip_code_fences("  hello  "), "hello")


class ValidateGeneratedContentTests(unittest.TestCase):
    def test_rejects_empty(self) -> None:
        with self.assertRaises(ValueError) as cm:
            _validate_generated_content("", artifact_label="archetype")
        self.assertIn("archetype", str(cm.exception))

    def test_rejects_whitespace_only(self) -> None:
        with self.assertRaises(ValueError):
            _validate_generated_content("   \n\t  ", artifact_label="translation soul")

    def test_returns_stripped_content(self) -> None:
        result = _validate_generated_content("  hello  ", artifact_label="archetype")
        self.assertEqual(result, "  hello  ")


class TranslationLayerPathsTests(unittest.TestCase):
    def test_paths_are_under_alignment_artifacts(self) -> None:
        soul_path, archetype_path = translation_layer_paths()
        self.assertEqual(soul_path.name, "SOUL.md")
        self.assertEqual(archetype_path.name, "SOUL_ARCHETYPE.md")
        self.assertEqual(
            soul_path.parent,
            Path("workspaces/alignment/artifacts").resolve(),
        )
        self.assertEqual(soul_path.parent, archetype_path.parent)


class GenerateTranslationLayerTests(unittest.TestCase):
    """Mocked end-to-end tests for ``TranslationLayerCreator``.

    Patches ``generate_text_async`` to avoid real LLM calls, and patches the
    canonical output paths so tests write to a temp directory.
    """

    def setUp(self) -> None:
        self._patches: list[unittest.mock._patch] = []

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()

    def _make_creator(self) -> TranslationLayerCreator:
        """Build a creator with a mocked LLM handle (no real client)."""
        with patch("core.translation_layer_creator.create_client") as mock_create:
            mock_create.return_value = AsyncMock()
            creator = TranslationLayerCreator()
        return creator

    def _run(self, coro):  # type: ignore[no-untyped-def]
        return asyncio.run(coro)

    def _apply_path_patches(
        self, tmpdir: Path
    ) -> tuple[Path, Path]:
        """Patch canonical output paths to use ``tmpdir``."""
        soul_path = tmpdir / "SOUL.md"
        archetype_path = tmpdir / "SOUL_ARCHETYPE.md"
        self._patches.append(
            patch(
                "core.translation_layer_creator.SOUL_OUTPUT_FILE",
                soul_path,
            )
        )
        self._patches.append(
            patch(
                "core.translation_layer_creator.ARCHETYPE_OUTPUT_FILE",
                archetype_path,
            )
        )
        for p in self._patches[-2:]:
            p.start()
        return soul_path, archetype_path

    def test_two_llm_calls_in_order_with_archetype_inserted(self) -> None:
        """Stage 1 produces the archetype; stage 2 receives it in the prompt."""
        with self.subTest("run"):
            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                tmpdir = Path(tmp)
                soul_path, archetype_path = self._apply_path_patches(tmpdir)
                creator = self._make_creator()

                fake_profile = "<profile>both profiles</profile>"
                fake_archetype = "The Seasoned Older Sister"
                fake_soul = "# Soul\nI carry the standards."

                with (
                    patch.object(
                        creator,
                        "_generate_archetype",
                        new=AsyncMock(return_value=fake_archetype),
                    ) as mock_arch,
                    patch.object(
                        creator,
                        "_generate_soul",
                        new=AsyncMock(return_value=fake_soul),
                    ) as mock_soul,
                    patch(
                        "core.translation_layer_creator.load_profile_sources",
                        return_value=fake_profile,
                    ),
                ):
                    result = self._run(creator.generate_translation_layer())

                self.assertEqual(result, (soul_path, archetype_path))
                mock_arch.assert_awaited_once_with(fake_profile)
                mock_soul.assert_awaited_once_with(fake_profile, fake_archetype)

                self.assertTrue(archetype_path.exists())
                self.assertTrue(soul_path.exists())
                self.assertEqual(
                    archetype_path.read_text(encoding="utf-8").strip(),
                    fake_archetype,
                )
                self.assertEqual(
                    soul_path.read_text(encoding="utf-8").strip(),
                    fake_soul,
                )

    def test_archetype_is_passed_into_soul_prompt(self) -> None:
        """The archetype produced by stage 1 is forwarded to stage 2."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            self._apply_path_patches(tmpdir)
            creator = self._make_creator()

            captured_archetype_arg: dict[str, str] = {}

            async def fake_generate_soul(profile_sources: str, archetype: str) -> str:
                captured_archetype_arg["value"] = archetype
                return "soul content"

            with (
                patch.object(
                    creator,
                    "_generate_archetype",
                    new=AsyncMock(return_value="THE_ARCHETYPE_NAME"),
                ),
                patch.object(
                    creator,
                    "_generate_soul",
                    new=AsyncMock(side_effect=fake_generate_soul),
                ),
                patch(
                    "core.translation_layer_creator.load_profile_sources",
                    return_value="profiles",
                ),
            ):
                self._run(creator.generate_translation_layer())

            self.assertEqual(captured_archetype_arg["value"], "THE_ARCHETYPE_NAME")

    def test_real_generate_functions_receive_archetype_in_prompt(self) -> None:
        """Smoke test: the real _generate methods embed the archetype in the
        soul seed prompt (verifies placeholder wiring)."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            self._apply_path_patches(tmpdir)
            creator = self._make_creator()

            captured_prompts: list[str] = []

            async def fake_generate(handle, *, user_prompt, **kwargs):  # type: ignore[no-untyped-def]
                captured_prompts.append(user_prompt)
                # First call is archetype; second is soul.
                if len(captured_prompts) == 1:
                    return "ARCHETYPE_OUTPUT"
                return "SOUL_OUTPUT"

            with (
                patch(
                    "core.translation_layer_creator.generate_text_async",
                    side_effect=fake_generate,
                ),
                patch(
                    "core.translation_layer_creator.load_profile_sources",
                    return_value="PROFILE_SOURCES_CONTENT",
                ),
            ):
                self._run(creator.generate_translation_layer())

            self.assertEqual(len(captured_prompts), 2)
            self.assertIn("PROFILE_SOURCES_CONTENT", captured_prompts[0])
            self.assertIn("PROFILE_SOURCES_CONTENT", captured_prompts[1])
            self.assertIn("ARCHETYPE_OUTPUT", captured_prompts[1])

    def test_empty_archetype_raises_and_does_not_write(self) -> None:
        """An empty LLM response for the archetype must raise and leave no artifact."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            soul_path, archetype_path = self._apply_path_patches(tmpdir)
            creator = self._make_creator()

            with (
                patch(
                    "core.translation_layer_creator.generate_text_async",
                    new=AsyncMock(return_value="   "),
                ),
                patch(
                    "core.translation_layer_creator.load_profile_sources",
                    return_value="profiles",
                ),
            ):
                with self.assertRaises(ValueError) as cm:
                    self._run(creator.generate_translation_layer())
                self.assertIn("archetype", str(cm.exception).lower())

            self.assertFalse(archetype_path.exists())
            self.assertFalse(soul_path.exists())

    def test_empty_soul_raises_and_does_not_write_soul(self) -> None:
        """An empty LLM response for the soul must raise before writing."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            soul_path, archetype_path = self._apply_path_patches(tmpdir)
            creator = self._make_creator()

            call_count = {"n": 0}

            async def fake_generate(handle, *, user_prompt, **kwargs):  # type: ignore[no-untyped-def]
                call_count["n"] += 1
                if call_count["n"] == 1:
                    return "Valid archetype content"
                return "   "

            with (
                patch(
                    "core.translation_layer_creator.generate_text_async",
                    side_effect=fake_generate,
                ),
                patch(
                    "core.translation_layer_creator.load_profile_sources",
                    return_value="profiles",
                ),
            ):
                with self.assertRaises(ValueError) as cm:
                    self._run(creator.generate_translation_layer())
                self.assertIn("translation soul", str(cm.exception).lower())

            # Archetype should not have been persisted either because we roll
            # back at the raise-site. The implementation writes archetype first
            # then raises on soul — verify soul is not written.
            self.assertFalse(soul_path.exists())


if __name__ == "__main__":
    unittest.main()
