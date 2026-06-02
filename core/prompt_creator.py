#!/usr/bin/env python3
"""Profile-aware prompt creator.

Loads the most recent `questions_with_answers_rlm_*.csv` from the active
profile's data directory, formats it into context, and writes
`human_profile.md`.
"""

from __future__ import annotations

import asyncio
import csv
import os
import sys
from dataclasses import dataclass
from typing import List

from core.config import Config
from lib.config import validate_provider_config
from lib.llm import LLMHandle, close_client_async, create_client, generate_text_async


ENSEMBLE_DRAFT_PROVIDERS = ("xai", "anthropic", "openai")
ENSEMBLE_SYNTHESIS_PROVIDER = "anthropic"


@dataclass(frozen=True)
class DraftResult:
    """One model's draft profile output."""

    provider: str
    model: str
    content: str


def load_dataset_context(config: Config) -> str:
    """Load the most recent dataset and format all context for the LLM."""
    try:
        dataset_csv = config.get_most_recent_file("questions_with_answers_rlm_*.csv")
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            "No question_asker dataset files found in "
            f"{config.paths.DATA_DIR}"
        ) from exc

    print(f"Info: Loading dataset {os.path.basename(dataset_csv)}")

    with open(dataset_csv, "r", encoding="utf-8") as file_handle:
        reader = csv.DictReader(
            file_handle,
            delimiter=config.csv.DELIMITER,
            quotechar=config.csv.QUOTECHAR,
        )
        data = list(reader)

    redact = config.get_redaction_function()
    section_template = config.profile.section_header_template
    answer_label = config.profile.answer_label
    formatted_sections: List[str] = []
    redaction_count = 0

    for row in data:
        category = row.get("Category", "").strip()
        goal = row.get("Goal", "").strip()
        element = row.get("Element", "").strip()

        if not category:
            continue

        qa_sections: List[str] = []

        iter_columns = list(zip(config.csv.QUESTION_COLUMNS, config.csv.ANSWER_COLUMNS))

        for index, columns in enumerate(iter_columns, start=1):
            question_col, answer_col = columns
            question = row.get(question_col, "").strip()
            answer = row.get(answer_col, "").strip()

            if not question or not answer:
                continue

            redacted_answer = redact(answer)
            if redacted_answer != answer:
                redaction_count += 1

            qa_sections.append(
                f"{index}. {question}\n\n   {answer_label}: {redacted_answer}"
            )

        if qa_sections:
            entry = section_template.format(category=category) + "\n\n"
            entry += f"## Goal: **{goal}**\n\n"
            entry += f"**Elements:** {element}\n\n"
            entry += "### Questions:\n\n" + "\n\n".join(qa_sections)
            formatted_sections.append(entry)

    if redaction_count > 0:
        print(f"Info: Applied redaction to {redaction_count} entries")

    combined_context = "\n\n---\n\n".join(formatted_sections)
    print(
        f"Info: Loaded {len(formatted_sections)} sections "
        f"({len(combined_context)} characters)"
    )
    return combined_context


async def _call_llm(
    config: Config, handle: LLMHandle, prompt: str, max_tokens: int = None
) -> str:
    """Generate text for a prompt using the shared async helper."""
    try:
        print(f"Info: Calling {handle.provider.upper()} with model {handle.model}")
        content = await generate_text_async(
            handle,
            user_prompt=prompt,
            temperature=config.api.TEMPERATURE,
            max_output_tokens=max_tokens or config.api.MAX_COMPLETION_TOKENS,
        )
        print(
            f"Info: {handle.provider.upper()} response successful "
            f"({len(content)} chars)"
        )
        return content
    except Exception as exc:
        error_message = str(exc)
        print(f"Error: LLM call failed with exception type {type(exc).__name__}")
        print(f"Error: {error_message}")
        if "rate_limit" in error_message.lower() or "429" in error_message:
            print(
                "Warning: Rate limit hit; wait before retrying or adjust provider limits"
            )
        return ""


def get_prompt_creator_providers() -> List[str]:
    """Return the distinct providers required by the ensemble workflow."""
    return list(dict.fromkeys([*ENSEMBLE_DRAFT_PROVIDERS, ENSEMBLE_SYNTHESIS_PROVIDER]))


def validate_prompt_creator_config(config: Config) -> List[str]:
    """Validate the inputs and providers required by build-prompts."""
    issues: List[str] = []
    if not config.paths.QUESTIONS_CSV.exists():
        issues.append(f"Questions CSV not found at {config.paths.QUESTIONS_CSV}")

    original_provider = config.api.LLM_PROVIDER
    try:
        for provider in get_prompt_creator_providers():
            config.api.LLM_PROVIDER = provider
            issues.extend(validate_provider_config(config.api))
    finally:
        config.api.LLM_PROVIDER = original_provider

    return list(dict.fromkeys(issues))


