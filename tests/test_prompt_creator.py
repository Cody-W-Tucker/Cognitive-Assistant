#!/usr/bin/env python3
"""Tests for ensemble prompt creation helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.config import Config
from core.prompt_creator import (
    DraftResult,
    _build_candidate_profiles_block,
    _build_synthesis_prompt,
    get_prompt_creator_providers,
    load_dataset_context,
)


class PromptCreatorTests(unittest.TestCase):
    def test_loads_qmd_answer_dataset(self) -> None:
        config = Config.from_profile("existential")
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory) / "questions_with_answers_qmd_20260926_000000.csv"
            dataset.write_text(
                "Category,Goal,Element,Question 1,AI_Answer 1\n"
                "Continuity,Ground the answer,Decision,What changed?,A concrete answer\n",
                encoding="utf-8",
            )
            with patch.object(config, "get_most_recent_file", return_value=dataset) as lookup:
                context = load_dataset_context(config)
        lookup.assert_called_once_with("questions_with_answers_qmd_*.csv")
        self.assertIn("What changed?", context)
        self.assertIn("A concrete answer", context)

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
