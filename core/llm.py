#!/usr/bin/env python3
"""Model calls for the bootstrap pipeline: one prompt in, one text reply out.

Providers are configured from the environment (``.env`` is loaded):
``<PROVIDER>_API_KEY``, ``<PROVIDER>_MODEL`` and ``<PROVIDER>_MAX_OUTPUT``.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()

DEFAULT_PROVIDER = "anthropic"
TEMPERATURE = 1.0

_DEFAULT_MODELS = {"openai": "gpt-5.6-sol", "xai": "grok-4.5", "anthropic": "claude-opus-4-8"}
_BASE_URLS = {"xai": "https://api.x.ai/v1"}
PROVIDERS = tuple(_DEFAULT_MODELS)

_FENCE = re.compile(r"```[A-Za-z]*\s*\n?([\s\S]*?)\s*```")


def model_name(provider: str) -> str:
    return os.getenv(f"{provider.upper()}_MODEL", _DEFAULT_MODELS[provider])


def _max_output(provider: str) -> int:
    return int(os.getenv(f"{provider.upper()}_MAX_OUTPUT", "128_000"))


def missing_config(provider: str) -> List[str]:
    """What stops ``provider`` from being called, as messages (empty when ready)."""
    if provider not in PROVIDERS:
        return [f"Invalid provider '{provider}'. Must be one of: {', '.join(PROVIDERS)}"]
    if not os.getenv(f"{provider.upper()}_API_KEY"):
        return [f"{provider.upper()}_API_KEY not found in environment (required for provider={provider})"]
    return []


def strip_fence(text: str) -> str:
    """Remove one code fence wrapping the whole reply; fences inside it stay."""
    stripped = text.strip()
    match = _FENCE.fullmatch(stripped)
    return match.group(1).strip() if match else stripped


def _client(provider: str) -> Any:
    api_key = os.getenv(f"{provider.upper()}_API_KEY", "")
    if provider == "anthropic":
        from anthropic import AsyncAnthropic

        return AsyncAnthropic(api_key=api_key)
    from openai import AsyncOpenAI

    return AsyncOpenAI(api_key=api_key, base_url=_BASE_URLS.get(provider))


async def _generate(client: Any, provider: str, prompt: str, max_tokens: int) -> str:
    model = model_name(provider)
    if provider == "anthropic":
        parts: List[str] = []
        async with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            temperature=TEMPERATURE,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text in stream.text_stream:
                parts.append(text)
        return "".join(parts)
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=TEMPERATURE,
        max_completion_tokens=max_tokens,
    )
    choice = response.choices[0].message if response.choices else None
    return str(choice.content or "") if choice else ""


async def complete(
    prompt: str,
    *,
    provider: str = DEFAULT_PROVIDER,
    min_chars: int = 1,
    label: str = "reply",
) -> str:
    """Send one prompt and return the reply without a wrapping code fence.

    Raises ``ValueError`` when the reply is shorter than ``min_chars``, so a
    truncated or failed generation is never written as an artifact.
    """
    client = _client(provider)
    try:
        text = strip_fence(await _generate(client, provider, prompt, _max_output(provider)))
    finally:
        await client.close()
    if len(text) < min_chars:
        raise ValueError(f"{label} from {provider} is unexpectedly short ({len(text)} chars)")
    return text


def parse_json_object(text: str, *, label: str) -> Dict[str, str]:
    """Parse a reply that must be one JSON object of strings."""
    try:
        parsed = json.loads(strip_fence(text))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse {label} JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} payload must be a JSON object")
    return {str(key): str(value) for key, value in parsed.items()}
