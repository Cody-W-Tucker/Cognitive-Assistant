#!/usr/bin/env python3
"""Generate personalized tool specs from the latest profile."""

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Dict, Optional

from config import config
from llm import LLMHandle, create_client, generate_text_async


SUPPORTED_TOOL_SPECS: dict[str, str] = {
    "memory.md": "Memory agent for durable continuity and retrieval.",
    "tasks.md": "Task agent for capturing, shaping, and retrieving commitments.",
}


class ToolSpecsCreator:
    """Generate personalized single-tool agent specs from an operational profile."""

    def __init__(self) -> None:
        self.handle: LLMHandle = create_client(
            config.api,
            model=config.api.get_model("refine"),
            async_mode=True,
        )

    async def generate_tool_specs(
        self,
        bio_path: Optional[Path] = None,
        seed_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Generate tool spec files from the selected profile and generic tool docs."""
        resolved_bio_path = self._resolve_bio_path(bio_path)
        bio_content = resolved_bio_path.read_text(encoding="utf-8")
        seed_documents = self._load_seed_documents(seed_dir)
        tool_specs_payload = await self._generate_tool_spec_documents(
            bio_content,
            seed_documents,
        )
        resolved_output_dir = output_dir or config.paths.TOOL_SPECS_DIR
        self._write_tool_specs(tool_specs_payload, resolved_output_dir)
        return resolved_output_dir

    def _resolve_bio_path(self, bio_path: Optional[Path]) -> Path:
        if bio_path is not None:
            resolved_path = Path(bio_path)
            if not resolved_path.exists():
                raise FileNotFoundError(f"Bio file not found: {resolved_path}")
            return resolved_path

        bio_files = sorted(config.paths.ARTIFACTS_DIR.glob("system_prompt*.md"))
        if not bio_files:
            raise FileNotFoundError(
                "No human_profile*.md files found in artifacts/. Run prompt_creator.py first or pass --bio."
            )
        return bio_files[-1]

    def _load_seed_documents(self, seed_dir: Optional[Path]) -> Dict[str, str]:
        resolved_seed_dir = (
            Path(seed_dir) if seed_dir is not None else config.paths.PROMPT_RUNTIME_DIR
        )
        if not resolved_seed_dir.exists():
            raise FileNotFoundError(f"Seed directory not found: {resolved_seed_dir}")

        seed_documents: Dict[str, str] = {}
        missing_files: list[str] = []
        for filename in SUPPORTED_TOOL_SPECS:
            seed_path = resolved_seed_dir / filename
            if not seed_path.exists():
                missing_files.append(filename)
                continue
            seed_documents[filename] = seed_path.read_text(encoding="utf-8")

        if missing_files:
            missing_list = ", ".join(missing_files)
            raise FileNotFoundError(
                f"Supported tool exemplar files not found in {resolved_seed_dir}: {missing_list}"
            )

        return seed_documents

    async def _generate_tool_spec_documents(
        self,
        bio_content: str,
        seed_documents: Dict[str, str],
    ) -> Dict[str, str]:
        prompt = config.prompts.tool_specs_creation_template.format(
            bio_content=bio_content,
            supported_tools=self._render_supported_tools(),
            seed_documents=self._render_seed_documents(seed_documents),
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

    def _render_seed_documents(self, seed_documents: Dict[str, str]) -> str:
        rendered_documents = []
        for filename, content in seed_documents.items():
            rendered_documents.append(
                f'<seed_document name="{filename}">\n{content.strip()}\n</seed_document>'
            )
        return "\n\n".join(rendered_documents)

    def _render_supported_tools(self) -> str:
        rendered_tools = []
        for filename, description in SUPPORTED_TOOL_SPECS.items():
            rendered_tools.append(f"- `{filename}`: {description}")
        return "\n".join(rendered_tools)

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

        if len(payload) != len(SUPPORTED_TOOL_SPECS):
            raise ValueError(
                "Generated tool specs must match the supported set exactly: "
                + ", ".join(SUPPORTED_TOOL_SPECS)
            )

        for filename, content in payload.items():
            if filename not in SUPPORTED_TOOL_SPECS:
                raise ValueError(
                    f"Unsupported tool spec filename '{filename}'. Supported files: {', '.join(SUPPORTED_TOOL_SPECS)}"
                )
            if "## Mission" not in content:
                raise ValueError(f"Tool spec file {filename} is missing '## Mission'")
            if "## Use This Tool For" not in content:
                raise ValueError(
                    f"Tool spec file {filename} is missing '## Use This Tool For'"
                )
            if "## Decision Rules" not in content:
                raise ValueError(
                    f"Tool spec file {filename} is missing '## Decision Rules'"
                )
            if "## Avoid" not in content:
                raise ValueError(f"Tool spec file {filename} is missing '## Avoid'")
            if len(content.strip()) < 200:
                raise ValueError(f"Tool spec file {filename} is unexpectedly short")

        missing_outputs = sorted(set(SUPPORTED_TOOL_SPECS) - set(payload))
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


def create_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line interface parser."""
    parser = argparse.ArgumentParser(
        description="Generate personalized tool specs from human_profile.md",
    )
    parser.add_argument(
        "--bio", type=Path, help="Path to a specific human_profile.md file"
    )
    parser.add_argument(
        "--seed-dir",
        type=Path,
        help="Directory containing seed markdown docs such as prompts/runtime/*.md",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Directory where generated tool spec files should be written",
    )
    return parser


async def _async_main(args: argparse.Namespace) -> int:
    creator = ToolSpecsCreator()
    result_dir = await creator.generate_tool_specs(
        bio_path=args.bio,
        seed_dir=args.seed_dir,
        output_dir=args.output,
    )
    print(f"Info: Tool specs generated in {result_dir}")
    return 0


def main() -> int:
    """CLI entrypoint for personalized tool spec generation."""
    issues = config.validate_llm_access()
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
