#!/usr/bin/env python3
"""Code, alignment prompts and the generated SOUL/posture stay strict ASCII."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PATTERNS = (
    "flake.nix",
    "*.md",
    "core/*.py",
    "tests/*.py",
    "profiles/alignment/**/*.md",
    "docs/*Alignment*.md",
    "docs/Layer-Profiles.md",
    "docs/CLI-and-Command-Reference.md",
    "docs/Workspaces-and-Generated-Artifacts.md",
    "docs/README.md",
    "workspaces/alignment/artifacts/SOUL.md",
    "workspaces/alignment/artifacts/INTERACTION_POSTURE.md",
)


class AsciiTests(unittest.TestCase):
    def test_files_are_strict_ascii(self) -> None:
        paths = sorted({path for pattern in PATTERNS for path in ROOT.glob(pattern)})
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(path=str(path.relative_to(ROOT))):
                text = path.read_text(encoding="utf-8")
                bad = next((ch for ch in text if ord(ch) > 0x7F), None)
                self.assertIsNone(bad, f"non-ASCII {bad!r}")


if __name__ == "__main__":
    unittest.main()
