"""Tests for operational corpus ingestion."""

import unittest

from core.ingest_corpus import _summarize_repeated_records


class SummarizeRepeatedRecordsTests(unittest.TestCase):
    def test_preserves_first_occurrence_order_and_counts_normalized_text(self) -> None:
        records = iter([
            {"user_text": " First "},
            {"user_text": "Second"},
            {"user_text": ""},
            {"user_text": "First"},
            {},
            {"user_text": "Third"},
            {"user_text": "Second"},
            {"user_text": "First"},
        ])
        self.assertEqual(_summarize_repeated_records(records), [
            {"user_text": "First", "repeated": 3},
            {"user_text": "Second", "repeated": 2},
            {"user_text": "Third"},
        ])

    def test_empty_input(self) -> None:
        self.assertEqual(_summarize_repeated_records([]), [])
