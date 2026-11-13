#!/usr/bin/env python3
"""CLI entry point: ``python -m core [--profile <name>] <command>``; ``--help`` lists the commands.

Runtime state lives under CA home ($CA_HOME, default $XDG_DATA_HOME/cognitive-assistant).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Awaitable, Callable, List, Sequence

from core.config import LayerProfile, get_profile, list_profiles


def _refuse(name: str, issues: List[str]) -> bool:
    """Print missing configuration; True when there was any."""
    if issues:
        print(f"Error: {name}: configuration issues found")
        for issue in issues:
            print(f"- {issue}")
    return bool(issues)


def _run_stage(name: str, issues: List[str], work: Callable[[], Awaitable[object]]) -> int:
    """Run one pipeline stage: refuse on missing configuration, report a failure as exit 1."""
    if _refuse(name, issues):
        return 1
    try:
        asyncio.run(work())
    except Exception as exc:
        print(f"Error: {name}: {exc}", file=sys.stderr)
        return 1
    return 0


def _profile_stage(command: str, profile: LayerProfile, args: argparse.Namespace) -> int:
    from core import ingest_corpus, prompt_creator, question_asker, skills_creator, tool_specs_creator

    stages = {
        "ingest-corpus": (ingest_corpus, {}),
        "ask-questions": (question_asker, {}),
        "build-prompts": (prompt_creator, {}),
        "build-skills": (skills_creator, {"bio_path": getattr(args, "bio", None)}),
        "build-tool-specs": (tool_specs_creator, {"bio_path": getattr(args, "bio", None)}),
    }
    module, options = stages[command]
    print(f"\n>>> {command} ({profile.name})")
    return _run_stage(command, module.requirements(profile), lambda: module.build(profile, **options))


def _update(args: argparse.Namespace) -> int:
    """Every per-profile build stage, then the cross-profile stages."""
    from core import alignment_spec, translation_layer_creator

    profiles = [get_profile(args.profile)] if args.profile else [get_profile(name) for name in list_profiles()]
    for profile in profiles:
        commands = ["build-prompts", "build-skills"]
        if profile.supported_tools and not args.skip_tool_specs:
            commands.append("build-tool-specs")
        for command in commands:
            code = _profile_stage(command, profile, args)
            if code:
                return code
    print("\n>>> build-translation-layer")
    code = _run_stage("build-translation-layer", translation_layer_creator.requirements(), translation_layer_creator.build)
    if code:
        return code
    print("\n>>> build-alignment-spec")
    return _run_stage("build-alignment-spec", alignment_spec.requirements(), alignment_spec.build)


def _print_proposal_summary(proposal: dict, *, file=sys.stdout) -> None:
    """One line on what the run proposed, then how to review it."""
    from core.paths import improve_dir

    edits = [edit for edit in proposal.get("edits", []) if isinstance(edit, dict)]
    print(
        f"proposal {proposal.get('id', '?')}: {len(edits)} candidate edit(s), "
        f"{proposal.get('stats', {}).get('transcripts', 0)} transcript(s)",
        file=file,
    )
    print(f"state: {improve_dir()}", file=file)
    if not edits:
        print("next: nothing to review (no candidate edits)", file=file)
        return
    vector = " ".join(f"{edit.get('id', '?')}=accepted" for edit in edits)
    print(f"next: review with `improve-apply --proposal {proposal.get('id', '?')} --decisions \"{vector}\"`", file=file)


def _improve_run(args: argparse.Namespace) -> int:
    import os

    from core import improve

    if args.auto and not args.headless:
        print("improve-run: --auto requires --headless", file=sys.stderr)
        return 2
    if not args.headless and not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("improve-run: manual route requires a TTY; automation should use `improve-run --headless`", file=sys.stderr)
        return 2
    home = os.environ.get("CA_IMPROVE_HOME")
    proposal = improve.run(
        tui=not args.headless,
        home=Path(home).expanduser() if home else None,
        since=args.since,
        analyzer=args.analyzer,
        min_gap_evidence=args.min_gap_evidence,
        harnesses=args.harness,
    )
    if not args.headless:
        _print_proposal_summary(proposal)
        return 0
    print(json.dumps(proposal))
    if not args.auto:
        _print_proposal_summary(proposal, file=sys.stderr)
        return 0
    cycle = improve.auto_cycle(proposal=proposal, min_sessions=args.min_sessions)
    verdict = cycle["verdict"]
    generation = f" -> generation {cycle['generation']}" if cycle["generation"] else ""
    print(
        f"auto: verdict {verdict.get('verdict')} ({verdict.get('reason', 'tested')}); action {cycle['action']}{generation}",
        file=sys.stderr,
    )
    return 0


def _improve_apply(args: argparse.Namespace) -> int:
    from core import improve

    decisions = reasons = None
    if args.decisions:
        on_disk = improve.read_proposal()
        if not args.proposal:
            print(
                "improve-apply: --decisions must name the proposal they review;"
                f" pass --proposal {on_disk.get('id', '?')} after reading it",
                file=sys.stderr,
            )
            return 2
        decisions, reasons = improve.parse_decisions(args.decisions)
    result = improve.apply(
        decisions=decisions,
        reasons=reasons,
        dry_run=args.dry_run,
        expected_proposal_id=args.proposal,
    )
    prefix = "[dry-run] " if args.dry_run else ""
    print(f"{prefix}{len(result['accepted'])} accepted - {len(result['rejected'])} rejected")
    for written in result["written"]:
        print(f"  wrote {written}")
    if not result["written"]:
        print("  nothing written")
    generation = result["generation"]
    if generation:
        print(f"  living SOUL generation {generation['generation']} ({len(generation['records'])} learned record(s))")
    return 0


def _soul(args: argparse.Namespace) -> int:
    from core import living_soul, outcome
    from core import paths

    if args.soul_command == "compile":
        if args.prefix_file is not None or args.suffix_file is not None:
            living_soul.write_compose_config(args.prefix_file, args.suffix_file)
        meta = living_soul.compile_soul(reason=args.reason)
        state = "new" if meta["changed"] else "unchanged"
        print(f"generation {meta['generation']} ({state}): {len(meta['records'])} learned record(s)")
        print(f"current: {living_soul.current_path()}")
    elif args.soul_command == "status":
        current = living_soul.current_generation()
        judged = outcome.verdicts()
        print(f"bootstrap: {paths.BOOTSTRAP_SOUL_PATH}")
        print(f"current: {current['generation'] if current else 'none'}")
        for meta in living_soul.list_generations():
            marker = "*" if current and meta["generation"] == current["generation"] else " "
            verdict = judged.get(meta["generation"], {}).get("verdict", "untested")
            print(
                f" {marker} {meta['generation']:>4}  {meta['createdAt']}  "
                f"{len(meta['records'])} record(s)  {verdict:<8}  {meta['reason']}"
            )
    elif args.soul_command == "rollback":
        meta = living_soul.rollback(args.generation)
        print(f"current -> generation {meta['generation']}")
    elif args.soul_command == "link":
        link = living_soul.link_into(args.hermes_home)
        print(f"{link} -> {living_soul.current_path()}")
    return 0


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

    update_parser = subparsers.add_parser(
        "update",
        help="Run build-prompts, build-skills and build-tool-specs for one or all profiles, then build-translation-layer and build-alignment-spec.",
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

    subparsers.add_parser(
        "build-alignment-spec",
        help="Generate alignment verification spec from unified skills.",
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
        "--since",
        default="30d",
        help="Only sessions newer than this (30d, 12h, 2w, all).",
    )
    improve_run_parser.add_argument(
        "--analyzer",
        default="model",
        help="Analyzer backend: model (default, tool-free chat completions via CA_LLM_BASE_URL) or mock (no model calls).",
    )
    improve_run_parser.add_argument(
        "--min-gap-evidence",
        type=int,
        default=2,
        help="Sessions of shared gap evidence needed before a candidate is proposed.",
    )
    improve_run_parser.add_argument(
        "--auto",
        action="store_true",
        help="With --headless: judge the change under test, revert it if sessions got worse, else adopt one kept record.",
    )
    improve_run_parser.add_argument(
        "--min-sessions",
        type=int,
        default=15,
        help="--auto: sessions needed on each side before judging a change (default 15).",
    )
    improve_run_parser.add_argument(
        "--harness",
        action="append",
        default=None,
        help="Only scan this harness (repeatable). A named harness whose store is missing fails the run.",
    )

    improve_apply_parser = subparsers.add_parser(
        "improve-apply",
        help="Review the current proposal: write accepted records and rebuild the living SOUL.",
    )
    improve_apply_parser.add_argument(
        "--decisions",
        action="append",
        default=None,
        help='Decisions vector, e.g. --decisions "e1=accepted e2=rejected:too-narrow". Repeatable.',
    )
    improve_apply_parser.add_argument(
        "--proposal",
        help="Id of the proposal these decisions review (required with --decisions).",
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
        "--min-gap-evidence",
        type=int,
        default=2,
        help="Sessions of shared gap evidence needed before a candidate is proposed.",
    )

    subparsers.add_parser(
        "journal-compact",
        help="Regenerate journal views (current.json/bootstrap.md) from events.jsonl; tolerates missing/malformed lines.",
    )

    soul_parser = subparsers.add_parser(
        "soul",
        help="Living SOUL in the CA state dir: bootstrap SOUL + accepted lineage, by generation.",
    )
    soul_sub = soul_parser.add_subparsers(dest="soul_command", required=True)
    soul_compile = soul_sub.add_parser("compile", help="Rebuild from bootstrap + lineage; new generation only on change.")
    soul_compile.add_argument("--prefix-file", help="Deployer text placed before the SOUL (persisted for later compiles).")
    soul_compile.add_argument("--suffix-file", help="Deployer text placed after the SOUL (persisted for later compiles).")
    soul_compile.add_argument("--reason", default="compile", help="Short reason recorded with the generation.")
    soul_sub.add_parser("status", help="Show the active generation and history.")
    soul_rollback = soul_sub.add_parser("rollback", help="Point current.md at an earlier generation.")
    soul_rollback.add_argument("generation", type=int)
    soul_link = soul_sub.add_parser("link", help="Make <hermes-home>/SOUL.md a symlink to the living SOUL.")
    soul_link.add_argument("hermes_home", type=Path)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "list-profiles":
        for name in list_profiles():
            print(name)
        return 0

    if args.command == "build-alignment-spec":
        from core import alignment_spec

        return _run_stage("build-alignment-spec", alignment_spec.requirements(), alignment_spec.build)

    if args.command == "enhance-skill":
        from core import skill_enhancer

        if _refuse("enhance-skill", skill_enhancer.requirements(args.apply)):
            return 1
        hermes_path = Path(args.hermes_path).expanduser() if args.hermes_path else None
        return skill_enhancer.run(skill_name=args.skill, hermes_path=hermes_path, apply=args.apply)

    if args.command == "build-translation-layer":
        from core import translation_layer_creator

        return _run_stage(
            "build-translation-layer", translation_layer_creator.requirements(), translation_layer_creator.build
        )

    if args.command == "review-queue":
        from core import langfuse_review

        return langfuse_review.run(dry_run=args.dry_run)

    if args.command == "improve-run":
        return _improve_run(args)

    if args.command == "improve-apply":
        return _improve_apply(args)

    if args.command == "improve-synthesize":
        from core import improve

        proposal = improve.synthesize_resume(min_gap_evidence=args.min_gap_evidence)
        print(json.dumps(proposal))
        _print_proposal_summary(proposal, file=sys.stderr)
        return 0

    if args.command == "soul":
        return _soul(args)

    if args.command == "journal-compact":
        from core import journal
        from core.paths import improve_dir

        summary = journal.compact(improve_dir())
        print(f"journal compact: {summary['event_count']} event(s) -> current.json/bootstrap.md")
        for name in sorted(summary.get("by_type", {})):
            print(f"  {name}: {summary['by_type'][name]}")
        return 0

    if args.command == "update":
        return _update(args)

    if not args.profile:
        raise SystemExit("Error: --profile is required. Available: " + ", ".join(list_profiles()))
    profile = get_profile(args.profile)

    if args.command == "health-check":
        from core import health_check

        return health_check.run(profile)

    return _profile_stage(args.command, profile, args)


if __name__ == "__main__":
    sys.exit(main())
