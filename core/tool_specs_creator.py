#!/usr/bin/env python3
"""Generate personalized single-tool agent specs from the latest profile output.

Gated on `profile.has_tool_specs`. Reads the latest `system_prompt*.md` from the
profile's artifacts directory, combines it with the profile's seed exemplar
documents (e.g. memory.md, tasks.md from prompts/), and asks the LLM to
produce a JSON map of {filename: SKILL.md content}, one entry per supported tool.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Dict, Optional

from core import adaptation_rules
from core.config import Config
from lib.llm import LLMHandle, close_client_async, create_client, generate_text_async


class ToolSpecsCreator:
    """Generate personalized single-tool agent specs."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.handle: LLMHandle = create_client(
            config.api,
            model=config.api.get_model("refine"),
            async_mode=True,
        )

    @property
    def supported_tools(self) -> dict[str, str]:
        return self.config.profile.supported_tools

    async def generate_tool_specs(
        self,
        bio_path: Optional[Path] = None,
        seed_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
    ) -> Path:
        resolved_bio_path = self._resolve_bio_path(bio_path)
        bio_content = resolved_bio_path.read_text(encoding="utf-8")
        active = adaptation_rules.active_adaptations(self.config)
        overlay = adaptation_rules.render_rule_overlay(active)
        skill_adaptations_path = adaptation_rules.write_skill_adaptations(
            self.config, active
        )
        print(f"Info: Wrote skill adaptations to {skill_adaptations_path}")
        if overlay:
            bio_content = f"{bio_content.rstrip()}\n\n{overlay}\n"
            rules_path = adaptation_rules.write_rules_overlay(self.config, active)
            if rules_path is not None:
                print(f"Info: Wrote adaptation rules overlay to {rules_path}")
        seed_documents = self._load_seed_documents(seed_dir)
        tool_specs_payload = await self._generate_tool_spec_documents(
            bio_content, seed_documents
        )
        resolved_output_dir = output_dir or self.config.paths.TOOL_SPECS_DIR
        self._write_tool_specs(tool_specs_payload, resolved_output_dir)
        captured_path = adaptation_rules.mark_adaptations_captured(
            self.config,
            [str(item.get("id")) for item in active if item.get("id")],
            captured_in="build-tool-specs",
        )
        if captured_path is not None:
            print(f"Info: Updated crystallization artifact {captured_path}")
        return resolved_output_dir

    def _resolve_bio_path(self, bio_path: Optional[Path]) -> Path:
        if bio_path is not None:
            resolved_path = Path(bio_path)
            if not resolved_path.exists():
                raise FileNotFoundError(f"Bio file not found: {resolved_path}")
            return resolved_path

        bio_files = sorted(self.config.paths.ARTIFACTS_DIR.glob("system_prompt*.md"))
        if not bio_files:
            raise FileNotFoundError(
                f"No system_prompt*.md files found in {self.config.paths.ARTIFACTS_DIR}. "
                "Run prompt_creator first or pass --bio."
            )
        return bio_files[-1]

    def _load_seed_documents(self, seed_dir: Optional[Path]) -> Dict[str, str]:
        resolved_seed_dir = (
            Path(seed_dir)
            if seed_dir is not None
            else self.config.paths.PROMPT_RUNTIME_DIR
        )
        if not resolved_seed_dir.exists():
            raise FileNotFoundError(f"Seed directory not found: {resolved_seed_dir}")

        seed_documents: Dict[str, str] = {}
        missing_files: list[str] = []
        for filename in self.supported_tools:
            seed_path = resolved_seed_dir / filename
            if not seed_path.exists():
                missing_files.append(filename)
                continue
            seed_documents[filename] = seed_path.read_text(encoding="utf-8")

        if missing_files:
            missing_list = ", ".join(missing_files)
            raise FileNotFoundError(
                f"Supported tool exemplar files not found in "
                f"{resolved_seed_dir}: {missing_list}"
            )
        return seed_documents

    async def _generate_tool_spec_documents(
        self,
        bio_content: str,
        seed_documents: Dict[str, str],
    ) -> Dict[str, str]:
        prompt = self.config.prompts.tool_specs_creation_template.format(
            bio_content=bio_content,
            supported_tools=self._render_supported_tools(),
            seed_documents=self._render_seed_documents(seed_documents),
        )
        response = await generate_text_async(
            self.handle,
            user_prompt=prompt,
            temperature=self.config.api.TEMPERATURE,
            max_output_tokens=self.config.api.MAX_COMPLETION_TOKENS,
        )
        payload = self._parse_json_response(response)
        self._validate_payload(payload)
        return payload

    def _render_seed_documents(self, seed_documents: Dict[str, str]) -> str:
        rendered = []
        for filename, content in seed_documents.items():
            rendered.append(
                f'<seed_document name="{filename}">\n{content.strip()}\n</seed_document>'
            )
        return "\n\n".join(rendered)

    def _render_supported_tools(self) -> str:
        return "\n".join(
            f"- `{filename}`: {description}"
            for filename, description in self.supported_tools.items()
        )

    def _parse_json_response(self, response: str) -> Dict[str, str]:
        match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", response)
        json_text = match.group(1) if match else response.strip()
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse tool specs JSON: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ValueError("Tool specs payload must be a JSON object")
        return {str(key): str(value) for key, value in parsed.items()}

    def _validate_payload(self, payload: Dict[str, str]) -> None:
        if not payload:
            raise ValueError("Generated tool specs payload is empty")

        if len(payload) != len(self.supported_tools):
            raise ValueError(
                "Generated tool specs must match the supported set exactly: "
                + ", ".join(self.supported_tools)
            )

        for filename, content in payload.items():
            if filename not in self.supported_tools:
                raise ValueError(
                    f"Unsupported tool spec filename '{filename}'. "
                    f"Supported files: {', '.join(self.supported_tools)}"
                )
            for required_section in (
                "## Mission",
                "## Use This Tool For",
                "## Decision Rules",
                "## Avoid",
            ):
                if required_section not in content:
                    raise ValueError(
                        f"Tool spec file {filename} is missing '{required_section}'"
                    )
            if len(content.strip()) < 200:
                raise ValueError(f"Tool spec file {filename} is unexpectedly short")

        missing_outputs = sorted(set(self.supported_tools) - set(payload))
        if missing_outputs:
            raise ValueError(
                "Generated tool specs are missing required files: "
                + ", ".join(missing_outputs)
            )

    def _write_tool_specs(self, payload: Dict[str, str], output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        for existing_file in output_dir.glob("*.md"):
            if existing_file.name not in payload:
                existing_file.unlink()
                print(f"Info: Removed stale tool spec file {existing_file}")
        for filename, content in payload.items():
            output_path = output_dir / filename
            output_path.write_text(content.strip() + "\n", encoding="utf-8")
            print(f"Info: Wrote {output_path}")


async def _async_run(
    config: Config,
    bio_path: Optional[Path],
    seed_dir: Optional[Path],
    output_dir: Optional[Path],
) -> int:
    creator = ToolSpecsCreator(config)
    try:
        result_dir = await creator.generate_tool_specs(
            bio_path=bio_path, seed_dir=seed_dir, output_dir=output_dir
        )
        print(f"Info: Tool specs generated in {result_dir}")
        return 0
    finally:
        await close_client_async(creator.handle)


def run(
    config: Config,
    *,
    bio_path: Optional[Path] = None,
    seed_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> int:
    """Synchronous entry point for CLI use."""
    if not config.profile.has_tool_specs:
        print(f"Error: profile '{config.profile.name}' does not enable tool specs")
        return 1

    issues = config.validate_llm_access()
    if issues:
        print("Error: Configuration issues found")
        for issue in issues:
            print(f"- {issue}")
        return 1

    try:
        return asyncio.run(_async_run(config, bio_path, seed_dir, output_dir))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


__all__ = ["ToolSpecsCreator", "run"]
