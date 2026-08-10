#!/usr/bin/env python3
"""Tests for agent persona discovery and soul generation."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from core.soul_creator import (
    AgentPersona,
    SoulCreator,
    build_persona_map_markdown,
    parse_persona_discovery_response,
    sanitize_slug,
)


class SanitizeSlugTests(unittest.TestCase):
    def test_valid_slugs(self) -> None:
        self.assertEqual(sanitize_slug("my-agent"), "my-agent")
        self.assertEqual(sanitize_slug("agent123"), "agent123")
        self.assertEqual(sanitize_slug("a-b"), "a-b")

    def test_uppercase_normalized(self) -> None:
        self.assertEqual(sanitize_slug("My-Agent"), "my-agent")

    def test_spaces_and_special_chars_replaced(self) -> None:
        self.assertEqual(sanitize_slug("my agent!"), "my-agent")
        self.assertEqual(sanitize_slug("agent@#$name"), "agent-name")

    def test_rejected_slugs(self) -> None:
        self.assertIsNone(sanitize_slug(""))
        self.assertIsNone(sanitize_slug("1agent"))  # Starts with digit after sanitization
        self.assertIsNone(sanitize_slug("---"))  # Empty after stripping
        self.assertIsNone(sanitize_slug("a"))  # Too short
        self.assertIsNone(sanitize_slug(None))  # type: ignore[arg-type]


class ParsePersonaDiscoveryResponseTests(unittest.TestCase):
    def _make_response(self, agents: list) -> str:
        return json.dumps({"agents": agents})

    def test_valid_single_agent(self) -> None:
        response = self._make_response([
            {
                "name": "The Builder",
                "slug": "the-builder",
                "archetype": "A hands-on maker",
                "responsibility": "Execution and shipping",
                "boundary": "Does not handle strategy",
                "fit_rationale": "User needs someone who ships",
            }
        ])
        personas = parse_persona_discovery_response(response)
        self.assertEqual(len(personas), 1)
        self.assertEqual(personas[0].slug, "the-builder")
        self.assertEqual(personas[0].name, "The Builder")

    def test_multiple_agents(self) -> None:
        response = self._make_response([
            {
                "name": "Agent A",
                "slug": "agent-a",
                "archetype": "Type A",
                "responsibility": "Domain A",
                "boundary": "Not domain B",
                "fit_rationale": "Because A",
            },
            {
                "name": "Agent B",
                "slug": "agent-b",
                "archetype": "Type B",
                "responsibility": "Domain B",
                "boundary": "Not domain A",
                "fit_rationale": "Because B",
            },
        ])
        personas = parse_persona_discovery_response(response)
        self.assertEqual(len(personas), 2)
        slugs = {p.slug for p in personas}
        self.assertEqual(slugs, {"agent-a", "agent-b"})

    def test_strips_code_fences(self) -> None:
        inner = self._make_response([
            {
                "name": "Agent X",
                "slug": "agent-x",
                "archetype": "Type X",
                "responsibility": "X work",
                "boundary": "Not Y",
                "fit_rationale": "Fit",
            }
        ])
        response = f"```json\n{inner}\n```"
        personas = parse_persona_discovery_response(response)
        self.assertEqual(len(personas), 1)

    def test_rejects_missing_keys(self) -> None:
        response = self._make_response([{"name": "Agent", "slug": "agent"}])
        with self.assertRaises(ValueError):
            parse_persona_discovery_response(response)

    def test_rejects_duplicate_slugs(self) -> None:
        agent = {
            "name": "A",
            "slug": "same-slug",
            "archetype": "T",
            "responsibility": "R",
            "boundary": "B",
            "fit_rationale": "F",
        }
        response = self._make_response([agent, agent])
        with self.assertRaises(ValueError):
            parse_persona_discovery_response(response)

    def test_rejects_empty_set(self) -> None:
        response = self._make_response([])
        with self.assertRaises(ValueError):
            parse_persona_discovery_response(response)

    def test_rejects_invalid_json(self) -> None:
        with self.assertRaises(ValueError):
            parse_persona_discovery_response("not json at all")

    def test_rejects_missing_agents_key(self) -> None:
        with self.assertRaises(ValueError):
            parse_persona_discovery_response('{"other": []}')

    def test_rejects_invalid_slug(self) -> None:
        response = self._make_response([
            {
                "name": "Bad",
                "slug": "1invalid",
                "archetype": "T",
                "responsibility": "R",
                "boundary": "B",
                "fit_rationale": "F",
            }
        ])
        with self.assertRaises(ValueError):
            parse_persona_discovery_response(response)


class BuildPersonaMapMarkdownTests(unittest.TestCase):
    def test_markdown_contains_all_agents(self) -> None:
        personas = [
            AgentPersona(
                name="Builder",
                slug="builder",
                archetype="A maker",
                responsibility="Shipping",
                boundary="Not strategy",
                fit_rationale="User ships",
            ),
            AgentPersona(
                name="Strategist",
                slug="strategist",
                archetype="A thinker",
                responsibility="Strategy",
                boundary="Not shipping",
                fit_rationale="User plans",
            ),
        ]
        md = build_persona_map_markdown(personas)
        self.assertIn("# Persona Map", md)
        self.assertIn("## Builder", md)
        self.assertIn("## Strategist", md)
        self.assertIn("`builder.md`", md)
        self.assertIn("`strategist.md`", md)
        self.assertIn("Discovered 2 distinct agent personas", md)


class SoulCreatorAgentSoulTests(unittest.TestCase):
    """End-to-end mocked tests for ``SoulCreator.generate_agents``.

    These tests verify that the specialist soul prompt receives the
    translation-layer content (not the raw profile corpus) and that
    generation fails clearly when translation artifacts are missing.
    """

    def _run(self, coro):  # type: ignore[no-untyped-def]
        return asyncio.run(coro)

    def _make_creator(self) -> SoulCreator:
        with patch("core.soul_creator.create_client") as mock_create:
            mock_create.return_value = AsyncMock()
            return SoulCreator()

    def test_agent_soul_prompt_receives_translation_layer_not_profile_corpus(self) -> None:
        """Stage 2 prompt must include the translation layer; it must NOT
        include the raw profile corpus."""
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            agents_dir = tmpdir / "agents"
            persona_map_file = tmpdir / "persona_map.md"

            translation_layer_content = "THE_TRANSLATION_LAYER_CONSTITUTION"
            archetype_content = "THE_ARCHETYPE"
            profile_evidence = "RAW_PROFILE_EVIDENCE_SHOULD_NOT_REACH_SOUL_PROMPT"

            persona = AgentPersona(
                name="The Builder",
                slug="the-builder",
                archetype="A maker",
                responsibility="Shipping",
                boundary="Not strategy",
                fit_rationale="User ships",
            )

            creator = self._make_creator()
            captured_soul_prompts: list[str] = []
            call_count = {"n": 0}

            async def fake_generate(handle, *, user_prompt, **kwargs):  # type: ignore[no-untyped-def]
                call_count["n"] += 1
                # Stage 1: persona discovery returns JSON
                if call_count["n"] == 1:
                    return json.dumps({
                        "agents": [
                            {
                                "name": persona.name,
                                "slug": persona.slug,
                                "archetype": persona.archetype,
                                "responsibility": persona.responsibility,
                                "boundary": persona.boundary,
                                "fit_rationale": persona.fit_rationale,
                            }
                        ]
                    })
                # Stage 2: agent soul
                captured_soul_prompts.append(user_prompt)
                return f"# Soul of {persona.slug}"

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
                patch("core.soul_creator.AGENTS_DIR", agents_dir),
                patch("core.soul_creator.PERSONA_MAP_FILE", persona_map_file),
            ):
                self._run(creator.generate_agents())

            # At least one soul prompt captured (one per persona).
            self.assertGreaterEqual(len(captured_soul_prompts), 1)
            for prompt in captured_soul_prompts:
                self.assertIn(translation_layer_content, prompt)
                self.assertNotIn(profile_evidence, prompt)

    def test_generate_agents_fails_clearly_when_translation_artifacts_missing(self) -> None:
        """Without translation artifacts, generate_agents must raise
        FileNotFoundError with an actionable message."""
        creator = self._make_creator()
        with (
            patch(
                "core.soul_creator.load_translation_layer",
                side_effect=FileNotFoundError(
                    "Translation layer SOUL.md not found. "
                    "Run `python -m core build-translation-layer` first."
                ),
            ),
        ):
            with self.assertRaises(FileNotFoundError) as cm:
                self._run(creator.generate_agents())
            self.assertIn("build-translation-layer", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
