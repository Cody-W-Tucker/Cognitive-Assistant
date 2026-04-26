#!/usr/bin/env python3
"""
Human Interview Asker - Personalized question answering using RLM file review

This script processes questions from a CSV file using the RLM CLI over configured
filesystem review paths, while preserving human interview context for personalization.

Features:
- Automatically loads the most recent human interview data for personalization
- Supports a human-seeded mode and a filesystem-only mode
- Defaults to human-seeded mode for downstream compatibility

Usage:
    python human_interview.py                                   # Run the interview process to be interviewed and create human answers
    python question_asker.py                                    # Human-seeded mode
    python question_asker.py --filesystem-only                  # Filesystem-only mode
"""

import argparse
import sys
import csv
import pandas as pd
import re
import time
from datetime import datetime

# Import config from current directory
from config import (
    config,
    get_most_recent_file,
    run_rlm_query,
)


def get_rlm_prompt(question: str, human_answer: str) -> str:
    """Build the prompt sent to RLM."""
    return config.prompts.rlm_query_template.format(
        synthesis_prompt=config.prompts.synthesis_prompt,
        question=question,
        human_answer=human_answer.strip() or "No human interview context provided.",
    )


def get_rlm_filesystem_only_prompt(question: str) -> str:
    """Build the filesystem-only prompt sent to RLM."""
    return config.prompts.rlm_query_template_filesystem_only.format(
        synthesis_prompt=config.prompts.synthesis_prompt,
        question=question,
    )


def ask_question(question: str, human_answer: str, include_human_answer: bool) -> str:
    """Send a question to RLM and return the synthesized response."""
    try:
        prompt = (
            get_rlm_prompt(question, human_answer)
            if include_human_answer
            else get_rlm_filesystem_only_prompt(question)
        )
        return run_rlm_query(prompt)

    except Exception as e:
        print(f"⚠️ Error calling RLM: {e}")
        return f"Error: {str(e)}"
def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--filesystem-only",
        action="store_true",
        help="Use only reviewed filesystem context and omit human interview context from the RLM prompt.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    include_human_answer = not args.filesystem_only

    # Validate configuration
    issues = config.validate_question_answering()
    if issues:
        print("❌ Configuration issues found:")
        for issue in issues:
            print(f"   - {issue}")
        sys.exit(1)

    print("📚 RLM review paths:")
    for review_path in config.rlm.REVIEW_PATHS:
        print(f"   - {review_path}")
    mode_label = "human-seeded" if include_human_answer else "filesystem-only"
    print(f"🧭 Question mode: {mode_label}")

    # Set up file paths from config
    questions_file = config.paths.QUESTIONS_CSV

    # Auto-detect latest human interview file
    try:
        human_interview_file = get_most_recent_file("human_interview_*.csv")
        print(f"Loaded {human_interview_file}")
    except FileNotFoundError:
        print("❌ No human interview files found in data directory")
        print("💡 Please run the human interview script first")
        sys.exit(1)

    # Check if input file exists
    if not questions_file.exists():
        print(f"❌ Error: Questions file not found at: {questions_file}")
        return

    # Create timestamped output file
    timestamp = datetime.now().strftime(config.output.TIMESTAMP_FORMAT)
    output_filename = config.output.QUESTIONS_WITH_ANSWERS_PATTERN.format(timestamp=timestamp)
    output_file = config.paths.DATA_DIR / output_filename

    # Load human interview data for personalization and downstream reporting
    try:
        human_interview_df = pd.read_csv(human_interview_file)
        if human_interview_df.shape[0] == 0:
            print("❌ Error: No human interview data loaded.")
            sys.exit(1)

        # Create lookup dictionary using CSVConfig column names
        human_interview_data = {}
        for _, row in human_interview_df.iterrows():
            category_key = "|".join(
                str(row[col]) for col in config.csv.CATEGORY_KEY_COLUMNS
            )
            answer_data = {}
            for col in config.csv.HUMAN_ANSWER_COLUMNS:
                answer_data[col] = (
                    str(row.get(col, "")).strip() if pd.notna(row.get(col, "")) else ""
                )
            human_interview_data[category_key] = answer_data

    except Exception as e:
        print(f"❌ Error loading human interview data: {e}")
        sys.exit(1)

    print(
        f"📖 Loaded {len(human_interview_data)} interview sections for personalization"
    )

    # Read the CSV file
    print(f"📖 Reading questions from: {questions_file}")
    df = pd.read_csv(questions_file)

    # Add answer columns if they don't exist using centralized configuration
    for col in config.csv.ANSWER_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    # Add human answer columns
    for col in config.csv.HUMAN_ANSWER_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    # Process questions
    question_sets = list(
        zip(
            config.csv.QUESTION_COLUMNS,
            config.csv.HUMAN_ANSWER_COLUMNS,
            config.csv.ANSWER_COLUMNS,
        )
    )

    # Count total questions to process
    total_questions = sum(
        row.isna()[a_col] for _, row in df.iterrows() for _, _, a_col in question_sets
    )
    processed_count = 0

    print(
        f"\n🚀 Starting to process {total_questions} questions with RLM-backed responses..."
    )

    for index, row in df.iterrows():
        category_key = "|".join(
            str(row[col]) for col in config.csv.CATEGORY_KEY_COLUMNS
        )

        for question_col, human_col, answer_col in question_sets:
            if question_col in df.columns:  # Check if question column exists
                if row.isna()[answer_col]:
                    query = str(row[question_col])

                    # Get corresponding human answer for context and output dataset
                    human_answer = ""
                    if category_key in human_interview_data:
                        human_answer = human_interview_data[category_key].get(human_col, "")

                    print(f"🤔 Processing with RLM ({mode_label}): {query[:60]}...")

                    max_retries = 3
                    base_delay = 1
                    response = ""
                    for attempt in range(max_retries):
                        response = ask_question(
                            query, human_answer, include_human_answer
                        )
                        if not response.startswith("Error:"):
                            break
                        if attempt < max_retries - 1:
                            delay = base_delay * (2**attempt)
                            print(
                                f"⚠️ {mode_label} RLM call failed, retrying in {delay}s... (attempt {attempt+1}/{max_retries})"
                            )
                            time.sleep(delay)

                    if response.startswith("Error:"):
                        cleaned_response = f"Failed after {max_retries} retries: {response}"
                    else:
                        cleaned_response = re.sub(
                            r"\s+", " ", response.replace("\n", " ")
                        ).strip()

                    df.at[index, answer_col] = cleaned_response

                    df.at[index, human_col] = human_answer

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

    # Final save
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
