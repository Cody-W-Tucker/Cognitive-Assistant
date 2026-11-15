"""Tests for operational corpus ingestion."""

import asyncio
import contextlib
import csv
import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch
from zipfile import ZipFile, ZipInfo

from core import ingest_corpus
from core.ingest_corpus import _summarize_repeated_records


class SummarizeRepeatedRecordsTests(unittest.TestCase):
    def test_preserves_first_occurrence_order_and_counts_normalized_text(self) -> None:
        records = iter([
            " First ",
            "Second",
            "",
            "First",
            "",
            "Third",
            "Second",
            "First",
        ])
        self.assertEqual(_summarize_repeated_records(records), [
            {"user_text": "First", "repeated": 3},
            {"user_text": "Second", "repeated": 2},
            {"user_text": "Third"},
        ])

    def test_empty_input(self) -> None:
        self.assertEqual(_summarize_repeated_records([]), [])


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    path.write_text(buffer.getvalue(), encoding="utf-8")


def _write_zip(path: Path, member: str, payload: Any) -> None:
    with ZipFile(path, "w") as archive:
        archive.writestr(ZipInfo(member, (2026, 1, 1, 0, 0, 0)), json.dumps(payload))


def _jsonl(*lines: dict[str, Any]) -> str:
    return "".join(json.dumps(line) + "\n" for line in lines)


def _write_intake(intake: Path) -> None:
    """One export per supported source, exercising every skip and note path."""
    intake.mkdir(parents=True)
    (intake / "opencode_conversations_2026-01-01.jsonl").write_text(_jsonl(
        {"title": "t", "messages": [
            {"role": "user", "content": "Hello &amp; welcome", "timestamp": 1},
            {"role": "assistant", "content": "ignored"},
            {"role": "user", "content": ""},
            {"role": "user", "content": [{"text": "Hello & welcome"}]},
        ]},
        {"messages": [{"role": "user", "content": {"parts": ["x", "y"]}}]},
    ), encoding="utf-8")
    (intake / "opencode_conversations_2025-01-01.jsonl").write_text("older, not read\n", encoding="utf-8")
    (intake / "cursor_ultimate_2026.jsonl").write_text(_jsonl(
        {"workspace_id": "w", "messages": [{"role": "assistant", "content": "a"}]},
        {"messages": [
            {"role": "user", "content": "<summary>s</summary>fix it"},
            {"role": "user", "content": "  "},
        ]},
    ), encoding="utf-8")

    webui = intake / "open-webui"
    webui.mkdir()
    (webui / "chat-export-1.json").write_text(json.dumps([{"chat": {"title": "c", "history": {"messages": {
        "r2": {"parentId": None, "timestamp": 5, "role": "user", "content": "second root", "childrenIds": []},
        "r1": {"parentId": None, "timestamp": 1, "role": "user", "content": "first root",
               "childrenIds": ["missing", "a1"]},
        "a1": {"parentId": "r1", "role": "assistant", "content": "ans", "childrenIds": ["u2"]},
        "u2": {"parentId": "a1", "role": "user", "content": "follow up", "childrenIds": []},
    }}}}]), encoding="utf-8")
    (webui / "chat-export-2.json").write_text("{broken", encoding="utf-8")
    (webui / "x.snapshot").write_text("", encoding="utf-8")

    perplexity = intake / "perplexity"
    perplexity.mkdir()
    _write_csv(perplexity / "Search_History.csv", ["QUERY_STRING", "CREATED"], [
        ["q one", "2026-01-01T00:00:00"], ["q two", "2026-01-01T02:00:00"],
        ["q one", "2026-01-01T02:10:00"], ["", "2026-01-01T03:00:00"], ["no date", ""],
    ])
    _write_csv(perplexity / "Memory.csv", [
        "IS_DELETED", "IS_FORGOTTEN", "IS_INVISIBLE", "MEMORY_KEY",
        "MEMORY_VALUE", "LAST_UPDATED_QUERY", "LAST_UPDATED_AT",
    ], [
        ["0", "false", "", "k1", "v1", "why k1", "t"], ["False", "0.0", "False", "k2", "v2", "", "t"],
        ["1", "", "", "k3", "v3", "", ""], ["", "true", "", "k4", "v4", "", ""],
        ["", "", "1", "k5", "v5", "", ""], ["", "", "", "", "v6", "", ""],
    ])
    _write_csv(perplexity / "Conversations.csv", ["TITLE", "OUTPUT_STR", "CREATED"], [
        ["Title A", json.dumps({"answer": "yes"}), "c"], ["Title B", "not json", ""],
        ["Title C", json.dumps({"answer": ""}), ""], ["", json.dumps({"answer": "x"}), ""],
        ["Title D", "", ""],
    ])

    _write_zip(intake / "OpenAI-Chat-export.zip", "conversations.json", [
        {"title": "o", "mapping": {
            "b": {"parent": None, "message": {"create_time": 9, "author": {"role": "user"},
                                              "content": {"parts": ["late root"]}}, "children": []},
            "a": {"parent": None, "message": None, "children": ["gone", "u"]},
            "u": {"parent": "a", "message": {"author": {"role": "user"},
                                             "content": {"parts": ["openai q"]}}, "children": []},
        }},
        {"mapping": {}},
        "not a dict",
    ])
    _write_zip(intake / "grok_export.zip", "x/prod-grok-backend.json", {
        "conversations": [
            {"conversation": {"title": "g"}, "responses": [
                {"response": {"sender": "human", "message": "grok q",
                              "create_time": {"$date": {"$numberLong": "1700000000000"}}}},
                {"response": {"sender": "assistant", "message": "a"}},
                {"response": {"sender": "human", "message": ""}},
            ]},
            {"conversation": {"id": "i"}, "responses": "bad"},
        ],
        "media_posts": [1, 2],
    })


