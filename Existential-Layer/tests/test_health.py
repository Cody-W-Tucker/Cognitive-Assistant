#!/usr/bin/env python3
"""Health-check tests for Existential-Layer."""

import unittest

from health_check import (
    check_prompt_files,
    check_prompt_rendering,
    check_required_paths,
    check_provider_setup,
    check_rlm_command,
    check_script_imports,
)


class HealthCheckTests(unittest.TestCase):
    """Validate static project health assumptions."""

    def test_prompt_files_load(self) -> None:
        self.assertEqual(check_prompt_files(), [])

    def test_prompt_templates_render(self) -> None:
        self.assertEqual(check_prompt_rendering(), [])

    def test_required_paths_exist(self) -> None:
        self.assertEqual(check_required_paths(), [])

    def test_modules_import(self) -> None:
        self.assertEqual(check_script_imports(), [])

    def test_provider_setup(self) -> None:
        self.assertEqual(check_provider_setup(), [])

    def test_rlm_command_exists(self) -> None:
        self.assertEqual(check_rlm_command(), [])


if __name__ == "__main__":
    unittest.main()
