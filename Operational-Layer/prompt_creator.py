#!/usr/bin/env python3
"""Prompt creator for operational datasets."""

import asyncio
import csv
import os
import sys

from config import config, get_most_recent_file, get_redaction_function
from llm import LLMHandle, create_client, generate_text_async


redact_sensitive_data = get_redaction_function()


def load_dataset_context() -> str:
    """Load the most recent operational dataset and format all context."""
    try:
        dataset_csv = get_most_recent_file("questions_with_answers_rlm_*.csv")
    except FileNotFoundError as exc:
        raise FileNotFoundError("No operational question_asker dataset files found") from exc

    print(f"Info: Loading dataset {os.path.basename(dataset_csv)}")

    with open(dataset_csv, "r", encoding="utf-8") as file_handle:
        reader = csv.DictReader(
            file_handle,
            delimiter=config.csv.DELIMITER,
            quotechar=config.csv.QUOTECHAR,
        )
        data = list(reader)

    formatted_sections = []
    redaction_count = 0

    for row in data:
        category = row.get("Category", "").strip()
        goal = row.get("Goal", "").strip()
        element = row.get("Element", "").strip()

        if not category:
            continue

        qa_sections = []
        for index, (question_col, answer_col) in enumerate(
            zip(config.csv.QUESTION_COLUMNS, config.csv.ANSWER_COLUMNS), start=1
        ):
            question = row.get(question_col, "").strip()
            answer = row.get(answer_col, "").strip()

            if question and answer:
                redacted_answer = redact_sensitive_data(answer)
                if redacted_answer != answer:
                    redaction_count += 1

                qa_sections.append(f"{index}. {question}\n\n   Operational Answer: {redacted_answer}")

        if qa_sections:
            formatted_entry = f"# Operational Category: **{category}**\n\n"
            formatted_entry += f"## Goal: **{goal}**\n\n"
            formatted_entry += f"**Elements:** {element}\n\n"
            formatted_entry += "### Questions:\n\n" + "\n\n".join(qa_sections)
            formatted_sections.append(formatted_entry)

    if redaction_count > 0:
        print(f"Info: Applied redaction to {redaction_count} entries")

    combined_context = "\n\n---\n\n".join(formatted_sections)
    print(
        f"Info: Loaded {len(formatted_sections)} sections ({len(combined_context)} characters)"
    )
    return combined_context


async def call_llm(handle: LLMHandle, prompt: str, **kwargs) -> str:
    """Generate text for a prompt using the shared async LLM helper."""
    try:
        print(f"Info: Calling {handle.provider.upper()} with model {handle.model}")
        content = await generate_text_async(
            handle,
            user_prompt=prompt,
            temperature=config.api.TEMPERATURE,
            max_output_tokens=kwargs.get("max_tokens", config.api.MAX_COMPLETION_TOKENS),
        )
        print(f"Info: {handle.provider.upper()} response successful ({len(content)} chars)")
        return content
    except Exception as exc:
        error_message = str(exc)
        print(f"Error: LLM call failed with exception type {type(exc).__name__}")
        print(f"Error: {error_message}")
        return ""


async def process_dataset() -> None:
    """Process operational dataset with a 2-call profile and prompt flow."""
    print("Info: Processing operational dataset with refinement")
    print("Info: Step 1 generates the operational profile")
    print("Info: Step 2 refines the profile into a system prompt")

    context = load_dataset_context()

    initial_client = create_client(
        config.api, model=config.api.get_model("initial"), async_mode=True
    )
    refine_client = create_client(
        config.api, model=config.api.get_model("refine"), async_mode=True
    )

    initial_summary = await call_llm(
        initial_client, config.prompts.initial_template.format(context=context)
    )
    if not initial_summary:
        print("Error: Failed to generate initial summary")
        return

    profile_path = config.paths.ARTIFACTS_DIR / "human_profile.md"
    print(f"Info: Saving initial summary to {profile_path}")
    profile_path.write_text(initial_summary.strip() + "\n", encoding="utf-8")

    refine_prompt = config.prompts.refine_template.format(
        existing_answer=initial_summary,
        context="",
    )
    final_summary = await call_llm(refine_client, refine_prompt)
    if not final_summary:
        print("Error: Failed to generate final refined summary")
        return

    system_prompt_path = config.paths.ARTIFACTS_DIR / "system_prompt.md"
    print(f"Info: Saving refined summary to {system_prompt_path}")
    system_prompt_path.write_text(final_summary.strip() + "\n", encoding="utf-8")

    print("Info: Artifacts created")
    print(f"- Initial summary: {profile_path}")
    print(f"- Refined summary: {system_prompt_path}")


def main() -> None:
    """CLI entrypoint for operational profile generation."""
    print("Operational Prompt Creator - Dataset Processing Pipeline")
    print("=" * 60)

    issues = config.validate()
    if issues:
        print("Error: Configuration issues found")
        for issue in issues:
            print(f"- {issue}")
        sys.exit(1)

    asyncio.run(process_dataset())
    print("\nInfo: Operational pipeline completed; artifacts written to artifacts/")


if __name__ == "__main__":
    main()
