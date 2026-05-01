#!/usr/bin/env python3
"""Shared prompt loading helpers."""

from functools import lru_cache
from pathlib import Path
from typing import Mapping


@lru_cache(maxsize=None)
def load_prompt(prompt_dir: str, prompt_files: tuple[tuple[str, str], ...], name: str) -> str:
    """Load a named prompt template from a runtime prompts directory."""
    prompt_map = dict(prompt_files)
    try:
        filename = prompt_map[name]
    except KeyError as exc:
        raise KeyError(f"Unknown prompt: {name}") from exc

    prompt_path = Path(prompt_dir) / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    return prompt_path.read_text(encoding="utf-8").strip()


def prompt_mapping_key(prompt_files: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    """Convert a prompt file mapping into a cacheable key."""
    return tuple(sorted(prompt_files.items()))
