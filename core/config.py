#!/usr/bin/env python3
"""Layer profiles: everything that varies between the existential and operational paths.

A profile's inputs live under ``profiles/<name>/`` (questions.csv, prompts/)
and its outputs under ``workspaces/<name>/`` (data/, artifacts/).

Usage:
    from core.config import get_profile
    profile = get_profile("existential")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

from core import paths

QUESTION_COLUMNS = ("Question 1", "Question 2", "Question 3")
ANSWER_COLUMNS = ("AI_Answer 1", "AI_Answer 2", "AI_Answer 3")
ANSWERS_PREFIX = "questions_with_answers_qmd_"
TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"


@dataclass(frozen=True)
class SkillSpec:
    """One skill generated from the named headings of a profile's human profile."""

    slug: str
    source_group: str
    source_headings: Tuple[str, ...]


@dataclass(frozen=True)
class LayerProfile:
    """Static declaration of everything a profile customizes."""

    name: str
    display_name: str
    qmd_collections: List[str]
    prompt_files: dict[str, str]
    skill_specs: List[SkillSpec]
    section_header_template: str
    answer_label: str
    redaction_patterns: List[str] = field(default_factory=lambda: [r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b"])
    has_corpus_ingest: bool = False
    # Tool spec files this profile generates, with what each tool is for.
    supported_tools: dict[str, str] = field(default_factory=dict)

    @property
    def profile_dir(self) -> Path:
        return paths.REPO_ROOT / "profiles" / self.name

    @property
    def prompts_dir(self) -> Path:
        return self.profile_dir / "prompts"

    @property
    def questions_csv(self) -> Path:
        return self.profile_dir / "questions.csv"

    @property
    def workspace_dir(self) -> Path:
        return paths.REPO_ROOT / "workspaces" / self.name

    @property
    def data_dir(self) -> Path:
        return self.workspace_dir / "data"

    @property
    def artifacts_dir(self) -> Path:
        return self.workspace_dir / "artifacts"

    @property
    def human_profile_path(self) -> Path:
        return self.artifacts_dir / "human_profile.md"

    @property
    def tool_specs_dir(self) -> Path:
        return self.artifacts_dir / "tool_specs"

    def answers_path(self, timestamp: str) -> Path:
        return self.data_dir / f"{ANSWERS_PREFIX}{timestamp}.csv"

    def latest_answers(self) -> Path:
        """The newest answered-questions CSV (timestamped names sort by time)."""
        found = sorted(self.data_dir.glob(f"{ANSWERS_PREFIX}*.csv"))
        if not found:
            raise FileNotFoundError(f"No answered questions in {self.data_dir}; run ask-questions first")
        return found[-1]

    def prompt(self, name: str) -> str:
        """Load one of the profile's prompt templates by logical name."""
        if name not in self.prompt_files:
            raise KeyError(f"Profile '{self.name}' does not declare prompt '{name}'")
        return (self.prompts_dir / self.prompt_files[name]).read_text(encoding="utf-8").strip()

    def redact(self, text: str) -> str:
        for pattern in self.redaction_patterns:
            text = re.sub(pattern, "[REDACTED]", text)
        return text


_PROFILES: dict[str, LayerProfile] = {}


def register_profile(profile: LayerProfile) -> None:
    """Register a layer profile so the CLI can resolve it by name."""
    _PROFILES[profile.name] = profile


def get_profile(name: str) -> LayerProfile:
    if name not in _PROFILES:
        available = ", ".join(sorted(_PROFILES)) or "(none registered)"
        raise KeyError(f"Unknown profile '{name}'. Available: {available}")
    return _PROFILES[name]


def list_profiles() -> List[str]:
    return sorted(_PROFILES)


def all_profiles() -> List[LayerProfile]:
    return [_PROFILES[name] for name in list_profiles()]


_SHARED_PROMPTS = {
    "synthesis_prompt": "synthesis_prompt.md",
    "initial_template": "initial_template.md",
    "ensemble_synthesis_template": "ensemble_synthesis_template.md",
    "skills_creation_template": "skills_creation_template.md",
    "qmd_query_template": "qmd_query_template.md",
}

EXISTENTIAL_PROFILE = LayerProfile(
    name="existential",
    display_name="Existential Layer",
    qmd_collections=["Journal", "Personal"],
    prompt_files=dict(_SHARED_PROMPTS),
    section_header_template="# Understanding: **{category}**",
    answer_label="AI Answer",
    skill_specs=[
        SkillSpec(
            slug="mode-detection",
            source_group="group-1",
            source_headings=("Core Frame", "High-Leverage Signals", "Interpretation Rules"),
        ),
        SkillSpec(
            slug="decision-calibration",
            source_group="group-2",
            source_headings=("Success Conditions", "Constraint Map"),
        ),
        SkillSpec(
            slug="relational-orientation",
            source_group="group-3",
            source_headings=("Growth / Trajectory", "Counterpart Implications", "Open Questions"),
        ),
    ],
)

OPERATIONAL_PROFILE = LayerProfile(
    name="operational",
    display_name="Operational Layer",
    qmd_collections=["Base", "Consulting", "Customers"],
    prompt_files={**_SHARED_PROMPTS, "tool_specs_creation_template": "tool_specs_creation_template.md"},
    has_corpus_ingest=True,
    supported_tools={
        "memory.md": "Memory agent for durable continuity and retrieval.",
        "tasks.md": "Task agent for capturing, shaping, and retrieving commitments.",
    },
    redaction_patterns=[
        r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",
        r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
    ],
    section_header_template="# Operational Category: **{category}**",
    answer_label="Operational Answer",
    skill_specs=[
        SkillSpec(
            slug="scope-framing",
            source_group="group-1",
            source_headings=("Core Frame", "High-Leverage Signals", "Salience Structure"),
        ),
        SkillSpec(
            slug="failure-recovery",
            source_group="group-2",
            source_headings=("Lived Thresholds", "Mode Shifts", "Breakdown and Repair"),
        ),
        SkillSpec(
            slug="complexity-reduction",
            source_group="group-3",
            source_headings=("Quality Detection", "Artifact Relation", "Success Conditions"),
        ),
        SkillSpec(
            slug="boundary-handoff",
            source_group="group-4",
            source_headings=("Tensions and Tradeoffs", "Boundary Conditions", "Counterpart Implications"),
        ),
    ],
)

register_profile(EXISTENTIAL_PROFILE)
register_profile(OPERATIONAL_PROFILE)
