#!/usr/bin/env python3
"""Profile-aware health checks for the unified pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import List

from core.config import ROOT_DIR, Config
from core.prompt_creator import get_prompt_creator_providers
from core.prompt_loader import load_prompt_for_profile
from lib.health import (
    check_prompt_files as shared_check_prompt_files,
    check_provider_setup,
    check_rlm_command,
    check_script_imports,
)
from lib.llm import create_client


SCRIPT_MODULES = [
    "core.config",
    "core.prompt_loader",
    "core.prompt_creator",
    "core.skills_creator",
    "core.skill_enhancer",
    "core.question_asker",
    "core.health_check",
    "core.archetype_catalog",
    "core.soul_creator",
    "core.translation_layer_creator",
    "core.alignment_spec",
]


# Sample placeholder values used to verify each prompt template renders.
_PLACEHOLDER_FIXTURES = {
    "synthesis_prompt": "sample synthesis",
    "question": "sample question",
    "category": "sample category",
    "goal": "sample goal",
    "element": "sample element",
    "context": "sample context",
    "existing_answer": "sample existing answer",
    "bio_content": "sample bio",
    "grouped_bio_content": "<skill_group name=\"group-1\">sample bio</skill_group>",
    "supported_tools": "- `memory.md`: Memory agent",
    "seed_documents": "sample seed",
    "profile_sources": "<profile_source layer=\"existential\">sample</profile_source>",
    "interaction_posture": "sample interaction posture",
    "translation_layer": "sample translation layer",
    "catalog": "{\"role-taker\": {}}",
    "context_registry": "{\"entries\": []}",
    "human_source_registry": "{\"sources\": []}",
    "stakeholder_registry": "{\"entries\": []}",
    "synthetic_perspective_registry": "{\"entries\": []}",
    "provenance_policy": "{\"sources\": []}",
    "profile_evidence_registry": "{\"entries\": []}",
    "domain_tiers": "{\"medium\": {}}",
    "trigger_vocabulary": "[\"uncertainty\"]",
    "agent_definition": "{\"id\": \"agent\"}",
    "skill_material": "<skill slug=\"sample\">sample</skill>",
    "skills_content": "<skill slug=\"sample\">sample</skill>",
    "agent_souls_content": "<agent_soul slug=\"agent\">sample</agent_soul>",
}


def _render_template(template: str, placeholders: List[str]) -> None:
    """Render a template with the configured placeholder fixtures."""
    fixture = {name: _PLACEHOLDER_FIXTURES.get(name, "sample") for name in placeholders}
    template.format(**fixture)


def check_prompt_rendering(config: Config) -> List[str]:
    """Verify all profile-declared prompt templates render with their placeholders."""
    issues: List[str] = []
    profile = config.profile

    render_specs = {
        "initial_template": ["context"],
        "ensemble_synthesis_template": ["candidate_profiles"],
        "skills_creation_template": ["grouped_bio_content"],
        "rlm_query_template": profile.rlm_prompt_placeholders,
        "tool_specs_creation_template": [
            "bio_content",
            "supported_tools",
            "seed_documents",
        ],
    }

    for prompt_name, placeholders in render_specs.items():
        if not config.prompts.has(prompt_name):
            continue
        try:
            template = getattr(config.prompts, prompt_name)
            _render_template(template, placeholders)
        except Exception as exc:
            issues.append(f"Failed to render {prompt_name}: {exc}")

    return issues


def check_required_paths(config: Config) -> List[str]:
    """Verify required project files and directories exist."""
    issues = config.validate_question_answering()
    if not config.paths.PROMPT_RUNTIME_DIR.exists():
        issues.append(
            f"Prompt runtime directory not found: {config.paths.PROMPT_RUNTIME_DIR}"
        )
    return issues


# Alignment prompts live outside the profile system; render them separately
# so health checks cover the restored translation-layer seeds.
_ALIGNMENT_PROMPT_FIXTURES = {
    "interaction_posture_seed.md": ["profile_sources"],
    "soul_seed.md": ["profile_sources", "interaction_posture"],
    "archetype_selection_seed.md": [
        "catalog",
        "interaction_posture",
        "translation_layer",
        "context_registry",
        "human_source_registry",
        "stakeholder_registry",
        "synthetic_perspective_registry",
        "provenance_policy",
        "profile_evidence_registry",
        "domain_tiers",
        "trigger_vocabulary",
    ],
    "agent_soul_seed.md": ["agent_definition", "interaction_posture", "skill_material"],
    "seed.md": ["skills_content", "agent_souls_content"],
}


def check_alignment_prompt_rendering() -> List[str]:
    """Verify alignment prompts render with their declared placeholders."""
    issues: List[str] = []
    prompts_dir = ROOT_DIR / "profiles" / "alignment" / "prompts"
    for filename, placeholders in _ALIGNMENT_PROMPT_FIXTURES.items():
        prompt_path = prompts_dir / filename
        if not prompt_path.exists():
            issues.append(f"Missing alignment prompt: {prompt_path}")
            continue
        try:
            template = prompt_path.read_text(encoding="utf-8")
            fixture = {
                name: _PLACEHOLDER_FIXTURES.get(name, "sample")
                for name in placeholders
            }
            template.format(**fixture)
        except Exception as exc:
            issues.append(f"Failed to render {filename}: {exc}")
    return issues


def run_health_checks(config: Config) -> List[str]:
    """Run all non-network health checks for a profile and return any issues."""
    issues: List[str] = []
    issues.extend(
        shared_check_prompt_files(
            prompt_files=config.profile.prompt_files,
            prompt_runtime_dir=config.profile.prompts_dir,
            load_prompt=lambda name: load_prompt_for_profile(config.profile, name),
        )
    )
    issues.extend(check_prompt_rendering(config))
    issues.extend(check_required_paths(config))
    issues.extend(check_alignment_prompt_rendering())
    issues.extend(check_script_imports(SCRIPT_MODULES))
    issues.extend(
        check_provider_setup(
            config=config,
            create_client=create_client,
            providers=get_prompt_creator_providers(),
        )
    )
    issues.extend(
        check_rlm_command(config.rlm.COMMAND[0] if config.rlm.COMMAND else "rlm")
    )
    return issues


def run(config: Config) -> int:
    """CLI entry point. Returns 0 on success, 1 on any issues."""
    issues = run_health_checks(config)
    if issues:
        print(f"Health check failed for profile '{config.profile.name}':")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print(f"Health check passed for profile '{config.profile.name}'.")
    return 0


__all__ = ["run", "run_health_checks"]
