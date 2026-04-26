#!/usr/bin/env python3
"""Utilities for loading runtime prompt templates from disk."""

from functools import lru_cache
from pathlib import Path


PROMPTS_DIR = Path(__file__).parent / "prompts" / "runtime"

PROMPT_FILES = {
    "synthesis_prompt": "synthesis_prompt.md",
    "initial_template": "initial_template.md",
    "refine_template": "refine_template.md",
    "rlm_query_template": "rlm_query_template.md",
    "rlm_query_template_filesystem_only": "rlm_query_template_filesystem_only.md",
    "workspace_extraction_template": "workspace_extraction_template.md",
    "baseline_system_prompt": "baseline_system_prompt.md",
    "combined_prompt_template": "combined_prompt_template.md",
}


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """Load a named prompt template from the runtime prompts directory."""
    try:
        filename = PROMPT_FILES[name]
    except KeyError as exc:
        raise KeyError(f"Unknown prompt: {name}") from exc

    prompt_path = PROMPTS_DIR / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    return prompt_path.read_text(encoding="utf-8").strip()
