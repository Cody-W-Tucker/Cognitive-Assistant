#!/usr/bin/env python3
"""Project health checks for configuration, prompts, imports, and provider readiness."""

import importlib
import os
import shutil
from pathlib import Path
from typing import List

from config import config
from llm import create_client
from prompt_loader import PROMPT_FILES, load_prompt


PROJECT_ROOT = Path(__file__).parent
SCRIPT_MODULES = [
    "baseline_question_asker",
    "bio_to_workspace",
    "config",
    "human_interview",
    "llm",
    "prompt_creator",
    "prompt_loader",
    "question_asker",
]


def check_prompt_files() -> List[str]:
    """Verify runtime prompt files exist and load."""
    issues: List[str] = []
    for name, filename in PROMPT_FILES.items():
        prompt_path = config.paths.PROMPT_RUNTIME_DIR / filename
        if not prompt_path.exists():
            issues.append(f"Missing prompt file: {prompt_path}")
            continue

        content = load_prompt(name)
        if not content:
            issues.append(f"Prompt file is empty: {prompt_path}")

    return issues


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
        load_prompt("workspace_extraction_template").format(
            bio_content="sample bio",
            file_specs="sample specs",
            timestamp="2026-01-01T00:00:00",
        )
    except Exception as exc:
        issues.append(f"Failed to render workspace_extraction_template: {exc}")

    try:
        load_prompt("baseline_system_prompt").format(question="sample question")
    except Exception as exc:
        issues.append(f"Failed to render baseline_system_prompt: {exc}")

    try:
        load_prompt("combined_prompt_template").format(
            assistant_main="assistant",
            tools_memory="memory",
            tools_obsidian="obsidian",
            tools_todoist="todoist",
        )
    except Exception as exc:
        issues.append(f"Failed to render combined_prompt_template: {exc}")

    return issues


def check_required_paths() -> List[str]:
    """Verify required project files and directories exist."""
    issues = config.validate_question_answering()
    if not config.paths.PROMPT_RUNTIME_DIR.exists():
        issues.append(f"Prompt runtime directory not found: {config.paths.PROMPT_RUNTIME_DIR}")
    return issues


def check_script_imports() -> List[str]:
    """Verify the main modules import successfully."""
    issues: List[str] = []
    for module_name in SCRIPT_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            issues.append(f"Failed to import {module_name}: {exc}")
    return issues


def check_provider_setup() -> List[str]:
    """Verify provider environment variables, package availability, and client creation."""
    issues: List[str] = []
    provider = config.api.LLM_PROVIDER
    provider_config = config.api.PROVIDERS.get(provider)

    if not provider_config:
        return [f"Unsupported provider configured: {provider}"]

    env_key = f"{provider.upper()}_API_KEY"
    if not os.getenv(env_key):
        issues.append(f"Missing environment variable: {env_key}")

    package_name = "anthropic" if provider == "anthropic" else "openai"
    try:
        importlib.import_module(package_name)
    except ImportError as exc:
        issues.append(f"Missing Python package '{package_name}': {exc}")
        return issues

    if os.getenv(env_key):
        try:
            create_client(config.api)
        except Exception as exc:
            issues.append(f"Failed to create {provider} client: {exc}")

    return issues


def check_rlm_command() -> List[str]:
    """Verify the configured RLM command is available."""
    issues: List[str] = []
    command = config.rlm.COMMAND[0] if config.rlm.COMMAND else "rlm"
    if shutil.which(command) is None:
        issues.append(f"RLM command not found on PATH: {command}")
    return issues


def run_health_checks() -> List[str]:
    """Run all non-network health checks and return a list of issues."""
    issues: List[str] = []
    issues.extend(check_prompt_files())
    issues.extend(check_prompt_rendering())
    issues.extend(check_required_paths())
    issues.extend(check_script_imports())
    issues.extend(check_provider_setup())
    issues.extend(check_rlm_command())
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
