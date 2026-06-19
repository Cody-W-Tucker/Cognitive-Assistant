"""LLM-backed Skill Enhancer for importing skills from Hermes source material."""

from __future__ import annotations

import asyncio
import difflib
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.skill_engine import (
    body_without_frontmatter,
    find_canonical_skill,
    generate_hermes_enhancement,
    repo_root,
    validate_skill_slug,
)
from lib.config import APIConfig, validate_provider_config
from lib.llm import close_client_async, create_client


DEFAULT_HERMES_SKILLS_DIR = Path("/var/lib/hermes/.hermes/skills")
GENERATED_START = "<!-- skill-enhancer: generated start -->"
GENERATED_END = "<!-- skill-enhancer: generated end -->"
SKIP_EXIT_CODE = 2


def _repo_root() -> Path:
    return repo_root()


def _validate_skill_name(skill_name: str) -> None:
    validate_skill_slug(skill_name)


def _discover_workspace_skill_names() -> list[str]:
    skill_names: set[str] = set()
    root = _repo_root() / "workspaces" / "skills"
    if not root.exists():
        return []

    for skill_file in root.glob("*/*/SKILL.md"):
        skill_name = skill_file.parent.name
        try:
            _validate_skill_name(skill_name)
        except ValueError:
            continue
        skill_names.add(skill_name)

    return sorted(skill_names)


def _candidate_skill_files(
    skill_name: str,
    hermes_path: Path | None,
) -> list[Path]:
    candidate_dirs: list[Path] = []
    candidate_files: list[Path] = []

    if hermes_path is not None:
        if hermes_path.name == "SKILL.md":
            candidate_files.append(hermes_path)
        candidate_files.append(hermes_path / skill_name / "SKILL.md")
        candidate_files.append(hermes_path / "SKILL.md")
        candidate_dirs.append(hermes_path)

    candidate_dirs.append(DEFAULT_HERMES_SKILLS_DIR)

    for directory in candidate_dirs:
        candidate_files.append(directory / skill_name / "SKILL.md")
        if directory.exists() and directory.is_dir():
            candidate_files.extend(directory.glob(f"**/{skill_name}/SKILL.md"))

    unique_files: list[Path] = []
    seen: set[Path] = set()
    for path in candidate_files:
        resolved = path.expanduser()
        if resolved not in seen:
            unique_files.append(resolved)
            seen.add(resolved)

    return unique_files


def _locate_hermes_skill(
    skill_name: str,
    hermes_path: Path | None,
) -> Path | None:
    for path in _candidate_skill_files(skill_name, hermes_path):
        if path.is_file():
            return path
    return None


def _unified_diff(
    hermes_content: str,
    local_content: str,
    hermes_path: Path,
    local_skill_path: Path,
) -> str:
    diff_lines = list(
        difflib.unified_diff(
            hermes_content.splitlines(),
            local_content.splitlines(),
            fromfile=str(hermes_path),
            tofile=str(local_skill_path),
            lineterm="",
        )
    )
    return "\n".join(diff_lines) + ("\n" if diff_lines else "")


def _has_hermes_side_changes(diff: str) -> bool:
    for line in diff.splitlines():
        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            continue
        if line.startswith("-"):
            return True
    return False


def _ensure_trailing_newline(content: str) -> str:
    return content if content.endswith("\n") else content + "\n"


def _artifact_context(
    hermes_skill_path: Path,
    canonical_skill_path_value: Path,
) -> str:
    return "\n".join(
        [
            "Enhancement context:",
            f"hermes_skill_path: {hermes_skill_path}",
            f"canonical_skill_path: {canonical_skill_path_value}",
            "matching: upstream Hermes skills are matched by skill name only",
        ]
    )


def _is_hermes_newer(hermes_skill_path: Path, local_skill_path: Path) -> bool:
    return hermes_skill_path.stat().st_mtime > local_skill_path.stat().st_mtime


def _format_preview(
    *,
    skill_name: str,
    diff: str,
    apply: bool,
) -> str:
    lines = [
        "Skill Enhancer preview",
        f"- skill: {skill_name}",
        "- llm input contract: local canonical skill plus diff-only improvement context",
        "",
        "--- DIFF THAT MAY IMPROVE IT ---",
        diff.strip() or "(no diff)",
    ]
    if not apply:
        lines.extend([
            "",
            "Dry run only. Re-run with --apply to write the enhanced canonical skill.",
        ])
    return "\n".join(lines)


def _timestamp_suffix() -> str:
    return datetime.now(timezone.utc).strftime("backup.%Y%m%d%H%M%S")


def _strip_generated_section(content: str) -> tuple[str, bool]:
    start = content.find(GENERATED_START)
    end = content.find(GENERATED_END)
    if start == -1 or end == -1 or end < start:
        return content.rstrip(), False

    end += len(GENERATED_END)
    return (content[:start] + content[end:]).strip(), True


def _wrap_generated_content(enhanced_content: str) -> str:
    return "\n".join(
        [
            GENERATED_START,
            enhanced_content.strip(),
            GENERATED_END,
            "",
        ]
    )


