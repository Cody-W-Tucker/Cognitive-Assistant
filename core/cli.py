#!/usr/bin/env python3
"""Unified CLI entry point: `python -m core <command> --profile <name>`.

Subcommands:
  ingest-interview   Interactive human interview (existential-style profiles)
  ingest-corpus      Normalize raw exports into ready/*.jsonl (operational)
  ask-questions      Run RLM against questions.csv -> answers CSV
  build-prompts      2-call refinement -> human_profile.md + system_prompt.md
  build-skills       Generate skills/ from latest human_profile.md
  build-tool-specs   Generate tool_specs/ from latest system_prompt.md (gated)
  health-check       Validate prompts, paths, provider access, RLM availability

Common flags:
  --profile <name>   Required. One of the registered profiles.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from core.config import Config, list_profiles


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m core",
        description="Unified pipeline for layer profiles.",
    )
    parser.add_argument(
        "--profile",
        required=False,
        help="Layer profile to operate on. Available: " + ", ".join(list_profiles()),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "ingest-interview",
        help="Run the interactive human interview (existential profiles).",
    ).add_argument("--resume", action="store_true", help="Resume the most recent session")

    parser_interview = subparsers.choices["ingest-interview"]
    parser_interview.add_argument(
        "--output", help="Custom output filename (within the profile data dir)"
    )
    parser_interview.add_argument(
        "--questions-file",
        type=Path,
        help="Path to a custom questions CSV (default: profile questions.csv)",
    )

    subparsers.add_parser(
        "ingest-corpus",
        help="Normalize intake exports into ready/*.jsonl (operational profiles).",
    )

    ask_parser = subparsers.add_parser(
        "ask-questions",
        help="Run RLM against the profile's questions.csv.",
    )
    ask_parser.add_argument(
        "--filesystem-only",
        action="store_true",
        help="Use filesystem-only RLM prompt (existential profiles).",
    )

    subparsers.add_parser(
        "build-prompts",
        help="2-call refinement: human_profile.md + system_prompt.md.",
    )

    skills_parser = subparsers.add_parser(
        "build-skills",
        help="Generate skills/ from the latest human_profile.md.",
    )
    skills_parser.add_argument("--bio", type=Path, help="Path to a specific human_profile.md")
    skills_parser.add_argument(
        "--output",
        type=Path,
        dest="output_dir",
        help="Output directory for skill folders",
    )

    tool_parser = subparsers.add_parser(
        "build-tool-specs",
        help="Generate tool_specs/ from the latest system_prompt.md (gated).",
    )
    tool_parser.add_argument("--bio", type=Path, help="Path to a specific system_prompt.md")
    tool_parser.add_argument(
        "--seed-dir",
        type=Path,
        help="Directory containing seed exemplar tool docs (default: profile prompts/runtime)",
    )
    tool_parser.add_argument(
        "--output",
        type=Path,
        dest="output_dir",
        help="Output directory for tool spec files",
    )

    subparsers.add_parser(
        "health-check",
        help="Validate prompts, paths, provider access, RLM availability.",
    )

    subparsers.add_parser(
        "list-profiles",
        help="Print the registered profile names.",
    )

    return parser


def _resolve_config(args: argparse.Namespace) -> Config:
    if not args.profile:
        raise SystemExit(
            "Error: --profile is required. Available: "
            + ", ".join(list_profiles())
        )
    return Config.from_profile(args.profile)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "list-profiles":
        for name in list_profiles():
            print(name)
        return 0

    config = _resolve_config(args)

    if args.command == "ingest-interview":
        from core import ingest_interview

        return ingest_interview.run(
            config,
            resume=args.resume,
            output=args.output,
            questions_file=args.questions_file,
        )

    if args.command == "ingest-corpus":
        from core import ingest_corpus

        return ingest_corpus.run(config)

    if args.command == "ask-questions":
        from core import question_asker

        return question_asker.run(config, filesystem_only=args.filesystem_only)

    if args.command == "build-prompts":
        from core import prompt_creator

        return prompt_creator.run(config)

    if args.command == "build-skills":
        from core import skills_creator

        return skills_creator.run(
            config, bio_path=args.bio, output_dir=args.output_dir
        )

    if args.command == "build-tool-specs":
        from core import tool_specs_creator

        return tool_specs_creator.run(
            config,
            bio_path=args.bio,
            seed_dir=args.seed_dir,
            output_dir=args.output_dir,
        )

    if args.command == "health-check":
        from core import health_check

        return health_check.run(config)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
