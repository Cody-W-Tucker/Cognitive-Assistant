#!/usr/bin/env python3
"""Generate OpenCode-style skills from the latest profile bio.

Profile-agnostic. Reads the most recent `human_profile*.md` from the active
profile's artifacts directory, asks the LLM to produce a JSON map of
{slug: SKILL.md content}, validates the payload, and writes one skill per
directory. Stale skill directories not in the new payload are removed.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

from core.config import Config
from lib.llm import LLMHandle, close_client_async, create_client, generate_text_async


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
        grouped_bio_content = self._build_grouped_bio_content(bio_content)
        skills_payload = await self._generate_skill_documents(grouped_bio_content)
        resolved_output_dir = output_dir or self.config.paths.SKILLS_DIR
        self._write_skills(skills_payload, resolved_output_dir)
        return resolved_output_dir

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

    async def _generate_skill_documents(self, grouped_bio_content: str) -> Dict[str, str]:
        prompt = self.config.prompts.skills_creation_template.format(
            grouped_bio_content=grouped_bio_content,
        )
        response = await generate_text_async(
            self.handle,
            user_prompt=prompt,
            temperature=self.config.api.TEMPERATURE,
            max_output_tokens=self.config.api.MAX_COMPLETION_TOKENS,
        )
        payload = self._parse_json_response(response)
        self._validate_payload(payload)
        return payload

    def _build_grouped_bio_content(self, bio_content: str) -> str:
        sections = self._parse_bio_sections(bio_content)
        groups = self.config.profile.skill_heading_groups
        if not groups:
            raise ValueError(
                f"Profile '{self.config.profile.name}' has no skill heading groups configured"
            )

        grouped_sections: List[str] = []
        for group_name, headings in groups:
            missing_headings = [heading for heading in headings if heading not in sections]
            if missing_headings:
                missing_text = ", ".join(missing_headings)
                raise ValueError(
                    f"Profile '{self.config.profile.name}' bio is missing grouped headings: "
                    f"{missing_text}"
                )

            group_parts = [
                f"<skill_group name=\"{group_name}\">",
                "<source_sections>",
            ]
            for heading in headings:
                group_parts.append(f"## {heading}\n{sections[heading].strip()}")
            group_parts.extend(["</source_sections>", "</skill_group>"])
            grouped_sections.append("\n\n".join(group_parts))

        return "\n\n".join(grouped_sections)

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

    def _parse_json_response(self, response: str) -> Dict[str, str]:
        match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", response)
        json_text = match.group(1) if match else response.strip()
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse skills JSON: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ValueError("Skills payload must be a JSON object")
        return {str(key): str(value) for key, value in parsed.items()}

    def _validate_payload(self, payload: Dict[str, str]) -> None:
        if not payload:
            raise ValueError("Generated skills payload is empty")

        expected_groups = {group_name for group_name, _ in self.config.profile.skill_heading_groups}
        if len(payload) < len(expected_groups):
            raise ValueError(
                f"Generated {len(payload)} skills; expected at least {len(expected_groups)} to cover configured heading groups"
            )

        if len(payload) > 10:
            raise ValueError(
                f"Generated too many skills ({len(payload)}); expected a small high-leverage set"
            )

        seen_groups: Set[str] = set()
        for skill_name, content in payload.items():
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill_name):
                raise ValueError(
                    f"Skill name '{skill_name}' must be a lowercase hyphenated slug"
                )
            if f"name: {skill_name}" not in content:
                raise ValueError(
                    f"Skill {skill_name} is missing matching frontmatter name"
                )
            if "description:" not in content:
                raise ValueError(
                    f"Skill {skill_name} is missing required description frontmatter"
                )
            source_group_match = re.search(
                r"^source_group:\s*(?P<group>[a-z0-9]+(?:-[a-z0-9]+)*)\s*$",
                content,
                flags=re.MULTILINE,
            )
            if source_group_match is None:
                raise ValueError(
                    f"Skill {skill_name} is missing required source_group frontmatter"
                )
            source_group = source_group_match.group("group")
            if source_group not in expected_groups:
                raise ValueError(
                    f"Skill {skill_name} references unknown source_group '{source_group}'"
                )
            seen_groups.add(source_group)
            if "## When To Use" not in content:
                raise ValueError(
                    f"Skill {skill_name} is missing '## When To Use' section"
                )
            if "## Do Not Use" not in content:
                raise ValueError(
                    f"Skill {skill_name} is missing '## Do Not Use' section"
                )
            if len(content.strip()) < 200:
                raise ValueError(f"Skill {skill_name} is unexpectedly short")

        missing_groups = expected_groups - seen_groups
        if missing_groups:
            missing_text = ", ".join(sorted(missing_groups))
            raise ValueError(
                f"Generated skills did not cover all configured heading groups: {missing_text}"
            )

    def _write_skills(self, payload: Dict[str, str], output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        for existing_dir in output_dir.iterdir():
            if existing_dir.is_dir() and existing_dir.name not in payload:
                shutil.rmtree(existing_dir)
                print(f"Info: Removed stale skill directory {existing_dir}")
        for skill_name, content in payload.items():
            skill_dir = output_dir / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_path = skill_dir / "SKILL.md"
            skill_path.write_text(content.strip() + "\n", encoding="utf-8")
            print(f"Info: Wrote {skill_path}")


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
