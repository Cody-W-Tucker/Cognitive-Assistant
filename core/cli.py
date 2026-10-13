#!/usr/bin/env python3
"""Unified CLI entry point: `python -m core <command> --profile <name>`.

Subcommands:
  ingest-corpus      Normalize intake exports into ready/*.jsonl (operational)
  ask-questions      Answer questions.csv with QMD retrieval and direct LLM synthesis
  build-prompts      Generate profile artifacts declared by the active profile
  build-skills       Generate canonical skills from latest human_profile.md
  enhance-skill      Enhance a skill from source material
  build-tool-specs   Generate tool_specs/ from latest human_profile.md (gated)
  build-translation-layer  Generate INTERACTION_POSTURE.md and SOUL.md from both profiles
  build-alignment-spec  Generate alignment verification spec from unified skills
  update             Run build-prompts, build-skills, build-translation-layer, build-alignment-spec, and build-tool-specs
  health-check       Validate prompts, paths, provider access, and QMD availability
   improve-run        Improvement pass: manual TTY route by default, --headless for JSON proposal into XDG state (never writes repo/Hermes)
   improve-apply      Review gate: apply a proposal (sole writer of experience records)
   improve-synthesize   Resume-only synthesis over persisted evidence/ledger (never discovers/analyzes)

Common flags:
  --profile <name>   Required for most commands. Optional for 'update' (all profiles).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from core.config import Config, list_profiles


def _decisions_hint(proposal: dict) -> str:
    """Build the improve-apply next-step hint from actual proposal edit ids.

    Never hardcodes a run-local label: with edits, names each actual edit
    id; with none, uses a neutral placeholder.
    """
    edits = proposal.get("edits", []) or []
    ids = [str(edit.get("id", "?")) for edit in edits if isinstance(edit, dict)]
    if not ids:
        return "next: nothing to review (no candidate edits); re-run, then review with `improve-apply --decisions \"<edit>=accepted ...\"`"
    vector = " ".join(f"{edit_id}=accepted" for edit_id in ids)
    return f"next: review with `improve-apply --decisions \"{vector}\"`"


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

    subparsers.add_parser(
        "ask-questions",
        help="Answer the profile's questions.csv with QMD retrieval.",
    )
    subparsers.add_parser(
        "build-prompts",
        help="Generate profile artifacts for the active profile.",
    )

    skills_parser = subparsers.add_parser(
        "build-skills",
        help="Generate canonical skills from the latest human_profile.md.",
    )
    skills_parser.add_argument("--bio", type=Path, help="Path to a specific human_profile.md")
    skills_parser.add_argument(
        "--output",
        type=Path,
        dest="output_dir",
        help="Output directory for profile-grouped skill folders (default: unified workspaces/skills)",
    )

    skill_enhancer_parser = subparsers.add_parser(
        "enhance-skill",
        help="Enhance a skill from source material.",
    )
    skill_enhancer_parser.add_argument("--skill", help="Skill name to enhance (default: all workspace skills).")
    skill_enhancer_parser.add_argument(
        "--hermes-path",
        type=Path,
        help="Path to Hermes source material.",
    )
    skill_enhancer_parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the LLM-backed enhancement after previewing the diff.",
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
        help="Run build-prompts, build-skills, build-translation-layer, build-alignment-spec, and build-tool-specs for one or all profiles.",
    )
    update_parser.add_argument(
        "--skip-tool-specs",
        action="store_true",
        help="Skip tool-specs generation even if profile supports it.",
    )

    subparsers.add_parser(
        "health-check",
        help="Validate prompts, paths, provider access, and QMD availability.",
    )

    subparsers.add_parser(
        "list-profiles",
        help="Print the registered profile names.",
    )

    alignment_parser = subparsers.add_parser(
        "build-alignment-spec",
        help="Generate alignment verification spec from unified skills.",
    )
    alignment_parser.add_argument(
        "--output",
        type=Path,
        dest="output_path",
        help="Output path for the alignment spec (default: workspaces/alignment/artifacts/alignment_spec.md)",
    )

    subparsers.add_parser(
        "build-translation-layer",
        help="Generate INTERACTION_POSTURE.md and SOUL.md from both profile layers.",
    )
    review_parser = subparsers.add_parser(
        "review-queue",
        help="Refill the Langfuse CA routing review queue.",
    )
    review_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report candidates without creating queue items.",
    )

    improve_run_parser = subparsers.add_parser(
        "improve-run",
        help="Run the CA improvement pass (manual TTY route by default, --headless for JSON).",
    )
    improve_run_parser.add_argument(
        "--headless",
        action="store_true",
        required=False,
        help="Headless run: emit exactly one JSON proposal object on stdout (never touches tracked files or live Hermes).",
    )
    improve_run_parser.add_argument(
        "--state-dir",
        type=Path,
        help="Private state dir (default: $XDG_DATA_HOME/cognitive-assistant/improve).",
    )
    improve_run_parser.add_argument(
        "--since",
        default="30d",
        help="Only sessions newer than this (30d, 12h, 2w, all).",
    )
    improve_run_parser.add_argument(
        "--analyzer",
        default="acpx",
        help="Analyzer backend: acpx (default, model calls via acpx only) or mock (no model calls).",
    )
    improve_run_parser.add_argument(
        "--min-gap-evidence",
        type=int,
        default=2,
        help="Sessions of shared gap evidence needed before a candidate is proposed.",
    )
    improve_run_parser.add_argument(
        "--soul-path",
        type=Path,
        help="Read-only SOUL baseline for synthesis context (default: workspaces/alignment/artifacts/SOUL.md).",
    )

    improve_apply_parser = subparsers.add_parser(
        "improve-apply",
        help="Review gate: apply the headless proposal (sole writer of experience records).",
    )
    improve_apply_parser.add_argument(
        "--decisions",
        action="append",
        default=None,
        help='Decisions vector, e.g. --decisions "e1=accepted e2=rejected:too-narrow". Repeatable.',
    )
    improve_apply_parser.add_argument(
        "--state-dir",
        type=Path,
        help="Private state dir holding the proposal (default: XDG).",
    )
    improve_apply_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be written; write nothing.",
    )

    improve_synth_parser = subparsers.add_parser(
        "improve-synthesize",
        help="Resume-only synthesis over persisted evidence/ledger (never discovers or analyzes).",
    )
    improve_synth_parser.add_argument(
        "--state-dir",
        type=Path,
        help="Private state dir holding evidence/ledger (default: $XDG_DATA_HOME/cognitive-assistant/improve).",
    )
    improve_synth_parser.add_argument(
        "--min-gap-evidence",
        type=int,
        default=2,
        help="Sessions of shared gap evidence needed before a candidate is proposed.",
    )
    improve_synth_parser.add_argument(
        "--soul-path",
        type=Path,
        help="Read-only SOUL baseline for synthesis context (default: workspaces/alignment/artifacts/SOUL.md).",
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

    if args.command == "enhance-skill":
        from core import skill_enhancer

        return skill_enhancer.run(
            skill_name=args.skill,
            hermes_path=Path(args.hermes_path).expanduser() if args.hermes_path else None,
            apply=args.apply,
        )

    if args.command == "build-translation-layer":
        from core import translation_layer_creator

        return translation_layer_creator.run()

    if args.command == "review-queue":
        from core import langfuse_review

        return langfuse_review.run(dry_run=args.dry_run)

    if args.command == "improve-run":
        import json
        import os

        from core import improve as improve_runtime

        home = Path(os.environ.get("CA_IMPROVE_HOME", Path.home().expanduser()))
        if args.headless:
            proposal = improve_runtime.run_headless(
                home=home,
                cwd=Path.cwd(),
                state_dir=args.state_dir,
                since=args.since,
                analyzer=args.analyzer,
                soul_path=args.soul_path,
                min_gap_evidence=args.min_gap_evidence,
            )
            print(json.dumps(proposal))
            print(
                f"proposal {proposal.get('id', '?')}: "
                f"{len(proposal.get('edits', []))} candidate edit(s), "
                f"{proposal.get('stats', {}).get('transcripts', 0)} transcript(s) discovered",
                file=sys.stderr,
            )
            print(
                "state: "
                + str(args.state_dir or improve_runtime.default_state_dir()),
                file=sys.stderr,
            )
            print(_decisions_hint(proposal), file=sys.stderr)
            return 0
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            print(
                "improve-run: manual route requires a TTY; "
                "automation should use `improve-run --headless`",
                file=sys.stderr,
            )
            return 2
        proposal = improve_runtime.run_tui(
            home=home,
            cwd=Path.cwd(),
            state_dir=args.state_dir,
            since=args.since,
            analyzer=args.analyzer,
            soul_path=args.soul_path,
            min_gap_evidence=args.min_gap_evidence,
        )
        print(
            f"proposal {proposal.get('id', '?')}: "
            f"{len(proposal.get('edits', []))} candidate edit(s), "
            f"{proposal.get('stats', {}).get('transcripts', 0)} transcript(s) discovered"
        )
        print("state: " + str(args.state_dir or improve_runtime.default_state_dir()))
        print(_decisions_hint(proposal))
        return 0

    if args.command == "improve-apply":
        from core import improve as improve_runtime

        state = args.state_dir or improve_runtime.default_state_dir()
        decisions: dict[str, str] | None = None
        if args.decisions:
            edit_ids = [
                edit["id"]
                for edit in improve_runtime.read_proposal(state).get("edits", [])
            ]
            parsed, reasons = improve_runtime.parse_decisions(args.decisions, edit_ids)
            decisions = {
                edit_id: f"{verdict}:{reasons[edit_id]}"
                if edit_id in reasons
                else verdict
                for edit_id, verdict in parsed.items()
            }
        result = improve_runtime.apply(
            state_dir=args.state_dir,
            decisions=decisions,
            dry_run=args.dry_run,
        )
        prefix = "[dry-run] " if args.dry_run else ""
        print(
            f"{prefix}{len(result['accepted'])} accepted - "
            f"{len(result['rejected'])} rejected"
        )
        for written in result["written"]:
            print(f"  wrote {written}")
        if not result["written"]:
            print("  nothing written")
        return 0

    if args.command == "improve-synthesize":
        import json

        from core import improve as improve_runtime

        proposal = improve_runtime.synthesize_resume(
            state_dir=args.state_dir,
            min_gap_evidence=args.min_gap_evidence,
            soul_path=args.soul_path,
        )
        print(json.dumps(proposal))
        print(
            f"proposal {proposal.get('id', '?')}: "
            f"{len(proposal.get('edits', []))} candidate edit(s), "
            f"{proposal.get('stats', {}).get('transcripts', 0)} transcript(s) resumed",
            file=sys.stderr,
        )
        print(
            "state: "
            + str(args.state_dir or improve_runtime.default_state_dir()),
            file=sys.stderr,
        )
        print(_decisions_hint(proposal), file=sys.stderr)
        return 0

    # update command handles profile resolution internally (supports "all profiles" mode)
    if args.command == "update":
        config = None  # type: ignore[assignment]
    else:
        config = _resolve_config(args)

    if args.command == "ingest-corpus":
        from core import ingest_corpus

        return ingest_corpus.run(config)

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
        from core import (
            alignment_spec,
            prompt_creator,
            skills_creator,
            tool_specs_creator,
            translation_layer_creator,
        )

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
                    print(f"\nError: Update failed for profile '{cfg.profile.name}'")
                    return exit_code

        # Cross-profile stages: translation layer, then alignment spec
        print(f"\n{'=' * 50}")
        print("Running cross-profile stages")
        print(f"{'=' * 50}")

        print("\n>>> Running build-translation-layer...")
        exit_code = translation_layer_creator.run()
        if exit_code != 0:
            print("Error: build-translation-layer failed")
            return exit_code

        print("\n>>> Running build-alignment-spec...")
        exit_code = alignment_spec.run()
        if exit_code != 0:
            print("Error: build-alignment-spec failed")
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
