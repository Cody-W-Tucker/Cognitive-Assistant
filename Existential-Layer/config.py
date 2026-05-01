#!/usr/bin/env python3
"""
Centralized Configuration for Layer Scripts

This file contains all shared configurations, prompts, and settings used across
the Layer scripts to eliminate duplication and enable easier maintenance.

Usage:
    from config import config
    client, model = config.api.create_client()
    prompt = config.prompts.initial_template
"""

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

class ExistentialPathConfig(PathConfig):
    """File path and directory configuration.

    You can add new paths here, they're automatically created.

    Usage:
    from config import config
    config.paths.DATA_DIR
    """

    def __init__(self):
        """Build all paths relative to the project root."""
        paths = {
            "DATA_DIR": "data",
            "ARTIFACTS_DIR": "artifacts",
            "SKILLS_DIR": "artifacts/skills",
            "PROMPTS_DIR": "prompts",
            "PROMPT_RUNTIME_DIR": "prompts/runtime",
            "QUESTIONS_CSV": "questions.csv",
        }
        super().__init__(Path(__file__).parent, paths)


@dataclass
class RLMConfig:
    """RLM CLI configuration and filesystem review targets."""

    COMMAND: List[str] = field(default_factory=lambda: ["rlm"])
    REVIEW_PATHS: List[Path] = field(
        default_factory=lambda: [
            Path("/home/codyt/Knowledge/Personal/Journal"),
            Path("/home/codyt/Knowledge/Personal/Knowledge"),
        ]
    )
    TIMEOUT_SECONDS: int = 300

    def validate_review_paths(self) -> List[str]:
        """Validate configured RLM review targets."""
        issues = []

        if not self.REVIEW_PATHS:
            issues.append(
                "RLM review paths are not configured. Add filesystem paths to RLMConfig.REVIEW_PATHS in config.py"
            )
            return issues

        for path in self.REVIEW_PATHS:
            if not path.exists():
                issues.append(f"RLM review path does not exist: {path}")

        return issues


@dataclass
class CSVConfig:
    """CSV parsing and processing configuration."""

    DELIMITER: str = ","
    QUOTECHAR: str = '"'
    FIELDNAMES: List[str] = field(
        default_factory=lambda: [
            "Category",
            "Goal",
            "Element",
            "Question 1",
            "Question 2",
            "Question 3",
            "Human_Answer 1",
            "Human_Answer 2",
            "Human_Answer 3",
            "AI_Answer 1",
            "AI_Answer 2",
            "AI_Answer 3",
        ]
    )
    ANSWER_COLUMNS: List[str] = field(
        default_factory=lambda: ["AI_Answer 1", "AI_Answer 2", "AI_Answer 3"]
    )
    QUESTION_COLUMNS: List[str] = field(
        default_factory=lambda: ["Question 1", "Question 2", "Question 3"]
    )
    HUMAN_ANSWER_COLUMNS: List[str] = field(
        default_factory=lambda: ["Human_Answer 1", "Human_Answer 2", "Human_Answer 3"]
    )
    # Columns used to create category keys for matching questions to answers
    CATEGORY_KEY_COLUMNS: List[str] = field(
        default_factory=lambda: ["Category", "Goal", "Element"]
    )


@dataclass
class RedactionConfig:
    """Sensitive data redaction configuration."""

    SENSITIVE_PATTERNS: List[str] = field(
        default_factory=lambda: [
            # Names (common patterns)
            r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",  # Full names
        ]
    )

    def get_redaction_function(self):
        """Return a redaction function configured with the patterns."""
        import re

        def redact_sensitive_data(
            text: str, custom_patterns: Optional[List[str]] = None
        ) -> str:
            """
            Redact sensitive information from text using configured patterns.

            Args:
                text: The text to redact
                custom_patterns: Optional additional regex patterns to redact
            """
            patterns = self.SENSITIVE_PATTERNS.copy()
            if custom_patterns:
                patterns.extend(custom_patterns)

            redacted_text = text
            for pattern in patterns:
                redacted_text = re.sub(pattern, "[REDACTED]", redacted_text)

            return redacted_text

        return redact_sensitive_data


@dataclass
class PromptsConfig:
    """All system prompts and LLM prompts used across scripts."""

    synthesis_prompt: str = field(default_factory=lambda: load_prompt("synthesis_prompt"))
    initial_template: str = field(default_factory=lambda: load_prompt("initial_template"))
    refine_template: str = field(default_factory=lambda: load_prompt("refine_template"))
    skills_creation_template: str = field(
        default_factory=lambda: load_prompt("skills_creation_template")
    )
    rlm_query_template: str = field(default_factory=lambda: load_prompt("rlm_query_template"))
    rlm_query_template_filesystem_only: str = field(
        default_factory=lambda: load_prompt("rlm_query_template_filesystem_only")
    )


@dataclass
class OutputConfig:
    """Output file naming and formatting configuration."""

    # Output file naming patterns
    QUESTIONS_WITH_ANSWERS_PATTERN: str = "questions_with_answers_rlm_{timestamp}.csv"
    HUMAN_INTERVIEW_PATTERN: str = "human_interview_{timestamp}.csv"

    # Timestamp format
    TIMESTAMP_FORMAT: str = "%Y%m%d_%H%M%S"


@dataclass
class Config:
    """Main configuration class containing all settings."""

    api: APIConfig = field(default_factory=APIConfig)
    paths: ExistentialPathConfig = field(default_factory=ExistentialPathConfig)
    rlm: RLMConfig = field(default_factory=RLMConfig)
    csv: CSVConfig = field(default_factory=CSVConfig)
    redaction: RedactionConfig = field(default_factory=RedactionConfig)
    prompts: PromptsConfig = field(default_factory=PromptsConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    def __post_init__(self):
        """Initialize configuration and ensure directories exist."""
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

        return issues + self.rlm.validate_review_paths()


# Create global config instance
config = Config()


# Convenience functions for common operations
def get_redaction_function():
    """Get configured redaction function."""
    return config.redaction.get_redaction_function()


def get_data_files(pattern: str) -> List[Path]:
    """Get list of data files matching pattern."""
    return shared_get_data_files(config.paths.DATA_DIR, pattern)


def get_most_recent_file(pattern: str) -> Path:
    """Get most recent file matching pattern."""
    return shared_get_most_recent_file(config.paths.DATA_DIR, pattern)


def run_rlm_query(query: str, review_paths: Optional[List[Path]] = None) -> str:
    """Run the RLM CLI against the configured filesystem review targets."""
    paths = review_paths or config.rlm.REVIEW_PATHS
    if not paths:
        raise ValueError(
            "No RLM review paths configured. Add filesystem paths to RLMConfig.REVIEW_PATHS in config.py"
        )
    return shared_run_rlm_query(
        command=config.rlm.COMMAND,
        review_paths=paths,
        timeout_seconds=config.rlm.TIMEOUT_SECONDS,
        query=query,
    )


# Export key functions and classes for easy importing
__all__ = [
    "config",
    "get_redaction_function",
    "get_data_files",
    "get_most_recent_file",
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
