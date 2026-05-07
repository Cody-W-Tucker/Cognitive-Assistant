#!/usr/bin/env python3
"""Profile-aware health-check tests.

Runs the unified health check against every registered profile. Network calls
(actual LLM client creation) and RLM availability checks are skipped here so
the test passes in CI without secrets or external binaries.
"""

from __future__ import annotations

import unittest

from core.config import Config, list_profiles
from core.health_check import (
    check_prompt_rendering,
    check_required_paths,
)
from core.prompt_loader import load_prompt_for_profile
from lib.health import check_prompt_files, check_script_imports


SCRIPT_MODULES = [
    "core.config",
    "core.prompt_loader",
    "core.prompt_creator",
    "core.skills_creator",
    "core.question_asker",
    "core.health_check",
    "core.cli",
    "core.soul_creator",
]


class ProfileHealthTests(unittest.TestCase):
    """Validate prompts, paths, and module imports for every profile."""

    def test_each_profile_static_health(self) -> None:
        for profile_name in list_profiles():
            with self.subTest(profile=profile_name):
                config = Config.from_profile(profile_name)
                self.assertEqual(
                    check_prompt_files(
                        prompt_files=config.profile.prompt_files,
                        prompt_runtime_dir=config.profile.prompts_dir,
                        load_prompt=lambda name: load_prompt_for_profile(
                            config.profile, name
                        ),
                    ),
                    [],
                )
                self.assertEqual(check_prompt_rendering(config), [])
                # Skipped: validate_question_answering checks RLM evidence
                # source which may be environment-specific. Just verify the
                # prompt runtime directory exists.
                self.assertTrue(config.paths.PROMPT_RUNTIME_DIR.exists())

    def test_modules_import(self) -> None:
        self.assertEqual(check_script_imports(SCRIPT_MODULES), [])


if __name__ == "__main__":
    unittest.main()
