"""TDD GREEN: checked-in synthesis prompt is stdout-only with a JSON plans contract."""

import unittest
from pathlib import Path


class TestSynthesisEditOnlyRed(unittest.TestCase):
    def test_synthesis_prompt_is_stdout_only_without_workspace_edits(self):
        prompt_path = Path(__file__).resolve().parents[1] / "improve" / "prompts" / "synthesis.md"
        text = prompt_path.read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("stdout", lowered, "synthesis prompt must declare stdout-only plans")
        self.assertIn(
            "text-only proposer", lowered, "synthesis prompt must declare text-only proposer"
        )
        self.assertNotIn("edit-only", lowered, "synthesis prompt must not declare edit-only workspace edits")
        self.assertNotIn("edit turn", lowered, "synthesis prompt must not describe an edit turn")
        self.assertIn("do not edit files", lowered, "synthesis prompt must forbid workspace edits")
        self.assertIn("do not use a workspace", lowered, "synthesis prompt must disclaim workspace use")
        self.assertIn('"plans"', text, "synthesis prompt must contract a plans JSON key")
        # Narrow provisional plan keys carried on stdout (not workspace frontmatter).
        self.assertIn("clusterId", text, "synthesis prompt must contract clusterId plan key")
        self.assertIn(
            "provisionalSources", text, "synthesis prompt must contract provisionalSources plan key"
        )
        self.assertIn(
            "provisionalIntent", text, "synthesis prompt must contract provisionalIntent plan key"
        )
        # Deterministic code assigns storage; the model never invents file targets.
        self.assertIn(
            "deterministic code assigns storage", lowered,
            "synthesis prompt must state deterministic code assigns storage",
        )


if __name__ == "__main__":
    unittest.main()
