#!/usr/bin/env python3
"""Project health checks for configuration, prompts, imports, and provider readiness."""

import sys
from pathlib import Path
from typing import List

from config import config
from llm import create_client
from prompt_loader import PROMPT_FILES, load_prompt


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from lib.health import (  # noqa: E402
    check_prompt_files as shared_check_prompt_files,
    check_provider_setup,
    check_rlm_command,
    check_script_imports,
)


SCRIPT_MODULES = [
    "baselines.baseline_question_asker",
    "config",
    "human_interview",
    "llm",
    "prompt_creator",
    "prompt_loader",
    "question_asker",
    "skills_creator",
]


def check_prompt_rendering() -> List[str]:
    """Verify prompt templates render with expected placeholders."""
    issues: List[str] = []

    try:
        config.prompts.initial_template.format(context="sample context")
    except Exception as exc:
        issues.append(f"Failed to render initial_template: {exc}")

    try:
        config.prompts.refine_template.format(
            existing_answer="sample answer", context="sample context"
        )
    except Exception as exc:
        issues.append(f"Failed to render refine_template: {exc}")

    try:
        config.prompts.skills_creation_template.format(
            bio_content="sample bio",
        )
    except Exception as exc:
        issues.append(f"Failed to render skills_creation_template: {exc}")

    try:
        config.prompts.rlm_query_template.format(
            synthesis_prompt="sample synthesis",
            question="sample question",
            human_answer="sample answer",
        )
    except Exception as exc:
        issues.append(f"Failed to render rlm_query_template: {exc}")

    try:
        config.prompts.rlm_query_template_filesystem_only.format(
            synthesis_prompt="sample synthesis",
            question="sample question",
        )
    except Exception as exc:
        issues.append(f"Failed to render rlm_query_template_filesystem_only: {exc}")

    try:
        load_prompt("baseline_system_prompt").format(question="sample question")
    except Exception as exc:
        issues.append(f"Failed to render baseline_system_prompt: {exc}")

    return issues


def check_required_paths() -> List[str]:
    """Verify required project files and directories exist."""
    issues = config.validate_question_answering()
    if not config.paths.PROMPT_RUNTIME_DIR.exists():
        issues.append(f"Prompt runtime directory not found: {config.paths.PROMPT_RUNTIME_DIR}")
    return issues
def run_health_checks() -> List[str]:
    """Run all non-network health checks and return a list of issues."""
    issues: List[str] = []
    issues.extend(
        shared_check_prompt_files(
            prompt_files=PROMPT_FILES,
            prompt_runtime_dir=config.paths.PROMPT_RUNTIME_DIR,
            load_prompt=load_prompt,
        )
    )
    issues.extend(check_prompt_rendering())
    issues.extend(check_required_paths())
    issues.extend(check_script_imports(SCRIPT_MODULES))
    issues.extend(check_provider_setup(config=config, create_client=create_client))
    issues.extend(check_rlm_command(config.rlm.COMMAND[0] if config.rlm.COMMAND else "rlm"))
    return issues


def main() -> int:
    """Run health checks from the command line."""
    issues = run_health_checks()
    if issues:
        print("Health check failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Health check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
