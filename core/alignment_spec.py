#!/usr/bin/env python3
"""Generate a personalized alignment verification spec from skills and agent souls.

Reads skills from the unified `workspaces/skills` store and agent souls from
`workspaces/alignment/artifacts/agents/`, validated against the committed
`agent_plan.json`, combines them with the alignment seed template, and produces
a single alignment spec that downstream tools (verify-alignment) can use to
evaluate any output.

`agent_plan.json` is the only authority for which agent souls exist. The persona
map is a projection of that plan and is never read as authority here.

Skills provide reusable operating procedures generated per profile. Agent souls
provide distinct persona identity documents declared in the plan. Both sources
feed the alignment spec.

This command sits above the profile system: it reads from both registered
profiles but does not belong to either. It is invoked without --profile.

Usage:
    python -m core build-alignment-spec
    python -m core build-alignment-spec --output /path/to/output.md
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional

from core.agent_plan_validator import ValidationError, validate_agent_plan
from core.config import ROOT_DIR
from core.skills_creator import canonical_skills_root
from lib.config import APIConfig, DEFAULT_PROVIDER, validate_provider_config
from lib.llm import LLMHandle, close_client_async, create_client, generate_text_async


# Paths relative to repo root
SEED_PATH = ROOT_DIR / "profiles" / "alignment" / "prompts" / "seed.md"
OUTPUT_DIR = ROOT_DIR / "workspaces" / "alignment" / "artifacts"
OUTPUT_FILE = OUTPUT_DIR / "alignment_spec.md"
AGENTS_DIR = OUTPUT_DIR / "agents"
PLAN_FILE = OUTPUT_DIR / "agent_plan.json"

UNIFIED_SKILLS_DIR = canonical_skills_root()

SKILLS_PLACEHOLDER = "{skills_content}"
AGENT_SOULS_PLACEHOLDER = "{agent_souls_content}"

# Static sections - not recomputed by the LLM.
SPEC_PREAMBLE = """\
# Personalized Artifact Verification Spec

You are an artifact verifier. You receive an AI-generated artifact (a spec, plan, document, code change, copy, summary, or other deliverable) and assess whether it is production-ready against the personalized checklist below. Run the artifact through each checklist item, score each item, and return a structured verdict.

"""

SPEC_POSTAMBLE = """\

## Instructions

1. Read the artifact in full before scoring. Note its stated purpose, consumer, and form.

2. Run the artifact through each checklist item above. For each item, score:
   - PASS - the artifact satisfies the item's "Satisfied when" cues
   - WEAK - partially satisfied; correctable without rework
   - FAIL - the artifact triggers the item's "Failed when" cues, or omits what the item requires

3. Return the verdict in the format below.

## Output format

```
VERDICT: SHIP | TIGHTEN | REWORK

| # | Checklist Item | Score | Evidence | Fix |
|---|----------------|-------|----------|-----|
| 1 | [item name] | PASS/WEAK/FAIL | [what in the artifact triggered this score] | [one-line correction or -] |

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


def load_planned_agent_ids(plan_path: Path) -> List[str]:
    """Return the agent ids declared by the committed ``agent_plan.json``.

    The validated final plan is the only authority for which agent souls the
    alignment spec loads. The persona map is a projection of the plan and is
    never consulted here.

    Raises:
        FileNotFoundError: if the plan is missing.
        ValueError: if the plan is unparseable, declares no agents, or declares
            a duplicate agent id.
    """
    if not plan_path.exists():
        raise FileNotFoundError(
            f"Agent plan not found at {plan_path}. Run build-agents first."
        )
    try:
        plan = validate_agent_plan(json.loads(plan_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(
            f"Agent plan at {plan_path} is invalid: {exc}. "
            "Run build-agents to regenerate."
        ) from exc

    ids = [agent["id"] for agent in plan["agents"]]  # type: ignore[index,union-attr]
    if not ids:
        raise ValueError(
            f"Agent plan at {plan_path} declares no agents. "
            "Run build-agents to regenerate."
        )
    seen: set[str] = set()
    for agent_id in ids:
        if agent_id in seen:
            raise ValueError(f"Agent plan declares duplicate agent id: '{agent_id}'.")
        seen.add(agent_id)
    return ids


class AlignmentSpecCreator:
    """Generate a personalized alignment spec from skills and agent souls."""

    def __init__(self) -> None:
        self.api = APIConfig()
        self.handle: LLMHandle = create_client(
            self.api,
            provider=DEFAULT_PROVIDER,
            model=self.api.get_model(provider=DEFAULT_PROVIDER),
            async_mode=True,
        )

    async def generate_spec(self, output_path: Optional[Path] = None) -> Path:
        """Generate the alignment spec and write to disk."""
        seed_content = self._load_seed()
        skills_content = self._load_all_skills()
        agent_souls_content = self._load_declared_agent_souls()

        prompt = seed_content.replace(SKILLS_PLACEHOLDER, skills_content)
        prompt = prompt.replace(AGENT_SOULS_PLACEHOLDER, agent_souls_content)
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
        """Load the seed methodology template and validate its placeholders."""
        if not SEED_PATH.exists():
            raise FileNotFoundError(f"Alignment seed not found at {SEED_PATH}")
        content = SEED_PATH.read_text(encoding="utf-8")
        for placeholder in (SKILLS_PLACEHOLDER, AGENT_SOULS_PLACEHOLDER):
            count = content.count(placeholder)
            if count != 1:
                raise ValueError(
                    f"Alignment seed must contain placeholder "
                    f"'{placeholder}' exactly once; found {count}."
                )
        return content

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

    def _load_declared_agent_souls(self) -> str:
        """Load only the agent souls declared by the committed agent plan."""
        slugs = load_planned_agent_ids(PLAN_FILE)
        sections: List[str] = []
        for slug in slugs:
            soul_path = AGENTS_DIR / f"{slug}.md"
            if not soul_path.exists():
                raise FileNotFoundError(
                    f"Declared agent soul missing: {soul_path}. "
                    f"The agent plan declares agent '{slug}' but no matching "
                    "file exists in agents/."
                )
            content = soul_path.read_text(encoding="utf-8").strip()
            if not content:
                raise ValueError(
                    f"Declared agent soul is empty: {soul_path}"
                )
            sections.append(
                f'<agent_soul slug="{slug}">\n'
                f"{content}\n"
                f"</agent_soul>"
            )
        print(f"Info: Loaded {len(sections)} declared agent souls")
        return "\n\n".join(sections)

    def _extract_spec(self, response: str) -> str:
        """Extract the alignment spec from the LLM response.

        The response should be a complete markdown document. Strip any
        wrapping fences if the LLM added them.
        """
        text = response.strip()
        # Remove markdown code fences if present
        if text.startswith("```markdown"):
            text = text[len("```markdown"):].strip()
        elif text.startswith("```md"):
            text = text[len("```md"):].strip()
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
    issues = validate_provider_config(api, DEFAULT_PROVIDER)
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

    if not PLAN_FILE.exists():
        print(
            f"Error: Agent plan not found at {PLAN_FILE}. "
            "Run build-agents first."
        )
        return 1

    try:
        return asyncio.run(_async_run(output_path))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


__all__ = [
    "AlignmentSpecCreator",
    "load_planned_agent_ids",
    "run",
]
