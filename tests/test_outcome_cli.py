"""Outcome CLI forwards preview and rescore options to the Node runtime."""
import unittest
from unittest.mock import patch

from core import cli, improve


class OutcomeCliTests(unittest.TestCase):
    def test_parser_and_dispatch(self) -> None:
        with patch("core.improve.score_outcomes", return_value={}) as score:
            self.assertEqual(cli.main(["improve-outcome", "--since", "70d", "--limit", "4", "--dry-run", "--rescore", "--analyzer", "mock"]), 0)
        score.assert_called_once_with(since="70d", limit=4, mature_days=3, dry_run=True, rescore=True, analyzer="mock")

    def test_runtime_flags(self) -> None:
        with patch("core.improve._runtime", return_value={}) as runtime:
            improve.score_outcomes(since="70d", limit=2, dry_run=True, rescore=True, analyzer="mock")
        runtime.assert_called_once_with("outcome", ["--since", "70d", "--mature-days", "3", "--analyzer", "mock", "--limit", "2", "--dry-run", "--rescore"])
