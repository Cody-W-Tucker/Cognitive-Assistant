#!/usr/bin/env python3
"""
Prompt Creator - Dataset Processing System

This script processes the dataset created by question_asker.py to generate system prompts.
Uses a 2-call approach for refinement.

Pipeline:
1. Dataset Processing:
   ├── Load questions_with_answers_rlm_*.csv
   ├── Call 1: Generate initial comprehensive summary
   └── Call 2: Refine the summary

2. Combine:
   └── prompt.md                # Combined final prompt from parts

Usage:
    python prompt_creator.py  # Runs full pipeline automatically

All files are saved to output/ and prompts/ directories.
"""

import os
import sys
import csv
from pathlib import Path
import asyncio

# Import config from current directory
from config import (
    config,
    get_redaction_function,
    get_most_recent_file,
)
from llm import LLMHandle, create_client, generate_text_async
from prompt_loader import load_prompt

# Get the redaction function
redact_sensitive_data = get_redaction_function()


def load_dataset_context() -> str:
    """
    Load the most recent question_asker dataset and format all context.

    Returns:
        Formatted context containing human answers and AI answers
    """
    try:
        dataset_csv = get_most_recent_file("questions_with_answers_rlm_*.csv")
    except FileNotFoundError:
        raise FileNotFoundError("No question_asker dataset files found")

    print(f"Info: Loading dataset {os.path.basename(dataset_csv)}")

    # Load CSV data
    with open(dataset_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(
            f,
            delimiter=config.csv.DELIMITER,
            quotechar=config.csv.QUOTECHAR,
        )
        data = list(reader)

    # Format complete context from the latest RLM dataset
    formatted_sections = []
    redaction_count = 0

    for row in data:
        category = row.get("Category", "").strip()
        goal = row.get("Goal", "").strip()
        element = row.get("Element", "").strip()

        if not category:
            continue

        # Build Q&A sections with human answers and AI answers
        qa_sections = []

        for i, (q_col, h_col, a_col) in enumerate(
            zip(
                config.csv.QUESTION_COLUMNS,
                config.csv.HUMAN_ANSWER_COLUMNS,
                config.csv.ANSWER_COLUMNS,
            )
        ):
            question = row.get(q_col, "").strip()
            human_answer = row.get(h_col, "").strip()
            ai_answer = row.get(a_col, "").strip()

            if question and (human_answer or ai_answer):
                # Apply redaction to sensitive content
                redacted_human = redact_sensitive_data(human_answer)
                redacted_ai = redact_sensitive_data(ai_answer)
                if redacted_human != human_answer or redacted_ai != ai_answer:
                    redaction_count += 1

                qa_sections.append(
                    f"{i+1}. {question}\n\n   Human Answer: {redacted_human}\n\n   AI Answer: {redacted_ai}"
                )

        if qa_sections:
            formatted_entry = f"# Understanding: **{category}**\n\n"
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

    except Exception as e:
        error_msg = str(e)
        print(f"Error: LLM call failed with exception type {type(e).__name__}")
        print(f"Error: {error_msg}")
        if "rate_limit" in error_msg.lower() or "429" in error_msg:
            print("Warning: Rate limit hit; wait before retrying or adjust provider limits")
        return ""





async def process_dataset():
    """
    Process question_asker dataset with 2-call approach:
    1. Generate comprehensive initial summary from all data
    2. Refine the summary
    """
    print("Info: Processing dataset with refinement")
    print("Info: Step 1 generates the initial summary")
    print("Info: Step 2 refines the summary")

    # Load complete dataset context
    context = load_dataset_context()

    initial_client = create_client(
        config.api, model=config.api.get_model("initial"), async_mode=True
    )
    refine_client = create_client(
        config.api, model=config.api.get_model("refine"), async_mode=True
    )

    # Call 1: Generate initial comprehensive summary
    print("Info: Generating initial comprehensive summary")
    initial_summary = await call_llm(
        initial_client, config.prompts.initial_template.format(context=context)
    )

    if not initial_summary:
        print("Error: Failed to generate initial summary")
        return

    # Save as human_interview_bio.md
    bio_path = config.paths.OUTPUT_DIR / "human_interview_bio.md"
    print(f"Info: Saving initial summary to {bio_path}")
    with open(bio_path, "w", encoding="utf-8") as f:
        f.write(initial_summary)
    print(f"Info: Saved initial summary ({len(initial_summary)} characters)")

    # Call 2: Refine the summary
    print("Info: Refining summary")
    refine_prompt = config.prompts.refine_template.format(
        existing_answer=initial_summary, context=""
    )
    final_summary = await call_llm(refine_client, refine_prompt)

    if not final_summary:
        print("Error: Failed to generate final refined summary")
        return

    # Save refined version as ai_interview_bio.md
    refined_path = config.paths.OUTPUT_DIR / "ai_interview_bio.md"
    print(f"Info: Saving refined summary to {refined_path}")
    with open(refined_path, "w", encoding="utf-8") as f:
        f.write(final_summary)
    print(f"Info: Saved refined summary ({len(final_summary)} characters)")

    # Save final condensed prompt to assistant directory
    main_path = config.paths.ASSISTANT_PROMPTS_DIR / "main.md"
    main_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Info: Saving final prompt to {main_path}")
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(final_summary)
    print(f"Info: Saved final prompt ({len(final_summary)} characters)")

    print("Info: Files created")
    print(f"- Initial summary: {bio_path}")
    print(f"- Refined summary: {refined_path}")
    print(f"- Final prompt: {main_path}")
    print("Info: Dataset processing completed")


def combine_prompts():
    """Combine existing prompt parts into final prompts."""
    print("Info: Combining prompt parts")

    import textwrap

    def load_prompts(prompts_dir):
        """Load all prompt files into a dictionary."""
        prompts = {}

        # Find all .md files recursively
        for md_file in Path(prompts_dir).rglob("*.md"):
            # Create variable name from path
            rel_path = md_file.relative_to(prompts_dir)
            var_name = (
                str(rel_path).replace(".md", "").replace("/", "_").replace("-", "_")
            )

            # Read file content
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    prompts[var_name] = f.read().strip()
            except Exception as e:
                print(f"Error: Failed to read {md_file}: {e}", file=sys.stderr)
                prompts[var_name] = ""

        return prompts

    # Load all prompts from prompt_parts directory
    prompts_dir = config.paths.PROMPT_PARTS_DIR
    if not prompts_dir.exists():
        print(f"Error: Prompt parts directory not found at {prompts_dir}")
        return

    prompts = load_prompts(prompts_dir)
    print(f"Info: Loaded {len(prompts)} prompt parts")

    # Add prompt structure with the template to introduce the different sections
    template = load_prompt("combined_prompt_template")

    # Clean up formatting and fill template with prompt content
    template = textwrap.dedent(template).strip()
    final_prompt = template.format(**prompts)

    # Write to prompt.md file
    output_file = config.paths.PROMPTS_DIR / config.output.COMBINED_PROMPT
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_prompt)

    print(f"Info: Combined prompt saved to {output_file}")
    print(f"Info: All prompt files are saved in {config.paths.PROMPTS_DIR}")


def main():
    print("Prompt Creator - Dataset Processing Pipeline")
    print("=" * 50)

    # Validate configuration
    issues = config.validate()
    if issues:
        print("Error: Configuration issues found")
        for issue in issues:
            print(f"- {issue}")
        sys.exit(1)

    # Run dataset processing followed by combine
    asyncio.run(process_dataset())
    combine_prompts()

    print(
        "\nInfo: Full pipeline completed; dataset processed and combined into final prompt.md"
    )


if __name__ == "__main__":
    main()
