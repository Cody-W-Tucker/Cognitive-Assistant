#!/usr/bin/env python3
"""Tests for catalog-constrained agent archetype selection and soul generation."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from typing import Dict
from unittest.mock import AsyncMock, patch

from core.archetype_catalog import ArchetypeSpec, load_archetype_catalog
from core.soul_creator import (
    SelectedArchetype,
    SoulCreator,
    build_persona_map_markdown,
    parse_archetype_selection_response,
)


def _make_test_catalog() -> Dict[str, ArchetypeSpec]:
    """Build a minimal test catalog."""
    return {
        "pattern-scout": ArchetypeSpec(
            slug="pattern-scout",
            name="Pattern Scout",
            purpose="Own the possibility surface",
            job_to_be_done="Make the adjacent possible legible",
            outcome="The user sees the field more clearly",
            scope_triggers=["An ambiguous situation"],
            scope_outputs=["Pattern reads"],
            out_of_scope=["Grounding claims in evidence"],
            authority_can_decide=["How a situation is framed"],
            authority_must_defer=["Whether a proposed frame is true"],
            approval_boundaries="User decides what to move toward",
            quality_expectations="Every pattern named must be recognizable",
            evidence_expectations="Ground pattern reads in durable signals",
            canonical_skills=["mode-detection", "scope-framing"],
        ),
        "constraint-reader": ArchetypeSpec(
            slug="constraint-reader",
            name="Constraint Reader",
            purpose="Own the grounded surface",
            job_to_be_done="Make the real object visible",
            outcome="Next move is grounded in what is actually the case",
            scope_triggers=["A failure where cause is unclear"],
            scope_outputs=["Causal reads"],
            out_of_scope=["Naming the frame or adjacent possibilities"],
            authority_can_decide=["Whether diagnosis is sufficient"],
            authority_must_defer=["Which frame best captures the situation"],
            approval_boundaries="User decides what to do with the diagnosis",
            quality_expectations="Every claim must trace to a source",
            evidence_expectations="Ground in observable evidence",
            canonical_skills=["diagnose-before-patching", "verify-before-trust"],
        ),
    }


class ParseArchetypeSelectionResponseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = _make_test_catalog()

    def _make_response(self, agents: list) -> str:
        return json.dumps({"agents": agents})

    def test_valid_single_selection(self) -> None:
        response = self._make_response([
            {
                "archetype": "pattern-scout",
                "calibration": "User defaults to familiar frames",
                "skills": ["mode-detection"],
            }
        ])
        selections = parse_archetype_selection_response(response, self.catalog)
        self.assertEqual(len(selections), 1)
        self.assertEqual(selections[0].slug, "pattern-scout")
        self.assertEqual(selections[0].skills, ["mode-detection"])

    def test_multiple_selections(self) -> None:
        response = self._make_response([
            {
                "archetype": "pattern-scout",
                "calibration": "User defaults to familiar frames",
                "skills": ["mode-detection"],
            },
            {
                "archetype": "constraint-reader",
                "calibration": "User skips diagnosis",
                "skills": ["diagnose-before-patching"],
            },
        ])
        selections = parse_archetype_selection_response(response, self.catalog)
        self.assertEqual(len(selections), 2)
        slugs = {s.slug for s in selections}
        self.assertEqual(slugs, {"pattern-scout", "constraint-reader"})

    def test_strips_code_fences(self) -> None:
        inner = self._make_response([
            {
                "archetype": "pattern-scout",
                "calibration": "Fit",
                "skills": ["mode-detection"],
            }
        ])
        response = f"```json\n{inner}\n```"
        selections = parse_archetype_selection_response(response, self.catalog)
        self.assertEqual(len(selections), 1)

    def test_rejects_unknown_archetype(self) -> None:
        response = self._make_response([
            {
                "archetype": "unknown-archetype",
                "calibration": "Fit",
                "skills": ["mode-detection"],
            }
        ])
        with self.assertRaises(ValueError) as ctx:
            parse_archetype_selection_response(response, self.catalog)
        self.assertIn("unknown archetype", str(ctx.exception).lower())
        self.assertIn("unknown-archetype", str(ctx.exception))

    def test_rejects_unknown_skill(self) -> None:
        response = self._make_response([
            {
                "archetype": "pattern-scout",
                "calibration": "Fit",
                "skills": ["nonexistent-skill"],
            }
        ])
        with self.assertRaises(ValueError) as ctx:
            parse_archetype_selection_response(response, self.catalog)
        self.assertIn("unknown skill", str(ctx.exception).lower())
        self.assertIn("nonexistent-skill", str(ctx.exception))

    def test_rejects_skill_not_in_archetype_canonical(self) -> None:
        """Skills must be drawn from the archetype's declared canonical_skills."""
        response = self._make_response([
            {
                "archetype": "pattern-scout",
                "calibration": "Fit",
                "skills": ["diagnose-before-patching"],  # belongs to constraint-reader
            }
        ])
        with self.assertRaises(ValueError) as ctx:
            parse_archetype_selection_response(response, self.catalog)
        self.assertIn("unknown skill", str(ctx.exception).lower())

    def test_rejects_missing_keys(self) -> None:
        response = self._make_response([{"archetype": "pattern-scout"}])
        with self.assertRaises(ValueError):
            parse_archetype_selection_response(response, self.catalog)

    def test_rejects_duplicate_archetypes(self) -> None:
        entry = {
            "archetype": "pattern-scout",
            "calibration": "Fit",
            "skills": ["mode-detection"],
        }
        response = self._make_response([entry, entry])
        with self.assertRaises(ValueError):
            parse_archetype_selection_response(response, self.catalog)

    def test_rejects_empty_set(self) -> None:
        response = self._make_response([])
        with self.assertRaises(ValueError):
            parse_archetype_selection_response(response, self.catalog)

    def test_rejects_invalid_json(self) -> None:
        with self.assertRaises(ValueError):
            parse_archetype_selection_response("not json at all", self.catalog)

    def test_rejects_missing_agents_key(self) -> None:
        with self.assertRaises(ValueError):
            parse_archetype_selection_response('{"other": []}', self.catalog)

    def test_rejects_empty_calibration(self) -> None:
        response = self._make_response([
            {
                "archetype": "pattern-scout",
                "calibration": "",
                "skills": ["mode-detection"],
            }
        ])
        with self.assertRaises(ValueError):
            parse_archetype_selection_response(response, self.catalog)

    def test_rejects_empty_skills(self) -> None:
        response = self._make_response([
            {
                "archetype": "pattern-scout",
                "calibration": "Fit",
                "skills": [],
            }
        ])
        with self.assertRaises(ValueError):
            parse_archetype_selection_response(response, self.catalog)

    def test_rejects_duplicate_or_empty_skill_identifiers(self) -> None:
        for skills, message in ((["mode-detection", "mode-detection"], "duplicate"), ([""], "non-empty")):
            response = self._make_response([{
                "archetype": "pattern-scout",
                "calibration": "Fit",
                "skills": skills,
            }])
            with self.assertRaisesRegex(ValueError, message):
                parse_archetype_selection_response(response, self.catalog)


class BuildPersonaMapMarkdownTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = _make_test_catalog()

    def test_markdown_contains_all_selected_archetypes(self) -> None:
        selections = [
            SelectedArchetype(
                slug="pattern-scout",
                calibration="User defaults to familiar frames",
                skills=["mode-detection"],
            ),
            SelectedArchetype(
                slug="constraint-reader",
                calibration="User skips diagnosis",
                skills=["diagnose-before-patching"],
            ),
        ]
        md = build_persona_map_markdown(selections, self.catalog)
        self.assertIn("# Persona Map", md)
        self.assertIn("## Pattern Scout", md)
        self.assertIn("## Constraint Reader", md)
        self.assertIn("`pattern-scout.md`", md)
        self.assertIn("`constraint-reader.md`", md)
        self.assertIn("Selected 2 archetype(s)", md)
        self.assertIn("User defaults to familiar frames", md)
        self.assertIn("`mode-detection`", md)


class ArchetypeCatalogLoadingTests(unittest.TestCase):
    def test_load_real_catalog(self) -> None:
        """Load the checked-in archetype catalog and verify basic structure."""
        catalog = load_archetype_catalog()
        self.assertIn("pattern-scout", catalog)
        self.assertIn("constraint-reader", catalog)
        self.assertIn("commitment-anchor", catalog)
        for spec in catalog.values():
            self.assertTrue(spec.slug)
            self.assertTrue(spec.name)
            self.assertTrue(spec.purpose)
            self.assertTrue(spec.canonical_skills)

    def test_catalog_filenames_match_slugs(self) -> None:
        """Every catalog filename must match its declared slug."""
        catalog = load_archetype_catalog()
        for spec in catalog.values():
            self.assertTrue(
                spec.slug in str(spec.contract_text()),
                f"Archetype {spec.name} slug mismatch",
            )


