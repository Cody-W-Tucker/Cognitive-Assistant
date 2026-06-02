#!/usr/bin/env python3
"""Unified configuration for the layer pipeline.

A `LayerProfile` declares everything that varies between the existential and
operational paths. A `Config` is built from a profile and exposes the same
attribute surface previous per-layer config modules used (`api`, `paths`, `rlm`,
`csv`, `redaction`, `prompts`, `output`, `profile`).

Usage:
    from core.config import Config
    config = Config.from_profile("existential")
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple

# Make the repo root importable so `lib.*` resolves regardless of how callers
# invoke the pipeline.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from lib.config import (  # noqa: E402
    APIConfig,
    PathConfig,
    RedactionConfig,
    get_data_files as shared_get_data_files,
    get_most_recent_file as shared_get_most_recent_file,
    run_rlm_query as shared_run_rlm_query,
    validate_provider_config,
)
from lib.prompts import (
    load_prompt as shared_load_prompt,
    prompt_mapping_key,
)  # noqa: E402


# ---------------------------------------------------------------------------
# LayerProfile — single inspectable surface for layer-specific behavior
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LayerProfile:
    """Static declaration of everything a profile customizes."""

    # Identity
    name: str
    display_name: str

    # On-disk locations
    profile_dir: Path  # profiles/<name>/
    workspace_dir: Path  # workspaces/<name>/
    questions_csv: Path  # profiles/<name>/questions.csv
    prompts_dir: Path  # profiles/<name>/prompts/runtime

    # Evidence source (exactly one is populated)
    rlm_review_paths: Optional[List[Path]] = None
    rlm_review_globs: Optional[List[str]] = None

    # Prompt set: logical_name -> filename inside prompts_dir
    prompt_files: dict[str, str] = field(default_factory=dict)

    # RLM prompt placeholder set used by question_asker and health_check fixtures
    rlm_prompt_placeholders: List[str] = field(default_factory=list)

    # Pipeline gates
    has_corpus_ingest: bool = False
    has_tool_specs: bool = False
    supported_tools: dict[str, str] = field(default_factory=dict)

    # Redaction patterns (regex strings)
    redaction_patterns: List[str] = field(
        default_factory=lambda: [r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b"]
    )

    # Prompt creator section header style
    section_header_template: str = "# Understanding: **{category}**"
    answer_label: str = "AI Answer"

    # Skills creator section grouping
    skill_heading_groups: List[Tuple[str, List[str]]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Profile registry — the two layer profiles
# ---------------------------------------------------------------------------


_PROFILES: dict[str, LayerProfile] = {}


def register_profile(profile: LayerProfile) -> None:
    """Register a layer profile so the CLI can resolve it by name."""
    _PROFILES[profile.name] = profile


def get_profile(name: str) -> LayerProfile:
    """Look up a registered profile by name."""
    if name not in _PROFILES:
        available = ", ".join(sorted(_PROFILES)) or "(none registered)"
        raise KeyError(f"Unknown profile '{name}'. Available: {available}")
    return _PROFILES[name]


def list_profiles() -> List[str]:
    """Return the registered profile names."""
    return sorted(_PROFILES)


# Built-in profiles ----------------------------------------------------------

EXISTENTIAL_PROFILE = LayerProfile(
    name="existential",
    display_name="Existential Layer",
    profile_dir=ROOT_DIR / "profiles" / "existential",
    workspace_dir=ROOT_DIR / "workspaces" / "existential",
    questions_csv=ROOT_DIR / "profiles" / "existential" / "questions.csv",
    prompts_dir=ROOT_DIR / "profiles" / "existential" / "prompts",
    rlm_review_paths=None,
    rlm_review_globs=[
        "ready/substrate/graph_pages.jsonl",
        "ready/substrate/mention_evidence.jsonl",
    ],
    prompt_files={
        "synthesis_prompt": "synthesis_prompt.md",
        "initial_template": "initial_template.md",
        "skills_creation_template": "skills_creation_template.md",
        "rlm_query_template": "rlm_query_template.md",
    },
    rlm_prompt_placeholders=["synthesis_prompt", "question"],
    has_corpus_ingest=False,
    has_tool_specs=False,
    section_header_template="# Understanding: **{category}**",
    answer_label="AI Answer",
    skill_heading_groups=[
        (
            "group-1",
            ["Core Frame", "High-Leverage Signals", "Interpretation Rules"],
        ),
        ("group-2", ["Success Conditions", "Constraint Map"]),
        (
            "group-3",
            ["Growth / Trajectory", "Counterpart Implications", "Open Questions"],
        ),
    ],
)

OPERATIONAL_PROFILE = LayerProfile(
    name="operational",
    display_name="Operational Layer",
    profile_dir=ROOT_DIR / "profiles" / "operational",
    workspace_dir=ROOT_DIR / "workspaces" / "operational",
    questions_csv=ROOT_DIR / "profiles" / "operational" / "questions.csv",
    prompts_dir=ROOT_DIR / "profiles" / "operational" / "prompts",
    rlm_review_paths=None,
    rlm_review_globs=["ready/**/*.jsonl"],
    prompt_files={
        "synthesis_prompt": "synthesis_prompt.md",
        "initial_template": "initial_template.md",
        "skills_creation_template": "skills_creation_template.md",
        "tool_specs_creation_template": "tool_specs_creation_template.md",
        "rlm_query_template": "rlm_query_template.md",
    },
    rlm_prompt_placeholders=[
        "synthesis_prompt",
        "category",
        "goal",
        "element",
        "question",
    ],
    has_corpus_ingest=True,
    has_tool_specs=True,
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
    skill_heading_groups=[
        (
            "group-1",
            ["Core Frame", "High-Leverage Signals", "Salience Structure"],
        ),
        (
            "group-2",
            ["Lived Thresholds", "Mode Shifts", "Breakdown and Repair"],
        ),
        (
            "group-3",
            ["Quality Detection", "Artifact Relation", "Success Conditions"],
        ),
        (
            "group-4",
            [
                "Tensions and Tradeoffs",
                "Boundary Conditions",
                "Counterpart Implications",
            ],
        ),
    ],
)

register_profile(EXISTENTIAL_PROFILE)
register_profile(OPERATIONAL_PROFILE)


# ---------------------------------------------------------------------------
# Path / RLM / CSV / Prompts / Output sub-configs derived from a profile
# ---------------------------------------------------------------------------


class ProfilePathConfig(PathConfig):
    """Filesystem layout for a profile rooted at its workspace directory.

    Profile-owned inputs (questions.csv, prompts/) live under `profile_dir`;
    runtime outputs (data/, artifacts/) live under `workspace_dir`.
    """

    def __init__(self, profile: LayerProfile) -> None:
        paths = {
            "DATA_DIR": "data",
            "INTAKE_DIR": "data/intake",
            "READY_DIR": "data/ready",
            "ARTIFACTS_DIR": "artifacts",
            "SKILLS_DIR": "artifacts/skills",
            "TOOL_SPECS_DIR": "artifacts/tool_specs",
        }
        super().__init__(profile.workspace_dir, paths)
        # Profile-owned inputs are not under workspace_dir; attach explicitly.
        self.PROFILE_DIR = profile.profile_dir
        self.PROMPTS_DIR = profile.prompts_dir.parent
        self.PROMPT_RUNTIME_DIR = profile.prompts_dir
        self.QUESTIONS_CSV = profile.questions_csv

    def ensure_directories_exist(self) -> None:
        """Ensure workspace directories exist; prompt/profile dirs are read-only."""
        for attr in [
            "DATA_DIR",
            "INTAKE_DIR",
            "READY_DIR",
            "ARTIFACTS_DIR",
            "SKILLS_DIR",
            "TOOL_SPECS_DIR",
        ]:
            getattr(self, attr).mkdir(parents=True, exist_ok=True)


@dataclass
class RLMConfig:
    """RLM CLI configuration derived from a profile."""

    profile: LayerProfile
    COMMAND: List[str] = field(default_factory=lambda: ["rlm"])
    TIMEOUT_SECONDS: int = 300

    @property
    def REVIEW_PATHS(self) -> Optional[List[Path]]:
        return self.profile.rlm_review_paths

    @property
    def REVIEW_GLOBS(self) -> Optional[List[str]]:
        return self.profile.rlm_review_globs

    def validate(self, data_dir: Path) -> List[str]:
        """Validate that the configured evidence source resolves to something."""
        issues: List[str] = []
        if self.profile.rlm_review_paths is not None:
            if not self.profile.rlm_review_paths:
                issues.append("RLM review paths are not configured for this profile")
                return issues
            for path in self.profile.rlm_review_paths:
                if not path.exists():
                    issues.append(f"RLM review path does not exist: {path}")
        elif self.profile.rlm_review_globs is not None:
            if not self.profile.rlm_review_globs:
                issues.append("RLM review globs are not configured for this profile")
                return issues
            if not _resolve_globs(data_dir, self.profile.rlm_review_globs):
                issues.append(
                    "No files matched the configured REVIEW_GLOBS under " f"{data_dir}"
                )
        else:
            issues.append("Profile has neither rlm_review_paths nor rlm_review_globs")
        return issues


def _resolve_globs(base_dir: Path, patterns: Iterable[str]) -> List[Path]:
    """Resolve glob patterns relative to a base dir into a deduped file list."""
    resolved: List[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for path in sorted(base_dir.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                resolved.append(path)
    return resolved


@dataclass
class CSVConfig:
    """CSV schema for profile question and answer datasets."""

    profile: LayerProfile
    DELIMITER: str = ","
    QUOTECHAR: str = '"'

    QUESTION_COLUMNS: List[str] = field(
        default_factory=lambda: ["Question 1", "Question 2", "Question 3"]
    )
    ANSWER_COLUMNS: List[str] = field(
        default_factory=lambda: ["AI_Answer 1", "AI_Answer 2", "AI_Answer 3"]
    )
    CATEGORY_KEY_COLUMNS: List[str] = field(
        default_factory=lambda: ["Category", "Goal", "Element"]
    )

    @property
    def FIELDNAMES(self) -> List[str]:
        base = [
            "Category",
            "Goal",
            "Element",
            *self.QUESTION_COLUMNS,
        ]
        base.extend(self.ANSWER_COLUMNS)
        return base


@dataclass
class ProfileRedactionConfig(RedactionConfig):
    """Redaction config sourced from the profile's pattern list."""

    SENSITIVE_PATTERNS: List[str] = field(default_factory=list)


