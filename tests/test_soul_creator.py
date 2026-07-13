#!/usr/bin/env python3
"""Tests for SOUL artifact cleanup."""

from __future__ import annotations

import unittest

from core.soul_creator import SoulCreator


class SoulCreatorValidationTests(unittest.TestCase):
    def test_archetype_accepts_short_prose_without_word_limit(self) -> None:
        creator = SoulCreator.__new__(SoulCreator)
        response = "A veteran founder-advisor."

        self.assertEqual(creator._extract_archetype(response), response)

    def test_soul_accepts_prose_without_word_count_validation(self) -> None:
        creator = SoulCreator.__new__(SoulCreator)
        response = "A short SOUL."

        self.assertEqual(creator._extract_soul(response), response)

    def test_soul_strips_markdown_code_fence(self) -> None:
        creator = SoulCreator.__new__(SoulCreator)
        response = "```markdown\n# SOUL\n```"

        self.assertEqual(creator._extract_soul(response), "# SOUL")


if __name__ == "__main__":
    unittest.main()
