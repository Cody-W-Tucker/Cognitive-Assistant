#!/usr/bin/env python3
"""Profile-aware question asker.

For each row in `questions.csv`, calls RLM once per question column with a
profile-specific prompt and writes results into a timestamped output CSV.
"""

from __future__ import annotations

import csv
import re
import sys
import time
from datetime import datetime

import pandas as pd

from core.config import Config


def _build_prompt(
    config: Config,
    question: str,
    *,
    category: str,
    goal: str,
    element: str,
) -> str:
    return config.prompts.rlm_query_template.format(
        synthesis_prompt=config.prompts.synthesis_prompt,
        category=category,
        goal=goal,
        element=element,
        question=question,
    )


def _ask_with_retry(
    config: Config,
    prompt: str,
    *,
    label: str,
    max_retries: int = 3,
    base_delay: int = 1,
) -> str:
    """Send a prompt to RLM with exponential-backoff retries."""
    response = ""
    for attempt in range(max_retries):
        try:
            response = config.run_rlm_query(prompt)
            return response
        except Exception as exc:
            response = f"Error: {exc}"
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                print(
                    f"Warning: {label} RLM call failed, retrying in {delay}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)
    return f"Failed after {max_retries} retries: {response}"


def _write_dataframe(df: pd.DataFrame, path, config: Config) -> None:
    df.to_csv(
        str(path),
        index=False,
        sep=config.csv.DELIMITER,
        quotechar=config.csv.QUOTECHAR,
        quoting=csv.QUOTE_MINIMAL,
    )


def run(config: Config) -> int:
    """Run the question-asking loop for the given profile."""
    issues = config.validate_question_answering()
    if issues:
        print("Error: Configuration issues found")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if config.profile.rlm_review_paths is not None:
        print("Info: RLM review paths")
        for review_path in config.profile.rlm_review_paths:
            print(f"- {review_path}")
    else:
        review_files = config.get_review_files()
        print("Info: RLM review files")
        for review_file in review_files:
            print(f"- {review_file}")

    mode_label = config.profile.name

    questions_file = config.paths.QUESTIONS_CSV
    print(f"Info: Reading questions from {questions_file}")
    df = pd.read_csv(questions_file)

    for col in config.csv.ANSWER_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    timestamp = datetime.now().strftime(config.output.TIMESTAMP_FORMAT)
    output_filename = config.output.QUESTIONS_WITH_ANSWERS_PATTERN.format(
        timestamp=timestamp
    )
    output_file = config.paths.DATA_DIR / output_filename

    question_sets = list(zip(config.csv.QUESTION_COLUMNS, config.csv.ANSWER_COLUMNS))

    total_questions = sum(
        row.isna()[answer_col]
        for _, row in df.iterrows()
        for _, answer_col in question_sets
    )
    processed_count = 0

    print(
        f"\nInfo: Starting to process {total_questions} questions with "
        f"RLM-backed responses"
    )

    for index, row in df.iterrows():
        category = str(row.get("Category", ""))
        goal = str(row.get("Goal", ""))
        element = str(row.get("Element", ""))

        for question_col, answer_col in question_sets:
            if question_col not in df.columns or not row.isna()[answer_col]:
                continue

            query = str(row[question_col])
            print(f"Info: Processing with RLM ({mode_label}): {query[:60]}...")

            prompt = _build_prompt(
                config,
                query,
                category=category,
                goal=goal,
                element=element,
            )

            response = _ask_with_retry(config, prompt, label=mode_label)

            if response.startswith("Error:") or response.startswith("Failed after"):
                cleaned_response = response
            else:
                cleaned_response = re.sub(
                    r"\s+", " ", response.replace("\n", " ")
                ).strip()

            df.at[index, answer_col] = cleaned_response

            processed_count += 1
            print(f"Info: Processed {processed_count}/{total_questions} questions")
            _write_dataframe(df, output_file, config)

    _write_dataframe(df, output_file, config)
    print(
        f"\nInfo: Completed processing {processed_count} questions; "
        f"saved to {output_file}"
    )
    return 0


__all__ = ["run"]