@dataclass
class PromptsConfig:
    """Lazily-loaded prompt template strings declared by the profile."""

    profile: LayerProfile

    def _load(self, name: str) -> str:
        if name not in self.profile.prompt_files:
            raise KeyError(
                f"Profile '{self.profile.name}' does not declare prompt '{name}'"
            )
        return shared_load_prompt(
            str(self.profile.prompts_dir),
            prompt_mapping_key(self.profile.prompt_files),
            name,
        )

    @property
    def synthesis_prompt(self) -> str:
        return self._load("synthesis_prompt")

    @property
    def initial_template(self) -> str:
        return self._load("initial_template")

    @property
    def skills_creation_template(self) -> str:
        return self._load("skills_creation_template")

    @property
    def rlm_query_template(self) -> str:
        return self._load("rlm_query_template")

    @property
    def tool_specs_creation_template(self) -> str:
        return self._load("tool_specs_creation_template")

    def has(self, name: str) -> bool:
        """Whether the profile declares this prompt name."""
        return name in self.profile.prompt_files


@dataclass
class OutputConfig:
    """Output file naming patterns."""

    QUESTIONS_WITH_ANSWERS_PATTERN: str = "questions_with_answers_rlm_{timestamp}.csv"
    TIMESTAMP_FORMAT: str = "%Y%m%d_%H%M%S"


