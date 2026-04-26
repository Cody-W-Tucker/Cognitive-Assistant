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

import os
import subprocess
from pathlib import Path
from typing import List, Optional, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv

from prompt_loader import load_prompt

# Load environment variables
load_dotenv()

@dataclass
class APIConfig:
    """API and LLM configuration settings."""

    # LLM Provider selection
    LLM_PROVIDER: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "xai"))
    TEMPERATURE: float = 1.0

    # Unified Provider Metadata
    PROVIDERS = {
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "initial_model": os.getenv("OPENAI_INITIAL_MODEL", os.getenv("OPENAI_MODEL", "gpt-5.5")),
            "refine_model": os.getenv("OPENAI_REFINE_MODEL", os.getenv("OPENAI_MODEL", "gpt-5.5")),
            "model": os.getenv("OPENAI_MODEL", "gpt-5.5"),
            "MAX_TOKENS": int(os.getenv("OPENAI_CONTEXT_WINDOW", "400000")),
            "MAX_COMPLETION_TOKENS": int(os.getenv("OPENAI_MAX_OUTPUT", "128000")),
        },
        "xai": {
            "api_key": os.getenv("XAI_API_KEY", ""),
            "initial_model": os.getenv("XAI_INITIAL_MODEL", "grok-4-fast"),
            "refine_model": os.getenv("XAI_REFINE_MODEL", "grok-4"),
            "model": os.getenv("XAI_MODEL", "grok-4"),  # fallback
            "MAX_TOKENS": int(os.getenv("XAI_CONTEXT_WINDOW", "2000000")),
            "MAX_COMPLETION_TOKENS": int(os.getenv("XAI_MAX_OUTPUT", "30000")),
            "base_url": "https://api.x.ai/v1",
        },
        "anthropic": {
            "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
            "initial_model": os.getenv("ANTHROPIC_INITIAL_MODEL", os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")),
            "refine_model": os.getenv("ANTHROPIC_REFINE_MODEL", os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")),
            "model": os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5"),
            "MAX_TOKENS": int(os.getenv("ANTHROPIC_CONTEXT_WINDOW", "200000")),
            "MAX_COMPLETION_TOKENS": int(os.getenv("ANTHROPIC_MAX_OUTPUT", "64000")),
        },
    }

    def get_model(self, purpose: str = "default", provider: Optional[str] = None) -> str:
        """Return the configured model for the given provider and purpose."""
        provider = provider or self.LLM_PROVIDER
        provider_config = self.PROVIDERS.get(provider, {})

        if purpose == "initial":
            return str(provider_config.get("initial_model") or provider_config.get("model", "unknown"))
        if purpose == "refine":
            return str(provider_config.get("refine_model") or provider_config.get("model", "unknown"))

        return str(provider_config.get("model", "unknown"))

    @property
    def MAX_COMPLETION_TOKENS(self) -> int:
        """Get max output tokens for the current LLM provider."""
        return self.PROVIDERS.get(self.LLM_PROVIDER, {}).get(
            "MAX_COMPLETION_TOKENS", 3000
        )

    @property
    def MAX_TOKENS(self) -> int:
        """Get context window for the current LLM provider."""
        return self.PROVIDERS.get(self.LLM_PROVIDER, {}).get("MAX_TOKENS", 50000)

    def create_client(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        async_mode: bool = False,
    ) -> tuple[Any, Optional[str]]:
        """Unified client factory with error catching."""
        provider = provider or self.LLM_PROVIDER
        config = self.PROVIDERS.get(provider)

        if not config:
            raise ValueError(f"Unsupported provider: {provider}")

        # Use provided model, or default from config
        if model is None:
            model = config.get("model", "")
        if not model:
            model = "unknown"

        try:
            if provider in ["openai", "xai"]:
                from openai import AsyncOpenAI, OpenAI

                client_cls = AsyncOpenAI if async_mode else OpenAI
                client = client_cls(
                    api_key=config["api_key"], base_url=config.get("base_url")
                )

                return client, str(model)

            elif provider == "anthropic":
                from anthropic import Anthropic, AsyncAnthropic

                client_cls = AsyncAnthropic if async_mode else Anthropic
                return client_cls(api_key=config["api_key"]), str(model)

            raise ValueError(f"Unsupported provider: {provider}")

        except ImportError:
            pkg = "anthropic" if provider == "anthropic" else "openai"
            raise ImportError(
                f"{pkg.capitalize()} package not installed. Run: pip install {pkg}"
            )
        except Exception as e:
            if "401" in str(e) or "invalid" in str(e).lower():
                env_key = f"{provider.upper()}_API_KEY"
                raise ValueError(
                    f"Authentication failed. Check {env_key} in your .env file"
                )
            raise

class PathConfig:
    """File path and directory configuration.

    You can add new paths here, they're automatically created.

    Usage:
    from config import config
    config.paths.DATA_DIR
    """

    def __init__(self):
        """Build all paths relative to the project root."""
        self.BASE_DIR = Path(__file__).parent

        # =================================================================
        # PATH DEFINITIONS - Add new paths here, they're automatically created
        # =================================================================

        paths = {
            # Private datasets and collected information
            "DATA_DIR": "data",
            # Public generated artifacts from the workflow
            "ARTIFACTS_DIR": "artifacts",
            # Generated OpenCode-style skills
            "SKILLS_DIR": "artifacts/skills",
            # Reusable prompt components
            "PROMPTS_DIR": "prompts",
            # Runtime prompt templates loaded directly by scripts
            "PROMPT_RUNTIME_DIR": "prompts/runtime",
            # User interview questions
            "QUESTIONS_CSV": "questions.csv",
        }

        # Build all paths automatically
        for attr_name, path_str in paths.items():
            path = self.BASE_DIR / path_str
            setattr(self, attr_name, path)

        # Set the annotated attributes
        self.DATA_DIR = self.DATA_DIR
        self.ARTIFACTS_DIR = self.ARTIFACTS_DIR
        self.SKILLS_DIR = self.SKILLS_DIR
        self.PROMPTS_DIR = self.PROMPTS_DIR
        self.PROMPT_RUNTIME_DIR = self.PROMPT_RUNTIME_DIR
        self.QUESTIONS_CSV = self.QUESTIONS_CSV

    def ensure_directories_exist(self):
        """Ensure all necessary directories exist."""
        # Auto-detect directories (anything ending in _DIR)
        directories = [
            getattr(self, attr_name)
            for attr_name in dir(self)
            if attr_name.endswith("_DIR") and not attr_name.startswith("_")
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


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
    paths: PathConfig = field(default_factory=PathConfig)
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
        issues = []

        # Check API keys based on selected provider
        provider = self.api.LLM_PROVIDER
        config = self.api.PROVIDERS.get(provider)

        if not config:
            issues.append(
                f"Invalid LLM_PROVIDER '{provider}'. Must be one of: {', '.join(self.api.PROVIDERS.keys())}"
            )
        else:
            if not config.get("api_key"):
                issues.append(
                    f"{provider.upper()}_API_KEY not found in environment (required for LLM_PROVIDER={provider})"
                )

        # Check required files
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
    if not config.paths.DATA_DIR.exists():
        return []
    return list(config.paths.DATA_DIR.glob(pattern))


def get_most_recent_file(pattern: str) -> Path:
    """Get most recent file matching pattern."""
    files = get_data_files(pattern)
    if not files:
        raise FileNotFoundError(f"No files found matching pattern: {pattern}")
    return max(files, key=lambda f: f.stat().st_mtime)


def run_rlm_query(query: str, review_paths: Optional[List[Path]] = None) -> str:
    """Run the RLM CLI against the configured filesystem review targets."""
    paths = review_paths or config.rlm.REVIEW_PATHS
    if not paths:
        raise ValueError(
            "No RLM review paths configured. Add filesystem paths to RLMConfig.REVIEW_PATHS in config.py"
        )

    command = list(config.rlm.COMMAND)
    for path in paths:
        command.extend(["--file", str(path)])
    command.append(query)

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=config.rlm.TIMEOUT_SECONDS,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip() or "RLM command failed without stderr output"
        raise RuntimeError(stderr)

    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError("RLM returned empty output")

    return stdout


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
