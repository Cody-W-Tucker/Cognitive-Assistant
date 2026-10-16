"""The packaged CA command is interactive by default; timer stays headless."""
from __future__ import annotations

import unittest
from pathlib import Path


class TestImproveFlakeRoutes(unittest.TestCase):
    def test_package_is_tui_default_and_systemd_is_headless(self) -> None:
        flake = Path(__file__).resolve().parents[1] / "flake.nix"
        text = flake.read_text(encoding="utf-8")
        self.assertIn('exec python -m core improve-run "$@"', text)
        self.assertIn('caPython = pkgs.python314.withPackages (python-pkgs: [ python-pkgs.python-dotenv ]);', text)
        self.assertIn('              caPython', text)
        self.assertIn('ExecStart = "${cfg.package}/bin/ca-improve --headless";', text)
        # Guard against regression to Python 3.12 wrapper.
        self.assertNotIn("python312", text)
        self.assertNotIn("python3.12", text)

    def test_flake_pins_python314_wrapper_and_devshell(self) -> None:
        flake = Path(__file__).resolve().parents[1] / "flake.nix"
        text = flake.read_text(encoding="utf-8")
        # Wrapper intent: pinned 3.14 interpreter with packages.
        self.assertIn("pkgs.python314.withPackages", text)
        self.assertIn("caPython = pkgs.python314.withPackages", text)
        # Dev-shell intent: mkShell on 3.14 (not 3.12).
        self.assertIn("mkShell", text)
        self.assertIn("pkgs.python314", text)
        # Explicitly guard against Python 3.12 in any spelling.
        self.assertNotIn("python312", text)
        self.assertNotIn("python3.12", text)


if __name__ == "__main__":
    unittest.main()
