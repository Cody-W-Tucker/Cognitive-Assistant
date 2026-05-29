#!/usr/bin/env python3
"""Unified CLI entry point: `python -m core <command> --profile <name>`.

Subcommands:
  ingest-corpus      Normalize intake exports into ready/*.jsonl (operational)
  ingest-substrate   Project schema graph/focus exports into ready/*.jsonl packets
  ask-questions      Run RLM against questions.csv -> answers CSV
  build-prompts      Generate profile artifacts declared by the active profile
  build-skills       Generate skills/ from latest human_profile.md
  build-tool-specs   Generate tool_specs/ from latest human_profile.md (gated)
  build-soul         Generate SOUL.md from existential and operational profile artifacts
  update             Run build-prompts, build-skills, and build-tool-specs
  health-check       Validate prompts, paths, provider access, RLM availability

Common flags:
  --profile <name>   Required for most commands. Optional for 'update' (all profiles).
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
        "ingest-corpus",
        help="Normalize intake exports into ready/*.jsonl (operational profiles).",
    )

    substrate_parser = subparsers.add_parser(
        "ingest-substrate",
        help="Project schema graph/focus exports into ready/*.jsonl packets.",
    )
    substrate_parser.add_argument(
        "--graph",
        type=Path,
        help="Path to a schema graph.json export.",
    )
    substrate_parser.add_argument(
        "--focus",
        type=Path,
        action="append",
        default=[],
        help="Path to a schema focus-bundle.json export. Repeat for multiple bundles.",
    )
    substrate_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for JSONL packets (default: workspaces/<profile>/data/ready/substrate)",
    )

    ask_parser = subparsers.add_parser(
        "ask-questions",
        help="Run RLM against the profile's questions.csv.",
    )
    subparsers.add_parser(
        "build-prompts",
        help="Generate profile artifacts for the active profile.",
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
        help="Generate tool_specs/ from the latest human_profile.md (gated).",
    )
    tool_parser.add_argument("--bio", type=Path, help="Path to a specific human_profile.md")
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

    update_parser = subparsers.add_parser(
        "update",
        help="Chain build-prompts, build-skills, and build-tool-specs for one or all profiles.",
    )
    update_parser.add_argument(
        "--skip-tool-specs",
        action="store_true",
        help="Skip tool-specs generation even if profile supports it.",
    )

    subparsers.add_parser(
        "health-check",
        help="Validate prompts, paths, provider access, RLM availability.",
    )

    subparsers.add_parser(
        "list-profiles",
        help="Print the registered profile names.",
    )

    alignment_parser = subparsers.add_parser(
        "build-alignment-spec",
        help="Generate alignment verification spec from both profile layers.",
    )
    alignment_parser.add_argument(
        "--output",
        type=Path,
        dest="output_path",
        help="Output path for the alignment spec (default: workspaces/alignment/artifacts/alignment_spec.md)",
    )

    soul_parser = subparsers.add_parser(
        "build-soul",
        help="Generate SOUL.md from the existential and operational human profiles.",
    )
    soul_parser.add_argument(
        "--output",
        type=Path,
        dest="output_path",
        help="Output path for SOUL.md (default: workspaces/alignment/artifacts/SOUL.md)",
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

    if args.command == "build-alignment-spec":
        from core import alignment_spec

        return alignment_spec.run(output_path=args.output_path)

    if args.command == "build-soul":
        from core import soul_creator

        return soul_creator.run(output_path=args.output_path)

    # update command handles profile resolution internally (supports "all profiles" mode)
    if args.command == "update":
        config = None  # type: ignore[assignment]
    else:
        config = _resolve_config(args)

    if args.command == "ingest-corpus":
        from core import ingest_corpus

        return ingest_corpus.run(config)

    if args.command == "ingest-substrate":
        from core import ingest_substrate

        return ingest_substrate.run(
            config,
            graph_path=args.graph,
            focus_paths=args.focus,
            output_dir=args.output_dir,
        )

    if args.command == "ask-questions":
        from core import question_asker

        return question_asker.run(config)

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

    if args.command == "update":
        from core import prompt_creator, skills_creator, tool_specs_creator

        def _update_single_profile(cfg: Config, skip_tool_specs: bool) -> int:
            print(f"\n{'=' * 50}")
            print(f"Updating profile: {cfg.profile.name}")
            print(f"{'=' * 50}")

            print("\n>>> Running build-prompts...")
            exit_code = prompt_creator.run(cfg)
            if exit_code != 0:
                print(f"Error: build-prompts failed for profile '{cfg.profile.name}'")
                return exit_code

            print("\n>>> Running build-skills...")
            exit_code = skills_creator.run(cfg, bio_path=None, output_dir=None)
            if exit_code != 0:
                print(f"Error: build-skills failed for profile '{cfg.profile.name}'")
                return exit_code

            if not skip_tool_specs and cfg.profile.has_tool_specs:
                print("\n>>> Running build-tool-specs...")
                exit_code = tool_specs_creator.run(
                    cfg, bio_path=None, seed_dir=None, output_dir=None
                )
                if exit_code != 0:
                    print(f"Error: build-tool-specs failed for profile '{cfg.profile.name}'")
                    return exit_code
            elif not skip_tool_specs:
                print("\n>>> Skipping build-tool-specs (not enabled for this profile)")

            return 0

        if args.profile:
            # Update single profile
            cfg = Config.from_profile(args.profile)
            exit_code = _update_single_profile(cfg, args.skip_tool_specs)
            if exit_code != 0:
                return exit_code
        else:
            # Update all profiles
            profiles = list_profiles()
            print(f"Updating all {len(profiles)} profiles: {', '.join(profiles)}")
            for profile_name in profiles:
                cfg = Config.from_profile(profile_name)
                exit_code = _update_single_profile(cfg, args.skip_tool_specs)
                if exit_code != 0:
                    print(f"\nError: Update failed for profile '{profile_name}'")
                    return exit_code

        print(f"\n{'=' * 50}")
        print("Update complete for all requested profiles")
        print(f"{'=' * 50}")
        return 0

    if args.command == "health-check":
        from core import health_check

        return health_check.run(config)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
