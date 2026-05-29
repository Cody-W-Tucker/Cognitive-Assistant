#!/usr/bin/env python3
"""Tests for schema export -> JSONL packet conversion."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.ingest_substrate import convert_substrate_exports


class IngestSubstrateTests(unittest.TestCase):
    def test_convert_graph_only_writes_graph_packets(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cognitive-assistant-substrate-") as tmp:
            root = Path(tmp)
            graph_path = root / "graph.json"
            output_dir = root / "ready"

            graph_path.write_text(
                json.dumps(
                    {
                        "people": [
                            {
                                "slug": "people/alice",
                                "title": "Alice",
                                "body": "Relationship notes",
                                "date": "2026-05-12T00:00:00",
                                "frontmatter": {"status": "active"},
                                "mentions": [
                                    {
                                        "slug": "notes/q2-retro",
                                        "title": "Q2 Retro",
                                        "date": "2026-05-12T00:00:00",
                                        "matched_lines": [
                                            {
                                                "line_number": 14,
                                                "text": "Alice flagged scope risk early.",
                                            }
                                        ],
                                        "expansion_rules": ["list_item_children"],
                                    }
                                ],
                            }
                        ],
                        "organizations": [],
                        "places": [],
                        "events": [],
                        "tasks": [],
                        "projects": [],
                        "concepts": [],
                        "notes": [],
                        "sources": [],
                        "journals": [],
                    },
                    ensure_ascii=True,
                ),
                encoding="utf-8",
            )

            counts = convert_substrate_exports(
                graph_path=graph_path,
                focus_paths=[],
                output_dir=output_dir,
            )

            self.assertEqual(
                counts,
                {
                    "graph_pages": 1,
                    "mention_evidence": 1,
                },
            )
            self.assertTrue((output_dir / "graph_pages.jsonl").exists())
            self.assertTrue((output_dir / "mention_evidence.jsonl").exists())
            self.assertFalse((output_dir / "focus_source_notes.jsonl").exists())
            self.assertFalse((output_dir / "focus_relations.jsonl").exists())

    def test_convert_graph_and_focus_exports_to_jsonl_packets(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cognitive-assistant-substrate-") as tmp:
            root = Path(tmp)
            graph_path = root / "graph.json"
            focus_path = root / "focus-bundle.json"
            output_dir = root / "ready"

            graph_path.write_text(
                json.dumps(
                    {
                        "people": [
                            {
                                "slug": "people/alice",
                                "title": "Alice",
                                "body": "Relationship notes",
                                "date": "2026-05-12T00:00:00",
                                "frontmatter": {"status": "active"},
                                "mentions": [
                                    {
                                        "slug": "notes/q2-retro",
                                        "title": "Q2 Retro",
                                        "date": "2026-05-12T00:00:00",
                                        "matched_lines": [
                                            {
                                                "line_number": 14,
                                                "text": "Alice flagged scope risk early.",
                                            }
                                        ],
                                        "expansion_rules": ["list_item_children"],
                                    }
                                ],
                            }
                        ],
                        "organizations": [],
                        "places": [],
                        "events": [],
                        "tasks": [],
                        "projects": [],
                        "concepts": [],
                        "notes": [],
                        "sources": [],
                        "journals": [],
                    },
                    ensure_ascii=True,
                ),
                encoding="utf-8",
            )

            focus_path.write_text(
                json.dumps(
                    {
                        "id": "focus/concepts/trust-building",
                        "focus": {"kind": "concept", "slug": "concepts/trust-building"},
                        "focus_body": "Trust grows when commitments are kept.",
                        "source_notes": [
                            {
                                "note_slug": "notes/client-history",
                                "source_path": "Knowledge/Writing/client-history.md",
                                "note_title": "Client History",
                                "note_summary": "Longstanding account notes",
                                "note_date": "2026-05-11T00:00:00",
                                "matched_lines": [
                                    {
                                        "line_number": 7,
                                        "text": "Trust increased after consistent delivery.",
                                    }
                                ],
                            }
                        ],
                        "relations": {
                            "people": [
                                {
                                    "slug": "people/alice",
                                    "title": "Alice",
                                    "source_path": "Knowledge/Entities/People/Alice.md",
                                    "note_slugs": ["notes/client-history"],
                                    "mentions": [
                                        {
                                            "slug": "notes/client-history",
                                            "title": "Client History",
                                            "date": "2026-05-11T00:00:00",
                                            "matched_lines": [
                                                {
                                                    "line_number": 7,
                                                    "text": "Trust increased after consistent delivery.",
                                                }
                                            ],
                                            "expansion_rules": [],
                                        }
                                    ],
                                }
                            ],
                            "concepts": [],
                            "events": [],
                            "projects": [],
                        },
                    },
                    ensure_ascii=True,
                ),
                encoding="utf-8",
            )

            counts = convert_substrate_exports(
                graph_path=graph_path,
                focus_paths=[focus_path],
                output_dir=output_dir,
            )

            self.assertEqual(
                counts,
                {
                    "graph_pages": 1,
                    "mention_evidence": 1,
                    "focus_source_notes": 1,
                    "focus_relations": 1,
                },
            )

            graph_page = json.loads((output_dir / "graph_pages.jsonl").read_text().splitlines()[0])
            mention = json.loads(
                (output_dir / "mention_evidence.jsonl").read_text().splitlines()[0]
            )
            focus_source = json.loads(
                (output_dir / "focus_source_notes.jsonl").read_text().splitlines()[0]
            )
            focus_relation = json.loads(
                (output_dir / "focus_relations.jsonl").read_text().splitlines()[0]
            )

            self.assertEqual(graph_page["kind"], "graph_page")
            self.assertEqual(graph_page["page_type"], "people")
            self.assertEqual(graph_page["slug"], "people/alice")

            self.assertEqual(mention["kind"], "mention_evidence")
            self.assertEqual(mention["target_slug"], "people/alice")
            self.assertEqual(mention["matched_lines"][0]["text"], "Alice flagged scope risk early.")

            self.assertEqual(focus_source["kind"], "focus_source_note")
            self.assertEqual(focus_source["focus_slug"], "concepts/trust-building")
            self.assertEqual(focus_source["note_slug"], "notes/client-history")

            self.assertEqual(focus_relation["kind"], "focus_relation")
            self.assertEqual(focus_relation["relation_group"], "people")
            self.assertEqual(focus_relation["related_slug"], "people/alice")


if __name__ == "__main__":
    unittest.main()
