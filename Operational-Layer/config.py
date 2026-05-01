#!/usr/bin/env python3
"""Centralized configuration for Operational Layer scripts."""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from prompt_loader import load_prompt


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


class OperationalPathConfig(PathConfig):
    """File path and directory configuration."""

    def __init__(self) -> None:
        paths = {
            "DATA_DIR": "data",
            "INTAKE_DIR": "data/intake",
            "READY_DIR": "data/ready",
            "ARTIFACTS_DIR": "artifacts",
            "SKILLS_DIR": "artifacts/skills",
            "PROMPTS_DIR": "prompts",
            "PROMPT_RUNTIME_DIR": "prompts/runtime",
            "QUESTIONS_CSV": "questions.csv",
        }

        super().__init__(Path(__file__).parent, paths)


@dataclass
class RLMConfig:
    """RLM CLI configuration and operational artifact targets."""

    COMMAND: List[str] = field(default_factory=lambda: ["rlm"])
    REVIEW_GLOBS: List[str] = field(
        default_factory=lambda: ["ready/**/*.jsonl"]
    )
    TIMEOUT_SECONDS: int = 300


@dataclass
class CSVConfig:
    """CSV parsing and processing configuration."""

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


@dataclass
class OperationalRedactionConfig(RedactionConfig):
    """Sensitive data redaction configuration for operational artifacts."""

    SENSITIVE_PATTERNS: List[str] = field(
        default_factory=lambda: [
            r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",
            r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        ]
    )


@dataclass
class PromptsConfig:
    """All system prompts and LLM prompts used across scripts."""

    synthesis_prompt: str = field(
        default_factory=lambda: load_prompt("synthesis_prompt")
    )
    initial_template: str = field(
        default_factory=lambda: load_prompt("initial_template")
    )
    refine_template: str = field(default_factory=lambda: load_prompt("refine_template"))
    skills_creation_template: str = field(
        default_factory=lambda: load_prompt("skills_creation_template")
    )
    rlm_query_template: str = field(
        default_factory=lambda: load_prompt("rlm_query_template")
    )


@dataclass
class OutputConfig:
    """Output file naming and formatting configuration."""

    QUESTIONS_WITH_ANSWERS_PATTERN: str = "questions_with_answers_rlm_{timestamp}.csv"
    TIMESTAMP_FORMAT: str = "%Y%m%d_%H%M%S"


@dataclass
class Config:
    """Main configuration class containing all settings."""

    api: APIConfig = field(default_factory=APIConfig)
    paths: OperationalPathConfig = field(default_factory=OperationalPathConfig)
    rlm: RLMConfig = field(default_factory=RLMConfig)
    csv: CSVConfig = field(default_factory=CSVConfig)
    redaction: OperationalRedactionConfig = field(
        default_factory=OperationalRedactionConfig
    )
    prompts: PromptsConfig = field(default_factory=PromptsConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    def __post_init__(self) -> None:
        self.paths.ensure_directories_exist()

    def validate(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = validate_provider_config(self.api)
        if not self.paths.QUESTIONS_CSV.exists():
            issues.append(f"Questions CSV not found at {self.paths.QUESTIONS_CSV}")

        return issues

    def validate_question_answering(self) -> List[str]:
        """Validate configuration needed specifically for the RLM-backed question flow."""
        issues = []
        if not self.paths.QUESTIONS_CSV.exists():
            issues.append(f"Questions CSV not found at {self.paths.QUESTIONS_CSV}")
        if not get_review_files():
            issues.append(
                "No operational artifact files matched the configured REVIEW_GLOBS in config.py"
            )
        return issues


config = Config()


def get_redaction_function():
    """Get configured redaction function."""
    return config.redaction.get_redaction_function()


def get_data_files(pattern: str) -> List[Path]:
    """Get list of data files matching a glob pattern recursively."""
    return shared_get_data_files(config.paths.DATA_DIR, pattern)


def get_most_recent_file(pattern: str) -> Path:
    """Get most recent file matching pattern."""
    return shared_get_most_recent_file(config.paths.DATA_DIR, pattern)


def get_review_files(patterns: Optional[List[str]] = None) -> List[Path]:
    """Resolve the operational artifact files that should be reviewed by RLM."""
    resolved_files: List[Path] = []
    seen_paths: set[Path] = set()
    for pattern in patterns or config.rlm.REVIEW_GLOBS:
        for file_path in sorted(config.paths.DATA_DIR.glob(pattern)):
            if file_path.is_file() and file_path not in seen_paths:
                seen_paths.add(file_path)
                resolved_files.append(file_path)
    return resolved_files


def run_rlm_query(query: str, review_paths: Optional[List[Path]] = None) -> str:
    """Run the RLM CLI against the configured operational artifact targets."""
    paths = review_paths or get_review_files()
    if not paths:
        raise ValueError(
            "No RLM review files configured. Add glob patterns to RLMConfig.REVIEW_GLOBS in config.py"
        )
    return shared_run_rlm_query(
        command=config.rlm.COMMAND,
        review_paths=paths,
        timeout_seconds=config.rlm.TIMEOUT_SECONDS,
        query=query,
    )


__all__ = [
    "config",
    "get_redaction_function",
    "get_data_files",
    "get_most_recent_file",
    "get_review_files",
    "Config",
    "APIConfig",
    "PathConfig",
    "RLMConfig",
    "CSVConfig",
    "RedactionConfig",
    "PromptsConfig",
    "OutputConfig",
    "run_rlm_query",
]
