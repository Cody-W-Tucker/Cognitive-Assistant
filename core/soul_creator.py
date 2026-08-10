#!/usr/bin/env python3
"""Persona discovery and per-agent soul generation.

Reads the generated translation layer and the latest existential and
operational human profiles, discovers a set of distinct agent personas the
user needs, then generates one soul document per persona.

Pipeline:
  1. Persona discovery — the LLM identifies distinct, non-redundant agent
     personas using the translation layer as the orchestrator constitution,
     the inferred archetype, and bounded profile evidence as the signal for
     what specialist domains are needed. The result is a structured persona
     map (JSON) plus a human-readable persona_map.md.
  2. Per-agent soul generation — for each declared persona, the LLM writes
     a first-person soul document consuming the persona definition and the
     translation layer's operational guidance. Specialist souls inherit the
     orchestrator constitution rather than re-deriving the user from raw
     psychometric profile material.

Outputs:
  workspaces/alignment/artifacts/persona_map.md   — intermediate, human-readable
  workspaces/alignment/artifacts/agents/<slug>.md — one per persona

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
from typing import List, Optional

from core.config import ROOT_DIR
from core.translation_layer_creator import (
    _strip_code_fences,
    _validate_generated_content,
    load_profile_sources,
    load_translation_layer,
)
from lib.config import APIConfig, DEFAULT_PROVIDER, validate_provider_config
from lib.llm import LLMHandle, close_client_async, create_client, generate_text_async


PERSONA_DISCOVERY_SEED_PATH = (
    ROOT_DIR / "profiles" / "alignment" / "prompts" / "persona_discovery_seed.md"
)
AGENT_SOUL_SEED_PATH = (
    ROOT_DIR / "profiles" / "alignment" / "prompts" / "agent_soul_seed.md"
)

OUTPUT_DIR = ROOT_DIR / "workspaces" / "alignment" / "artifacts"
PERSONA_MAP_FILE = OUTPUT_DIR / "persona_map.md"
AGENTS_DIR = OUTPUT_DIR / "agents"

MAX_PERSONAS = 8
MIN_PERSONAS = 1
SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9\-]{0,38}[a-z0-9]$")
MAX_AGENT_SOUL_OUTPUT_TOKENS = 2400
MAX_PERSONA_DISCOVERY_OUTPUT_TOKENS = 6000


@dataclass(frozen=True)
class AgentPersona:
    """One discovered agent persona."""

    name: str
    slug: str
    archetype: str
    responsibility: str
    boundary: str
    fit_rationale: str


def sanitize_slug(raw: str) -> Optional[str]:
    """Return a safe slug or None if the input cannot be made safe.

    Rules: lowercase ASCII letters, digits, hyphens only; 2-40 chars;
    must start with a letter.
    """
    if not raw or not isinstance(raw, str):
        return None
    slug = raw.strip().lower()
    slug = re.sub(r"[^a-z0-9\-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if SLUG_PATTERN.match(slug):
        return slug
    return None


def parse_persona_discovery_response(response: str) -> List[AgentPersona]:
    """Parse the JSON persona map from the LLM response.

    Handles responses with or without markdown code fences.
    Raises ValueError on parse failure or validation failure.
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
        raise ValueError(f"Could not parse persona discovery response as JSON: {exc}") from exc

    if not isinstance(data, dict) or "agents" not in data:
        raise ValueError("Persona discovery response missing 'agents' key")

    raw_agents = data["agents"]
    if not isinstance(raw_agents, list):
        raise ValueError("'agents' must be a list")

    personas: List[AgentPersona] = []
    seen_slugs: set[str] = set()

    for idx, raw in enumerate(raw_agents):
        if not isinstance(raw, dict):
            raise ValueError(f"Agent entry {idx} is not an object")

        required_keys = {"name", "slug", "archetype", "responsibility", "boundary", "fit_rationale"}
        missing = required_keys - set(raw.keys())
        if missing:
            raise ValueError(f"Agent entry {idx} missing keys: {', '.join(sorted(missing))}")

        slug = sanitize_slug(raw["slug"])
        if slug is None:
            raise ValueError(
                f"Agent entry {idx} has invalid slug: {raw['slug']!r}"
            )
        if slug in seen_slugs:
            raise ValueError(f"Duplicate slug: {slug}")
        seen_slugs.add(slug)

        name = str(raw["name"]).strip()
        if not name:
            raise ValueError(f"Agent entry {idx} has empty name")

        personas.append(
            AgentPersona(
                name=name,
                slug=slug,
                archetype=str(raw["archetype"]).strip(),
                responsibility=str(raw["responsibility"]).strip(),
                boundary=str(raw["boundary"]).strip(),
                fit_rationale=str(raw["fit_rationale"]).strip(),
            )
        )

    if len(personas) < MIN_PERSONAS:
        raise ValueError(
            f"Persona discovery returned {len(personas)} agents; minimum is {MIN_PERSONAS}"
        )
    if len(personas) > MAX_PERSONAS:
        raise ValueError(
            f"Persona discovery returned {len(personas)} agents; maximum is {MAX_PERSONAS}"
        )

    return personas


