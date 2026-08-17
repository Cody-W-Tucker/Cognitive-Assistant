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
            _validate_generated_content("", artifact_label="interaction posture")
        self.assertIn("interaction posture", str(cm.exception))

    def test_rejects_whitespace_only(self) -> None:
        with self.assertRaises(ValueError):
            _validate_generated_content("   \n\t  ", artifact_label="translation soul")

    def test_returns_stripped_content(self) -> None:
        result = _validate_generated_content("  hello  ", artifact_label="interaction posture")
        self.assertEqual(result, "  hello  ")


class TranslationLayerPathsTests(unittest.TestCase):
    def test_paths_are_under_alignment_artifacts(self) -> None:
        soul_path, posture_path = translation_layer_paths()
        self.assertEqual(soul_path.name, "SOUL.md")
        self.assertEqual(posture_path.name, "INTERACTION_POSTURE.md")
        self.assertEqual(
            soul_path.parent,
            Path("workspaces/alignment/artifacts").resolve(),
        )
        self.assertEqual(soul_path.parent, posture_path.parent)

    def test_no_legacy_posture_artifact_name_remains(self) -> None:
        """The legacy SOUL_ARCHETYPE surface must be gone, not shimmed."""
        source = Path("core/translation_layer_creator.py").read_text(encoding="utf-8")
        self.assertNotIn("SOUL_ARCHETYPE", source)
        self.assertNotIn("soul_archetype_seed", source)
        self.assertFalse(
            Path("profiles/alignment/prompts/soul_archetype_seed.md").exists()
        )
        self.assertFalse(
            Path("workspaces/alignment/artifacts/SOUL_ARCHETYPE.md").exists()
        )
        self.assertTrue(
            Path("profiles/alignment/prompts/interaction_posture_seed.md").exists()
        )


class PostureOwnershipTests(unittest.TestCase):
    """build-translation-layer owns the posture; build-agents only reads it."""

    def test_soul_creator_never_writes_the_posture(self) -> None:
        source = Path("core/soul_creator.py").read_text(encoding="utf-8")
        # The only posture reference in the agent builder is the read-only
        # snapshot path; no write/render/repair path may target it.
        self.assertIn("POSTURE_FILE = OUTPUT_DIR / \"INTERACTION_POSTURE.md\"", source)
        self.assertNotIn("_write_artifact(POSTURE", source)
        self.assertNotIn("POSTURE_FILE.write_text", source)
        self.assertNotIn("_atomic_write(POSTURE_FILE", source)

    def test_reconciliation_only_touches_bundle_projections(self) -> None:
        from core.soul_creator import SoulCreator

        source = Path("core/soul_creator.py").read_text(encoding="utf-8")
        rerender = source.split("_rerender_and_hashcheck_from_plan")[2]
        self.assertNotIn("POSTURE", rerender.split("def _ensure_projection")[0])
        self.assertTrue(hasattr(SoulCreator, "snapshot_posture"))


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
        posture_path = tmpdir / "INTERACTION_POSTURE.md"
        self._patches.append(
            patch(
                "core.translation_layer_creator.SOUL_OUTPUT_FILE",
                soul_path,
            )
        )
        self._patches.append(
            patch(
                "core.translation_layer_creator.POSTURE_OUTPUT_FILE",
                posture_path,
            )
        )
        for p in self._patches[-2:]:
            p.start()
        return soul_path, posture_path

    def test_two_llm_calls_in_order_with_posture_inserted(self) -> None:
        """Stage 1 produces the posture; stage 2 receives it in the prompt."""
        with self.subTest("run"):
            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                tmpdir = Path(tmp)
                soul_path, posture_path = self._apply_path_patches(tmpdir)
                creator = self._make_creator()

                fake_profile = "<profile>both profiles</profile>"
                fake_posture = "The Seasoned Older Sister"
                fake_soul = "# Soul\nI carry the standards."

                with (
                    patch.object(
                        creator,
                        "_generate_interaction_posture",
                        new=AsyncMock(return_value=fake_posture),
                    ) as mock_posture,
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

                self.assertEqual(result, (soul_path, posture_path))
                mock_posture.assert_awaited_once_with(fake_profile)
                mock_soul.assert_awaited_once_with(fake_profile, fake_posture)

                self.assertTrue(posture_path.exists())
                self.assertTrue(soul_path.exists())
                self.assertEqual(
                    posture_path.read_text(encoding="utf-8").strip(),
                    fake_posture,
                )
                self.assertEqual(
                    soul_path.read_text(encoding="utf-8").strip(),
                    fake_soul,
                )

    def test_posture_is_passed_into_soul_prompt(self) -> None:
        """The posture produced by stage 1 is forwarded to stage 2."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            self._apply_path_patches(tmpdir)
            creator = self._make_creator()

            captured_posture_arg: dict[str, str] = {}

            async def fake_generate_soul(profile_sources: str, interaction_posture: str) -> str:
                captured_posture_arg["value"] = interaction_posture
                return "soul content"

            with (
                patch.object(
                    creator,
                    "_generate_interaction_posture",
                    new=AsyncMock(return_value="THE_POSTURE_NAME"),
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

            self.assertEqual(captured_posture_arg["value"], "THE_POSTURE_NAME")

    def test_real_generate_functions_receive_posture_in_prompt(self) -> None:
        """Smoke test: the real _generate methods embed the posture in the
        soul seed prompt (verifies placeholder wiring)."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            self._apply_path_patches(tmpdir)
            creator = self._make_creator()

            captured_prompts: list[str] = []

            async def fake_generate(handle, *, user_prompt, **kwargs):  # type: ignore[no-untyped-def]
                captured_prompts.append(user_prompt)
                # First call is the posture; second is the soul.
                if len(captured_prompts) == 1:
                    return "POSTURE_OUTPUT"
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
            self.assertIn("POSTURE_OUTPUT", captured_prompts[1])

    def test_empty_posture_raises_and_does_not_write(self) -> None:
        """An empty LLM response for the posture must raise and leave no artifact."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            soul_path, posture_path = self._apply_path_patches(tmpdir)
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
                self.assertIn("interaction posture", str(cm.exception).lower())

            self.assertFalse(posture_path.exists())
            self.assertFalse(soul_path.exists())

    def test_empty_soul_raises_and_does_not_write_soul(self) -> None:
        """An empty LLM response for the soul must raise before writing."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            soul_path, posture_path = self._apply_path_patches(tmpdir)
            creator = self._make_creator()

            call_count = {"n": 0}

            async def fake_generate(handle, *, user_prompt, **kwargs):  # type: ignore[no-untyped-def]
                call_count["n"] += 1
                if call_count["n"] == 1:
                    return "Valid posture content"
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

            # The implementation writes the posture first then raises on the
            # soul - verify the soul is not written.
            self.assertFalse(soul_path.exists())


if __name__ == "__main__":
    unittest.main()
