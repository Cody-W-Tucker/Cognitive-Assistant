#!/usr/bin/env python3
"""Tests for the CA-native recursive improvement runtime (first vertical slice).

Slice 1 covers: global transcript discovery (Hermes, Claude Code, Codex,
OpenCode only; Pi/Grok/Cursor explicitly excluded — Pi sessions are
machine/automation work and must not be analyzed; own sessions excluded),
headless proposal generation into XDG state without touching tracked files,
the apply sole-gate, and the experience compiler hook. No model calls.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

from core import improve

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_BIN = REPO_ROOT / "improve" / "bin" / "ca-improve.js"


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for line in lines:
            handle.write(json.dumps(line) + "\n")


def _make_fixture_home(root: Path) -> Path:
    """Build a fake HOME with one session per supported store plus traps."""
    home = root / "fakehome"
    # Pi trap (excluded): ~/.pi/agent/sessions/<escaped-cwd>/<ts>_<uuid>.jsonl
    # Pi sessions are machine/automation work and must not be analyzed, so
    # these rows must never surface from discovery even though the parser
    # internals are retained.
    _write_jsonl(
        home / ".pi" / "agent" / "sessions" / "-tmp-proj" / "2026-10-11T00-00-00_pi-1.jsonl",
        [
            {"type": "session", "cwd": "/tmp/proj", "id": "pi-1"},
            {"role": "user", "content": "help me refactor this"},
            {"role": "assistant", "content": "sure, here goes"},
        ],
    )
    # Claude Code: ~/.claude/projects/<munged>/<uuid>.jsonl
    _write_jsonl(
        home / ".claude" / "projects" / "-tmp-proj" / "claude-1.jsonl",
        [
            {"cwd": "/tmp/proj", "sessionId": "claude-1", "type": "user", "message": {"content": "fix the bug"}},
            {"cwd": "/tmp/proj", "sessionId": "claude-1", "type": "assistant", "message": {"content": "fixed"}},
        ],
    )
    # Codex: ~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<uuid>.jsonl
    _write_jsonl(
        home / ".codex" / "sessions" / "2026" / "10" / "11" / "rollout-001-codex-1.jsonl",
        [
            {"type": "session_meta", "cwd": "/tmp/proj", "id": "codex-1"},
            {"role": "user", "content": "add a test"},
        ],
    )
    # OpenCode (sqlite, v2 layout): ~/.local/share/opencode/opencode.db
    oc_db = home / ".local" / "share" / "opencode" / "opencode.db"
    oc_db.parent.mkdir(parents=True, exist_ok=True)
    import time as _time

    _now = int(_time.time())
    conn = sqlite3.connect(oc_db)
    conn.execute(
        "CREATE TABLE session_v2 (id TEXT PRIMARY KEY, project_id TEXT, directory TEXT,"
        " title TEXT, time_created INTEGER, time_updated INTEGER)"
    )
    conn.execute(
        "CREATE TABLE session_message (id TEXT PRIMARY KEY, session_id TEXT,"
        " type TEXT, seq INTEGER, time_created INTEGER, time_updated INTEGER, data TEXT)"
    )
    conn.execute(
        "INSERT INTO session_v2 VALUES ('opencode-1', 'p1', '/tmp/proj', 't', ?, ?)",
        (_now, _now),
    )
    conn.execute(
        "INSERT INTO session_message VALUES ('m1', 'opencode-1', 'user', 0, ?,"
        " ?, '{\"text\": \"review this diff\"}')",
        (_now, _now),
    )
    conn.commit()
    conn.close()
    # Hermes (sqlite): ~/.hermes/state.db
    h_db = home / ".hermes" / "state.db"
    h_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(h_db)
    conn.execute(
        "CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT, source TEXT,"
        " created_at INTEGER, updated_at INTEGER)"
    )
    conn.execute(
        "INSERT INTO sessions VALUES ('hermes-1', '/tmp/proj', 'cli', ?, ?)",
        (_now, _now),
    )
    conn.execute(
        "CREATE TABLE messages (id TEXT PRIMARY KEY, session_id TEXT, role TEXT, text BLOB)"
    )
    conn.execute(
        "INSERT INTO messages VALUES ('hm1', 'hermes-1', 'user', 'check the logs')"
    )
    conn.commit()
    conn.close()
    # Traps: excluded harnesses must never be read (Pi/Grok/Cursor).
    _write_jsonl(
        home / ".grok" / "sessions" / "grok-1.jsonl",
        [{"role": "user", "content": "grok session"}],
    )
    _write_jsonl(
        home / ".cursor" / "sessions" / "cursor-1.jsonl",
        [{"role": "user", "content": "cursor session"}],
    )
    # Trap: Pi must stay excluded even with a well-formed store present
    # (covered above); the runtime's own session (sentinel) must be self-excluded.
    _write_jsonl(
        home / ".pi" / "agent" / "sessions" / "-tmp-proj" / "2026-10-11T00-00-01_self-1.jsonl",
        [
            {"type": "session", "cwd": "/tmp/proj", "id": "self-1"},
            {"role": "user", "content": "<!-- ca-improve:self-session --> analyze this"},
        ],
    )
    return home


class ImproveDiscoveryTests(unittest.TestCase):
    def test_discovers_supported_fixture_stores_independent_of_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = _make_fixture_home(root)
            state_dir = root / "state"
            # Run from a CWD that holds no stores: discovery must be global.
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            result = improve.discover_transcripts(home=home, cwd=elsewhere, state_dir=state_dir)
            by_harness: dict[str, list[dict]] = {}
            for transcript in result["transcripts"]:
                by_harness.setdefault(transcript["harness"], []).append(transcript)
            # Default scope is Hermes/Claude/Codex/OpenCode only; Pi is excluded.
            for harness in ("claude", "codex", "opencode", "hermes"):
                self.assertIn(harness, by_harness, f"missing harness {harness}")
            self.assertNotIn("pi", by_harness, "Pi sessions must not be discovered")
            ids = {t["id"] for t in result["transcripts"]}
            self.assertNotIn("pi-1", ids)
            self.assertIn("pi", result["excluded"])
            # Every discovered path lives under the fixture HOME, never the CWD.
            for transcript in result["transcripts"]:
                location = transcript.get("path") or transcript.get("db", "")
                self.assertTrue(
                    str(location).startswith(str(home)),
                    f"{transcript['id']} not under fixture HOME: {location}",
                )

    def test_explicit_pi_harness_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = _make_fixture_home(root)
            with self.assertRaisesRegex(RuntimeError, "machine/automation"):
                improve.discover_transcripts(
                    home=home, cwd=root, state_dir=root / "state", harnesses=["pi"]
                )

    def test_sqlite_since_and_cursor_are_meaningful_global_scope(self) -> None:
        import time

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "fakehome"
            now_s = int(time.time())
            old_s = now_s - 90 * 86400
            oc_db = home / ".local" / "share" / "opencode" / "opencode.db"
            oc_db.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(oc_db)
            conn.execute(
                "CREATE TABLE session_v2 (id TEXT PRIMARY KEY, project_id TEXT, directory TEXT,"
                " title TEXT, time_created INTEGER, time_updated INTEGER)"
            )
            conn.execute(
                "INSERT INTO session_v2 VALUES ('opencode-old', 'p1', '/tmp/proj', 'old', ?, ?)",
                (old_s, old_s),
            )
            conn.execute(
                "INSERT INTO session_v2 VALUES ('opencode-new', 'p1', '/tmp/proj', 'new', ?, ?)",
                (now_s, now_s),
            )
            conn.commit()
            conn.close()
            h_db = home / ".hermes" / "state.db"
            h_db.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(h_db)
            conn.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT)")
            conn.execute("INSERT INTO sessions VALUES ('hermes-seen', '/tmp/proj')")
            conn.execute("INSERT INTO sessions VALUES ('hermes-fresh', '/tmp/proj')")
            conn.commit()
            conn.close()
            state_dir = root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "cursor.json").write_text(
                json.dumps({"analyzedIds": ["hermes-seen"]}), encoding="utf-8"
            )
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            result = improve.discover_transcripts(
                home=home, cwd=elsewhere, state_dir=state_dir, since="30d"
            )
            ids = {t["id"] for t in result["transcripts"]}
            # --since filters the old SQLite row where a committed timestamp exists.
            self.assertIn("opencode-new", ids)
            self.assertNotIn("opencode-old", ids)
            # Persistent cursor skips already-analyzed SQLite rows without timestamp guessing.
            self.assertIn("hermes-fresh", ids)
            self.assertNotIn("hermes-seen", ids)
            for transcript in result["transcripts"]:
                location = transcript.get("path") or transcript.get("db", "")
                self.assertTrue(str(location).startswith(str(home)))

    def test_excludes_grok_cursor_and_self_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = _make_fixture_home(root)
            result = improve.discover_transcripts(home=home, cwd=root, state_dir=root / "state")
            ids = {t["id"] for t in result["transcripts"]}
            harnesses = {t["harness"] for t in result["transcripts"]}
            self.assertNotIn("grok-1", ids)
            self.assertNotIn("cursor-1", ids)
            self.assertNotIn("self-1", ids)
            self.assertNotIn("pi-1", ids)
            self.assertNotIn("grok", harnesses)
            self.assertNotIn("cursor", harnesses)
            self.assertNotIn("pi", harnesses)
            self.assertIn("grok", result["excluded"])
            self.assertIn("cursor", result["excluded"])
            self.assertIn("pi", result["excluded"])

    def test_hermes_since_filters_old_vs_new_timestamps(self) -> None:
        import time

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "fakehome"
            now_s = int(time.time())
            old_s = now_s - 90 * 86400
            h_db = home / ".hermes" / "state.db"
            h_db.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(h_db)
            conn.execute(
                "CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT, source TEXT,"
                " created_at INTEGER, updated_at INTEGER)"
            )
            conn.execute(
                "INSERT INTO sessions VALUES ('hermes-old', '/tmp/proj', 'cli', ?, ?)",
                (old_s, old_s),
            )
            conn.execute(
                "INSERT INTO sessions VALUES ('hermes-new', '/tmp/proj', 'cli', ?, ?)",
                (now_s, now_s),
            )
            conn.execute(
                "CREATE TABLE messages (id TEXT PRIMARY KEY, session_id TEXT, role TEXT, text BLOB)"
            )
            conn.execute("INSERT INTO messages VALUES ('m-old', 'hermes-old', 'user', 'old task')")
            conn.execute("INSERT INTO messages VALUES ('m-new', 'hermes-new', 'user', 'new task')")
            conn.commit()
            conn.close()
            state_dir = root / "state"
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            result = improve.discover_transcripts(
                home=home, cwd=elsewhere, state_dir=state_dir, since="30d"
            )
            ids = {t["id"] for t in result["transcripts"]}
            self.assertIn("hermes-new", ids)
            self.assertNotIn("hermes-old", ids)
            for transcript in result["transcripts"]:
                location = transcript.get("path") or transcript.get("db", "")
                self.assertTrue(str(location).startswith(str(home)))

    def test_synthesize_emits_narrow_plans_annotation_owns_per_source_quotes(self) -> None:
        import subprocess as _sp

        node_script = (
            "import { synthesizeCandidates } from %r;\n" % str(REPO_ROOT / "improve" / "src" / "synthesize.js")
            + "import { buildMockFinalAnnotation } from %r;\n" % str(REPO_ROOT / "improve" / "src" / "annotate.js")
            + "const ledger = { clusters: [{ id: 'g-abc', proposedInstruction: 'exp-x',"
            " representativeQuote: 'FIRST-QUOTE', mistake: 'FIRST-MISTAKE',"
            " sources: ['s1','s2'], count: 2, eligible: true,"
            " perSource: { s1: { quote: 'QUOTE-ONE', mistake: 'MISTAKE-ONE' },"
            " s2: { quote: 'QUOTE-TWO', mistake: 'MISTAKE-TWO' } } }] };\n"
            "const evidenceIndex = new Map([['s1', [{ quote: 'QUOTE-ONE', effect: 'MOMENT-ONE' }]],"
            " ['s2', [{ quote: 'QUOTE-TWO', effect: 'MOMENT-TWO' }]]]);\n"
            "const plans = synthesizeCandidates(ledger, { evidenceIndex });\n"
            "const finals = plans.map((p) => buildMockFinalAnnotation(p, { ledger, evidenceIndex }));\n"
            "console.log(JSON.stringify({ plans, finals }));\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            probe = Path(directory) / "probe.mjs"
            probe.write_text(node_script, encoding="utf-8")
            proc = _sp.run(
                ["node", str(probe)], cwd=str(REPO_ROOT),
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(proc.returncode, 0, f"stderr: {proc.stderr}")
            payload = json.loads(proc.stdout.strip().splitlines()[-1])
            plans = payload["plans"]
            # Synthesis emits narrow plans only: no final record/evidence.
            self.assertEqual(len(plans), 1)
            for forbidden in ("record", "evidence", "title", "body", "counterevidence", "compilerImplication"):
                self.assertNotIn(forbidden, plans[0], f"synth plan must not carry {forbidden}")
            self.assertEqual(plans[0]["clusterId"], "g-abc")
            # Annotation owns the durable per-source quote mappings.
            finals = payload["finals"]
            by_source = {e["source"]: e for e in finals[0]["record"]["evidence"]}
            self.assertIn("s1", by_source)
            self.assertIn("s2", by_source)
            self.assertIn("QUOTE-ONE", by_source["s1"]["text"])
            self.assertIn("QUOTE-TWO", by_source["s2"]["text"])
            self.assertNotIn("FIRST-QUOTE", by_source["s2"]["text"])
            self.assertIn("MOMENT-ONE", by_source["s1"].get("moment", ""))
            self.assertIn("MOMENT-TWO", by_source["s2"].get("moment", ""))

    def test_review_skip_does_not_satisfy_required_decision(self) -> None:
        import io
        import sys
        from unittest.mock import patch

        proposal = {
            "id": "prop-skip",
            "edits": [
                {
                    "id": "e1", "title": "t", "kind": "add", "rationale": "why",
                    "evidence": [{"source": "s1", "text": "ev"}],
                    "record": {"id": "rec-1", "title": "rt", "body": "rb",
                               "sources": ["s1"], "evidence": []},
                    "stagedArtifact": "staged", "diff": "diff",
                }
            ],
        }
        with patch.object(sys.stdin, "isatty", return_value=True):
            with patch("builtins.input", return_value="skip"):
                captured = io.StringIO()
                with patch.object(sys, "stdout", captured):
                    decisions = improve.review_in_terminal(proposal)
        out = captured.getvalue()
        self.assertEqual(decisions, {"e1": "rejected"})
        self.assertIn("rejected", out.lower())
        self.assertIn("skip", out.lower())
        # Programmatic skip must not satisfy the apply gate either.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir, _proposal = _run_fixture_proposal(root)
            with self.assertRaisesRegex(RuntimeError, "bad verdict|rejected|accepted"):
                improve.apply(
                    state_dir=state_dir,
                    experience_root=root / "exp",
                    decisions={"e1": "skipped"},
                )


def _git_tracked_status() -> str:
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


class ImproveRunTests(unittest.TestCase):
    def test_headless_stdout_is_clean_machine_readable_json(self) -> None:
        import shutil

        node = shutil.which("node")
        self.assertIsNotNone(node, "node required for runtime stdout check")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = _make_fixture_home(root)
            state_dir = root / "xdg" / "improve"
            proc = subprocess.run(
                [node, str(RUNTIME_BIN), "discover", "--home", str(home),
                 "--state-dir", str(state_dir), "--since", "30d"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            # stdout must be exactly one JSON document; progress stays on stderr.
            lines = proc.stdout.strip().splitlines()
            self.assertEqual(len(lines), 1, f"expected exactly one JSON stdout line, got {len(lines)}")
            parsed = json.loads(lines[0])
            self.assertIn("transcripts", parsed)
            self.assertTrue(proc.stdout.strip().startswith("{"))

    def test_python_improve_run_stdout_is_single_json_document(self) -> None:
        import sys

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = _make_fixture_home(root)
            state_dir = root / "xdg" / "improve"
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            env = dict(os.environ)
            env["CA_IMPROVE_HOME"] = str(home)
            env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
            proc = subprocess.run(
                [sys.executable, "-m", "core", "improve-run", "--headless",
                 "--state-dir", str(state_dir), "--analyzer", "mock"],
                cwd=str(elsewhere),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(proc.returncode, 0, f"stderr: {proc.stderr}")
            lines = proc.stdout.strip().splitlines()
            self.assertEqual(len(lines), 1, f"expected exactly one JSON stdout line, got {len(lines)}: {proc.stdout!r}")
            parsed = json.loads(lines[0])
            self.assertIn("edits", parsed)
            self.assertIn("stats", parsed)

    def test_headless_run_writes_proposal_without_touching_tracked_files(self) -> None:
        before = _git_tracked_status()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = _make_fixture_home(root)
            _add_eligible_codex_sessions(home)
            state_dir = root / "xdg" / "improve"
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            proposal = improve.run_headless(
                home=home, cwd=elsewhere, state_dir=state_dir, analyzer="mock"
            )
            self.assertFalse(proposal.get("reviewed", True))
            self.assertGreaterEqual(len(proposal["edits"]), 1)
            edit = proposal["edits"][0]
            for key in ("id", "evidence", "record", "stagedArtifact", "diff"):
                self.assertIn(key, edit, f"edit missing {key}")
            self.assertTrue((state_dir / "proposal.json").exists())
            self.assertTrue((state_dir / "ledger.json").exists())
            self.assertTrue((state_dir / "cursor.json").exists())
            self.assertGreaterEqual(len(list((state_dir / "evidence").glob("*.json"))), 1)
        self.assertEqual(_git_tracked_status(), before)


def _add_eligible_codex_sessions(home: Path) -> None:
    """Add substantial Codex sessions so mock analysis meets the recurrence floor legitimately.

    The base fixture sessions are intentionally trivial (skipped by analysis).
    These two sessions carry 1 user turn + 3 tool calls each, so mockInvoke
    yields the same canonical gap for both and the fold floor (minGapEvidence=2)
    is met via the plan->stage->measure->annotate path. No pipeline fabrication.
    """
    for i in range(2):
        _write_jsonl(
            home / ".codex" / "sessions" / "2026" / "10" / "12" / f"rollout-eligible-{i}-codex-eligible.jsonl",
            [
                {"type": "session_meta", "cwd": "/tmp/proj", "id": f"codex-eligible-{i}"},
                {"role": "user", "content": "bootstrap context please"},
                {"kind": "tool", "name": "read", "input": {"file_path": "a"}},
                {"kind": "tool", "name": "search", "input": {"query": "b"}},
                {"kind": "tool", "name": "test", "input": {"command": "c"}},
            ],
        )


def _run_fixture_proposal(root: Path) -> tuple[Path, dict]:
    home = _make_fixture_home(root)
    _add_eligible_codex_sessions(home)
    state_dir = root / "xdg" / "improve"
    elsewhere = root / "elsewhere"
    elsewhere.mkdir(exist_ok=True)
    proposal = improve.run_headless(
        home=home, cwd=elsewhere, state_dir=state_dir, analyzer="mock"
    )
    assert len(proposal["edits"]) >= 1
    return state_dir, proposal


class ImproveApplyTests(unittest.TestCase):
    def test_apply_refuses_missing_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "no proposal"):
                improve.apply(
                    state_dir=Path(directory) / "empty-state",
                    experience_root=Path(directory) / "exp",
                    decisions={"e1": "accepted"},
                )

    def test_apply_refuses_unreviewed_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir, _ = _run_fixture_proposal(root)
            # No decisions vector and no TTY: the gate must refuse, writing nothing.
            with self.assertRaisesRegex(RuntimeError, "unreviewed"):
                improve.apply(
                    state_dir=state_dir,
                    experience_root=root / "exp",
                    decisions=None,
                )
            self.assertFalse((root / "exp").exists())

    def test_apply_accepted_writes_only_approved_source_and_staged_artifact(self) -> None:
        before = _git_tracked_status()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir, proposal = _run_fixture_proposal(root)
            edit = proposal["edits"][0]
            record_id = edit["record"]["id"]
            result = improve.apply(
                state_dir=state_dir,
                experience_root=root / "exp",
                decisions={edit["id"]: "accepted"},
            )
            self.assertEqual(result["accepted"], [edit["id"]])
            authored = root / "exp" / "authored" / f"{record_id}.md"
            staged = root / "exp" / "staged" / f"{record_id}.md"
            self.assertTrue(authored.exists())
            self.assertTrue(staged.exists())
            self.assertIn(record_id, authored.read_text(encoding="utf-8"))
            self.assertEqual(staged.read_text(encoding="utf-8"), edit["stagedArtifact"])
            # Exactly the two approved files -- nothing else.
            written = sorted(p.relative_to(root / "exp").as_posix() for p in [
                authored, staged,
            ])
            all_files = sorted(
                p.relative_to(root / "exp").as_posix()
                for p in (root / "exp").rglob("*") if p.is_file()
            )
            self.assertEqual(all_files, written)
            # Re-apply is refused: the proposal was consumed by the gate.
            with self.assertRaisesRegex(RuntimeError, "already applied"):
                improve.apply(
                    state_dir=state_dir,
                    experience_root=root / "exp",
                    decisions={edit["id"]: "accepted"},
                )
        self.assertEqual(_git_tracked_status(), before)

    def test_review_in_terminal_shows_full_evidence_record_and_diff(self) -> None:
        import io
        from unittest.mock import patch

        long_text = "EVIDENCE-" + "x" * 500
        record_body = "RECORD-BODY-" + "y" * 800
        staged = "STAGED-" + "z" * 3000
        diff = "DIFF-" + "w" * 3000
        proposal = {
            "id": "prop-tui",
            "edits": [
                {
                    "id": "e1",
                    "title": "tui title",
                    "kind": "add",
                    "rationale": "why",
                    "evidence": [
                        {"source": f"s{i}", "text": f"{long_text}-{i}"} for i in range(7)
                    ],
                    "record": {
                        "id": "rec-1",
                        "title": "rec title",
                        "body": record_body,
                        "sources": ["s0"],
                        "evidence": [{"source": "s0", "text": long_text}],
                    },
                    "stagedArtifact": staged,
                    "diff": diff,
                }
            ],
        }
        import sys

        with patch.object(sys.stdin, "isatty", return_value=True):
            with patch("builtins.input", return_value="accept"):
                captured = io.StringIO()
                with patch.object(sys, "stdout", captured):
                    decisions = improve.review_in_terminal(proposal)
        out = captured.getvalue()
        self.assertEqual(decisions, {"e1": "accepted"})
        for i in range(7):
            self.assertIn(f"{long_text}-{i}", out)
        self.assertIn(record_body, out)
        self.assertIn(staged, out)
        self.assertIn(diff, out)

    def test_apply_rejects_unknown_decision_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir, proposal = _run_fixture_proposal(root)
            # Normalize fixture to a single edit with id e1.
            data = json.loads((state_dir / "proposal.json").read_text(encoding="utf-8"))
            data["edits"][0]["id"] = "e1"
            data["edits"] = data["edits"][:1]
            data.pop("appliedAt", None)
            (state_dir / "proposal.json").write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unknown edit"):
                improve.apply(
                    state_dir=state_dir,
                    experience_root=root / "exp",
                    decisions={"unknown": "accepted"},
                )
            self.assertFalse((root / "exp").exists())

    def test_apply_rejected_records_rejection_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir, proposal = _run_fixture_proposal(root)
            edit = proposal["edits"][0]
            result = improve.apply(
                state_dir=state_dir,
                experience_root=root / "exp",
                decisions={edit["id"]: "rejected:too-narrow"},
            )
            self.assertEqual(result["rejected"], [edit["id"]])
            self.assertFalse((root / "exp" / "authored").exists())
            self.assertFalse((root / "exp" / "staged").exists())
            rejections = (state_dir / "rejections.jsonl").read_text(encoding="utf-8")
            self.assertIn(edit["id"], rejections)
            self.assertIn("too-narrow", rejections)


    def test_apply_refuses_unannotated_synth_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir = root / "xdg" / "improve"
            state_dir.mkdir(parents=True, exist_ok=True)
            proposal = {
                "id": "prop-unannotated",
                "appliedAt": None,
                "edits": [
                    {
                        "id": "e1",
                        "kind": "add",
                        "clusterId": "g-aaa",
                        "provisionalIntent": "Bootstrap context once",
                        "provisionalSources": ["s1", "s2"],
                    }
                ],
            }
            (state_dir / "proposal.json").write_text(json.dumps(proposal), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "annotation|annotat"):
                improve.apply(
                    state_dir=state_dir,
                    experience_root=root / "exp",
                    decisions={"e1": "accepted"},
                )
            self.assertFalse((root / "exp").exists())

    def test_apply_staged_failure_rolls_back_authored_half(self) -> None:
        from unittest.mock import patch

        from core import experience

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir, proposal = _run_fixture_proposal(root)
            edit = proposal["edits"][0]
            record_id = edit["record"]["id"]
            authored = root / "exp" / "authored" / f"{record_id}.md"
            staged = root / "exp" / "staged" / f"{record_id}.md"
            self.assertFalse(authored.exists())
            self.assertFalse(staged.exists())
            with patch.object(
                experience, "write_staged_artifact", side_effect=RuntimeError("staged boom")
            ):
                with self.assertRaisesRegex(RuntimeError, "staged boom"):
                    improve.apply(
                        state_dir=state_dir,
                        experience_root=root / "exp",
                        decisions={edit["id"]: "accepted"},
                    )
            self.assertFalse(authored.exists(), "authored half must be rolled back")
            self.assertFalse(staged.exists(), "staged half must not exist")

    def test_apply_dry_run_accepts_valid_proposal_with_deterministic_record_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir, proposal = _run_fixture_proposal(root)
            edit = proposal["edits"][0]
            edit_id = edit["id"]
            record_id = edit["record"]["id"]
            # Deterministic annotation-authored id, never the run-local plan id.
            self.assertTrue(record_id.startswith("exp-"))
            self.assertNotEqual(record_id, edit_id)
            result = improve.apply(
                state_dir=state_dir,
                experience_root=root / "exp",
                decisions={edit_id: "accepted"},
                dry_run=True,
            )
            self.assertEqual(result["accepted"], [edit_id])
            self.assertEqual(result["written"], [])
            self.assertTrue(result["dry_run"])
            self.assertFalse((root / "exp").exists(), "dry run must write nothing")

    def test_apply_rejects_accepted_keep_missing_record_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir = root / "xdg" / "improve"
            state_dir.mkdir(parents=True, exist_ok=True)
            proposal = {
                "id": "prop-no-record-id",
                "appliedAt": None,
                "edits": [
                    {
                        "id": "e1",
                        "kind": "add",
                        "annotation": {"verdict": "keep", "reason": "m"},
                        "record": {
                            "title": "t",
                            "body": "b",
                            "sources": ["s1", "s2"],
                            "clusterId": "g-aaa",
                            "evidence": [],
                            "counterevidence": "none observed",
                            "compilerImplication": "compiler appends",
                        },
                        "stagedArtifact": "artifact",
                        "diff": "diff",
                    }
                ],
            }
            (state_dir / "proposal.json").write_text(json.dumps(proposal), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "missing id"):
                improve.apply(
                    state_dir=state_dir,
                    experience_root=root / "exp",
                    decisions={"e1": "accepted"},
                )
            self.assertFalse((root / "exp").exists())


class ImproveCompilerTests(unittest.TestCase):
    def test_canonical_staged_experience_is_compiler_consumed(self) -> None:
        from unittest.mock import patch

        from core import experience
        from core.config import Config
        from core.prompt_creator import load_dataset_context

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir, proposal = _run_fixture_proposal(root)
            edit = proposal["edits"][0]
            improve.apply(
                state_dir=state_dir,
                experience_root=root / "exp",
                decisions={edit["id"]: "accepted"},
            )
            # The compiler hook consumes the staged artifact through the real
            # prompt-creator path, with the experience root pointed at tmp.
            with patch.object(
                experience, "experience_root", return_value=root / "exp"
            ):
                block = experience.compile_experience_block(root / "exp")
                self.assertIn(edit["record"]["id"], block)
                self.assertIn(edit["stagedArtifact"].splitlines()[0], block)
                config = Config.from_profile("existential")
                dataset = root / "questions_with_answers_qmd_20260926_000000.csv"
                dataset.write_text(
                    "Category,Goal,Element,Question 1,AI_Answer 1\n"
                    "Continuity,Ground the answer,Decision,What changed?,A concrete answer\n",
                    encoding="utf-8",
                )
                with patch.object(
                    config, "get_most_recent_file", return_value=dataset
                ):
                    context = load_dataset_context(config)
                self.assertIn("What changed?", context)
                self.assertIn(edit["record"]["id"], context)

    def test_compiler_consumes_authored_alongside_staged(self) -> None:
        from unittest.mock import patch

        from core import experience

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir, proposal = _run_fixture_proposal(root)
            edit = proposal["edits"][0]
            improve.apply(
                state_dir=state_dir,
                experience_root=root / "exp",
                decisions={edit["id"]: "accepted"},
            )
            with patch.object(
                experience, "experience_root", return_value=root / "exp"
            ):
                block = experience.compile_experience_block(root / "exp")
                # Durable authored record must be present alongside staged artifact.
                self.assertIn("## Experience record:", block)
                self.assertIn("## Staged experience:", block)
                self.assertIn(edit["record"]["id"], block)

    def test_soul_stays_baseline_only(self) -> None:
        soul_path = (
            REPO_ROOT / "workspaces" / "alignment" / "artifacts" / "SOUL.md"
        )
        self.assertTrue(soul_path.exists(), "SOUL baseline must exist for this test")
        before = soul_path.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir, proposal = _run_fixture_proposal(root)
            edit = proposal["edits"][0]
            improve.apply(
                state_dir=state_dir,
                experience_root=root / "exp",
                decisions={edit["id"]: "accepted"},
            )
        self.assertEqual(soul_path.read_text(encoding="utf-8"), before)


class ImproveCLIRegistrationTests(unittest.TestCase):
    def test_improve_run_requires_headless(self) -> None:
        from core.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["improve-run", "--headless"])
        self.assertEqual(args.command, "improve-run")
        self.assertTrue(args.headless)

    def test_improve_apply_accepts_decisions_vector(self) -> None:
        from core.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(
            ["improve-apply", "--decisions", "e1=accepted"]
        )
        self.assertEqual(args.command, "improve-apply")
        self.assertEqual(args.decisions, ["e1=accepted"])

    def test_decisions_hint_uses_actual_edit_ids(self) -> None:
        from core.cli import _decisions_hint

        hint = _decisions_hint({"edits": [{"id": "e7"}, {"id": "e8"}]})
        self.assertIn("e7=accepted", hint)
        self.assertIn("e8=accepted", hint)
        self.assertNotIn("e1=accepted", hint)

    def test_decisions_hint_empty_proposal_uses_neutral_placeholder(self) -> None:
        from core.cli import _decisions_hint

        hint = _decisions_hint({"edits": []})
        self.assertNotIn("e1=accepted", hint)


if __name__ == "__main__":
    unittest.main()
