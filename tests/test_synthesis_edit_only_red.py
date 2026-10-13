"""TDD RED: checked-in synthesis prompt is edit-only with no JSON plan contract."""

import unittest
from pathlib import Path


class TestSynthesisEditOnlyRed(unittest.TestCase):
    def test_synthesis_prompt_is_edit_only_without_json_plan_contract(self):
        prompt_path = Path(__file__).resolve().parents[1] / "improve" / "prompts" / "synthesis.md"
        text = prompt_path.read_text(encoding="utf-8")
        self.assertTrue(
            "edit-only" in text.lower() or "edit only" in text.lower(),
            "synthesis prompt must declare edit-only workspace edits",
        )
        self.assertIn("workspace", text.lower(), "synthesis prompt must mention workspace")
        self.assertNotIn("change plan", text.lower(), "synthesis prompt must not contract a JSON change plan")
        # Mandated provenance YAML frontmatter contract: workspace files carry
        # ONLY clusterId + provisionalSources as structured frontmatter (not JSON).
        self.assertIn("clusterId", text, "synthesis prompt must mandate clusterId frontmatter provenance")
        self.assertIn(
            "provisionalSources", text, "synthesis prompt must mandate provisionalSources frontmatter provenance"
        )
        self.assertNotIn(
            "provisionalIntent", text, "synthesis prompt must not contract provisionalIntent (only the two mandated keys)"
        )
        self.assertNotIn('"plans"', text, "synthesis prompt must not contract a plans JSON key")


if __name__ == "__main__":
    unittest.main()
