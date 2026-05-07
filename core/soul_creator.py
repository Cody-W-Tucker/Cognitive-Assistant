#!/usr/bin/env python3
"""Generate a durable SOUL.md from both layer system prompts.

Reads the latest existential and operational system prompts, combines them with
the alignment soul seed template, and produces a single SOUL.md artifact for
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
from lib.config import APIConfig, validate_provider_config
from lib.llm import LLMHandle, close_client_async, create_client, generate_text_async


SEED_PATH = ROOT_DIR / "profiles" / "alignment" / "prompts" / "soul_seed.md"
OUTPUT_DIR = ROOT_DIR / "workspaces" / "alignment" / "artifacts"
OUTPUT_FILE = OUTPUT_DIR / "SOUL.md"
MAX_SOUL_OUTPUT_TOKENS = 6000


class SoulCreator:
    """Generate a durable SOUL.md from both layer prompts."""

    def __init__(self) -> None:
        self.api = APIConfig()
        self.handle: LLMHandle = create_client(
            self.api,
            model=self.api.get_model("refine"),
            async_mode=True,
        )

    async def generate_soul(self, output_path: Optional[Path] = None) -> Path:
        """Generate the SOUL.md artifact and write it to disk."""
        seed_content = self._load_seed()
        system_prompts = self._load_system_prompts()

        prompt = seed_content.format(system_prompts=system_prompts)
        response = await generate_text_async(
            self.handle,
            user_prompt=prompt,
            temperature=self.api.TEMPERATURE,
            max_output_tokens=MAX_SOUL_OUTPUT_TOKENS,
        )

        soul_content = self._extract_soul(response)
        resolved_output = output_path or OUTPUT_FILE
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        resolved_output.write_text(soul_content + "\n", encoding="utf-8")
        print(f"Info: Wrote SOUL.md to {resolved_output}")
        return resolved_output

    def _load_seed(self) -> str:
        if not SEED_PATH.exists():
            raise FileNotFoundError(f"Soul seed not found at {SEED_PATH}")
        return SEED_PATH.read_text(encoding="utf-8")

    def _load_system_prompts(self) -> str:
        existential_prompt = self._load_latest_system_prompt(
            EXISTENTIAL_PROFILE.workspace_dir / "artifacts",
            "existential",
        )
        operational_prompt = self._load_latest_system_prompt(
            OPERATIONAL_PROFILE.workspace_dir / "artifacts",
            "operational",
        )
        return "\n\n".join([existential_prompt, operational_prompt])

    def _load_latest_system_prompt(self, artifacts_dir: Path, layer_name: str) -> str:
        if not artifacts_dir.exists():
            raise FileNotFoundError(f"Artifacts directory not found: {artifacts_dir}")

        prompt_files = sorted(artifacts_dir.glob("system_prompt*.md"))
        if not prompt_files:
            raise FileNotFoundError(
                f"No system_prompt*.md files found in {artifacts_dir}. Run build-prompts first."
            )

        content = prompt_files[-1].read_text(encoding="utf-8").strip()
        return (
            f'<system_prompt layer="{layer_name}">\n'
            f"{content}\n"
            f"</system_prompt>"
        )

    def _extract_soul(self, response: str) -> str:
        text = response.strip()
        if text.startswith("```markdown"):
            text = text[len("```markdown") :].strip()
        elif text.startswith("```md"):
            text = text[len("```md") :].strip()
        elif text.startswith("```"):
            text = text[3:].strip()

        if text.endswith("```"):
            text = text[:-3].strip()

        required_sections = [
            "# SOUL",
            "## Opening",
            "## Core Truths",
            "## Boundaries",
            "## Voice",
            "## Continuity",
            "## Closing",
        ]
        for section in required_sections:
            if section not in text:
                raise ValueError(f"Generated SOUL.md is missing '{section}'")

        word_count = len(text.split())
        if word_count < 180:
            raise ValueError(
                f"Generated SOUL.md is unexpectedly short ({word_count} words)."
            )
        if word_count > 1400:
            raise ValueError(
                f"Generated SOUL.md is unexpectedly long ({word_count} words)."
            )

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
    issues = validate_provider_config(api)
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
