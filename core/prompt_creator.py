#!/usr/bin/env python3
"""Profile-aware prompt creator.

Loads the most recent `questions_with_answers_rlm_*.csv` from the active
profile's data directory, formats it into context (with human answers if the
profile carries them), and runs the 2-call refinement pipeline:

  1. initial_template -> human_profile.md
  2. refine_template  -> system_prompt.md
"""

from __future__ import annotations

import asyncio
import csv
import os
import sys
from typing import List

from core import adaptation_rules
from core.config import Config
from lib.llm import LLMHandle, close_client_async, create_client, generate_text_async


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
    include_human = config.profile.include_human_answers

    formatted_sections: List[str] = []
    redaction_count = 0

    for row in data:
        category = row.get("Category", "").strip()
        goal = row.get("Goal", "").strip()
        element = row.get("Element", "").strip()

        if not category:
            continue

        qa_sections: List[str] = []

        if include_human:
            iter_columns = list(
                zip(
                    config.csv.QUESTION_COLUMNS,
                    config.csv.HUMAN_ANSWER_COLUMNS,
                    config.csv.ANSWER_COLUMNS,
                )
            )
        else:
            iter_columns = list(
                zip(config.csv.QUESTION_COLUMNS, config.csv.ANSWER_COLUMNS)
            )

        for index, columns in enumerate(iter_columns, start=1):
            if include_human:
                question_col, human_col, answer_col = columns
                question = row.get(question_col, "").strip()
                human_answer = row.get(human_col, "").strip()
                ai_answer = row.get(answer_col, "").strip()

                if not question or (not human_answer and not ai_answer):
                    continue

                redacted_human = redact(human_answer)
                redacted_ai = redact(ai_answer)
                if redacted_human != human_answer or redacted_ai != ai_answer:
                    redaction_count += 1

                qa_sections.append(
                    f"{index}. {question}\n\n"
                    f"   Human Answer: {redacted_human}\n\n"
                    f"   {answer_label}: {redacted_ai}"
                )
            else:
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


async def _process_dataset(config: Config) -> int:
    """Run the 2-call refinement pipeline."""
    print("Info: Processing dataset with refinement")
    print("Info: Step 1 generates the initial profile")
    print("Info: Step 2 refines the profile into a system prompt")

    context = load_dataset_context(config)
    active_adaptations = adaptation_rules.active_adaptations(config)
    overlay = adaptation_rules.render_rule_overlay(active_adaptations)
    skill_adaptations_path = adaptation_rules.write_skill_adaptations(
        config, active_adaptations
    )
    print(f"Info: Wrote skill adaptations to {skill_adaptations_path}")
    if overlay:
        context = f"{context}\n\n{overlay}"
        rules_path = adaptation_rules.write_rules_overlay(config, active_adaptations)
        if rules_path is not None:
            print(f"Info: Wrote adaptation rules overlay to {rules_path}")

    initial_client = create_client(
        config.api, model=config.api.get_model("initial"), async_mode=True
    )
    refine_client = create_client(
        config.api, model=config.api.get_model("refine"), async_mode=True
    )

    try:
        initial_summary = await _call_llm(
            config,
            initial_client,
            config.prompts.initial_template.format(context=context),
        )
        if not initial_summary:
            print("Error: Failed to generate initial summary")
            return 1

        profile_path = config.paths.ARTIFACTS_DIR / "human_profile.md"
        print(f"Info: Saving initial summary to {profile_path}")
        profile_path.write_text(initial_summary.strip() + "\n", encoding="utf-8")

        refine_prompt = config.prompts.refine_template.format(
            existing_answer=initial_summary, context=overlay
        )
        final_summary = await _call_llm(config, refine_client, refine_prompt)
        if not final_summary:
            print("Error: Failed to generate final refined summary")
            return 1

        system_prompt_path = config.paths.ARTIFACTS_DIR / "system_prompt.md"
        print(f"Info: Saving refined summary to {system_prompt_path}")
        system_prompt_path.write_text(final_summary.strip() + "\n", encoding="utf-8")

        print("Info: Artifacts created")
        print(f"- Initial summary: {profile_path}")
        print(f"- Refined summary: {system_prompt_path}")
        captured_path = adaptation_rules.mark_adaptations_captured(
            config,
            [str(item.get("id")) for item in active_adaptations if item.get("id")],
            captured_in="build-prompts",
        )
        if captured_path is not None:
            print(f"Info: Updated crystallization artifact {captured_path}")
        return 0
    finally:
        await close_client_async(initial_client)
        await close_client_async(refine_client)


def run(config: Config) -> int:
    """Synchronous entry point for CLI use."""
    print(f"{config.profile.display_name} - Prompt Creator")
    print("=" * 60)

    issues = config.validate()
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
