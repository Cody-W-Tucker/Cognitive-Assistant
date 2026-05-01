#!/usr/bin/env python3
"""Shared LLM client creation and text generation helpers."""

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from lib.llm import (  # noqa: E402
    LLMHandle,
    create_client,
    generate_text,
    generate_text_async,
)


__all__ = ["LLMHandle", "create_client", "generate_text", "generate_text_async"]
