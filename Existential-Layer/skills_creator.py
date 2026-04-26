#!/usr/bin/env python3
"""Generate OpenCode-style skills from the latest human interview bio."""

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
        name="user-request-interpretation",
        description=(
            "Use when the user's request is ambiguous, high-context, or likely to be "
            "misread by generic advice, especially when subtext matters more than the "
            "surface wording."
        ),
        when_to_use=[
            "The request seems to mean more than it literally says.",
            "The user is sensing that something is off but has not named it cleanly.",
            "A generic response would likely miss the real problem being solved.",
        ],
        avoid_for=[
            "Straightforward factual questions.",
            "Routine coding, formatting, or procedural tasks.",
            "Requests that are already explicit and low-context.",
        ],
    ),
    SkillSpec(
        name="user-decision-support",
        description=(
            "Use for strategic choices, tradeoff-heavy planning, or uncertain next moves "
            "where the user needs a strong thinking partner rather than generic planning advice."
        ),
        when_to_use=[
            "The user is choosing between multiple viable paths.",
            "The right move depends on reversibility, proof, timing, or hidden constraints.",
            "A standard plan or productivity frame would be too shallow.",
        ],
        avoid_for=[
            "Simple execution requests with a clear path.",
            "Low-stakes to-do breakdowns.",
            "Mechanical planning tasks with no deeper tradeoff.",
        ],
    ),
    SkillSpec(
        name="user-response-calibration",
        description=(
            "Use when tone, depth, pacing, or challenge level matter because a generic assistant "
            "response would likely sound reductive, overly soothing, or patronizing."
        ),
        when_to_use=[
            "The topic is philosophically, emotionally, or strategically loaded.",
            "The user needs peer-level engagement rather than coaching language.",
            "You need help deciding how direct, structured, or challenging to be.",
        ],
        avoid_for=[
            "Short transactional answers.",
            "Routine retrieval or explanation tasks.",
            "Cases where default assistant tone is already sufficient.",
        ],
    ),
    SkillSpec(
        name="user-context-model",
        description=(
            "Use when a novel, personal, or high-context interaction would benefit from background "
            "awareness of the user's values, motivations, and sensitivities without restating them explicitly."
        ),
        when_to_use=[
            "The interaction is unusual enough that generic assumptions may be wrong.",
            "The answer depends on deeper priorities, motivations, or known sensitivities.",
            "You need background reasoning fuel, not a script to repeat back to the user.",
        ],
        avoid_for=[
            "Routine objective tasks.",
            "Low-context requests where background personalization adds little value.",
            "Situations where loading broad user context would be unnecessary overhead.",
        ],
    ),
    SkillSpec(
        name="user-growth-constraints",
        description=(
            "Use when a recommendation might collide with recurring traps, blindspots, or failure "
            "patterns that are easy for a generic model to miss in novel or high-stakes situations."
        ),
        when_to_use=[
            "The user is translating insight into action, offers, or commitments.",
            "A recommendation could accidentally reinforce a known failure pattern.",
            "You need quiet constraint-awareness in the background while reasoning.",
        ],
        avoid_for=[
            "Basic information requests.",
            "Small routine actions with limited downside.",
            "Any response that would only use this skill to psychologize the user.",
        ],
    ),
]


class SkillsCreator:
    """Generate skills from a human-readable interview bio."""

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
        """Generate skill files from the selected bio."""
        resolved_bio_path = self._resolve_bio_path(bio_path)
        bio_content = resolved_bio_path.read_text(encoding="utf-8")
        skills_payload = await self._generate_skill_documents(bio_content)
        resolved_output_dir = output_dir or config.paths.SKILLS_DIR
        self._write_skills(skills_payload, resolved_output_dir)
        return resolved_output_dir

    def _resolve_bio_path(self, bio_path: Optional[Path]) -> Path:
        """Resolve the input bio path, defaulting to the latest generated bio."""
        if bio_path is not None:
            resolved_path = Path(bio_path)
            if not resolved_path.exists():
                raise FileNotFoundError(f"Bio file not found: {resolved_path}")
            return resolved_path

        bio_files = sorted(config.paths.ARTIFACTS_DIR.glob("human_interview_bio*.md"))
        if not bio_files:
            raise FileNotFoundError(
                "No human_interview_bio*.md files found in artifacts/. Run prompt_creator.py first or pass --bio."
            )
        return bio_files[-1]

    async def _generate_skill_documents(self, bio_content: str) -> Dict[str, str]:
        """Generate SKILL.md content for each configured skill."""
        skill_specs = self._format_skill_specs()
        prompt = config.prompts.skills_creation_template.format(
            bio_content=bio_content,
            skill_specs=skill_specs,
        )

        response = await generate_text_async(
            self.handle,
            user_prompt=prompt,
            temperature=0.3,
            max_output_tokens=config.api.MAX_COMPLETION_TOKENS,
        )
        payload = self._parse_json_response(response)
        self._validate_payload(payload)
        return payload

    def _format_skill_specs(self) -> str:
        """Render the predefined skill specs for the generation prompt."""
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
        """Parse a JSON object from the LLM response."""
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
        """Validate the generated skill payload before writing files."""
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
            raise ValueError(f"Generated skills did not match expected set: {'; '.join(parts)}")

        for skill_name, content in payload.items():
            if f"name: {skill_name}" not in content:
                raise ValueError(f"Skill {skill_name} is missing matching frontmatter name")
            if "description:" not in content:
                raise ValueError(f"Skill {skill_name} is missing required description frontmatter")
            if len(content.strip()) < 200:
                raise ValueError(f"Skill {skill_name} is unexpectedly short")

    def _write_skills(self, payload: Dict[str, str], output_dir: Path) -> None:
        """Write each generated skill to its own directory."""
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
        description="Generate OpenCode-style skills from human_interview_bio.md",
    )
    parser.add_argument(
        "--bio",
        type=Path,
        help="Path to a specific human_interview_bio.md file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Directory where generated skill folders should be written",
    )
    return parser


async def _async_main(args: argparse.Namespace) -> int:
    """Run the asynchronous skill generation flow."""
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