# ---------------------------------------------------------------------------
# Top-level Config aggregate
# ---------------------------------------------------------------------------


@dataclass
class Config:
    """Top-level configuration bound to a single layer profile."""

    profile: LayerProfile
    api: APIConfig = field(default_factory=APIConfig)
    paths: ProfilePathConfig = field(init=False)
    rlm: RLMConfig = field(init=False)
    csv: CSVConfig = field(init=False)
    redaction: ProfileRedactionConfig = field(init=False)
    prompts: PromptsConfig = field(init=False)
    output: OutputConfig = field(default_factory=OutputConfig)

    def __post_init__(self) -> None:
        self.paths = ProfilePathConfig(self.profile)
        self.rlm = RLMConfig(profile=self.profile)
        self.csv = CSVConfig(profile=self.profile)
        self.redaction = ProfileRedactionConfig(
            SENSITIVE_PATTERNS=list(self.profile.redaction_patterns),
        )
        self.prompts = PromptsConfig(profile=self.profile)
        self.paths.ensure_directories_exist()

    # ----- factory methods ---------------------------------------------------

    @classmethod
    def from_profile(cls, profile_name: str) -> "Config":
        """Build a config bound to the named profile."""
        return cls(profile=get_profile(profile_name))

    # ----- validation --------------------------------------------------------

    def validate(self) -> List[str]:
        """Validate provider config and required profile inputs."""
        issues = validate_provider_config(self.api)
        if not self.paths.QUESTIONS_CSV.exists():
            issues.append(f"Questions CSV not found at {self.paths.QUESTIONS_CSV}")
        return issues

    def validate_llm_access(self) -> List[str]:
        """Validate just provider/LLM access (for scripts that don't need RLM)."""
        return validate_provider_config(self.api)

    def validate_question_answering(self) -> List[str]:
        """Validate everything required to run the RLM-backed question loop."""
        issues: List[str] = []
        if not self.paths.QUESTIONS_CSV.exists():
            issues.append(f"Questions CSV not found at {self.paths.QUESTIONS_CSV}")
        issues.extend(self.rlm.validate(self.paths.DATA_DIR))
        return issues

    # ----- helper accessors --------------------------------------------------

    def get_data_files(self, pattern: str) -> List[Path]:
        return shared_get_data_files(self.paths.DATA_DIR, pattern)

    def get_most_recent_file(self, pattern: str) -> Path:
        return shared_get_most_recent_file(self.paths.DATA_DIR, pattern)

    def get_review_files(self, patterns: Optional[List[str]] = None) -> List[Path]:
        """Resolve glob-based review files (operational-style profiles only)."""
        if self.profile.rlm_review_globs is None:
            raise ValueError(
                f"Profile '{self.profile.name}' uses filesystem review paths, "
                "not glob-based review files"
            )
        return _resolve_globs(
            self.paths.DATA_DIR, patterns or self.profile.rlm_review_globs
        )

    def run_rlm_query(
        self, query: str, review_paths: Optional[List[Path]] = None
    ) -> str:
        """Run the RLM CLI against the configured evidence source."""
        if review_paths is not None:
            paths = review_paths
        elif self.profile.rlm_review_paths is not None:
            paths = list(self.profile.rlm_review_paths)
        else:
            paths = self.get_review_files()

        if not paths:
            raise ValueError(
                f"No RLM review targets configured for profile '{self.profile.name}'"
            )

        return shared_run_rlm_query(
            command=self.rlm.COMMAND,
            review_paths=paths,
            timeout_seconds=self.rlm.TIMEOUT_SECONDS,
            query=query,
        )

    def get_redaction_function(self) -> Callable[[str, Optional[List[str]]], str]:
        """Return the configured redaction function."""
        return self.redaction.get_redaction_function()


__all__ = [
    "APIConfig",
    "Config",
    "CSVConfig",
    "LayerProfile",
    "OutputConfig",
    "PromptsConfig",
    "ProfilePathConfig",
    "ProfileRedactionConfig",
    "RLMConfig",
    "EXISTENTIAL_PROFILE",
    "OPERATIONAL_PROFILE",
    "get_profile",
    "list_profiles",
    "register_profile",
]
