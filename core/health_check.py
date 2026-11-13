#!/usr/bin/env python3
"""Profile health check: prompts, inputs, provider access and QMD, without calling a model."""

from __future__ import annotations

import importlib
import shutil
import string
from pathlib import Path
from typing import List

from core import llm, paths, prompt_creator
from core.config import LayerProfile

STAGE_MODULES = (
    "core.ingest_corpus",
    "core.question_asker",
    "core.prompt_creator",
    "core.skills_creator",
    "core.tool_specs_creator",
    "core.skill_enhancer",
    "core.translation_layer_creator",
    "core.alignment_spec",
)


def check_template(path: Path) -> List[str]:
    """A prompt template must exist, be non-empty and parse as a format string."""
    if not path.exists():
        return [f"Missing prompt file: {path}"]
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return [f"Prompt file is empty: {path}"]
    try:
        for _, field, _, _ in string.Formatter().parse(text):
            if field is not None and not field.isidentifier():
                return [f"Prompt {path.name} has a non-keyword placeholder {{{field}}}"]
    except ValueError as exc:
        return [f"Prompt {path.name} is not a valid template: {exc}"]
    return []


def check_prompts(profile: LayerProfile) -> List[str]:
    templates = [profile.prompts_dir / filename for filename in profile.prompt_files.values()]
    templates += sorted(paths.ALIGNMENT_PROMPTS_DIR.glob("*.md"))
    return [issue for template in templates for issue in check_template(template)]


def check_imports() -> List[str]:
    issues = []
    for module in STAGE_MODULES:
        try:
            importlib.import_module(module)
        except Exception as exc:
            issues.append(f"Failed to import {module}: {exc}")
    return issues


def check_providers() -> List[str]:
    issues = [issue for provider in prompt_creator.PROVIDERS for issue in llm.missing_config(provider)]
    for package in ("anthropic", "openai"):
        try:
            importlib.import_module(package)
        except ImportError as exc:
            issues.append(f"Missing Python package '{package}': {exc}")
    return issues


def run_health_checks(profile: LayerProfile) -> List[str]:
    issues = check_prompts(profile)
    if not profile.questions_csv.exists():
        issues.append(f"Questions CSV not found at {profile.questions_csv}")
    if not profile.qmd_collections:
        issues.append(f"No QMD collections configured for profile '{profile.name}'")
    issues += check_imports()
    issues += check_providers()
    if shutil.which("qmd") is None:
        issues.append("QMD command not found on PATH: qmd")
    return list(dict.fromkeys(issues))


def run(profile: LayerProfile) -> int:
    issues = run_health_checks(profile)
    if issues:
        print(f"Health check failed for profile '{profile.name}':")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print(f"Health check passed for profile '{profile.name}'.")
    return 0
