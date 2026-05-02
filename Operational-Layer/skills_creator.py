#!/usr/bin/env python3
"""Generate OpenCode-style operational skills from the latest profile."""

import argparse
import asyncio
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, Optional

from config import config
from llm import LLMHandle, create_client, generate_text_async

class SkillsCreator:
    """Generate skills from an operational profile."""

    def __init__(self) -> None:
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
        """Generate skill files from the selected profile."""
        resolved_bio_path = self._resolve_bio_path(bio_path)
        bio_content = resolved_bio_path.read_text(encoding="utf-8")
        skills_payload = await self._generate_skill_documents(bio_content)
        resolved_output_dir = output_dir or config.paths.SKILLS_DIR
        self._write_skills(skills_payload, resolved_output_dir)
        return resolved_output_dir

    def _resolve_bio_path(self, bio_path: Optional[Path]) -> Path:
        if bio_path is not None:
            resolved_path = Path(bio_path)
            if not resolved_path.exists():
                raise FileNotFoundError(f"Bio file not found: {resolved_path}")
            return resolved_path

        bio_files = sorted(config.paths.ARTIFACTS_DIR.glob("human_profile*.md"))
        if not bio_files:
            raise FileNotFoundError(
                "No human_profile*.md files found in artifacts/. Run prompt_creator.py first or pass --bio."
            )
        return bio_files[-1]

    async def _generate_skill_documents(self, bio_content: str) -> Dict[str, str]:
        prompt = config.prompts.skills_creation_template.format(
            bio_content=bio_content,
        )

        response = await generate_text_async(
            self.handle,
            user_prompt=prompt,
            temperature=config.api.TEMPERATURE,
            max_output_tokens=config.api.MAX_COMPLETION_TOKENS,
        )
        payload = self._parse_json_response(response)
        self._validate_payload(payload)
        return payload

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

        if len(payload) > 6:
            raise ValueError(
                f"Generated too many skills ({len(payload)}); expected a small high-leverage set"
            )

        for skill_name, content in payload.items():
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill_name):
                raise ValueError(
                    f"Skill name '{skill_name}' must be a lowercase hyphenated slug"
                )
            if f"name: {skill_name}" not in content:
                raise ValueError(f"Skill {skill_name} is missing matching frontmatter name")
            if "description:" not in content:
                raise ValueError(f"Skill {skill_name} is missing required description frontmatter")
            if "## When To Use" not in content:
                raise ValueError(f"Skill {skill_name} is missing '## When To Use' section")
            if "## Do Not Use" not in content:
                raise ValueError(f"Skill {skill_name} is missing '## Do Not Use' section")
            if len(content.strip()) < 200:
                raise ValueError(f"Skill {skill_name} is unexpectedly short")

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


def create_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line interface parser."""
    parser = argparse.ArgumentParser(
        description="Generate OpenCode-style skills from human_profile.md",
    )
    parser.add_argument("--bio", type=Path, help="Path to a specific human_profile.md file")
    parser.add_argument(
        "--output",
        type=Path,
        help="Directory where generated skill folders should be written",
    )
    return parser


async def _async_main(args: argparse.Namespace) -> int:
    creator = SkillsCreator()
    result_dir = await creator.generate_skills(bio_path=args.bio, output_dir=args.output)
    print(f"Info: Skills generated in {result_dir}")
    return 0


def main() -> int:
    """CLI entrypoint for skill generation."""
    issues = config.validate()
    if issues:
        print("Error: Configuration issues found")
        for issue in issues:
            print(f"- {issue}")
        return 1

    parser = create_argument_parser()
    args = parser.parse_args()

    try:
        return asyncio.run(_async_main(args))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
