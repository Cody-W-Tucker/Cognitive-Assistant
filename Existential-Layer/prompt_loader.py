#!/usr/bin/env python3
"""Utilities for loading runtime prompt templates from disk."""

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from lib.prompts import load_prompt as shared_load_prompt  # noqa: E402
from lib.prompts import prompt_mapping_key  # noqa: E402


PROMPTS_DIR = Path(__file__).parent / "prompts" / "runtime"

PROMPT_FILES = {
    "synthesis_prompt": "synthesis_prompt.md",
    "initial_template": "initial_template.md",
    "refine_template": "refine_template.md",
    "skills_creation_template": "skills_creation_template.md",
    "rlm_query_template": "rlm_query_template.md",
    "rlm_query_template_filesystem_only": "rlm_query_template_filesystem_only.md",
    "baseline_system_prompt": "baseline_system_prompt.md",
}
def load_prompt(name: str) -> str:
    """Load a named prompt template from the runtime prompts directory."""
    return shared_load_prompt(str(PROMPTS_DIR), prompt_mapping_key(PROMPT_FILES), name)
