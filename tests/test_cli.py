#!/usr/bin/env python3
"""Tests for CLI registration of the translation-layer command."""

from __future__ import annotations

import unittest

from core.cli import _build_parser


class TranslationLayerCLIRegistrationTests(unittest.TestCase):
    def test_build_translation_layer_is_registered(self) -> None:
        parser = _build_parser()
        # Should not raise; 'build-translation-layer' is a known subcommand.
        args = parser.parse_args(["build-translation-layer"])
        self.assertEqual(args.command, "build-translation-layer")

    def test_build_translation_layer_does_not_accept_output(self) -> None:
        parser = _build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "build-translation-layer",
                "--output",
                "/tmp/SOUL.md",
            ])

    def test_build_soul_is_not_registered(self) -> None:
        parser = _build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["build-soul"])

    def test_update_help_mentions_translation_layer(self) -> None:
        parser = _build_parser()
        # The update subparser exists and accepts --skip-tool-specs.
        args = parser.parse_args(["update", "--skip-tool-specs"])
        self.assertEqual(args.command, "update")


if __name__ == "__main__":
    unittest.main()
