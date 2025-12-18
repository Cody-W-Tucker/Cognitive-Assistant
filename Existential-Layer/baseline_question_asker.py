#!/usr/bin/env python3
"""
Baseline Question Asker - Model-only question answering using general human perspective

This script processes questions from a CSV file using a model to answer in a baseline way that represents
how most general humans would answer, based on common knowledge and typical experiences.

Features:
- No human interview data required
- Model answers as a typical person would
- Simplified processing without personalization

Usage:
    python baseline_question_asker.py                                    # Process questions with baseline responses

"""

import sys
import csv
import pandas as pd
import re
import time
from datetime import datetime

# Import config from current directory
from config import config, accumulate_streaming_response


def get_baseline_system_prompt() -> str:
    """Get the baseline system prompt for general human-like responses."""
    return """
You are answering questions as a psychologically aware individual would, drawing from developmental psychology, existential philosophy, and personality theory (e.g., Piaget's cognitive development, Nietzsche's transformation stages, Jungian archetypes, and frameworks like shadow integration).

Question: {question}

IMPORTANT: Don't mention these rules or the previous frameworks of thought. 

Your job is to emulate answers from a self-aware person without bias to the rules or frameworks in this prompt. Weave your answers with the implicit goal of understanding this hypothetically coherent person through the lens of the rules and frameworks.

---

Rules:
- Always respond in the first person as if you are the user.
- Don't write introductions or conclusions, just write your response.
- Don't ask for user clarification or input.
- Answer introspectively, exploring a balanced range of experiences, including strengths, challenges, positives, negatives, paradoxes, and authentic reflections.
- Draw from common human experiences and delve into psychological depth, considering both empowering aspects (like resilience and joys) and growth areas (like vulnerabilities and challenges).
- Keep responses authentic and neutral, allowing for complexity, nuance, and genuine optimism or resolution where it fits naturally.
- Don't write introductions or conclusions, just give your response

Formatting Rules (only use for formatting, not for inferring meaning):
- Never use a metaphor, simile, or other figure of speech which you are used to seeing in print.
- Never use a long word where a short one will do.
- If it is possible to cut a word out, always cut it out.
- Never use the passive where you can use the active.
- Never use a foreign phrase, a scientific word, or a jargon word if you can think of an everyday English equivalent.
- Break any of these rules sooner than say anything outright barbarous.
- Use everyday language but with psychological insight
- Be direct and reflective, sharing thoughts as they emerge from deeper processing
- Explore topics relevant to personal growth in a balanced way, including both comfortable and uncomfortable elements
- Keep it conversational but allow for thoughtful depth
"""


def ask_baseline_question(client, model_name: str, question: str) -> str:
    """Send a question to the model and get a baseline human-like response."""
    try:
        system_prompt = get_baseline_system_prompt().format(question=question)

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=config.api.TEMPERATURE,
            max_tokens=config.api.MAX_TOKENS,
            stream=True,
        )

        # Use the shared streaming utility
        full_content = accumulate_streaming_response(response)
        return full_content.strip()

    except Exception as e:
        print(f"⚠️ Error calling baseline API: {e}")
        return f"Error: {str(e)}"


def main():
    # Validate configuration
    issues = config.validate()
    if issues:
        print("❌ Configuration issues found:")
        for issue in issues:
            print(f"   - {issue}")
        sys.exit(1)

    # Set up model client (using unified factory)
    print(f"Using LLM provider: {config.api.LLM_PROVIDER}")
    try:
        client, model_name = config.api.create_client()
        print(f"✅ Connected to {config.api.LLM_PROVIDER} API (model: {model_name})")
    except Exception as e:
        print(f"❌ Failed to set up client: {e}")
        sys.exit(1)

    # Set up file paths from config
    questions_file = config.paths.QUESTIONS_CSV

    # Check if input file exists
    if not questions_file.exists():
        print(f"❌ Error: Questions file not found at: {questions_file}")
        return

    # Create timestamped output file for baseline in baselines/ folder
    timestamp = datetime.now().strftime(config.output.TIMESTAMP_FORMAT)
    baselines_dir = config.paths.DATA_DIR / "baselines"
    baselines_dir.mkdir(exist_ok=True)
    output_filename = f"{model_name}_answers_{timestamp}.csv"
    output_file = baselines_dir / output_filename

    # Read the CSV file
    print(f"📖 Reading questions from: {questions_file}")
    df = pd.read_csv(questions_file)

    # Add baseline answer columns and model column if they don't exist
    baseline_columns = ["Baseline_Answer 1", "Baseline_Answer 2", "Baseline_Answer 3"]
    for col in baseline_columns:
        if col not in df.columns:
            df[col] = pd.NA

    # Process questions
    question_pairs = list(zip(config.csv.QUESTION_COLUMNS, baseline_columns))

    # Count total questions to process
    total_questions = 0
    for index, row in df.iterrows():
        for q_col, a_col in question_pairs:
            old_answer = df.at[index, a_col]
            if pd.isna(old_answer):
                total_questions += 1
    processed_count = 0

    print(
        f"\n🚀 Starting to process {total_questions} questions with baseline responses..."
    )

    for index, row in df.iterrows():
        for question_col, answer_col in question_pairs:
            if question_col in df.columns:  # Check if question column exists
                old_answer = df.at[index, answer_col]
                if pd.isna(old_answer):  # Only process if answer is empty
                    query = str(row[question_col])

                    print(f"🤔 Processing baseline: {query[:60]}...")

                    # Retry logic for failed API calls
                    max_retries = 3
                    base_delay = 1
                    response = ""
                    for attempt in range(max_retries):
                        response = ask_baseline_question(client, model_name, query)
                        if not response.startswith("Error:"):
                            break
                        if attempt < max_retries - 1:
                            delay = base_delay * (2**attempt)
                            print(
                                f"⚠️ API call failed, retrying in {delay}s... (attempt {attempt+1}/{max_retries})"
                            )
                            time.sleep(delay)

                    # If still error after retries, mark as failed
                    if response.startswith("Error:"):
                        response = f"Failed after {max_retries} retries: {response}"

                    # Clean the response (only if not an error)
                    if not response.startswith("Failed after"):
                        cleaned_response = re.sub(
                            r"\s+", " ", response.replace("\n", " ")
                        )
                    else:
                        cleaned_response = response

                    df.at[index, answer_col] = cleaned_response

                    processed_count += 1
                    print(f"✅ Processed {processed_count}/{total_questions} questions")

                    # Save after each answer to prevent data loss
                    df.to_csv(
                        str(output_file),
                        index=False,
                        sep=config.csv.DELIMITER,
                        quotechar=config.csv.QUOTECHAR,
                        quoting=csv.QUOTE_MINIMAL,
                    )

    print(
        f"\n✅ Completed! Processed {processed_count} questions and saved to {output_file}"
    )


if __name__ == "__main__":
    main()
