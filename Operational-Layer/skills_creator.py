#!/usr/bin/env python3
"""Generate OpenCode-style operational skills from the latest profile."""

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from config import config
from llm import LLMHandle, create_client, generate_text_async


@dataclass(frozen=True)
class SkillSpec:
    """Specification for a generated skill."""

    name: str
    description: str
    when_to_use: List[str]
    avoid_for: List[str]


SKILL_SPECS: List[SkillSpec] = [
    SkillSpec(
        name="user-planning-execution-calibration",
        description=(
            "Use when it is unclear whether the user wants planning, diagnosis, review, or direct implementation, "
            "and a generic agent might choose the wrong mode."
        ),
        when_to_use=[
            "The request mixes planning language with implementation language.",
            "The user is asking for what to do next but may want action instead of a plan.",
            "Choosing the wrong response mode would create obvious friction.",
        ],
        avoid_for=[
            "Straightforward execution requests with explicit instructions.",
            "Purely factual questions.",
            "Simple formatting or retrieval tasks.",
        ],
    ),
    SkillSpec(
        name="user-review-and-quality-bar",
        description=(
            "Use when reviewing code, plans, content, or structure where the user has strong hidden standards that "
            "a generic quality pass might miss."
        ),
        when_to_use=[
            "The user asks for review, critique, or style matching.",
            "The task depends on understanding what this user considers high quality.",
            "A shallow best-practices answer would likely miss the real bar.",
        ],
        avoid_for=[
            "Tasks with no meaningful quality judgment involved.",
            "Routine mechanical edits.",
            "Cases where default engineering standards are clearly sufficient.",
        ],
    ),
    SkillSpec(
        name="user-workflow-sequencing",
        description=(
            "Use when a task has multiple steps and the order of inspection, planning, implementation, and verification "
            "matters to this user."
        ),
        when_to_use=[
            "The task is non-trivial and could be approached in several valid orders.",
            "The user seems to expect current-state inspection before action.",
            "Choosing the wrong sequence would make the work feel careless or generic.",
        ],
        avoid_for=[
            "One-step tasks with obvious sequencing.",
            "Requests that are already fully specified and low-risk.",
            "Pure conversation without execution decisions.",
        ],
    ),
    SkillSpec(
        name="user-tooling-context-expectations",
        description=(
            "Use when deciding how much repository, environment, or tool context should be gathered before answering or acting."
        ),
        when_to_use=[
            "The request depends on local code, files, or tool availability.",
            "The user is likely to expect file-grounded rather than generic advice.",
            "You need to infer how much exploration is necessary before responding.",
        ],
        avoid_for=[
            "Questions answerable without workspace context.",
            "Simple commands with no ambiguity.",
            "Situations where extra exploration would just add latency.",
        ],
    ),
    SkillSpec(
        name="user-automation-hotspot-detection",
        description=(
            "Use when repeated workflow sequences suggest the user would benefit from scripts, prompts, or reusable automation patterns."
        ),
        when_to_use=[
            "The same request pattern is appearing across tasks or projects.",
            "The user is doing repeated coordination, setup, review, or translation work.",
            "A generic one-off answer would miss a chance to reduce future repetition.",
        ],
        avoid_for=[
            "One-off tasks with no repetition signal.",
            "Small requests where automation would be overkill.",
            "Cases where the user explicitly wants manual exploration instead.",
        ],
    ),
]


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
        skill_specs = self._format_skill_specs()
        prompt = config.prompts.skills_creation_template.format(
            bio_content=bio_content,
            skill_specs=skill_specs,
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

    def _format_skill_specs(self) -> str:
        sections: List[str] = []
        for spec in SKILL_SPECS:
            sections.append(f"- Name: {spec.name}")
            sections.append(f"  Description: {spec.description}")
            sections.append("  When To Use:")
            for item in spec.when_to_use:
                sections.append(f"    - {item}")
            sections.append("  Do Not Use:")
            for item in spec.avoid_for:
                sections.append(f"    - {item}")
        return "\n".join(sections)

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
        expected_names = {spec.name for spec in SKILL_SPECS}
        actual_names = set(payload.keys())

        if actual_names != expected_names:
            missing = sorted(expected_names - actual_names)
            extra = sorted(actual_names - expected_names)
            parts: List[str] = []
            if missing:
                parts.append(f"missing {', '.join(missing)}")
            if extra:
                parts.append(f"extra {', '.join(extra)}")
            raise ValueError(
                f"Generated skills did not match expected set: {'; '.join(parts)}"
            )

        for skill_name, content in payload.items():
            if f"name: {skill_name}" not in content:
                raise ValueError(f"Skill {skill_name} is missing matching frontmatter name")
            if "description:" not in content:
                raise ValueError(f"Skill {skill_name} is missing required description frontmatter")
            if len(content.strip()) < 200:
                raise ValueError(f"Skill {skill_name} is unexpectedly short")

    def _write_skills(self, payload: Dict[str, str], output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
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
