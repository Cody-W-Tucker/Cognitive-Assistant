#!/usr/bin/env python3
"""Generate a profile's declared skills from its human profile.

Each ``SkillSpec`` scopes the human profile to its headings; the skill is
created on first build and refined from its current SKILL.md afterwards.
Generated skills live in ``workspaces/skills/<profile>/``; a skill the
profile no longer declares is removed from there.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from core import llm, paths
from core.config import LayerProfile, SkillSpec
from core.skill_engine import (
    create_declared_skill_document,
    refine_declared_skill_document,
    skill_path,
    validate_declared_skill_document,
    validate_skill_slug,
    with_generation_metadata,
)


def requirements(profile: LayerProfile) -> List[str]:
    issues = llm.missing_config(llm.DEFAULT_PROVIDER)
    if not profile.skill_specs:
        issues.append(f"Profile '{profile.name}' has no skill specs configured")
    return issues


def parse_sections(bio_content: str) -> Dict[str, str]:
    """Level-2 heading -> section text."""
    matches = list(re.finditer(r"^## (?P<heading>.+?)\n", bio_content, flags=re.MULTILINE))
    if not matches:
        raise ValueError("Bio content does not contain any level-2 headings")
    sections: Dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(bio_content)
        sections[match.group("heading").strip()] = bio_content[match.end() : end].strip()
    return sections


def scoped_content(profile: LayerProfile, spec: SkillSpec, sections: Dict[str, str]) -> str:
    """The parts of the human profile this skill is built from."""
    missing = [heading for heading in spec.source_headings if heading not in sections]
    if missing:
        raise ValueError(
            f"Profile '{profile.name}' bio is missing headings for skill '{spec.slug}': {', '.join(missing)}"
        )
    parts = [f'<skill_group name="{spec.source_group}" declared_slug="{spec.slug}">', "<source_sections>"]
    parts.extend(f"## {heading}\n{sections[heading].strip()}" for heading in spec.source_headings)
    parts.extend(["</source_sections>", "</skill_group>"])
    return "\n\n".join(parts)


async def _build_one(profile: LayerProfile, spec: SkillSpec, sections: Dict[str, str]) -> None:
    validate_skill_slug(spec.slug)
    scoped = scoped_content(profile, spec, sections)
    path = skill_path(profile.name, spec.slug)
    if path.exists():
        content = await refine_declared_skill_document(
            spec=spec,
            source_profile=profile.name,
            scoped_bio_content=scoped,
            local_content=path.read_text(encoding="utf-8"),
        )
    else:
        content = await create_declared_skill_document(
            spec=spec,
            source_profile=profile.name,
            skills_creation_template=profile.prompt("skills_creation_template"),
            scoped_bio_content=scoped,
        )
    content = with_generation_metadata(spec, content, profile.name)
    validate_declared_skill_document(spec, content, profile.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Info: Wrote {path}")


def remove_undeclared(profile: LayerProfile) -> None:
    """Remove undeclared skills only from this profile's owned folder."""
    declared = {spec.slug for spec in profile.skill_specs}
    for directory in sorted((paths.SKILLS_DIR / profile.name).glob("*")):
        if not directory.is_dir() or directory.name in declared:
            continue
        shutil.rmtree(directory)
        print(f"Info: Removed stale generated skill {directory}")


async def build(profile: LayerProfile, *, bio_path: Optional[Path] = None) -> None:
    bio = Path(bio_path) if bio_path else profile.human_profile_path
    if not bio.exists():
        raise FileNotFoundError(f"Human profile not found at {bio}; run build-prompts first or pass --bio")
    sections = parse_sections(bio.read_text(encoding="utf-8"))
    for spec in profile.skill_specs:
        await _build_one(profile, spec, sections)
    remove_undeclared(profile)
    print(f"Info: Skills generated in {paths.SKILLS_DIR / profile.name}")
