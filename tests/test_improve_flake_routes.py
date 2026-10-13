"""The packaged CA command is interactive by default; timer stays headless."""
from __future__ import annotations

import unittest
from pathlib import Path


class TestImproveFlakeRoutes(unittest.TestCase):
    def test_package_is_tui_default_and_systemd_is_headless(self) -> None:
        flake = Path(__file__).resolve().parents[1] / "flake.nix"
        text = flake.read_text(encoding="utf-8")
        self.assertIn('exec python -m core improve-run "$@"', text)
        self.assertIn('caPython = pkgs.python312.withPackages (python-pkgs: [ python-pkgs.python-dotenv ]);', text)
        self.assertIn('              caPython', text)
        self.assertIn('ExecStart = "${cfg.package}/bin/ca-improve --headless";', text)


if __name__ == "__main__":
    unittest.main()