async def _generate_draft(config: Config, provider: str, prompt: str) -> DraftResult:
    """Generate one draft profile from a specific provider."""
    handle = create_client(
        config.api,
        provider=provider,
        model=config.api.get_model("initial", provider=provider),
        async_mode=True,
    )

    try:
        content = await _call_llm(
            config,
            handle,
            prompt,
            max_tokens=config.api.get_max_completion_tokens(provider),
        )
        return DraftResult(provider=provider, model=handle.model, content=content)
    finally:
        await close_client_async(handle)


def _build_candidate_profiles_block(draft_results: List[DraftResult]) -> str:
    """Serialize candidate drafts for the synthesis prompt."""
    draft_blocks = []
    for result in draft_results:
        draft_blocks.append(
            "\n".join(
                [
                    f'<candidate provider="{result.provider}" model="{result.model}">',
                    result.content.strip(),
                    "</candidate>",
                ]
            )
        )

    return "\n\n".join(draft_blocks)


def _save_draft_artifacts(config: Config, draft_results: List[DraftResult]) -> None:
    """Persist candidate drafts without interfering with downstream human_profile discovery."""
    for result in draft_results:
        draft_path = config.paths.ARTIFACTS_DIR / f"profile_candidate_{result.provider}.md"
        print(f"Info: Saving {result.provider.upper()} draft to {draft_path}")
        draft_path.write_text(result.content.strip() + "\n", encoding="utf-8")


async def _process_dataset(config: Config) -> int:
    """Run the profile-specific prompt generation pipeline."""
    print("Info: Processing dataset into profile artifacts")
    print("Info: Step 1 generates ensemble draft profiles")

    context = load_dataset_context(config)
    base_prompt = config.prompts.initial_template.format(context=context)

    draft_results = await asyncio.gather(
        *[
            _generate_draft(config, provider, base_prompt)
            for provider in ENSEMBLE_DRAFT_PROVIDERS
        ]
    )
    successful_drafts = [result for result in draft_results if result.content]
    if len(successful_drafts) != len(ENSEMBLE_DRAFT_PROVIDERS):
        failed_providers = [
            provider
            for provider in ENSEMBLE_DRAFT_PROVIDERS
            if provider not in {result.provider for result in successful_drafts}
        ]
        print(
            "Error: Failed to generate all ensemble drafts: "
            + ", ".join(failed_providers)
        )
        return 1

    _save_draft_artifacts(config, successful_drafts)

    print("Info: Step 2 synthesizes the drafts with Anthropic")
    synthesis_handle = create_client(
        config.api,
        provider=ENSEMBLE_SYNTHESIS_PROVIDER,
        model=config.api.get_model("refine", provider=ENSEMBLE_SYNTHESIS_PROVIDER),
        async_mode=True,
    )
    try:
        synthesis_prompt = _build_synthesis_prompt(
            config,
            candidate_profiles=_build_candidate_profiles_block(successful_drafts),
        )
        final_profile = await _call_llm(
            config,
            synthesis_handle,
            synthesis_prompt,
            max_tokens=config.api.get_max_completion_tokens(ENSEMBLE_SYNTHESIS_PROVIDER),
        )
        if not final_profile:
            print("Error: Failed to synthesize final profile")
            return 1

        profile_path = config.paths.ARTIFACTS_DIR / "human_profile.md"
        print(f"Info: Saving synthesized profile to {profile_path}")
        profile_path.write_text(final_profile.strip() + "\n", encoding="utf-8")

        print("Info: Artifacts created")
        print(f"- Human profile: {profile_path}")
        for result in successful_drafts:
            print(
                f"- Candidate draft: {config.paths.ARTIFACTS_DIR / ('profile_candidate_' + result.provider + '.md')}"
            )
        return 0
    finally:
        await close_client_async(synthesis_handle)


def _build_synthesis_prompt(config: Config, *, candidate_profiles: str) -> str:
    """Render the profile-specific ensemble synthesis prompt template."""
    return config.prompts.ensemble_synthesis_template.format(
        candidate_profiles=candidate_profiles,
    )


def run(config: Config) -> int:
    """Synchronous entry point for CLI use."""
    print(f"{config.profile.display_name} - Prompt Creator")
    print("=" * 60)

    issues = validate_prompt_creator_config(config)
    if issues:
        print("Error: Configuration issues found")
        for issue in issues:
            print(f"- {issue}")
        return 1

    try:
        return asyncio.run(_process_dataset(config))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


__all__ = ["run", "load_dataset_context"]
