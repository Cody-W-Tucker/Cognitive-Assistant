#!/usr/bin/env python3
"""Shared fixtures: an isolated CA home, a bootstrap SOUL, and a fake user home with sessions."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core import improve, paths


def write_jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for line in lines:
            handle.write(json.dumps(line) + "\n")


def add_eligible_codex_sessions(user_home: Path) -> None:
    """Two substantial Codex sessions; the mock analyzer reports the same gap in both,
    which meets the default two-session evidence floor."""
    for i in range(2):
        write_jsonl(
            user_home / ".codex" / "sessions" / "2026" / "10" / "12" / f"rollout-eligible-{i}.jsonl",
            [
                {"type": "session_meta", "payload": {"id": f"codex-eligible-{i}", "cwd": "/tmp/proj"}},
                {
                    "type": "response_item",
                    "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "bootstrap context please"}]},
                },
                *(
                    {"type": "response_item", "payload": {"type": "function_call", "name": name, "arguments": "{}"}}
                    for name in ("read", "search", "test")
                ),
            ],
        )


class CAHomeTestCase(unittest.TestCase):
    """Runs each test against a fresh CA home and bootstrap SOUL, never the real ones."""

    BOOTSTRAP_SOUL = "# SOUL.md\n\nBootstrap voice.\n"

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.ca_home = self.root / "ca"
        self.bootstrap = self.root / "bootstrap" / "SOUL.md"
        self.bootstrap.parent.mkdir()
        self.bootstrap.write_text(self.BOOTSTRAP_SOUL, encoding="utf-8")
        self.user_home = self.root / "user"
        self.user_home.mkdir()
        self._env = mock.patch.dict(os.environ, {"CA_HOME": str(self.ca_home)})
        self._env.start()
        self._soul = mock.patch.object(paths, "BOOTSTRAP_SOUL_PATH", self.bootstrap)
        self._soul.start()

    def tearDown(self) -> None:
        self._soul.stop()
        self._env.stop()
        self._tmp.cleanup()

    def run_mock_proposal(self) -> dict:
        """A headless mock-analyzer run over sessions that yield at least one candidate."""
        add_eligible_codex_sessions(self.user_home)
        proposal = improve.run(home=self.user_home, analyzer="mock")
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
