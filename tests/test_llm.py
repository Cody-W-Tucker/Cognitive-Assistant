#!/usr/bin/env python3
"""Tests for shared LLM request helpers."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any

from lib.llm import LLMHandle, generate_text


class FakeMessages:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(content=[SimpleNamespace(text="ok")])


class LLMHelperTests(unittest.TestCase):
    def test_anthropic_omits_empty_system_prompt(self) -> None:
        messages = FakeMessages()
        client = SimpleNamespace(messages=messages)
        handle = LLMHandle(
            client=client,
            model="claude-test",
            provider="anthropic",
            async_mode=False,
        )

        result = generate_text(
            handle,
            user_prompt="hello",
            temperature=0.0,
            max_output_tokens=10,
        )

        self.assertEqual(result, "ok")
        self.assertNotIn("system", messages.kwargs)

    def test_anthropic_includes_system_prompt_when_present(self) -> None:
        messages = FakeMessages()
        client = SimpleNamespace(messages=messages)
        handle = LLMHandle(
            client=client,
            model="claude-test",
            provider="anthropic",
            async_mode=False,
        )

        generate_text(
            handle,
            user_prompt="hello",
            system_prompt="system instructions",
            temperature=0.0,
            max_output_tokens=10,
        )

        self.assertEqual(messages.kwargs["system"], "system instructions")


if __name__ == "__main__":
    unittest.main()
