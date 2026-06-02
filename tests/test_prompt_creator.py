#!/usr/bin/env python3
"""Tests for ensemble prompt creation helpers."""

from __future__ import annotations

import unittest

from core.prompt_creator import (
    DraftResult,
    _build_candidate_profiles_block,
    _build_synthesis_prompt,
    get_prompt_creator_providers,
)
from core.config import Config


class PromptCreatorTests(unittest.TestCase):
    def test_get_prompt_creator_providers_is_distinct(self) -> None:
        self.assertEqual(
            get_prompt_creator_providers(),
            ["xai", "anthropic", "openai"],
        )

    def test_build_synthesis_prompt_includes_consensus_instructions(self) -> None:
        config = Config.from_profile("existential")
        candidate_profiles = _build_candidate_profiles_block(
            [
                DraftResult(provider="xai", model="grok-test", content="draft one"),
                DraftResult(
                    provider="anthropic",
                    model="claude-test",
                    content="draft two",
                ),
            ]
        )

        prompt = _build_synthesis_prompt(
            config,
            candidate_profiles=candidate_profiles,
        )

        self.assertIn("Only keep a claim if it is supported by at least two", prompt)
        self.assertIn('<candidate provider="xai" model="grok-test">', prompt)
        self.assertIn("draft two", prompt)


if __name__ == "__main__":
    unittest.main()
