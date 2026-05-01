#!/usr/bin/env python3
"""Shared configuration primitives for layer pipelines."""

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, List, Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass
class APIConfig:
    """API and LLM configuration settings."""

    LLM_PROVIDER: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "xai"))
    TEMPERATURE: float = 1.0

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
            "model": os.getenv("XAI_MODEL", "grok-4"),
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
        return self.PROVIDERS.get(self.LLM_PROVIDER, {}).get("MAX_COMPLETION_TOKENS", 3000)

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
        provider_config = self.PROVIDERS.get(provider)

        if not provider_config:
            raise ValueError(f"Unsupported provider: {provider}")

        if model is None:
            model = provider_config.get("model", "")
        if not model:
            model = "unknown"

        try:
            if provider in ["openai", "xai"]:
                from openai import AsyncOpenAI, OpenAI

                client_cls = AsyncOpenAI if async_mode else OpenAI
                client = client_cls(
                    api_key=provider_config["api_key"],
                    base_url=provider_config.get("base_url"),
                )
                return client, str(model)

            if provider == "anthropic":
                from anthropic import Anthropic, AsyncAnthropic

                client_cls = AsyncAnthropic if async_mode else Anthropic
                return client_cls(api_key=provider_config["api_key"]), str(model)

            raise ValueError(f"Unsupported provider: {provider}")
        except ImportError:
            package = "anthropic" if provider == "anthropic" else "openai"
            raise ImportError(
                f"{package.capitalize()} package not installed. Run: pip install {package}"
            )
        except Exception as exc:
            if "401" in str(exc) or "invalid" in str(exc).lower():
                env_key = f"{provider.upper()}_API_KEY"
                raise ValueError(
                    f"Authentication failed. Check {env_key} in your .env file"
                )
            raise


class PathConfig:
    """File path and directory configuration."""

    def __init__(self, base_dir: Path, paths: dict[str, str]) -> None:
        self.BASE_DIR = base_dir
        for attr_name, path_str in paths.items():
            setattr(self, attr_name, self.BASE_DIR / path_str)

    def ensure_directories_exist(self) -> None:
        """Ensure all necessary directories exist."""
        directories = [
            getattr(self, attr_name)
            for attr_name in dir(self)
            if attr_name.endswith("_DIR") and not attr_name.startswith("_")
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


@dataclass
class RedactionConfig:
    """Sensitive data redaction configuration."""

    SENSITIVE_PATTERNS: List[str] = field(
        default_factory=lambda: [r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b"]
    )

    def get_redaction_function(self):
        """Return a redaction function configured with the patterns."""

        def redact_sensitive_data(
            text: str, custom_patterns: Optional[List[str]] = None
        ) -> str:
            patterns = self.SENSITIVE_PATTERNS.copy()
            if custom_patterns:
                patterns.extend(custom_patterns)

            redacted_text = text
            for pattern in patterns:
                redacted_text = re.sub(pattern, "[REDACTED]", redacted_text)

            return redacted_text

        return redact_sensitive_data


def validate_provider_config(api_config: APIConfig) -> List[str]:
    """Validate provider selection and API key presence."""
    issues = []
    provider = api_config.LLM_PROVIDER
    provider_config = api_config.PROVIDERS.get(provider)

    if not provider_config:
        issues.append(
            f"Invalid LLM_PROVIDER '{provider}'. Must be one of: {', '.join(api_config.PROVIDERS.keys())}"
        )
    elif not provider_config.get("api_key"):
        issues.append(
            f"{provider.upper()}_API_KEY not found in environment (required for LLM_PROVIDER={provider})"
        )

    return issues


def get_data_files(data_dir: Path, pattern: str) -> List[Path]:
    """Get list of data files matching a glob pattern."""
    if not data_dir.exists():
        return []
    return list(data_dir.glob(pattern))


def get_most_recent_file(data_dir: Path, pattern: str) -> Path:
    """Get the most recent file matching a glob pattern."""
    files = get_data_files(data_dir, pattern)
    if not files:
        raise FileNotFoundError(f"No files found matching pattern: {pattern}")
    return max(files, key=lambda file_path: file_path.stat().st_mtime)


def run_rlm_query(
    *,
    command: List[str],
    review_paths: Iterable[Path],
    timeout_seconds: int,
    query: str,
) -> str:
    """Run the RLM CLI against a collection of review targets."""
    resolved_paths = list(review_paths)
    if not resolved_paths:
        raise ValueError("No RLM review targets were provided")

    full_command = list(command)
    for path in resolved_paths:
        full_command.extend(["--file", str(path)])
    full_command.append(query)

    result = subprocess.run(
        full_command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip() or "RLM command failed without stderr output"
        raise RuntimeError(stderr)

    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError("RLM returned empty output")

    return stdout
