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
from config import config
from llm import LLMHandle, create_client, generate_text
from prompt_loader import load_prompt


def get_baseline_system_prompt() -> str:
    """Get the baseline system prompt for general human-like responses."""
    return load_prompt("baseline_system_prompt")


def ask_baseline_question(handle: LLMHandle, question: str) -> str:
    """Send a question to the model and get a baseline human-like response."""
    try:
        system_prompt = get_baseline_system_prompt().format(question=question)

        return generate_text(
            handle,
            system_prompt=system_prompt,
            user_prompt=question,
            temperature=config.api.TEMPERATURE,
            max_output_tokens=config.api.MAX_TOKENS,
        )

    except Exception as e:
        print(f"Warning: Error calling baseline API: {e}")
        return f"Error: {str(e)}"


def main():
    # Validate configuration
    issues = config.validate()
    if issues:
        print("Error: Configuration issues found")
        for issue in issues:
            print(f"- {issue}")
        sys.exit(1)

    # Set up model client (using unified factory)
    print(f"Info: Using LLM provider {config.api.LLM_PROVIDER}")
    try:
        handle = create_client(config.api)
        model_name = handle.model
        print(f"Info: Connected to {handle.provider} API (model {model_name})")
    except Exception as e:
        print(f"Error: Failed to set up client: {e}")
        sys.exit(1)

    # Set up file paths from config
    questions_file = config.paths.QUESTIONS_CSV

    # Check if input file exists
    if not questions_file.exists():
        print(f"Error: Questions file not found at {questions_file}")
        return

    # Create timestamped output file in the same folder as this script
    timestamp = datetime.now().strftime(config.output.TIMESTAMP_FORMAT)
    from pathlib import Path
    baselines_dir = Path(__file__).parent
    output_filename = f"{model_name}_answers_{timestamp}.csv"
    output_file = baselines_dir / output_filename

    # Read the CSV file
    print(f"Info: Reading questions from {questions_file}")
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
        f"\nInfo: Starting to process {total_questions} questions with baseline responses"
    )

    for index, row in df.iterrows():
        for question_col, answer_col in question_pairs:
            if question_col in df.columns:  # Check if question column exists
                old_answer = df.at[index, answer_col]
                if pd.isna(old_answer):  # Only process if answer is empty
                    query = str(row[question_col])

                    print(f"Info: Processing baseline question: {query[:60]}...")

                    # Retry logic for failed API calls
                    max_retries = 3
                    base_delay = 1
                    response = ""
                    for attempt in range(max_retries):
                        response = ask_baseline_question(handle, query)
                        if not response.startswith("Error:"):
                            break
                        if attempt < max_retries - 1:
                            delay = base_delay * (2**attempt)
                            print(
                                f"Warning: API call failed, retrying in {delay}s (attempt {attempt+1}/{max_retries})"
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
                    print(f"Info: Processed {processed_count}/{total_questions} questions")

                    # Save after each answer to prevent data loss
                    df.to_csv(
                        str(output_file),
                        index=False,
                        sep=config.csv.DELIMITER,
                        quotechar=config.csv.QUOTECHAR,
                        quoting=csv.QUOTE_MINIMAL,
                    )

    print(
        f"\nInfo: Completed processing {processed_count} questions; saved to {output_file}"
    )


if __name__ == "__main__":
    main()
