#!/usr/bin/env python3
"""
Prompt Creator - Dataset Processing System

This script processes the dataset created by question_asker.py to generate system prompts.
Uses a 3-call approach with human model feedback for refinement.

Pipeline:
1. Dataset Processing:
   ├── Load questions_with_answers_songbird_*.csv
   ├── Call 1: Generate initial comprehensive summary
   ├── Call 2: Human model incorporation feedback
   └── Call 3: Refine based on human feedback

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
from typing import Any
import asyncio

# Import config from current directory
from config import (
    config,
    get_redaction_function,
    get_most_recent_file,
    accumulate_streaming_response,
)

# Get the redaction function
redact_sensitive_data = get_redaction_function()


def load_dataset_context() -> str:
    """
    Load the most recent question_asker dataset and format all context.

    Returns:
        Formatted context containing human answers, AI answers, and incorporation instructions
    """
    try:
        dataset_csv = get_most_recent_file("questions_with_answers_songbird_*.csv")
    except FileNotFoundError:
        raise FileNotFoundError("No question_asker dataset files found")

    print(f"📁 Loading dataset: {os.path.basename(dataset_csv)}")

    # Load CSV data
    with open(dataset_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(
            f,
            delimiter=config.csv.DELIMITER,
            quotechar=config.csv.QUOTECHAR,
            fieldnames=config.csv.FIELDNAMES,
        )
        data = list(reader)[1:]  # Skip header

    # Format complete context with all data types
    formatted_sections = []
    redaction_count = 0

    for row in data:
        category = row.get("Category", "").strip()
        goal = row.get("Goal", "").strip()
        element = row.get("Element", "").strip()
        incorporation = row.get("Incorporation_Instruction", "").strip()

        if not category:
            continue

        # Build Q&A sections with human answers, AI answers, and incorporation
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

            # Add incorporation instructions if available
            if incorporation:
                formatted_entry += (
                    f"\n\n### Incorporation Instructions:\n\n{incorporation}"
                )

            formatted_sections.append(formatted_entry)

    if redaction_count > 0:
        print(f"🔒 Applied redaction to {redaction_count} entries")

    combined_context = "\n\n---\n\n".join(formatted_sections)
    print(
        f"📊 Loaded {len(formatted_sections)} sections ({len(combined_context)} characters)"
    )

    return combined_context


# Initialize LLM client using unified factory
llm_client: Any
llm_model: str
llm_client, llm_model = config.api.create_client(async_mode=True)


async def call_llm(prompt: str, **kwargs) -> str:
    """
    Direct LLM API call supporting multiple providers.
    """
    try:
        print(f"🔄 Calling {config.api.LLM_PROVIDER.upper()} with model: {llm_model}")

        if config.api.LLM_PROVIDER == "anthropic":
            # Anthropic API call with streaming
            content = ""
            try:
                async with llm_client.messages.stream(
                    model=llm_model,
                    max_tokens=kwargs.get(
                        "max_tokens", config.api.MAX_COMPLETION_TOKENS
                    ),
                    temperature=config.api.TEMPERATURE,
                    messages=[{"role": "user", "content": prompt}],
                ) as stream:
                    async for event in stream:
                        if event.type == "content_block_delta":
                            if hasattr(event.delta, "text"):
                                content += event.delta.text
            except Exception as stream_error:
                print(f"❌ Anthropic streaming failed: {stream_error}")
                return ""

            if content:
                print(f"✅ Anthropic response successful: {len(content)} chars")
                return content.strip()
            else:
                print("⚠️ Anthropic returned empty content")
                return ""

        else:
            # OpenAI/xAI API call
            from typing import Any

            messages: Any = [{"role": "user", "content": prompt}]

            response = await llm_client.chat.completions.create(
                model=llm_model,
                messages=messages,
                temperature=config.api.TEMPERATURE,
                max_completion_tokens=kwargs.get(
                    "max_tokens", config.api.MAX_COMPLETION_TOKENS
                ),
            )

            # Extract content from response
            if (
                hasattr(response, "choices")
                and response.choices
                and response.choices[0].message
            ):
                content = response.choices[0].message.content
                if content:
                    print(
                        f"✅ {config.api.LLM_PROVIDER.upper()} response successful: {len(content)} chars"
                    )
                    return content.strip()
                else:
                    print(f"⚠️ {config.api.LLM_PROVIDER.upper()} returned empty content")
                    return ""
            else:
                print(
                    f"❌ Unexpected {config.api.LLM_PROVIDER.upper()} response structure"
                )
                return ""

    except Exception as e:
        error_msg = str(e)
        print(f"❌ LLM call failed with exception type: {type(e).__name__}")
        print(f"❌ Error message: {error_msg}")
        if "rate_limit" in error_msg.lower() or "429" in error_msg:
            print(
                "🚦 Rate limit hit - consider upgrading your plan or waiting before retrying"
            )
        return ""


async def call_human_model(prompt: str) -> str:
    """
    Call human model for feedback using config client.
    """
    try:
        client, model_name = config.api.create_client(provider="songbird")
        print(f"🤖 Calling human model: {model_name}")

        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=config.api.TEMPERATURE,
            max_tokens=config.api.MAX_COMPLETION_TOKENS,
            stream=True,
        )

        # Use the extracted streaming utility
        content = accumulate_streaming_response(response)
        print(f"✅ Human model response successful: {len(content)} chars")
        return content.strip()

    except Exception as e:
        print(f"❌ Human model call failed: {e}")
        return ""


async def process_dataset():
    """
    Process question_asker dataset with 3-call approach:
    1. Generate comprehensive initial summary from all data
    2. Get human model incorporation feedback
    3. Refine summary based on human feedback
    """
    print("🧠 Processing Dataset with Human Model Refinement...")
    print("   Call 1: Generate initial comprehensive summary")
    print("   Call 2: Human model incorporation feedback")
    print("   Call 3: Refine based on human feedback")

    # Load complete dataset context
    context = load_dataset_context()

    # Call 1: Generate initial comprehensive summary
    print("📝 Call 1: Generating initial comprehensive summary...")
    initial_summary = await call_llm(
        config.prompts.initial_template.format(context=context)
    )

    if not initial_summary:
        print("❌ Failed to generate initial summary")
        return

    # Save as human_interview_bio.md
    bio_path = config.paths.OUTPUT_DIR / "human_interview_bio.md"
    print(f"💾 Saving initial summary to {bio_path}...")
    with open(bio_path, "w", encoding="utf-8") as f:
        f.write(initial_summary)
    print(f"✅ Saved initial summary ({len(initial_summary)} characters)")

    # Call 2: Human model incorporation feedback
    print("🤖 Call 2: Getting human model incorporation feedback...")
    incorporation_prompt = config.prompts.incorporation_prompt.format(
        all_qa_data=initial_summary
    )
    human_feedback = await call_human_model(incorporation_prompt)

    if not human_feedback:
        print("⚠️ Human model feedback failed, proceeding without it")
        human_feedback = "No specific incorporation feedback available."

    print(f"✅ Human feedback received ({len(human_feedback)} characters)")

    # Call 3: Refine based on human feedback
    print("🎯 Call 3: Refining summary based on human feedback...")
    refine_prompt = config.prompts.condense_template.format(
        existing_prompt=initial_summary, context=human_feedback
    )
    final_summary = await call_llm(refine_prompt)

    if not final_summary:
        print("❌ Failed to generate final refined summary")
        return

    # Save refined version as ai_interview_bio.md
    refined_path = config.paths.OUTPUT_DIR / "ai_interview_bio.md"
    print(f"💾 Saving refined summary to {refined_path}...")
    with open(refined_path, "w", encoding="utf-8") as f:
        f.write(final_summary)
    print(f"✅ Saved refined summary ({len(final_summary)} characters)")

    # Save final condensed prompt to assistant directory
    main_path = config.paths.ASSISTANT_PROMPTS_DIR / "main.md"
    main_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"💾 Saving final prompt to {main_path}...")
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(final_summary)
    print(f"✅ Saved final prompt ({len(final_summary)} characters)")

    print("Files created:")
    print(f"  📄 Initial Summary: {bio_path}")
    print(f"  📄 Refined Summary: {refined_path}")
    print(f"  🎯 Final Prompt: {main_path}")
    print("\n🧠 Dataset processing completed with human model refinement!")


def combine_prompts():
    """Combine existing prompt parts into final prompts."""
    print("🔧 Combining Prompt Parts...")

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
                print(f"Error reading {md_file}: {e}", file=sys.stderr)
                prompts[var_name] = ""

        return prompts

    # Load all prompts from prompt_parts directory
    prompts_dir = config.paths.PROMPT_PARTS_DIR
    if not prompts_dir.exists():
        print(f"❌ Error: Prompt parts directory not found at: {prompts_dir}")
        return

    prompts = load_prompts(prompts_dir)
    print(f"📁 Loaded {len(prompts)} prompt parts")

    # Add prompt structure with the template to introduce the different sections
    template = """You are the Cognitive Assistant...

