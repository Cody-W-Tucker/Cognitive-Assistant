#!/usr/bin/env python3
"""Shared LLM client creation and text generation helpers."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class LLMHandle:
    """Resolved LLM client metadata used by scripts."""

    client: Any
    model: str
    provider: str
    async_mode: bool


def create_client(
    api_config: Any, model: Optional[str] = None, async_mode: bool = False
) -> LLMHandle:
    """Create a provider-specific client and retain provider metadata."""
    client, resolved_model = api_config.create_client(model=model, async_mode=async_mode)
    return LLMHandle(
        client=client,
        model=str(resolved_model or "unknown"),
        provider=api_config.LLM_PROVIDER,
        async_mode=async_mode,
    )


def generate_text(
    handle: LLMHandle,
    *,
    user_prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float,
    max_output_tokens: int,
) -> str:
    """Generate text using a synchronous client."""
    if handle.async_mode:
        raise ValueError("Synchronous generation requires async_mode=False")

    if handle.provider == "anthropic":
        kwargs: dict[str, Any] = {
            "model": handle.model,
            "max_tokens": max_output_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        response = handle.client.messages.create(
            **kwargs,
        )
        return _extract_anthropic_text(response)

    response = handle.client.chat.completions.create(
        model=handle.model,
        messages=_build_chat_messages(user_prompt, system_prompt),
        temperature=temperature,
        max_completion_tokens=max_output_tokens,
    )
    return _extract_openai_text(response)


async def generate_text_async(
    handle: LLMHandle,
    *,
    user_prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float,
    max_output_tokens: int,
) -> str:
    """Generate text using an asynchronous client."""
    if not handle.async_mode:
        raise ValueError("Asynchronous generation requires async_mode=True")

    if handle.provider == "anthropic":
        kwargs: dict[str, Any] = {
            "model": handle.model,
            "max_tokens": max_output_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        response = await handle.client.messages.create(**kwargs)
        return _extract_anthropic_text(response)

    response = await handle.client.chat.completions.create(
        model=handle.model,
        messages=_build_chat_messages(user_prompt, system_prompt),
        temperature=temperature,
        max_completion_tokens=max_output_tokens,
    )
    return _extract_openai_text(response)


def _build_chat_messages(
    user_prompt: str, system_prompt: Optional[str]
) -> list[dict[str, str]]:
    """Build an OpenAI-compatible message list."""
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    return messages


def _extract_openai_text(response: Any) -> str:
    """Extract message content from an OpenAI-compatible response."""
    if response.choices and response.choices[0].message and response.choices[0].message.content:
        return str(response.choices[0].message.content).strip()
    raise ValueError("Empty response from LLM")


def _extract_anthropic_text(response: Any) -> str:
    """Extract text blocks from an Anthropic response."""
    parts: list[str] = []
    for block in getattr(response, "content", []):
        text = getattr(block, "text", None)
        if text:
            parts.append(text)

    content = "".join(parts).strip()
    if content:
        return content
    raise ValueError("Empty response from LLM")
