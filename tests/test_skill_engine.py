#!/usr/bin/env python3
"""Tests for shared skill artifact mechanics."""

from __future__ import annotations

import unittest

from core.config import SkillSpec
from core.skill_engine import (
    body_without_frontmatter,
    extract_frontmatter,
    normalize_skill_markdown,
    parse_json_response,
    parse_markdown_response,
    validate_skill_document,
    with_generation_metadata,
)


VALID_SKILL = """---
name: example-skill
description: Use this skill when a concrete example needs enough content to satisfy validation and stay narrow.
source_group: example-group
category: examples
compatibility: opencode
---

# Example Skill

## When To Use
Use this when the shared skill engine needs a representative valid OpenCode skill document with enough substance to clear common validation.

## Do Not Use
Do not use this as a real runtime skill or as evidence that broader workflow behavior was exercised.
"""


class SkillEngineTests(unittest.TestCase):
    def test_parse_json_and_markdown_fences(self) -> None:
        self.assertEqual(parse_json_response('```json\n{"example-skill": "body"}\n```'), {"example-skill": "body"})
        self.assertEqual(parse_markdown_response("```markdown\n# Title\n```"), "# Title")

    def test_frontmatter_body_and_normalization_helpers(self) -> None:
        self.assertIn("name: example-skill", extract_frontmatter(VALID_SKILL))
        self.assertTrue(body_without_frontmatter(VALID_SKILL).lstrip().startswith("# Example Skill"))
        normalized = normalize_skill_markdown("```markdown\n# Body\n```", VALID_SKILL)
        self.assertTrue(normalized.startswith("---\nname: example-skill"))
        self.assertTrue(normalized.endswith("# Body\n"))

    def test_validate_and_generation_metadata(self) -> None:
        validate_skill_document("example-skill", VALID_SKILL)
        spec = SkillSpec(
            slug="example-skill",
            source_group="declared-group",
            source_headings=("Heading",),
        )
        updated = with_generation_metadata(spec, VALID_SKILL, "existential")
        self.assertIn("source_group: declared-group", updated)
        self.assertIn("source_profile: existential", updated)
        self.assertIn("compatibility: opencode", updated)

    def test_generation_metadata_updates_only_frontmatter(self) -> None:
        spec = SkillSpec(
            slug="example-skill",
            source_group="declared-group",
            source_headings=("Heading",),
        )
        content = VALID_SKILL + "\nBody note keeps source_group: body-group untouched.\n"

        updated = with_generation_metadata(spec, content, "existential")

        self.assertIn("source_group: declared-group", extract_frontmatter(updated))
        self.assertIn("source_group: body-group", updated)


if __name__ == "__main__":
    unittest.main()
