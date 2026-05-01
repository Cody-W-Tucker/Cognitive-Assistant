#!/usr/bin/env python3
"""Operational question asker using RLM over work artifacts."""

import csv
import re
import sys
import time
from datetime import datetime

import pandas as pd

from config import config, get_review_files, run_rlm_query


def get_rlm_prompt(
    question: str,
    *,
    category: str = "",
    goal: str = "",
    element: str = "",
) -> str:
    """Build the prompt sent to RLM."""
    return config.prompts.rlm_query_template.format(
        synthesis_prompt=config.prompts.synthesis_prompt,
        category=category,
        goal=goal,
        element=element,
        question=question,
    )


def ask_question(
    question: str,
    *,
    category: str = "",
    goal: str = "",
    element: str = "",
) -> str:
    """Send a question to RLM and return the synthesized response."""
    try:
        return run_rlm_query(
            get_rlm_prompt(
                question,
                category=category,
                goal=goal,
                element=element,
            )
        )
    except Exception as exc:
        print(f"Warning: Error calling RLM: {exc}")
        return f"Error: {str(exc)}"


def main() -> None:
    """Run the operational taxonomy against the configured artifact corpus."""
    issues = config.validate_question_answering()
    if issues:
        print("Error: Configuration issues found")
        for issue in issues:
            print(f"- {issue}")
        sys.exit(1)

    review_files = get_review_files()
    print("Info: RLM review files")
    for review_file in review_files:
        print(f"- {review_file}")

    questions_file = config.paths.QUESTIONS_CSV
    print(f"Info: Reading questions from {questions_file}")
    df = pd.read_csv(questions_file)

    for col in config.csv.ANSWER_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    timestamp = datetime.now().strftime(config.output.TIMESTAMP_FORMAT)
    output_filename = config.output.QUESTIONS_WITH_ANSWERS_PATTERN.format(timestamp=timestamp)
    output_file = config.paths.DATA_DIR / output_filename

    question_sets = list(zip(config.csv.QUESTION_COLUMNS, config.csv.ANSWER_COLUMNS))
    total_questions = sum(
        row.isna()[answer_col]
        for _, row in df.iterrows()
        for _, answer_col in question_sets
    )
    processed_count = 0

    print(
        f"\nInfo: Starting to process {total_questions} questions with RLM-backed operational responses"
    )

    for index, row in df.iterrows():
        for question_col, answer_col in question_sets:
            if question_col not in df.columns or not row.isna()[answer_col]:
                continue

            query = str(row[question_col])
            category = str(row.get("Category", ""))
            goal = str(row.get("Goal", ""))
            element = str(row.get("Element", ""))
            print(f"Info: Processing operational question: {query[:80]}...")

            max_retries = 3
            base_delay = 1
            response = ""
            for attempt in range(max_retries):
                response = ask_question(
                    query,
                    category=category,
                    goal=goal,
                    element=element,
                )
                if not response.startswith("Error:"):
                    break
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    print(
                        f"Warning: RLM call failed, retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(delay)

            if response.startswith("Error:"):
                cleaned_response = f"Failed after {max_retries} retries: {response}"
            else:
                cleaned_response = re.sub(r"\s+", " ", response.replace("\n", " ")).strip()

            df.at[index, answer_col] = cleaned_response
            processed_count += 1
            print(f"Info: Processed {processed_count}/{total_questions} questions")

            df.to_csv(
                str(output_file),
                index=False,
                sep=config.csv.DELIMITER,
                quotechar=config.csv.QUOTECHAR,
                quoting=csv.QUOTE_MINIMAL,
            )

    df.to_csv(
        str(output_file),
        index=False,
        sep=config.csv.DELIMITER,
        quotechar=config.csv.QUOTECHAR,
        quoting=csv.QUOTE_MINIMAL,
    )

    print(f"\nInfo: Completed processing {processed_count} questions; saved to {output_file}")


if __name__ == "__main__":
    main()
