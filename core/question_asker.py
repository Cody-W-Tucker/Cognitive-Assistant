#!/usr/bin/env python3
"""Profile-aware question asker.

For each row in `questions.csv`, calls RLM once per question column with a
profile-specific prompt and writes results into a timestamped output CSV.

Behavior selection by profile:
  - include_human_answers=True  -> auto-loads latest human_interview_*.csv,
    threads Human_Answer N into the RLM prompt and into the output CSV. A
    `--filesystem-only` flag is honored when the profile also declares a
    `rlm_query_template_filesystem_only` prompt (e.g. existential).
  - include_human_answers=False -> passes (category, goal, element, question)
    placeholders to the RLM prompt; no human answers are loaded or written.
"""

from __future__ import annotations

import csv
import re
import sys
import time
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from core.config import Config


def _build_prompt_with_human(config: Config, question: str, human_answer: str) -> str:
    return config.prompts.rlm_query_template.format(
        synthesis_prompt=config.prompts.synthesis_prompt,
        question=question,
        human_answer=human_answer.strip() or "No human interview context provided.",
    )


def _build_prompt_filesystem_only(config: Config, question: str) -> str:
    return config.prompts.rlm_query_template_filesystem_only.format(
        synthesis_prompt=config.prompts.synthesis_prompt,
        question=question,
    )


def _build_prompt_taxonomy(
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


def _load_human_interview_lookup(config: Config) -> Dict[str, Dict[str, str]]:
    """Load the most recent human interview CSV into a category-keyed lookup."""
    interview_path = config.get_most_recent_file("human_interview_*.csv")
    print(f"Info: Loaded {interview_path}")

    interview_df = pd.read_csv(interview_path)
    if interview_df.shape[0] == 0:
        raise RuntimeError("No human interview data loaded")

    lookup: Dict[str, Dict[str, str]] = {}
    for _, row in interview_df.iterrows():
        key = "|".join(str(row[col]) for col in config.csv.CATEGORY_KEY_COLUMNS)
        answers: Dict[str, str] = {}
        for col in config.csv.HUMAN_ANSWER_COLUMNS:
            value = row.get(col, "")
            answers[col] = str(value).strip() if pd.notna(value) else ""
        lookup[key] = answers
    return lookup


def _write_dataframe(df: pd.DataFrame, path, config: Config) -> None:
    df.to_csv(
        str(path),
        index=False,
        sep=config.csv.DELIMITER,
        quotechar=config.csv.QUOTECHAR,
        quoting=csv.QUOTE_MINIMAL,
    )


def run(config: Config, *, filesystem_only: bool = False) -> int:
    """Run the question-asking loop for the given profile."""
    issues = config.validate_question_answering()
    if issues:
        print("Error: Configuration issues found")
        for issue in issues:
            print(f"- {issue}")
        return 1

    use_human = config.profile.include_human_answers and not filesystem_only
    if filesystem_only and not config.prompts.has("rlm_query_template_filesystem_only"):
        print(
            "Error: --filesystem-only requested but profile does not declare "
            "rlm_query_template_filesystem_only"
        )
        return 1
    if filesystem_only and not config.profile.include_human_answers:
        print("Info: --filesystem-only is a no-op for this profile (no human answers)")

    # Print evidence source for visibility
    if config.profile.rlm_review_paths is not None:
        print("Info: RLM review paths")
        for review_path in config.profile.rlm_review_paths:
            print(f"- {review_path}")
    else:
        review_files = config.get_review_files()
        print("Info: RLM review files")
        for review_file in review_files:
            print(f"- {review_file}")

    if config.profile.include_human_answers:
        mode_label = "human-seeded" if use_human else "filesystem-only"
        print(f"Info: Question mode {mode_label}")
    else:
        mode_label = "operational"

    # Load human interview data if needed
    human_lookup: Dict[str, Dict[str, str]] = {}
    if use_human:
        try:
            human_lookup = _load_human_interview_lookup(config)
        except FileNotFoundError:
            print("Error: No human interview files found in data directory")
            print("Info: Run `python -m core ingest-interview` first")
            return 1
        except Exception as exc:
            print(f"Error: Failed to load human interview data: {exc}")
            return 1
        print(
            f"Info: Loaded {len(human_lookup)} interview sections for personalization"
        )

    # Read questions CSV
    questions_file = config.paths.QUESTIONS_CSV
    print(f"Info: Reading questions from {questions_file}")
    df = pd.read_csv(questions_file)

    # Ensure answer columns exist
    for col in config.csv.ANSWER_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    if config.profile.include_human_answers:
        for col in config.csv.HUMAN_ANSWER_COLUMNS:
            if col not in df.columns:
                df[col] = pd.NA

    # Set up output path
    timestamp = datetime.now().strftime(config.output.TIMESTAMP_FORMAT)
    output_filename = config.output.QUESTIONS_WITH_ANSWERS_PATTERN.format(
        timestamp=timestamp
    )
    output_file = config.paths.DATA_DIR / output_filename

    # Build per-row column tuples
    if config.profile.include_human_answers:
        question_sets = list(
            zip(
                config.csv.QUESTION_COLUMNS,
                config.csv.HUMAN_ANSWER_COLUMNS,
                config.csv.ANSWER_COLUMNS,
            )
        )
    else:
        question_sets = list(
            zip(config.csv.QUESTION_COLUMNS, config.csv.ANSWER_COLUMNS)
        )

    # Count work to do
    total_questions = sum(
        row.isna()[answer_col]
        for _, row in df.iterrows()
        for cols in question_sets
        for answer_col in [cols[-1]]
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
        category_key = "|".join(
            str(row[col]) for col in config.csv.CATEGORY_KEY_COLUMNS
        )

        for cols in question_sets:
            if config.profile.include_human_answers:
                question_col, human_col, answer_col = cols
            else:
                question_col, answer_col = cols
                human_col = None

            if question_col not in df.columns or not row.isna()[answer_col]:
                continue

            query = str(row[question_col])
            human_answer = ""
            if use_human and category_key in human_lookup:
                human_answer = human_lookup[category_key].get(human_col, "")

            print(f"Info: Processing with RLM ({mode_label}): {query[:60]}...")

            # Build the right prompt for this profile/mode
            if config.profile.include_human_answers:
                if use_human:
                    prompt = _build_prompt_with_human(config, query, human_answer)
                else:
                    prompt = _build_prompt_filesystem_only(config, query)
            else:
                prompt = _build_prompt_taxonomy(
                    config, query, category=category, goal=goal, element=element
                )

            response = _ask_with_retry(config, prompt, label=mode_label)

            if response.startswith("Error:") or response.startswith("Failed after"):
                cleaned_response = response
            else:
                cleaned_response = re.sub(
                    r"\s+", " ", response.replace("\n", " ")
                ).strip()

            df.at[index, answer_col] = cleaned_response
            if human_col is not None:
                df.at[index, human_col] = human_answer

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