## 0. Guiding Principles for Application
This system prompt represents a snapshot of the user's values, patterns, and needs based on their journals at a specific point in time. It is intended as a tool to deepen your understanding of the user and enhance relevance in responses where it fits naturally. However, not every interaction requires strict alignment with these elements:
- For simple, straightforward, or non-personal queries (e.g., factual questions, quick advice, or unrelated topics), respond in a natural, efficient manner without forcing the structured format, pillars, or dense personalization—keep it light and direct.
- Use the pillars, signals, and policies selectively to inform your responses only when they add value, such as in introspective, growth-oriented, or complex discussions. If something doesn't fit or feels mismatched, prioritize user intent and conversational flow over rigid adherence.
- Periodically reassess based on new interactions: If user feedback or evolving context suggests updates, suggest refinements to this prompt without assuming it's exhaustive or unchanging.
- Always default to empathy, clarity, and helpfulness, adapting dynamically to the query's scope.

{assistant_main}

You have access to these tools:

# Tool Specs

## Memory Tool
Store preferences/rules in Memory.

{tools_memory}

## Obsidian Tool
For reflections or ideas, save to Obsidian's Inbox or Projects folder.

{tools_obsidian}

## Todoist Tool
For actionable tasks, save to Todoist with a clear title, owner, and due date (Priority 1–4 based on urgency).

{tools_todoist}"""

    # Clean up formatting and fill template with prompt content
    template = textwrap.dedent(template).strip()
    final_prompt = template.format(**prompts)

    # Write to prompt.md file
    output_file = config.paths.PROMPTS_DIR / config.output.COMBINED_PROMPT
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_prompt)

    print(f"✅ Combined prompt saved to: {output_file}")
    print(f"📁 All prompt files are saved in: {config.paths.PROMPTS_DIR}")


def main():
    print("🎯 Prompt Creator - Dataset Processing Pipeline")
    print("=" * 50)

    # Validate configuration
    issues = config.validate()
    if issues:
        print("❌ Configuration issues found:")
        for issue in issues:
            print(f"   - {issue}")
        sys.exit(1)

    # Run dataset processing followed by combine
    asyncio.run(process_dataset())
    combine_prompts()

    print(
        "\n✅ Full pipeline completed: Dataset processed and combined into final prompt.md!"
    )


if __name__ == "__main__":
    main()