EXPECTED_OUTPUTS = {
    "opencode/interactions": '{"repeated": 2, "user_text": "Hello & welcome"}\n{"user_text": "x\\ny"}\n',
    "cursor/requests": '{"user_text": "fix it"}\n',
    "open-webui/interactions": (
        '{"user_text": "first root"}\n{"user_text": "follow up"}\n{"user_text": "second root"}\n'
    ),
    "perplexity/search_queries": '{"repeated": 2, "user_text": "q one"}\n{"user_text": "q two"}\n',
    "perplexity/memory_items": '{"user_text": "why k1"}\n{"user_text": "k2"}\n',
    "perplexity/conversations": '{"user_text": "Title A"}\n',
    "openai/interactions": '{"user_text": "openai q"}\n',
    "grok/interactions": '{"user_text": "grok q"}\n',
}

# (source, records_written, records_skipped, notes)
EXPECTED_SOURCES = [
    ("opencode", 2, 1, []),
    ("cursor", 1, 2, []),
    ("open-webui", 3, 1, [
        "Skipped invalid JSON export: chat-export-2.json",
        "Ignored 1 .snapshot files (unsupported binary/source format)",
    ]),
    ("perplexity", 5, 10, []),
    ("openai", 1, 1, []),
    ("grok", 1, 2, ["Ignored 2 Grok media_posts entries; extracted conversation prompts only"]),
]


class BuildTests(unittest.TestCase):
    """Pin ready output, manifest and summary for every supported source format."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.data_dir = Path(tmp.name)
        self.profile = SimpleNamespace(data_dir=self.data_dir, qmd_collections=["c"], has_corpus_ingest=True)

    def _build(self) -> str:
        out = io.StringIO()
        with patch("core.ingest_corpus.datetime") as fake_datetime, contextlib.redirect_stdout(out):
            fake_datetime.now.return_value = datetime(2026, 1, 2, 3, 4, 5)
            fake_datetime.fromisoformat = datetime.fromisoformat
            fake_datetime.fromtimestamp = datetime.fromtimestamp
            asyncio.run(ingest_corpus.build(self.profile))
        return out.getvalue()

    def test_every_source_format(self) -> None:
        _write_intake(self.data_dir / "intake")
        stdout = self._build()
        ready = self.data_dir / "ready"
        stamp = "20260102_030405"

        for stem, content in EXPECTED_OUTPUTS.items():
            with self.subTest(stem=stem):
                self.assertEqual((ready / f"{stem}_{stamp}.jsonl").read_text(encoding="utf-8"), content)
        written = sorted(str(p.relative_to(ready)) for p in ready.rglob("*.jsonl"))
        self.assertEqual(written, sorted(f"{stem}_{stamp}.jsonl" for stem in EXPECTED_OUTPUTS))

        sources = []
        for source, records_written, records_skipped, notes in EXPECTED_SOURCES:
            files = [str(ready / f"{stem}_{stamp}.jsonl") for stem in EXPECTED_OUTPUTS if stem.startswith(source + "/")]
            sources.append({
                "source": source, "status": "processed", "output_files": files,
                "records_written": records_written, "records_skipped": records_skipped, "notes": notes,
            })
        manifest = {
            "generated_at": "2026-01-02T03:04:05",
            "intake_dir": str(self.data_dir / "intake"),
            "ready_dir": str(ready),
            "qmd_collections": ["c"],
            "schema_version": ingest_corpus.SCHEMA_VERSION,
            "sources": sources,
        }
        manifest_text = (ready / f"preprocessing_manifest_{stamp}.json").read_text(encoding="utf-8")
        self.assertEqual(manifest_text, json.dumps(manifest, indent=2, ensure_ascii=True) + "\n")

        lines = ["Preprocessing complete"]
        for entry in sources:
            lines.append(f"- {entry['source']}: {entry['records_written']} written, {entry['records_skipped']} skipped")
            lines.extend(f"  - {path}" for path in entry["output_files"])
        self.assertEqual(stdout, "\n".join(lines) + "\n")

    def test_malformed_perplexity_timestamp_raises(self) -> None:
        perplexity = self.data_dir / "intake" / "perplexity"
        perplexity.mkdir(parents=True)
        _write_csv(perplexity / "Search_History.csv", ["QUERY_STRING", "CREATED"], [["q", "not-a-date"]])
        with self.assertRaises(ValueError):
            self._build()
