#!/usr/bin/env python3
"""Generate the translation layer artifacts: SOUL_ARCHETYPE.md and SOUL.md.

The translation layer is the cross-profile bridge between the raw profile
sources and the specialist agent system. It distills the existential and
operational human profiles into two artifacts:

  1. SOUL_ARCHETYPE.md — the single archetypal counterpart type most deeply
     suited to this user over years.
  2. SOUL.md           — the durable orchestrator soul: the user-fit
     constitution, mode-routing guidance, and operating commitments that
     specialists inherit.

Pipeline:
  1. Archetype inference — both profile human_profile artifacts + the
     archetype seed prompt produce SOUL_ARCHETYPE.md.
  2. Soul synthesis      — both profile human_profile artifacts + the
     inferred archetype + the soul seed prompt produce SOUL.md.

Outputs:
  workspaces/alignment/artifacts/SOUL_ARCHETYPE.md
  workspaces/alignment/artifacts/SOUL.md

This command sits above the profile system: it reads from both registered
profiles but does not belong to either. It is invoked without --profile.

Usage:
    python -m core build-translation-layer
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

from core.config import EXISTENTIAL_PROFILE, OPERATIONAL_PROFILE, ROOT_DIR
from lib.config import APIConfig, DEFAULT_PROVIDER, validate_provider_config
from lib.llm import LLMHandle, close_client_async, create_client, generate_text_async


ARCHETYPE_SEED_PATH = (
    ROOT_DIR / "profiles" / "alignment" / "prompts" / "soul_archetype_seed.md"
)
SOUL_SEED_PATH = ROOT_DIR / "profiles" / "alignment" / "prompts" / "soul_seed.md"

OUTPUT_DIR = ROOT_DIR / "workspaces" / "alignment" / "artifacts"
SOUL_OUTPUT_FILE = OUTPUT_DIR / "SOUL.md"
ARCHETYPE_OUTPUT_FILE = OUTPUT_DIR / "SOUL_ARCHETYPE.md"

MAX_SOUL_OUTPUT_TOKENS = 2400
MAX_ARCHETYPE_OUTPUT_TOKENS = 6000


def translation_layer_paths() -> tuple[Path, Path]:
    """Return (SOUL.md path, SOUL_ARCHETYPE.md path)."""
    return SOUL_OUTPUT_FILE, ARCHETYPE_OUTPUT_FILE


def load_translation_layer() -> tuple[str, str]:
    """Load the generated translation layer artifacts from disk.

    Returns (soul_content, archetype_content). Raises FileNotFoundError if
    either artifact is missing.
    """
    soul_path, archetype_path = translation_layer_paths()
    if not soul_path.exists():
        raise FileNotFoundError(
            f"Translation layer SOUL.md not found at {soul_path}. "
            "Run `python -m core build-translation-layer` first."
        )
    if not archetype_path.exists():
        raise FileNotFoundError(
            f"Translation layer SOUL_ARCHETYPE.md not found at {archetype_path}. "
            "Run `python -m core build-translation-layer` first."
        )
    return soul_path.read_text(encoding="utf-8"), archetype_path.read_text(encoding="utf-8")


def _strip_code_fences(response: str) -> str:
    """Strip optional markdown code fences from an LLM response."""
    text = response.strip()
    if text.startswith("```markdown"):
        text = text[len("```markdown"):].strip()
    elif text.startswith("```md"):
        text = text[len("```md"):].strip()
    elif text.startswith("```"):
        text = text[3:].strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    return text


def _validate_generated_content(content: str, *, artifact_label: str) -> str:
    """Reject empty LLM output after fence stripping.

    Returns the stripped content unchanged when valid. Raises ``ValueError``
    when the content is empty or whitespace-only so we never persist an
    invalid artifact.
    """
    if not content or not content.strip():
        raise ValueError(
            f"Generated {artifact_label} is empty; refusing to write an invalid artifact."
        )
    return content


def _load_text_file(path: Path, label: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found at {path}")
    return path.read_text(encoding="utf-8")


def _write_artifact(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + "\n", encoding="utf-8")


def load_profile_sources() -> str:
    """Load the latest human_profile artifact from each registered profile.

    Returns a single string with both profile sources wrapped in
    ``<profile_source>`` tags so downstream prompts can reference them.
    """
    existential_source = _load_latest_artifact(
        EXISTENTIAL_PROFILE.workspace_dir / "artifacts",
        "existential",
        artifact_pattern="human_profile*.md",
        artifact_label="human_profile",
    )
    operational_source = _load_latest_artifact(
        OPERATIONAL_PROFILE.workspace_dir / "artifacts",
        "operational",
        artifact_pattern="human_profile*.md",
        artifact_label="human_profile",
    )
    return "\n\n".join([existential_source, operational_source])


def _load_latest_artifact(
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
            f"No {artifact_pattern} files found in {artifacts_dir}. "
            "Run build-prompts first."
        )

    content = prompt_files[-1].read_text(encoding="utf-8").strip()

    return (
        f'<profile_source layer="{layer_name}" artifact="{artifact_label}">\n'
        f"{content}\n"
        f"</profile_source>"
    )


class TranslationLayerCreator:
    """Generate the translation layer artifacts from both profile sources."""

    def __init__(self) -> None:
        self.api = APIConfig()
        self.handle: LLMHandle = create_client(
            self.api,
            provider=DEFAULT_PROVIDER,
            model=self.api.get_model(provider=DEFAULT_PROVIDER),
            async_mode=True,
        )

    async def generate_translation_layer(self) -> tuple[Path, Path]:
        """Generate both translation layer artifacts and write them to disk.

        The artifacts are written to the canonical paths under
        ``workspaces/alignment/artifacts/``. Returns (soul_path, archetype_path).
        Raises ``ValueError`` if either LLM stage returns empty content so the
        invalid output is never persisted.
        """
        profile_sources = load_profile_sources()

        archetype = await self._generate_archetype(profile_sources)
        _write_artifact(ARCHETYPE_OUTPUT_FILE, archetype)
        print(f"Info: Wrote translation archetype to {ARCHETYPE_OUTPUT_FILE}")

        soul = await self._generate_soul(profile_sources, archetype)
        _write_artifact(SOUL_OUTPUT_FILE, soul)
        print(f"Info: Wrote translation layer soul to {SOUL_OUTPUT_FILE}")

        return SOUL_OUTPUT_FILE, ARCHETYPE_OUTPUT_FILE

    async def _generate_archetype(self, profile_sources: str) -> str:
        archetype_seed = _load_text_file(ARCHETYPE_SEED_PATH, "Translation archetype seed")
        prompt = archetype_seed.format(profile_sources=profile_sources)
        response = await generate_text_async(
            self.handle,
            user_prompt=prompt,
            temperature=self.api.TEMPERATURE,
            max_output_tokens=MAX_ARCHETYPE_OUTPUT_TOKENS,
        )
        stripped = _strip_code_fences(response)
        return _validate_generated_content(stripped, artifact_label="archetype")

    async def _generate_soul(self, profile_sources: str, archetype: str) -> str:
        soul_seed = _load_text_file(SOUL_SEED_PATH, "Translation soul seed")
        prompt = soul_seed.format(profile_sources=profile_sources, archetype=archetype)
        response = await generate_text_async(
            self.handle,
            user_prompt=prompt,
            temperature=self.api.TEMPERATURE,
            max_output_tokens=MAX_SOUL_OUTPUT_TOKENS,
        )
        stripped = _strip_code_fences(response)
        return _validate_generated_content(stripped, artifact_label="translation soul")


async def _async_run() -> int:
    creator = TranslationLayerCreator()
    try:
        await creator.generate_translation_layer()
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
    "TranslationLayerCreator",
    "load_translation_layer",
    "load_profile_sources",
    "translation_layer_paths",
    "run",
]
