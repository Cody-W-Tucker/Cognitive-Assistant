#!/usr/bin/env python3
"""Private lineage journal: append-only JSONL plus derived views."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


def _mp_append_worker(args: tuple[str, int, int]) -> list[str]:
    """Multiprocessing helper: append ``count`` events, return ids.

    Module-level for spawn pickling. Each worker appends ``count`` events
    with deterministic safe ``run_id`` values.
    """
    from pathlib import Path as _Path

    from core import journal as _journal

    state_str, worker_id, count = args
    state = _Path(state_str)
    ids: list[str] = []
    for i in range(count):
        evt = _journal.append_event(state, "run_completed", {"run_id": f"mp-{worker_id}-{i}"})
        ids.append(str(evt["id"]))
    return ids


class JournalNestedForbiddenKeysTests(unittest.TestCase):
    def test_nested_forbidden_keys_rejected_at_any_depth(self) -> None:
        from core import journal

        nested_cases: list[dict] = [
            {"db_password": "safe-ref-1"},
            {"outer": {"db_password": "safe-ref-1"}},
            {"l1": {"l2": {"db_password": "safe-ref-1"}}},
            {"l1": {"l2": {"l3": {"db_password": "safe-ref-1"}}}},
            {"transcript_text": "safe-ref-1"},
            {"outer": {"transcript_text": "safe-ref-1"}},
            {"l1": {"l2": {"transcript_text": "safe-ref-1"}}},
            {"prompt_content": "safe-ref-1"},
            {"outer": {"prompt_content": "safe-ref-1"}},
            {"l1": {"l2": {"l3": {"prompt_content": "safe-ref-1"}}}},
            {"outer": {"api_key": "safe-ref-1"}},
            {"l1": {"l2": {"api_key": "safe-ref-1"}}},
            {"refs": [{"prompt_content": "safe-ref-1"}]},
            {"refs": [{"outer": {"transcript_text": "safe-ref-1"}}]},
        ]
        for payload in nested_cases:
            with self.subTest(payload=payload):
                with tempfile.TemporaryDirectory() as directory:
                    state = Path(directory) / "state"
                    with self.assertRaises((ValueError, RuntimeError)):
                        journal.append_event(state, "run_completed", payload)

    def test_normalized_equivalent_keys_rejected_at_any_depth(self) -> None:
        from core import journal

        normalized_cases: list[dict] = [
            {"DB_PASSWORD": "safe-ref-1"},
            {"outer": {"DB_PASSWORD": "safe-ref-1"}},
            {"db-password": "safe-ref-1"},
            {"outer": {"db-password": "safe-ref-1"}},
            {"api-key": "safe-ref-1"},
            {"outer": {"api-key": "safe-ref-1"}},
            {"l1": {"l2": {"api-key": "safe-ref-1"}}},
            {"API KEY": "safe-ref-1"},
            {"outer": {"API KEY": "safe-ref-1"}},
            {"transcript-text": "safe-ref-1"},
            {"outer": {"transcript-text": "safe-ref-1"}},
            {"TRANSCRIPT_TEXT": "safe-ref-1"},
            {"outer": {"TRANSCRIPT_TEXT": "safe-ref-1"}},
            {"prompt-content": "safe-ref-1"},
            {"outer": {"prompt-content": "safe-ref-1"}},
            {"PROMPT_CONTENT": "safe-ref-1"},
            {"l1": {"l2": {"PROMPT_CONTENT": "safe-ref-1"}}},
        ]
        for payload in normalized_cases:
            with self.subTest(payload=payload):
                with tempfile.TemporaryDirectory() as directory:
                    state = Path(directory) / "state"
                    with self.assertRaises((ValueError, RuntimeError)):
                        journal.append_event(state, "run_completed", payload)


class JournalMultiprocessingRaceTests(unittest.TestCase):
    def test_multiprocessing_append_event_ids_unique_and_views_complete(self) -> None:
        import multiprocessing as mp

        from core import journal

        workers = 8
        per_worker = 5
        total = workers * per_worker
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            ctx = mp.get_context("spawn")
            with ctx.Pool(processes=workers) as pool:
                results = pool.map(
                    _mp_append_worker,
                    [(str(state), w, per_worker) for w in range(workers)],
                )
            flat_ids = [i for sub in results for i in sub]
            self.assertEqual(len(flat_ids), total)
            self.assertEqual(
                len(set(flat_ids)), total, "event IDs must be unique under concurrent appends"
            )
            events_path = state / "journal" / "events.jsonl"
            physical = [
                line for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()
            ]
            self.assertEqual(len(physical), total, "JSONL physical count must equal events")
            events = journal.read_events(state)
            self.assertEqual(len(events), total)
            summary = journal.compact(state)
            self.assertEqual(summary["event_count"], total)
            current = json.loads((state / "journal" / "current.json").read_text(encoding="utf-8"))
            self.assertEqual(current["event_count"], total)


class JournalAppendCompactTests(unittest.TestCase):
    def test_append_and_compact_is_deterministic(self) -> None:
        from core import journal

        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            journal.append_event(state, "run_completed", {"run_id": "run-1"})
            journal.append_event(state, "proposal_created", {"proposal_id": "prop-1", "edit_count": 1})
            first = journal.compact(state)
            current_text = (state / "journal" / "current.json").read_text(encoding="utf-8")
            bootstrap_text = (state / "journal" / "bootstrap.md").read_text(encoding="utf-8")
            second = journal.compact(state)
            self.assertEqual(first, second)
            self.assertEqual(current_text, (state / "journal" / "current.json").read_text(encoding="utf-8"))
            self.assertEqual(bootstrap_text, (state / "journal" / "bootstrap.md").read_text(encoding="utf-8"))
            # Append-only history preserved.
            lines = (state / "journal" / "events.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertIn("run_completed", lines[0])
            # Views are generated, history is append-only.
            current = json.loads(current_text)
            self.assertEqual(current["event_count"], 2)
            self.assertIn("generated", json.dumps(current).lower() + bootstrap_text.lower())

    def test_rejects_forbidden_content(self) -> None:
        from core import journal

        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            with self.assertRaises((ValueError, RuntimeError)):
                journal.append_event(state, "run_completed", {"note": "/home/user/secret/transcript.txt"})
            with self.assertRaises((ValueError, RuntimeError)):
                journal.append_event(state, "run_completed", {"transcript": "raw user text"})
            with self.assertRaises((ValueError, RuntimeError)):
                journal.append_event(state, "run_completed", {"prompt": "do this"})
            with self.assertRaises((ValueError, RuntimeError)):
                journal.append_event(state, "run_completed", {"api_key": "sk-abcdefgh12345678"})
            with self.assertRaises((ValueError, RuntimeError)):
                journal.append_event(state, "run_completed", {"soul_text": "x" * 3000})
            # No journal dir artefacts from rejected writes beyond empty init.
            journal_path = state / "journal" / "events.jsonl"
            if journal_path.exists():
                content = journal_path.read_text(encoding="utf-8")
                self.assertNotIn("/home/user", content)
                self.assertNotIn("sk-abcdefgh", content)

    def test_malformed_lines_tolerant_and_compact_does_not_gc(self) -> None:
        from core import journal

        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            journal.append_event(state, "run_completed", {"run_id": "run-1"})
            # Protected state outside journal with current behavior.
            (state / "evidence").mkdir(parents=True, exist_ok=True)
            (state / "evidence" / "s1.json").write_text('{"ok": true}', encoding="utf-8")
            (state / "proposal.json").write_text('{"id": "p"}', encoding="utf-8")
            (state / "ledger.json").write_text('{"clusters": []}', encoding="utf-8")
            (state / "open-gaps.json").write_text('{"gaps": []}', encoding="utf-8")
            (state / "cursor.json").write_text('{"analyzedIds": []}', encoding="utf-8")
            # Corrupt the JSONL with malformed lines.
            with open(state / "journal" / "events.jsonl", "a", encoding="utf-8") as handle:
                handle.write("not-json{{{\n")
                handle.write('{"type": "bogus"}\n')
            summary = journal.compact(state)
            self.assertGreaterEqual(summary["event_count"], 1)
            # Compact tolerates malformed; protected files remain.
            self.assertTrue((state / "evidence" / "s1.json").exists())
            self.assertTrue((state / "proposal.json").exists())
            self.assertTrue((state / "ledger.json").exists())
            self.assertTrue((state / "cursor.json").exists())
            # Runtime still works after corruption: another append succeeds.
            journal.append_event(state, "run_completed", {"run_id": "run-2"})
            events = journal.read_events(state)
            self.assertGreaterEqual(len(events), 2)

    def test_event_ids_unique_with_malformed_lines(self) -> None:
        from core import journal

        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            first = journal.append_event(state, "run_completed", {"run_id": "run-1"})
            events_path = state / "journal" / "events.jsonl"
            before = events_path.read_text(encoding="utf-8")
            with open(events_path, "a", encoding="utf-8") as handle:
                handle.write("not-json{{{\n")
                handle.write('{"type": "bogus"}\n')
            # Append-only: existing history untouched, next id skips physical lines.
            second = journal.append_event(state, "run_completed", {"run_id": "run-2"})
            self.assertNotEqual(first["id"], second["id"])
            raw_lines = [
                line for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()
            ]
            self.assertTrue(events_path.read_text(encoding="utf-8").startswith(before))
            self.assertEqual(len(raw_lines), 4)
            ids = [json.loads(line).get("id") for line in raw_lines if line.strip().startswith("{")]
            ids = [i for i in ids if i]
            # Parsed valid ids remain unique (malformed lines carry no id).
            self.assertEqual(len(set(ids)), len(ids))

    def test_compact_excludes_unsafe_handwritten_payload(self) -> None:
        from core import journal

        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            journal.append_event(state, "run_completed", {"run_id": "run-1"})
            secret = "sk-abcdefgh12345678"
            with open(state / "journal" / "events.jsonl", "a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "id": "evt-000099",
                            "type": "run_completed",
                            "at": "2026-01-01T00:00:00+00:00",
                            "payload": {
                                "run_id": "/abs/path/secret",
                                "transcript": "raw user text",
                                "note": secret,
                            },
                        }
                    )
                    + "\n"
                )
            summary = journal.compact(state)
            self.assertEqual(summary["event_count"], 1)
            current_text = (state / "journal" / "current.json").read_text(encoding="utf-8")
            bootstrap_text = (state / "journal" / "bootstrap.md").read_text(encoding="utf-8")
            self.assertNotIn(secret, current_text + bootstrap_text)
            self.assertNotIn("/abs/path/secret", current_text + bootstrap_text)
            self.assertNotIn("raw user text", current_text + bootstrap_text)

    def test_views_grow_with_history_but_still_refuse_unsafe_text(self) -> None:
        from core import journal

        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            for i in range(200):
                journal.append_event(state, "run_completed", {"run_id": f"run-{i:04d}-" + "x" * 150})
            summary = journal.compact(state)
            self.assertEqual(summary["event_count"], 200)
            self.assertGreater(len((state / "journal" / "current.json").read_text()), journal.MAX_STRING_CHARS)
            with self.assertRaises(ValueError):
                journal.append_event(state, "run_completed", {"run_id": "sk-abcdefgh12345678"})
    def test_cli_journal_compact(self) -> None:
        import os
        from unittest import mock

        from core import cli as cli_mod
        from core import journal

        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(os.environ, {"CA_HOME": directory}):
            state = Path(directory) / "improve"
            journal.append_event(state, "run_completed", {"run_id": "run-1"})
            (state / "journal" / "current.json").unlink()
            self.assertEqual(cli_mod.main(["journal-compact"]), 0)
            self.assertTrue((state / "journal" / "current.json").exists())
            self.assertTrue((state / "journal" / "bootstrap.md").exists())


if __name__ == "__main__":
    unittest.main()
