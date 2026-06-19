#!/usr/bin/env python3
"""Generate a personalized alignment verification spec from unified skills.

Reads skills from the unified `workspaces/skills` store, combines them with the
alignment seed template, and produces a single alignment spec that downstream
tools (verify-alignment) can use to evaluate any output.

This command sits above the profile system: it reads from both registered
profiles but does not belong to either. It is invoked without --profile.

Usage:
    python -m core build-alignment-spec
    python -m core build-alignment-spec --output /path/to/output.md
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import List, Optional

from core.config import ROOT_DIR
from core.skills_creator import canonical_skills_root
from lib.config import APIConfig, validate_provider_config
from lib.llm import LLMHandle, close_client_async, create_client, generate_text_async


# Paths relative to repo root
SEED_PATH = ROOT_DIR / "profiles" / "alignment" / "prompts" / "seed.md"
OUTPUT_DIR = ROOT_DIR / "workspaces" / "alignment" / "artifacts"
OUTPUT_FILE = OUTPUT_DIR / "alignment_spec.md"

UNIFIED_SKILLS_DIR = canonical_skills_root()

# Static sections — not recomputed by the LLM.
SPEC_PREAMBLE = """\
# Personalized Artifact Verification Spec

You are an artifact verifier. You receive an AI-generated artifact (a spec, plan, document, code change, copy, summary, or other deliverable) and assess whether it is production-ready against the personalized checklist below. Run the artifact through each checklist item, score each item, and return a structured verdict.

"""

SPEC_POSTAMBLE = """\

## Instructions

1. Read the artifact in full before scoring. Note its stated purpose, consumer, and form.

2. Run the artifact through each checklist item above. For each item, score:
   - PASS — the artifact satisfies the item's "Satisfied when" cues
   - WEAK — partially satisfied; correctable without rework
   - FAIL — the artifact triggers the item's "Failed when" cues, or omits what the item requires

3. Return the verdict in the format below.

## Output format

```
VERDICT: SHIP | TIGHTEN | REWORK

| # | Checklist Item | Score | Evidence | Fix |
|---|----------------|-------|----------|-----|
| 1 | [item name] | PASS/WEAK/FAIL | [what in the artifact triggered this score] | [one-line correction or —] |

CORRECTIONS (if TIGHTEN):
- [imperative instruction the generating agent can execute]

REWORK (if REWORK):
- [structural problem with the artifact]
- [what the artifact should do instead]
```

Verdict logic:
- SHIP: all PASS, or at most one minor WEAK requiring no correction.
- TIGHTEN: one or more WEAK with actionable corrections; no FAIL.
- REWORK: any FAIL, or compounding WEAK indicating the artifact does not hold together.
"""


class AlignmentSpecCreator:
    """Generate a personalized alignment spec from unified skills."""

    def __init__(self) -> None:
        self.api = APIConfig()
        self.handle: LLMHandle = create_client(
            self.api,
            model=self.api.get_model("refine"),
            async_mode=True,
        )

    async def generate_spec(self, output_path: Optional[Path] = None) -> Path:
        """Generate the alignment spec and write to disk."""
        seed_content = self._load_seed()
        skills_content = self._load_all_skills()

        prompt = seed_content.replace("{skills_content}", skills_content)
        response = await generate_text_async(
            self.handle,
            user_prompt=prompt,
            temperature=self.api.TEMPERATURE,
            max_output_tokens=self.api.MAX_COMPLETION_TOKENS,
        )

        search_path = self._extract_spec(response)
        spec_content = SPEC_PREAMBLE + search_path + SPEC_POSTAMBLE

        resolved_output = output_path or OUTPUT_FILE
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        resolved_output.write_text(spec_content + "\n", encoding="utf-8")
        print(f"Info: Wrote alignment spec to {resolved_output}")
        return resolved_output

    def _load_seed(self) -> str:
        """Load the seed methodology template."""
        if not SEED_PATH.exists():
            raise FileNotFoundError(f"Alignment seed not found at {SEED_PATH}")
        return SEED_PATH.read_text(encoding="utf-8")

    def _load_all_skills(self) -> str:
        """Load all unified skills into a tagged document."""
        sections = self._load_skills_from_root(UNIFIED_SKILLS_DIR)
        if not sections:
            raise FileNotFoundError(
                "No skills found in workspaces/skills. Run build-skills or import skills first."
            )

        return "\n\n".join(sections)

    def _load_skills_from_root(self, skills_dir: Path) -> List[str]:
        """Load all SKILL.md files from the unified profile tree."""
        if not skills_dir.exists():
            print(f"Warning: Unified skills directory not found: {skills_dir}")
            return []

        skills: List[str] = []
        for skill_file in sorted(skills_dir.glob("*/*/SKILL.md")):
            source_profile = skill_file.parent.parent.name
            skill_name = skill_file.parent.name
            content = skill_file.read_text(encoding="utf-8").strip()
            skills.append(
                f'<skill source_profile="{source_profile}" name="{skill_name}">\n'
                f"{content}\n"
                f"</skill>"
            )

        if skills:
            print(f"Info: Loaded {len(skills)} unified skills")
        else:
            print(f"Warning: No skills found in {skills_dir}")

        return skills

    def _extract_spec(self, response: str) -> str:
        """Extract the alignment spec from the LLM response.

        The response should be a complete markdown document. Strip any
        wrapping fences if the LLM added them.
        """
        text = response.strip()
        # Remove markdown code fences if present
        if text.startswith("```markdown"):
            text = text[len("```markdown") :].strip()
        elif text.startswith("```md"):
            text = text[len("```md") :].strip()
        elif text.startswith("```"):
            text = text[3:].strip()

        if text.endswith("```"):
            text = text[:-3].strip()

        if len(text) < 200:
            raise ValueError(
                f"Generated alignment spec is unexpectedly short ({len(text)} chars). "
                "LLM may have produced an error or truncated output."
            )

        return text


async def _async_run(output_path: Optional[Path]) -> int:
    """Async entry point."""
    creator = AlignmentSpecCreator()
    try:
        await creator.generate_spec(output_path=output_path)
        return 0
    finally:
        await close_client_async(creator.handle)


def run(*, output_path: Optional[Path] = None) -> int:
    """Synchronous entry point for CLI use."""
    api = APIConfig()
    issues = validate_provider_config(api)
    if issues:
        print("Error: Configuration issues found")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if not UNIFIED_SKILLS_DIR.exists() or not any(UNIFIED_SKILLS_DIR.glob("*/*/SKILL.md")):
        print(
            "Error: No skills found in workspaces/skills. "
            "Run build-skills or import skills first."
        )
        return 1

    try:
        return asyncio.run(_async_run(output_path))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


__all__ = ["AlignmentSpecCreator", "run"]
