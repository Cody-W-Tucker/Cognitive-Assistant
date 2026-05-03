#!/usr/bin/env python3
"""Profile-aware prompt loader.

Thin wrapper that resolves a prompt name through the profile's `prompt_files`
mapping and delegates to `lib.prompts.load_prompt`. Use:

    from core.prompt_loader import load_prompt_for_profile
    text = load_prompt_for_profile(profile, "synthesis_prompt")
"""

from __future__ import annotations

from core.config import LayerProfile
from lib.prompts import load_prompt as shared_load_prompt
from lib.prompts import prompt_mapping_key


def load_prompt_for_profile(profile: LayerProfile, name: str) -> str:
    """Load a named prompt template using the profile's prompt mapping."""
    if name not in profile.prompt_files:
        raise KeyError(
            f"Profile '{profile.name}' does not declare prompt '{name}'"
        )
    return shared_load_prompt(
        str(profile.prompts_dir),
        prompt_mapping_key(profile.prompt_files),
        name,
    )


__all__ = ["load_prompt_for_profile"]