def _backup_path(skill_path: Path) -> Path:
    base = skill_path.with_name(f"{skill_path.name}.{_timestamp_suffix()}")
    if not base.exists():
        return base
    index = 1
    while True:
        candidate = skill_path.with_name(f"{skill_path.name}.{_timestamp_suffix()}.{index}")
        if not candidate.exists():
            return candidate
        index += 1


def _merge_or_backup_write(
    skill_path: Path,
    local_content: str,
    enhanced_content: str,
) -> Path | None:
    wrapped_content = _wrap_generated_content(enhanced_content)
    preserved_content, had_generated_section = _strip_generated_section(local_content)

    if had_generated_section:
        final_content = (
            f"{preserved_content}\n\n{wrapped_content}"
            if preserved_content
            else wrapped_content
        )
        skill_path.write_text(_ensure_trailing_newline(final_content), encoding="utf-8")
        return None

    backup_path: Path | None = None
    if local_content.strip():
        backup_path = _backup_path(skill_path)
        backup_path.write_text(_ensure_trailing_newline(local_content), encoding="utf-8")

    skill_path.write_text(_ensure_trailing_newline(enhanced_content.strip()), encoding="utf-8")
    return backup_path


async def _enhance_async(
    api: APIConfig,
    *,
    skill_name: str,
    hermes_content: str,
    local_content: str,
    diff: str,
    enhancement_context: str,
) -> str:
    handle = create_client(
        api,
        model=api.get_model("refine"),
        async_mode=True,
    )
    try:
        return await generate_hermes_enhancement(
            handle=handle,
            skill_name=skill_name,
            hermes_content=hermes_content,
            local_content=local_content,
            diff=diff,
            context=enhancement_context,
            temperature=api.TEMPERATURE,
            max_output_tokens=api.MAX_COMPLETION_TOKENS,
        )
    finally:
        await close_client_async(handle)


def _run_single_skill(skill_name: str, hermes_path: Path | None, apply: bool) -> int:
    """Locate one Hermes source skill and generate or preview an enhanced canonical skill."""
    try:
        _validate_skill_name(skill_name)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    local_skill_path = find_canonical_skill(skill_name)
    if local_skill_path is None:
        return SKIP_EXIT_CODE

    hermes_skill_path = _locate_hermes_skill(skill_name, hermes_path)
    if hermes_skill_path is None:
        return SKIP_EXIT_CODE

    hermes_content = hermes_skill_path.read_text(encoding="utf-8")
    local_content = local_skill_path.read_text(encoding="utf-8")

    if not _is_hermes_newer(hermes_skill_path, local_skill_path):
        return SKIP_EXIT_CODE

    content_diff = _unified_diff(
        hermes_content=body_without_frontmatter(hermes_content).lstrip(),
        local_content=body_without_frontmatter(local_content).lstrip(),
        hermes_path=hermes_skill_path,
        local_skill_path=local_skill_path,
    )
    if not content_diff or not _has_hermes_side_changes(content_diff):
        return SKIP_EXIT_CODE

    enhancement_context = _artifact_context(hermes_skill_path, local_skill_path)

    print(
        _format_preview(
            skill_name=skill_name,
            diff=content_diff,
            apply=apply,
        )
    )

    if not apply:
        return 0

    api = APIConfig()
    issues = validate_provider_config(api)
    if issues:
        print("Error: Configuration issues found")
        for issue in issues:
            print(f"- {issue}")
        return 1

    local_skill_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        enhanced_content = asyncio.run(
            _enhance_async(
                api,
                skill_name=skill_name,
                hermes_content=hermes_content,
                local_content=local_content,
                diff=content_diff,
                enhancement_context=enhancement_context,
            )
        )
        backup_path = _merge_or_backup_write(
            local_skill_path,
            local_content,
            enhanced_content,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if backup_path is not None:
        print(f"Info: Backed up previous canonical skill: {backup_path}")
    print(f"Wrote enhanced canonical skill: {local_skill_path}")
    return 0


def run(skill_name: str | None = None, hermes_path: Path | None = None, apply: bool = False) -> int:
    """Preview or enhance one named skill, or all discovered workspace skills."""
    if skill_name is not None:
        exit_code = _run_single_skill(skill_name, hermes_path, apply)
        return 0 if exit_code == SKIP_EXIT_CODE else exit_code

    skill_names = _discover_workspace_skill_names()
    if not skill_names:
        return 0

    failures = 0
    found_updates = 0
    for index, discovered_skill_name in enumerate(skill_names, start=1):
        exit_code = _run_single_skill(discovered_skill_name, hermes_path, apply)
        if exit_code == 0:
            found_updates += 1
        elif exit_code != SKIP_EXIT_CODE:
            failures += 1

    if found_updates > 0 and not apply:
        print()
        print(f"Would change {found_updates} skill(s).")

    if found_updates == 0:
        return 0
    return 1 if failures else 0
