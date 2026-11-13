#!/usr/bin/env python3
"""Generate personalized single-tool agent specs from a profile's human profile.

Each supported tool has a seed exemplar of the same name in the profile's
prompts directory (e.g. memory.md, tasks.md). One model call returns a JSON
map of {filename: spec}; files no longer supported are removed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from core import llm
from core.config import LayerProfile

REQUIRED_SECTIONS = ("## Mission", "## Use This Tool For", "## Decision Rules", "## Avoid")
MIN_SPEC_CHARS = 200


def requirements(profile: LayerProfile) -> List[str]:
    if not profile.supported_tools:
        return [f"profile '{profile.name}' does not generate tool specs"]
    issues = llm.missing_config(llm.DEFAULT_PROVIDER)
    missing = [name for name in profile.supported_tools if not (profile.prompts_dir / name).exists()]
    if missing:
        issues.append(f"Tool exemplar files not found in {profile.prompts_dir}: {', '.join(missing)}")
    return issues


def _prompt(profile: LayerProfile, bio_content: str) -> str:
    seeds = "\n\n".join(
        f'<seed_document name="{name}">\n{(profile.prompts_dir / name).read_text(encoding="utf-8").strip()}\n</seed_document>'
        for name in profile.supported_tools
    )
    tools = "\n".join(f"- `{name}`: {description}" for name, description in profile.supported_tools.items())
    return profile.prompt("tool_specs_creation_template").format(
        bio_content=bio_content, supported_tools=tools, seed_documents=seeds
    )


def validate_payload(profile: LayerProfile, payload: Dict[str, str]) -> None:
    if set(payload) != set(profile.supported_tools):
        raise ValueError(
            f"Generated tool specs must be exactly: {', '.join(profile.supported_tools)} (got {', '.join(payload) or 'none'})"
        )
    for filename, content in payload.items():
        for section in REQUIRED_SECTIONS:
            if section not in content:
                raise ValueError(f"Tool spec file {filename} is missing '{section}'")
        if len(content.strip()) < MIN_SPEC_CHARS:
            raise ValueError(f"Tool spec file {filename} is unexpectedly short")


async def build(profile: LayerProfile, *, bio_path: Optional[Path] = None) -> None:
    bio = Path(bio_path) if bio_path else profile.human_profile_path
    if not bio.exists():
        raise FileNotFoundError(f"Human profile not found at {bio}; run build-prompts first or pass --bio")
    reply = await llm.complete(_prompt(profile, bio.read_text(encoding="utf-8")), label="tool specs")
    payload = llm.parse_json_object(reply, label="tool specs")
    validate_payload(profile, payload)
    output = profile.tool_specs_dir
    output.mkdir(parents=True, exist_ok=True)
    for existing in output.glob("*.md"):
        if existing.name not in payload:
            existing.unlink()
            print(f"Info: Removed stale tool spec file {existing}")
    for filename, content in payload.items():
        (output / filename).write_text(content.strip() + "\n", encoding="utf-8")
        print(f"Info: Wrote {output / filename}")
