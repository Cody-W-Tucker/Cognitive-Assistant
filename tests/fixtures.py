#!/usr/bin/env python3
"""Shared fixtures: an isolated CA home, a bootstrap SOUL, and a fake Langfuse holding sessions."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock
from urllib.parse import parse_qs, urlparse

from core import improve, paths
from core.cli import main


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def run_cli(argv: List[str]) -> tuple[int, str, str]:
    """Run ``python -m core`` in-process; return the exit code, stdout and stderr."""
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


class FakeLangfuse:
    """Serves ``/api/public/v2/observations`` over fixture observations, like the real instance.

    Supports the filters the runtime uses (sessionId, name, isRootObservation,
    fromStartTime) and cursor paging; the runtime finds it via LANGFUSE_BASE_URL.
    """

    def __init__(self) -> None:
        self.observations: List[Dict[str, Any]] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:  # quiet test output
                pass

            def do_GET(self) -> None:
                url = urlparse(self.path)
                query = {key: values[0] for key, values in parse_qs(url.query).items()}
                status, body = fake._page(url.path, query)
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"

    @property
    def env(self) -> Dict[str, str]:
        return {"LANGFUSE_BASE_URL": self.url, "LANGFUSE_PUBLIC_KEY": "pk-test", "LANGFUSE_SECRET_KEY": "sk-test"}

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def _page(self, path: str, query: Dict[str, str]) -> tuple[int, Dict[str, Any]]:
        if path != "/api/public/v2/observations":
            return 404, {"message": "not found"}

        def keep(row: Dict[str, Any]) -> bool:
            return (
                ("sessionId" not in query or row["sessionId"] == query["sessionId"])
                and ("name" not in query or row["name"] == query["name"])
                and ("isRootObservation" not in query or str(row["isRootObservation"]).lower() == query["isRootObservation"])
                and ("fromStartTime" not in query or row["startTime"] >= query["fromStartTime"])
            )

        rows = sorted((row for row in self.observations if keep(row)), key=lambda row: row["startTime"], reverse=True)
        offset, limit = int(query.get("cursor", 0)), int(query.get("limit", 50))
        meta = {"cursor": str(offset + limit)} if offset + limit < len(rows) else {}
        return 200, {"data": rows[offset : offset + limit], "meta": meta}

    def add_claude_session(self, session_id: str, *, user: str = "bootstrap context please", start: datetime | None = None) -> None:
        """One finished Claude Code turn with three tool calls (enough to pass the trivial-session gate)."""
        begin = start or datetime.now(timezone.utc) - timedelta(days=2)
        root = f"{session_id}-root"
        self.observations.append(
            {
                "id": root, "traceId": f"{session_id}-trace", "sessionId": session_id, "type": "SPAN",
                "name": "Conversational Turn", "isRootObservation": True, "environment": "default",
                "startTime": _iso(begin), "endTime": _iso(begin + timedelta(minutes=1)),
                "metadata": {"source": "claude-code", "cwd": "/tmp/proj"},
                "input": json.dumps({"role": "user", "content": user}),
                "output": json.dumps({"role": "assistant", "content": "done"}),
            }
        )
        for index, name in enumerate(("read", "search", "test")):
            self.observations.append(
                {
                    "id": f"{root}-tool{index}", "traceId": f"{session_id}-trace", "sessionId": session_id,
                    "type": "TOOL", "name": f"Tool: {name}", "isRootObservation": False, "parentObservationId": root,
                    "environment": "default", "startTime": _iso(begin + timedelta(seconds=index + 1)),
                    "endTime": _iso(begin + timedelta(seconds=index + 2)), "metadata": {},
                    "input": "{}", "output": json.dumps("ok"),
                }
            )

    def add_eligible_sessions(self) -> None:
        """Two substantial sessions; the mock analyzer reports the same gap in both,
        which meets the default two-session evidence floor."""
        for i in range(2):
            self.add_claude_session(f"eligible-{i}")


class CAHomeTestCase(unittest.TestCase):
    """Runs each test against a fresh CA home, bootstrap SOUL and fake Langfuse, never the real ones."""

    BOOTSTRAP_SOUL = "# SOUL.md\n\nBootstrap voice.\n"

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.ca_home = self.root / "ca"
        self.bootstrap = self.root / "bootstrap" / "SOUL.md"
        self.bootstrap.parent.mkdir()
        self.bootstrap.write_text(self.BOOTSTRAP_SOUL, encoding="utf-8")
        self.langfuse = FakeLangfuse()
        self.addCleanup(self.langfuse.close)
        self._env = mock.patch.dict(os.environ, {"CA_HOME": str(self.ca_home), **self.langfuse.env})
        self._env.start()
        self._soul = mock.patch.object(paths, "BOOTSTRAP_SOUL_PATH", self.bootstrap)
        self._soul.start()

    def tearDown(self) -> None:
        self._soul.stop()
        self._env.stop()
        self._tmp.cleanup()

    def run_mock_proposal(self) -> dict:
        """A headless mock-analyzer run over sessions that yield at least one candidate."""
        self.langfuse.add_eligible_sessions()
        proposal = improve.run(analyzer="mock")
        self.assertGreaterEqual(len(proposal["edits"]), 1)
        return proposal


class FakeLLM:
    """Stands in for ``core.llm.complete``: records each prompt and answers via ``reply(prompt, label)``."""

    def __init__(self, reply) -> None:
        self.reply = reply
        self.calls: list[dict] = []

    async def __call__(self, prompt: str, *, provider: str = "anthropic", min_chars: int = 1, label: str = "reply") -> str:
        self.calls.append({"prompt": prompt, "provider": provider, "label": label})
        text = self.reply(prompt, label)
        if len(text) < min_chars:
            raise ValueError(f"{label} from {provider} is unexpectedly short ({len(text)} chars)")
        return text


class RepoSandboxTestCase(CAHomeTestCase):
    """Runs bootstrap stages against a copy of the repo's prompts in a temp dir, never the checkout."""

    def setUp(self) -> None:
        super().setUp()
        import shutil

        self.repo = self.root / "repo"
        shutil.copytree(paths.REPO_ROOT / "profiles", self.repo / "profiles")
        artifacts = self.repo / "workspaces" / "alignment" / "artifacts"
        patches = {
            "REPO_ROOT": self.repo,
            "SKILLS_DIR": self.repo / "workspaces" / "skills",
            "ALIGNMENT_PROMPTS_DIR": self.repo / "profiles" / "alignment" / "prompts",
            "ALIGNMENT_ARTIFACTS_DIR": artifacts,
            "BOOTSTRAP_SOUL_PATH": artifacts / "SOUL.md",
            "INTERACTION_POSTURE_PATH": artifacts / "INTERACTION_POSTURE.md",
            "ALIGNMENT_SPEC_PATH": artifacts / "alignment_spec.md",
        }
        self._paths = [mock.patch.object(paths, name, value) for name, value in patches.items()]
        for patcher in self._paths:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in self._paths:
            patcher.stop()
        super().tearDown()

    def fake_llm(self, reply) -> FakeLLM:
        fake = FakeLLM(reply)
        patcher = mock.patch("core.llm.complete", fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        return fake
