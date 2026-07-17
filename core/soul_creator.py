#!/usr/bin/env python3
"""Generate a durable SOUL.md from both layer source artifacts.

Reads the latest existential and operational human profiles, infers a fitting
archetype, then uses that archetype to produce a single SOUL.md artifact for
Hermes/OpenClaw-style agents.

Usage:
    python -m core build-soul
    python -m core build-soul --output /path/to/SOUL.md
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

from core.config import ROOT_DIR, EXISTENTIAL_PROFILE, OPERATIONAL_PROFILE
from lib.config import APIConfig, DEFAULT_PROVIDER, validate_provider_config
from lib.llm import LLMHandle, close_client_async, create_client, generate_text_async


ARCHETYPE_SEED_PATH = (
    ROOT_DIR / "profiles" / "alignment" / "prompts" / "soul_archetype_seed.md"
)
SOUL_SEED_PATH = ROOT_DIR / "profiles" / "alignment" / "prompts" / "soul_seed.md"
OUTPUT_DIR = ROOT_DIR / "workspaces" / "alignment" / "artifacts"
OUTPUT_FILE = OUTPUT_DIR / "SOUL.md"
ARCHETYPE_OUTPUT_FILE = OUTPUT_DIR / "SOUL_ARCHETYPE.md"
MAX_SOUL_OUTPUT_TOKENS = 2400
MAX_ARCHETYPE_OUTPUT_TOKENS = 6000
class SoulCreator:
    """Generate a durable SOUL.md from both layer source artifacts."""

    def __init__(self) -> None:
        self.api = APIConfig()
        self.handle: LLMHandle = create_client(
            self.api,
            provider=DEFAULT_PROVIDER,
            model=self.api.get_model(provider=DEFAULT_PROVIDER),
            async_mode=True,
        )

    async def generate_soul(self, output_path: Optional[Path] = None) -> Path:
        """Generate the SOUL.md artifact and write it to disk."""
        archetype_profile_sources = self._load_profile_sources()
        archetype = await self._generate_archetype(archetype_profile_sources)
        self._write_artifact(ARCHETYPE_OUTPUT_FILE, archetype)
        soul_profile_sources = self._load_profile_sources()

        soul_seed = self._load_text_file(SOUL_SEED_PATH, "Soul seed")
        prompt = soul_seed.format(profile_sources=soul_profile_sources, archetype=archetype)
        response = await generate_text_async(
            self.handle,
            user_prompt=prompt,
            temperature=self.api.TEMPERATURE,
            max_output_tokens=MAX_SOUL_OUTPUT_TOKENS,
        )

        soul_content = self._extract_soul(response)
        resolved_output = output_path or OUTPUT_FILE
        self._write_artifact(resolved_output, soul_content)
        print(f"Info: Wrote SOUL.md to {resolved_output}")
        return resolved_output

    async def _generate_archetype(self, profile_sources: str) -> str:
        archetype_seed = self._load_text_file(ARCHETYPE_SEED_PATH, "Soul archetype seed")
        prompt = archetype_seed.format(profile_sources=profile_sources)
        response = await generate_text_async(
            self.handle,
            user_prompt=prompt,
            temperature=self.api.TEMPERATURE,
            max_output_tokens=MAX_ARCHETYPE_OUTPUT_TOKENS,
        )
        return self._extract_archetype(response)

    def _load_text_file(self, path: Path, label: str) -> str:
        if not path.exists():
            raise FileNotFoundError(f"{label} not found at {path}")
        return path.read_text(encoding="utf-8")

    def _write_artifact(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")

    def _load_profile_sources(self) -> str:
        existential_prompt = self._load_latest_artifact(
            EXISTENTIAL_PROFILE.workspace_dir / "artifacts",
            "existential",
            artifact_pattern="human_profile*.md",
            artifact_label="human_profile",
        )
        operational_prompt = self._load_latest_artifact(
            OPERATIONAL_PROFILE.workspace_dir / "artifacts",
            "operational",
            artifact_pattern="human_profile*.md",
            artifact_label="human_profile",
        )
        return "\n\n".join([existential_prompt, operational_prompt])

    def _load_latest_artifact(
        self,
        artifacts_dir: Path,
        layer_name: str,
        *,
        artifact_pattern: str,
        artifact_label: str,
    ) -> str:
        if not artifacts_dir.exists():
            raise FileNotFoundError(f"Artifacts directory not found: {artifacts_dir}")

        prompt_files = sorted(artifacts_dir.glob(artifact_pattern))
        if not prompt_files:
            raise FileNotFoundError(
                f"No {artifact_pattern} files found in {artifacts_dir}. Run build-prompts first."
            )

        content = prompt_files[-1].read_text(encoding="utf-8").strip()

        return (
            f'<profile_source layer="{layer_name}" artifact="{artifact_label}">\n'
            f"{content}\n"
            f"</profile_source>"
        )

    def _extract_archetype(self, response: str) -> str:
        return self._strip_code_fences(response)

    def _extract_soul(self, response: str) -> str:
        return self._strip_code_fences(response)

    def _strip_code_fences(self, response: str) -> str:
        text = response.strip()
        if text.startswith("```markdown"):
            text = text[len("```markdown") :].strip()
        elif text.startswith("```md"):
            text = text[len("```md") :].strip()
        elif text.startswith("```"):
            text = text[3:].strip()

        if text.endswith("```"):
            text = text[:-3].strip()

        return text


async def _async_run(output_path: Optional[Path]) -> int:
    creator = SoulCreator()
    try:
        await creator.generate_soul(output_path=output_path)
        return 0
    finally:
        await close_client_async(creator.handle)


def run(*, output_path: Optional[Path] = None) -> int:
    api = APIConfig()
    issues = validate_provider_config(api, DEFAULT_PROVIDER)
    if issues:
        print("Error: Configuration issues found")
        for issue in issues:
            print(f"- {issue}")
        return 1

    try:
        return asyncio.run(_async_run(output_path))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


__all__ = ["SoulCreator", "run"]