class SoulCreatorAgentSoulTests(unittest.TestCase):
    """End-to-end mocked tests for ``SoulCreator.generate_agents``."""

    def _run(self, coro):  # type: ignore[no-untyped-def]
        return asyncio.run(coro)

    def _make_creator(self) -> SoulCreator:
        with patch("core.soul_creator.create_client") as mock_create:
            mock_create.return_value = AsyncMock()
            return SoulCreator()

    def test_agent_soul_prompt_receives_translation_layer_and_skill_material(self) -> None:
        """Stage 2 prompt must include the translation layer and skill material;
        it must NOT include the raw profile corpus."""
        catalog = _make_test_catalog()

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            agents_dir = tmpdir / "agents"
            persona_map_file = tmpdir / "persona_map.md"

            translation_layer_content = "THE_TRANSLATION_LAYER_CONSTITUTION"
            archetype_content = "THE_ARCHETYPE"
            profile_evidence = "RAW_PROFILE_EVIDENCE_SHOULD_NOT_REACH_SOUL_PROMPT"
            skill_content = "THE_SKILL_CONTENT_FOR_MODE_DETECTION"

            selection = SelectedArchetype(
                slug="pattern-scout",
                calibration="User defaults to familiar frames",
                skills=["mode-detection"],
            )

            creator = self._make_creator()
            captured_soul_prompts: list[str] = []
            call_count = {"n": 0}

            async def fake_generate(handle, *, user_prompt, **kwargs):  # type: ignore[no-untyped-def]
                call_count["n"] += 1
                if call_count["n"] == 1:
                    return json.dumps({
                        "agents": [
                            {
                                "archetype": selection.slug,
                                "calibration": selection.calibration,
                                "skills": selection.skills,
                            }
                        ]
                    })
                captured_soul_prompts.append(user_prompt)
                return f"# Soul of {selection.slug}"

            with (
                patch(
                    "core.soul_creator.generate_text_async",
                    side_effect=fake_generate,
                ),
                patch(
                    "core.soul_creator.load_translation_layer",
                    return_value=(translation_layer_content, archetype_content),
                ),
                patch(
                    "core.soul_creator.load_profile_sources",
                    return_value=profile_evidence,
                ),
                patch(
                    "core.soul_creator.load_archetype_catalog",
                    return_value=catalog,
                ),
                patch(
                    "core.soul_creator.find_canonical_skill",
                    return_value=tmpdir / "skill.md",
                ),
                patch(
                    "core.soul_creator.AGENTS_DIR",
                    agents_dir,
                ),
                patch(
                    "core.soul_creator.PERSONA_MAP_FILE",
                    persona_map_file,
                ),
            ):
                # Write a fake skill file
                (tmpdir / "skill.md").write_text(skill_content, encoding="utf-8")
                self._run(creator.generate_agents())

            self.assertGreaterEqual(len(captured_soul_prompts), 1)
            for prompt in captured_soul_prompts:
                self.assertIn(translation_layer_content, prompt)
                self.assertIn(skill_content, prompt)
                self.assertNotIn(profile_evidence, prompt)

    def test_generate_agents_fails_clearly_when_translation_artifacts_missing(self) -> None:
        """Without translation artifacts, generate_agents must raise
        FileNotFoundError with an actionable message."""
        creator = self._make_creator()
        with patch(
            "core.soul_creator.load_translation_layer",
            side_effect=FileNotFoundError(
                "Translation layer SOUL.md not found. "
                "Run `python -m core build-translation-layer` first."
            ),
        ):
            with self.assertRaises(FileNotFoundError) as cm:
                self._run(creator.generate_agents())
            self.assertIn("build-translation-layer", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
