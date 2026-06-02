#!/usr/bin/env python3
"""Reusable health-check helpers for layer pipelines."""

import importlib
import os
import shutil
from pathlib import Path
from typing import Callable, Iterable, List


def check_prompt_files(
    *,
    prompt_files: dict[str, str],
    prompt_runtime_dir: Path,
    load_prompt: Callable[[str], str],
) -> List[str]:
    """Verify runtime prompt files exist and load."""
    issues: List[str] = []
    for name, filename in prompt_files.items():
        prompt_path = prompt_runtime_dir / filename
        if not prompt_path.exists():
            issues.append(f"Missing prompt file: {prompt_path}")
            continue

        content = load_prompt(name)
        if not content:
            issues.append(f"Prompt file is empty: {prompt_path}")

    return issues


def check_script_imports(script_modules: Iterable[str]) -> List[str]:
    """Verify the main modules import successfully."""
    issues: List[str] = []
    for module_name in script_modules:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            issues.append(f"Failed to import {module_name}: {exc}")
    return issues


def check_provider_setup(
    *, config, create_client: Callable, providers: Iterable[str] | None = None
) -> List[str]:
    """Verify provider environment variables, packages, and client creation."""
    issues: List[str] = []
    provider_names = list(providers or [config.api.LLM_PROVIDER])

    for provider in provider_names:
        provider_config = config.api.PROVIDERS.get(provider)

        if not provider_config:
            issues.append(f"Unsupported provider configured: {provider}")
            continue

        env_key = f"{provider.upper()}_API_KEY"
        if not os.getenv(env_key):
            issues.append(f"Missing environment variable: {env_key}")

        package_name = "anthropic" if provider == "anthropic" else "openai"
        try:
            importlib.import_module(package_name)
        except ImportError as exc:
            issues.append(f"Missing Python package '{package_name}': {exc}")
            continue

        if os.getenv(env_key):
            try:
                create_client(config.api, provider=provider)
            except Exception as exc:
                issues.append(f"Failed to create {provider} client: {exc}")

    return issues


def check_rlm_command(command: str) -> List[str]:
    """Verify the configured RLM command is available."""
    issues: List[str] = []
    if shutil.which(command) is None:
        issues.append(f"RLM command not found on PATH: {command}")
    return issues