def _format_persona_json(persona: AgentPersona) -> str:
    """Format one persona as a JSON object for the persona map."""
    return json.dumps(
        {
            "name": persona.name,
            "slug": persona.slug,
            "archetype": persona.archetype,
            "responsibility": persona.responsibility,
            "boundary": persona.boundary,
            "fit_rationale": persona.fit_rationale,
        },
        indent=2,
    )


def build_persona_map_markdown(personas: List[AgentPersona]) -> str:
    """Build the human-readable persona_map.md content."""
    lines: List[str] = []
    lines.append("# Persona Map\n")
    lines.append(
        f"Discovered {len(personas)} distinct agent personas from the "
        "existential and operational profile artifacts.\n"
    )

    for persona in personas:
        lines.append(f"## {persona.name}")
        lines.append(f"- **Slug:** `{persona.slug}`")
        lines.append(f"- **Archetype:** {persona.archetype}")
        lines.append(f"- **Responsibility:** {persona.responsibility}")
        lines.append(f"- **Boundary:** {persona.boundary}")
        lines.append(f"- **Fit rationale:** {persona.fit_rationale}")
        lines.append("")

    lines.append("## Agent Souls\n")
    lines.append(
        "One soul document per persona lives in `agents/` alongside this file.\n"
    )
    for persona in personas:
        lines.append(f"- `{persona.slug}.md` — {persona.name}")

    return "\n".join(lines) + "\n"


class SoulCreator:
    """Discover agent personas and generate per-agent soul documents."""

    def __init__(self) -> None:
        self.api = APIConfig()
        self.handle: LLMHandle = create_client(
            self.api,
            provider=DEFAULT_PROVIDER,
            model=self.api.get_model(provider=DEFAULT_PROVIDER),
            async_mode=True,
        )

    async def generate_agents(self) -> Path:
        """Run the full pipeline: persona discovery + per-agent souls."""
        translation_layer, archetype = load_translation_layer()
        profile_evidence = load_profile_sources()

        personas = await self._discover_personas(
            translation_layer, archetype, profile_evidence
        )
        persona_map_content = build_persona_map_markdown(personas)
        self._write_artifact(PERSONA_MAP_FILE, persona_map_content)
        print(f"Info: Wrote persona map to {PERSONA_MAP_FILE}")

        AGENTS_DIR.mkdir(parents=True, exist_ok=True)
        self._cleanup_stale_agents({p.slug for p in personas})

        persona_definitions_text = "\n\n".join(
            f"### {p.name} ({p.slug})\n"
            f"- Archetype: {p.archetype}\n"
            f"- Responsibility: {p.responsibility}\n"
            f"- Boundary: {p.boundary}\n"
            f"- Fit rationale: {p.fit_rationale}"
            for p in personas
        )

        for persona in personas:
            soul_content = await self._generate_agent_soul(
                persona, translation_layer, persona_definitions_text
            )
            _validate_generated_content(
                soul_content, artifact_label=f"agent soul for {persona.slug}"
            )
            agent_path = AGENTS_DIR / f"{persona.slug}.md"
            self._write_artifact(agent_path, soul_content)
            print(f"Info: Wrote agent soul to {agent_path}")

        return PERSONA_MAP_FILE

    async def _discover_personas(
        self,
        translation_layer: str,
        archetype: str,
        profile_evidence: str,
    ) -> List[AgentPersona]:
        """Stage 1: LLM discovers the persona set from the translation layer."""
        seed = self._load_text_file(PERSONA_DISCOVERY_SEED_PATH, "Persona discovery seed")
        prompt = seed.format(
            translation_layer=translation_layer,
            archetype=archetype,
            profile_evidence=profile_evidence,
        )
        response = await generate_text_async(
            self.handle,
            user_prompt=prompt,
            temperature=self.api.TEMPERATURE,
            max_output_tokens=MAX_PERSONA_DISCOVERY_OUTPUT_TOKENS,
        )
        return parse_persona_discovery_response(response)

    async def _generate_agent_soul(
        self,
        persona: AgentPersona,
        translation_layer: str,
        persona_definitions_text: str,
    ) -> str:
        """Stage 2: LLM generates one agent's soul document."""
        seed = self._load_text_file(AGENT_SOUL_SEED_PATH, "Agent soul seed")
        persona_definition = (
            f"Name: {persona.name}\n"
            f"Slug: {persona.slug}\n"
            f"Archetype: {persona.archetype}\n"
            f"Responsibility: {persona.responsibility}\n"
            f"Boundary: {persona.boundary}\n"
            f"Fit rationale: {persona.fit_rationale}\n\n"
            f"All personas in this constellation:\n{persona_definitions_text}"
        )
        prompt = seed.format(
            persona_definition=persona_definition,
            translation_layer=translation_layer,
        )
        response = await generate_text_async(
            self.handle,
            user_prompt=prompt,
            temperature=self.api.TEMPERATURE,
            max_output_tokens=MAX_AGENT_SOUL_OUTPUT_TOKENS,
        )
        return _strip_code_fences(response)

    def _cleanup_stale_agents(self, active_slugs: set[str]) -> None:
        """Remove agent soul files that are no longer in the active persona set."""
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
    "AgentPersona",
    "sanitize_slug",
    "parse_persona_discovery_response",
    "build_persona_map_markdown",
    "run",
]
