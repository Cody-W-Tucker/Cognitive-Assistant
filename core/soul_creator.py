#!/usr/bin/env python3
"""Catalog-constrained agent archetype selection and per-agent soul generation.

Reads the generated translation layer, the latest existential and operational
human profiles, and the predefined archetype catalog, then selects applicable
archetypes, calibrates them to the user, and generates one soul document per
selected archetype.

Pipeline:
  1. Archetype selection — the LLM selects which predefined archetypes apply
     to this user and produces a calibration for each: why this archetype is
     needed, what user-specific patterns it addresses. The result is a
     structured selection (JSON) plus a human-readable persona_map.md.
  2. Per-agent soul generation — for each selected archetype, the LLM writes
     a first-person soul document consuming the full archetype contract,
     user calibration, translation layer, and relevant skill material.

Outputs:
  workspaces/alignment/artifacts/persona_map.md   — intermediate, human-readable
  workspaces/alignment/artifacts/agents/<slug>.md — one per selected archetype

This command sits above the profile system: it reads from both registered
profiles but does not belong to either. It is invoked without --profile.

Prerequisites:
  The translation layer must have been generated first via
  ``python -m core build-translation-layer``.

Usage:
    python -m core build-agents
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from core.archetype_catalog import (
    ARCHETYPES_DIR,
    ArchetypeSpec,
    load_archetype_catalog,
    validate_archetype_slugs,
    validate_skill_assignments,
)
from core.config import ROOT_DIR
from core.skill_engine import find_canonical_skill
from core.translation_layer_creator import (
    _strip_code_fences,
    _validate_generated_content,
    load_profile_sources,
    load_translation_layer,
)
from lib.config import APIConfig, DEFAULT_PROVIDER, validate_provider_config
from lib.llm import LLMHandle, close_client_async, create_client, generate_text_async


ARCHETYPE_SELECTION_SEED_PATH = (
    ROOT_DIR / "profiles" / "alignment" / "prompts" / "archetype_selection_seed.md"
)
AGENT_SOUL_SEED_PATH = (
    ROOT_DIR / "profiles" / "alignment" / "prompts" / "agent_soul_seed.md"
)

OUTPUT_DIR = ROOT_DIR / "workspaces" / "alignment" / "artifacts"
PERSONA_MAP_FILE = OUTPUT_DIR / "persona_map.md"
AGENTS_DIR = OUTPUT_DIR / "agents"

MAX_AGENT_SOUL_OUTPUT_TOKENS = 2400
MAX_ARCHETYPE_SELECTION_OUTPUT_TOKENS = 6000


@dataclass(frozen=True)
class SelectedArchetype:
    """One archetype selected from the catalog with user-specific calibration."""

    slug: str
    calibration: str
    skills: List[str]


def parse_archetype_selection_response(
    response: str,
    catalog: Dict[str, ArchetypeSpec],
) -> List[SelectedArchetype]:
    """Parse the JSON archetype selection from the LLM response.

    Validates that every archetype slug is in the catalog and every skill
    slug matches the archetype's declared canonical skills. Unknown slugs
    fail with a clear error.
    """
    text = response.strip()

    # Strip markdown code fences if present.
    if text.startswith("```"):
        first_newline = text.index("\n") if "\n" in text else 3
        text = text[first_newline + 1:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse archetype selection response as JSON: {exc}") from exc

    if not isinstance(data, dict) or "agents" not in data:
        raise ValueError("Archetype selection response missing 'agents' key")

    raw_agents = data["agents"]
    if not isinstance(raw_agents, list):
        raise ValueError("'agents' must be a list")

    if not raw_agents:
        raise ValueError("Archetype selection returned 0 agents; minimum is 1")

    selections: List[SelectedArchetype] = []
    seen_slugs: set[str] = set()

    for idx, raw in enumerate(raw_agents):
        if not isinstance(raw, dict):
            raise ValueError(f"Agent entry {idx} is not an object")

        required_keys = {"archetype", "calibration", "skills"}
        missing = required_keys - set(raw.keys())
        if missing:
            raise ValueError(f"Agent entry {idx} missing keys: {', '.join(sorted(missing))}")

        if not isinstance(raw["archetype"], str):
            raise ValueError(f"Agent entry {idx}: 'archetype' must be a string")
        archetype_slug = raw["archetype"].strip()
        if archetype_slug not in catalog:
            available = ", ".join(sorted(catalog))
            raise ValueError(
                f"Agent entry {idx}: unknown archetype '{archetype_slug}'. "
                f"Available archetypes: {available}"
            )
        if archetype_slug in seen_slugs:
            raise ValueError(f"Duplicate archetype selection: {archetype_slug}")
        seen_slugs.add(archetype_slug)

        if not isinstance(raw["calibration"], str):
            raise ValueError(f"Agent entry {idx}: 'calibration' must be a string")
        calibration = raw["calibration"].strip()
        if not calibration:
            raise ValueError(f"Agent entry {idx}: empty calibration")

        raw_skills = raw["skills"]
        if not isinstance(raw_skills, list):
            raise ValueError(f"Agent entry {idx}: 'skills' must be a list")
        if not raw_skills:
            raise ValueError(f"Agent entry {idx}: empty skills list")

        if any(not isinstance(skill, str) or not skill.strip() for skill in raw_skills):
            raise ValueError(
                f"Agent entry {idx}: every skill identifier must be a non-empty string"
            )
        skill_slugs = [skill.strip() for skill in raw_skills]
        duplicates = sorted({skill for skill in skill_slugs if skill_slugs.count(skill) > 1})
        if duplicates:
            raise ValueError(
                f"Agent entry {idx}: duplicate skill identifier(s): {', '.join(duplicates)}"
            )
        archetype_spec = catalog[archetype_slug]

        # Validate skills match the archetype's canonical skills
        canonical_set = set(archetype_spec.canonical_skills)
        unknown_skills = [s for s in skill_slugs if s not in canonical_set]
        if unknown_skills:
            raise ValueError(
                f"Agent entry {idx} (archetype '{archetype_slug}'): "
                f"unknown skill(s): {', '.join(unknown_skills)}. "
                f"Canonical skills for this archetype: {', '.join(archetype_spec.canonical_skills)}"
            )

        selections.append(
            SelectedArchetype(
                slug=archetype_slug,
                calibration=calibration,
                skills=skill_slugs,
            )
        )

    return selections


def _format_selected_archetype_for_persona_map(
    selection: SelectedArchetype,
    catalog: Dict[str, ArchetypeSpec],
) -> str:
    """Format one selected archetype for the persona map markdown."""
    spec = catalog[selection.slug]
    skills_list = ", ".join(f"`{s}`" for s in selection.skills)
    return (
        f"## {spec.name}\n"
        f"- **Slug:** `{selection.slug}`\n"
        f"- **Purpose:** {spec.purpose}\n"
        f"- **Calibration:** {selection.calibration}\n"
        f"- **Canonical skills:** {skills_list}\n"
    )


def build_persona_map_markdown(
    selections: List[SelectedArchetype],
    catalog: Dict[str, ArchetypeSpec],
) -> str:
    """Build the human-readable persona_map.md content."""
    lines: List[str] = []
    lines.append("# Persona Map\n")
    lines.append(
        f"Selected {len(selections)} archetype(s) from the catalog and "
        "calibrated them to the user.\n"
    )

    for selection in selections:
        lines.append(
            _format_selected_archetype_for_persona_map(selection, catalog)
        )

    lines.append("## Agent Souls\n")
    lines.append(
        "One soul document per selected archetype lives in `agents/` "
        "alongside this file.\n"
    )
    for selection in selections:
        spec = catalog[selection.slug]
        lines.append(f"- `{selection.slug}.md` — {spec.name}")

    return "\n".join(lines) + "\n"


def _load_skill_material(skill_slugs: List[str]) -> str:
    """Load canonical skill content for the listed skill slugs.

    Returns a tagged document suitable for injection into the agent soul
    prompt. Missing skills raise a clear error (should have been caught
    earlier during validation).
    """
    sections: List[str] = []
    for skill_slug in skill_slugs:
        skill_path = find_canonical_skill(skill_slug)
        if skill_path is None:
            raise ValueError(
                f"Skill '{skill_slug}' not found in canonical skill store. "
                "Cannot generate agent soul without skill material."
            )
        content = skill_path.read_text(encoding="utf-8").strip()
        sections.append(
            f'<skill name="{skill_slug}">\n{content}\n</skill>'
        )
    return "\n\n".join(sections)


class SoulCreator:
    """Select archetypes from catalog and generate per-agent soul documents."""

    def __init__(self) -> None:
        self.api = APIConfig()
        self.handle: LLMHandle = create_client(
            self.api,
            provider=DEFAULT_PROVIDER,
            model=self.api.get_model(provider=DEFAULT_PROVIDER),
            async_mode=True,
        )

    async def generate_agents(self) -> Path:
        """Run the full pipeline: archetype selection + per-agent souls."""
        translation_layer, archetype = load_translation_layer()
        profile_evidence = load_profile_sources()
        catalog = load_archetype_catalog()

        # Validate all archetype skill assignments upfront
        for spec in catalog.values():
            validate_skill_assignments(spec.slug, spec.canonical_skills)

        selections = await self._select_archetypes(
            catalog, translation_layer, archetype, profile_evidence
        )

        persona_map_content = build_persona_map_markdown(selections, catalog)
        self._write_artifact(PERSONA_MAP_FILE, persona_map_content)
        print(f"Info: Wrote persona map to {PERSONA_MAP_FILE}")

        AGENTS_DIR.mkdir(parents=True, exist_ok=True)
        self._cleanup_stale_agents({s.slug for s in selections})

        for selection in selections:
            spec = catalog[selection.slug]
            skill_material = _load_skill_material(selection.skills)
            soul_content = await self._generate_agent_soul(
                spec, selection, translation_layer, skill_material
            )
            _validate_generated_content(
                soul_content, artifact_label=f"agent soul for {selection.slug}"
            )
            agent_path = AGENTS_DIR / f"{selection.slug}.md"
            self._write_artifact(agent_path, soul_content)
            print(f"Info: Wrote agent soul to {agent_path}")

        return PERSONA_MAP_FILE

    async def _select_archetypes(
        self,
        catalog: Dict[str, ArchetypeSpec],
        translation_layer: str,
        archetype: str,
        profile_evidence: str,
    ) -> List[SelectedArchetype]:
        """Stage 1: LLM selects applicable archetypes from the catalog."""
        seed = self._load_text_file(
            ARCHETYPE_SELECTION_SEED_PATH, "Archetype selection seed"
        )

        # Build catalog summary for the prompt
        catalog_summary = "\n\n".join(
            spec.contract_text() for spec in catalog.values()
        )

        prompt = seed.format(
            catalog=catalog_summary,
            translation_layer=translation_layer,
            archetype=archetype,
            profile_evidence=profile_evidence,
        )
        response = await generate_text_async(
            self.handle,
            user_prompt=prompt,
            temperature=self.api.TEMPERATURE,
            max_output_tokens=MAX_ARCHETYPE_SELECTION_OUTPUT_TOKENS,
        )
        return parse_archetype_selection_response(response, catalog)

    async def _generate_agent_soul(
        self,
        spec: ArchetypeSpec,
        selection: SelectedArchetype,
        translation_layer: str,
        skill_material: str,
    ) -> str:
        """Stage 2: LLM generates one agent's soul document."""
        seed = self._load_text_file(AGENT_SOUL_SEED_PATH, "Agent soul seed")

        archetype_contract = spec.contract_text()
        agent_definition = (
            f"Name: {spec.name}\n"
            f"Slug: {selection.slug}\n\n"
            f"## Operating Contract\n\n{archetype_contract}\n\n"
            f"## User Calibration\n\n{selection.calibration}\n\n"
            f"## Assigned Skills\n\n"
            f"Skills: {', '.join(selection.skills)}"
        )

        prompt = seed.format(
            agent_definition=agent_definition,
            translation_layer=translation_layer,
            skill_material=skill_material,
        )
        response = await generate_text_async(
            self.handle,
            user_prompt=prompt,
            temperature=self.api.TEMPERATURE,
            max_output_tokens=MAX_AGENT_SOUL_OUTPUT_TOKENS,
        )
        return _strip_code_fences(response)

    def _cleanup_stale_agents(self, active_slugs: set[str]) -> None:
        """Remove agent soul files that are no longer in the active selection."""
        if not AGENTS_DIR.exists():
            return
        for agent_file in AGENTS_DIR.glob("*.md"):
            slug = agent_file.stem
            if slug not in active_slugs:
                agent_file.unlink()
                print(f"Info: Removed stale agent soul {agent_file}")

    def _load_text_file(self, path: Path, label: str) -> str:
        if not path.exists():
            raise FileNotFoundError(f"{label} not found at {path}")
        return path.read_text(encoding="utf-8")

    def _write_artifact(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


async def _async_run() -> int:
    creator = SoulCreator()
    try:
        await creator.generate_agents()
        return 0
    finally:
        await close_client_async(creator.handle)


def run() -> int:
    """Synchronous entry point for CLI use."""
    api = APIConfig()
    issues = validate_provider_config(api, DEFAULT_PROVIDER)
    if issues:
        print("Error: Configuration issues found")
        for issue in issues:
            print(f"- {issue}")
        return 1

    try:
        return asyncio.run(_async_run())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


__all__ = [
    "SoulCreator",
    "SelectedArchetype",
    "parse_archetype_selection_response",
    "build_persona_map_markdown",
    "run",
]
