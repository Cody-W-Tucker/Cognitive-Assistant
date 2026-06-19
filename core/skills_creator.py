#!/usr/bin/env python3
"""Generate OpenCode-style skills from the latest profile bio.

Profile-agnostic. Reads the most recent `human_profile*.md` from the active
profile's artifacts directory, scopes the profile content by declared skill
spec, asks the LLM to create or refine one skill at a time, validates each
document, and writes into the unified
`workspaces/skills/<profile>/<skill>/SKILL.md` store. Profiles still own source
bios/prompts; they do not own skill output paths.
"""

from __future__ import annotations

import asyncio
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, Optional

from core.config import Config, SkillSpec
from core.skill_engine import (
    canonical_skills_root,
    create_declared_skill_document,
    extract_frontmatter_value,
    find_canonical_skill,
    generate_hermes_enhancement,
    refine_declared_skill_document,
    validate_declared_skill_document,
    validate_skill_slug,
    with_generation_metadata,
)
from lib.llm import LLMHandle, close_client_async, create_client


class SkillsCreator:
    """Generate skills from a profile bio."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.handle: LLMHandle = create_client(
            config.api,
            model=config.api.get_model("refine"),
            async_mode=True,
        )

    async def generate_skills(
        self,
        bio_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Generate skill files from the selected bio."""
        resolved_bio_path = self._resolve_bio_path(bio_path)
        bio_content = resolved_bio_path.read_text(encoding="utf-8")
        sections = self._parse_bio_sections(bio_content)
        resolved_output_dir = output_dir or canonical_skills_root()
        declared_slugs = await self._generate_declared_skills(sections, resolved_output_dir)
        self._cleanup_stale_generated_skills(resolved_output_dir, declared_slugs)
        return resolved_output_dir

    async def generate_hermes_enhancement(
        self,
        *,
        skill_name: str,
        hermes_content: str,
        local_content: str,
        diff: str,
        context: str,
    ) -> str:
        """Generate one enhanced SKILL.md from source material and local seed context."""
        return await generate_hermes_enhancement(
            handle=self.handle,
            skill_name=skill_name,
            hermes_content=hermes_content,
            local_content=local_content,
            diff=diff,
            context=context,
            temperature=self.config.api.TEMPERATURE,
            max_output_tokens=self.config.api.MAX_COMPLETION_TOKENS,
        )

    def _resolve_bio_path(self, bio_path: Optional[Path]) -> Path:
        if bio_path is not None:
            resolved_path = Path(bio_path)
            if not resolved_path.exists():
                raise FileNotFoundError(f"Bio file not found: {resolved_path}")
            return resolved_path

        bio_files = sorted(self.config.paths.ARTIFACTS_DIR.glob("human_profile*.md"))
        if not bio_files:
            raise FileNotFoundError(
                f"No human_profile*.md files found in {self.config.paths.ARTIFACTS_DIR}. "
                "Run prompt_creator first or pass --bio."
            )
        return bio_files[-1]

    async def _generate_declared_skills(
        self,
        sections: Dict[str, str],
        output_dir: Path,
    ) -> set[str]:
        specs = self.config.profile.skill_specs
        if not specs:
            raise ValueError(
                f"Profile '{self.config.profile.name}' has no skill specs configured"
            )

        declared_slugs: set[str] = set()
        for spec in specs:
            validate_skill_slug(spec.slug)
            declared_slugs.add(spec.slug)
            scoped_bio_content = self._build_scoped_bio_content(spec, sections)
            existing_path = find_canonical_skill(spec.slug, self.config.profile.name)
            if existing_path is None:
                content = await self._create_skill_document(spec, scoped_bio_content)
            else:
                local_content = existing_path.read_text(encoding="utf-8")
                content = await self._refine_skill_document(
                    spec,
                    scoped_bio_content,
                    local_content,
                )
            content = with_generation_metadata(spec, content, self.config.profile.name)
            validate_declared_skill_document(spec, content, self.config.profile.name)
            self._write_skill(spec.slug, content, output_dir, existing_path)
        return declared_slugs

    async def _create_skill_document(self, spec: SkillSpec, scoped_bio_content: str) -> str:
        return await create_declared_skill_document(
            handle=self.handle,
            spec=spec,
            source_profile=self.config.profile.name,
            skills_creation_template=self.config.prompts.skills_creation_template,
            scoped_bio_content=scoped_bio_content,
            temperature=self.config.api.TEMPERATURE,
            max_output_tokens=self.config.api.MAX_COMPLETION_TOKENS,
        )

    async def _refine_skill_document(
        self,
        spec: SkillSpec,
        scoped_bio_content: str,
        local_content: str,
    ) -> str:
        return await refine_declared_skill_document(
            handle=self.handle,
            spec=spec,
            source_profile=self.config.profile.name,
            scoped_bio_content=scoped_bio_content,
            local_content=local_content,
            temperature=self.config.api.TEMPERATURE,
            max_output_tokens=self.config.api.MAX_COMPLETION_TOKENS,
        )

    def _build_scoped_bio_content(self, spec: SkillSpec, sections: Dict[str, str]) -> str:
        missing_headings = [
            heading for heading in spec.source_headings if heading not in sections
        ]
        if missing_headings:
            missing_text = ", ".join(missing_headings)
            raise ValueError(
                f"Profile '{self.config.profile.name}' bio is missing headings for "
                f"skill '{spec.slug}': {missing_text}"
            )

        group_parts = [
            f'<skill_group name="{spec.source_group}" declared_slug="{spec.slug}">',
            "<source_sections>",
        ]
        for heading in spec.source_headings:
            group_parts.append(f"## {heading}\n{sections[heading].strip()}")
        group_parts.extend(["</source_sections>", "</skill_group>"])
        return "\n\n".join(group_parts)

    def _parse_bio_sections(self, bio_content: str) -> Dict[str, str]:
        section_matches = list(
            re.finditer(r"^## (?P<heading>.+?)\n", bio_content, flags=re.MULTILINE)
        )
        if not section_matches:
            raise ValueError("Bio content does not contain any level-2 headings")

        sections: Dict[str, str] = {}
        for index, match in enumerate(section_matches):
            heading = match.group("heading").strip()
            start = match.end()
            end = (
                section_matches[index + 1].start()
                if index + 1 < len(section_matches)
                else len(bio_content)
            )
            sections[heading] = bio_content[start:end].strip()
        return sections

    def _write_skill(
        self,
        skill_name: str,
        content: str,
        output_dir: Path,
        existing_path: Path | None,
    ) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        skill_dir = output_dir / self.config.profile.name / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"
        skill_path.write_text(content.strip() + "\n", encoding="utf-8")
        if existing_path is not None and existing_path != skill_path and existing_path.exists():
            shutil.rmtree(existing_path.parent)
            self._remove_empty_parent(existing_path.parent.parent, output_dir)
        print(f"Info: Wrote {skill_path}")

    def _cleanup_stale_generated_skills(self, output_dir: Path, declared_slugs: set[str]) -> None:
        if not output_dir.exists():
            return
        for skill_path in sorted(output_dir.glob("*/*/SKILL.md")):
            content = skill_path.read_text(encoding="utf-8")
            source_profile = extract_frontmatter_value(content, "source_profile")
            if source_profile != self.config.profile.name:
                continue
            skill_name = extract_frontmatter_value(content, "name") or skill_path.parent.name
            if skill_name in declared_slugs:
                continue
            shutil.rmtree(skill_path.parent)
            self._remove_empty_parent(skill_path.parent.parent, output_dir)
            print(f"Info: Removed stale generated skill {skill_path.parent}")

    def _remove_empty_parent(self, directory: Path, stop_at: Path) -> None:
        if directory == stop_at or not directory.exists():
            return
        try:
            directory.rmdir()
        except OSError:
            return

async def _async_run(
    config: Config,
    bio_path: Optional[Path],
    output_dir: Optional[Path],
) -> int:
    creator = SkillsCreator(config)
    try:
        result_dir = await creator.generate_skills(
            bio_path=bio_path, output_dir=output_dir
        )
        print(f"Info: Skills generated in {result_dir}")
        return 0
    finally:
        await close_client_async(creator.handle)


def run(
    config: Config,
    *,
    bio_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> int:
    """Synchronous entry point for CLI use."""
    issues = config.validate_llm_access()
    if issues:
        print("Error: Configuration issues found")
        for issue in issues:
            print(f"- {issue}")
        return 1

    try:
        return asyncio.run(_async_run(config, bio_path, output_dir))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


__all__ = ["SkillsCreator", "run"]
