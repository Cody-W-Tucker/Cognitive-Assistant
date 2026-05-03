#!/usr/bin/env python3
"""Interactive human-interview ingestion (existential-style profiles).

Walks the user through `questions.csv` (Category x Goal x Element x 3 questions),
captures multi-line answers via stdin, and writes a timestamped
`human_interview_<ts>.csv` under the profile's data directory.

Bug-fix vs. legacy `Existential-Layer/human_interview.py`:
The legacy script keyed in-memory answers by `Answer N` while iterating
`config.csv.ANSWER_COLUMNS` (which contains `AI_Answer N`). The translation only
worked because of an internal convention. This unified version writes directly
into `Human_Answer N` columns when the profile carries human answers, and uses
a single consistent key throughout.
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from core.config import Config


def _human_answer_key(index: int) -> str:
    return f"Human_Answer {index}"


def _load_existing_answers(
    config: Config, output_file: Path
) -> Dict[str, Dict[str, str]]:
    """Load previously-recorded human answers from a resumable session file."""
    if not output_file.exists():
        return {}

    try:
        df = pd.read_csv(output_file)
    except Exception as exc:
        print(f"Warning: Could not load existing answers: {exc}")
        return {}

    answers: Dict[str, Dict[str, str]] = {}
    for _, row in df.iterrows():
        category_key = "|".join(
            str(row[col]) for col in config.csv.CATEGORY_KEY_COLUMNS
        )
        recorded = {}
        for index in range(1, 4):
            col = _human_answer_key(index)
            value = row.get(col, "")
            recorded[col] = str(value).strip() if pd.notna(value) else ""
        answers[category_key] = recorded
    return answers


def _save_answers_to_csv(
    config: Config,
    questions_df: pd.DataFrame,
    answers: Dict[str, Dict[str, str]],
    output_file: Path,
) -> None:
    """Write the merged questions + human-answer dataframe."""
    output_df = questions_df.copy()

    for index in range(1, 4):
        col = _human_answer_key(index)
        if col not in output_df.columns:
            output_df[col] = ""

    for idx, row in output_df.iterrows():
        category_key = "|".join(
            str(row[col]) for col in config.csv.CATEGORY_KEY_COLUMNS
        )
        if category_key not in answers:
            continue
        for index in range(1, 4):
            col = _human_answer_key(index)
            value = answers[category_key].get(col, "")
            if value:
                output_df.at[idx, col] = value

    output_df.to_csv(
        str(output_file),
        index=False,
        sep=config.csv.DELIMITER,
        quotechar=config.csv.QUOTECHAR,
        quoting=csv.QUOTE_MINIMAL,
    )


def _ask_question_interactive(
    question: str, category_context: str, question_number: int
) -> str:
    """Prompt the user for one multi-line answer (double-Enter to finish)."""
    print("\n" + "=" * 80)
    print(f"Category: {category_context}")
    print(f"Question {question_number}: {question}")
    print("=" * 80)
    print("\nInfo: Press Enter twice on a blank line to finish your answer.")
    print("Response:")

    lines: list[str] = []
    while True:
        try:
            line = input()
        except KeyboardInterrupt:
            print(
                "\n\nWarning: Interview paused. You can resume later with --resume"
            )
            return ""
        except EOFError:
            break
        if line.strip() == "" and lines and lines[-1].strip() == "":
            break
        lines.append(line)

    answer = "\n".join(lines).strip()
    if answer.endswith("\n\n"):
        answer = answer[:-1]
    return answer


def _conduct_interview(
    config: Config,
    questions_df: pd.DataFrame,
    existing_answers: Optional[Dict[str, Dict[str, str]]] = None,
) -> Dict[str, Dict[str, str]]:
    """Run the full interview loop, supporting resume via existing_answers."""
    answers: Dict[str, Dict[str, str]] = (
        dict(existing_answers) if existing_answers else {}
    )

    total_questions = len(questions_df) * 3
    answered_count = sum(
        1
        for category_answers in answers.values()
        for value in category_answers.values()
        if value.strip()
    )

    print("Human Interview Process")
    print(f"Info: Total questions {total_questions}")
    print(f"Info: Already answered {answered_count}")
    print(f"Info: Remaining {total_questions - answered_count}")
    print(
        "Info: Press Ctrl+C to pause and Enter twice on a blank line to "
        "finish an answer"
    )
    print("\nInfo: Starting interview\n")

    for idx, row in questions_df.iterrows():
        category = row["Category"]
        goal = row["Goal"]
        element = row["Element"]
        category_context = f"{category} \u2192 {goal}"
        category_key = "|".join(
            str(row[col]) for col in config.csv.CATEGORY_KEY_COLUMNS
        )

        if category_key not in answers:
            answers[category_key] = {
                _human_answer_key(i): "" for i in range(1, 4)
            }

        print(f"\nInfo: Section {idx + 1}/{len(questions_df)}: {category}")

        for question_number in range(1, 4):
            question_col = f"Question {question_number}"
            answer_col = _human_answer_key(question_number)

            if answers[category_key].get(answer_col, "").strip():
                print(
                    f"Info: Question {question_number} already answered; skipping"
                )
                continue

            question = row[question_col]
            answer = _ask_question_interactive(
                question, category_context, question_number
            )
            if answer.strip():
                answers[category_key][answer_col] = answer
                answered_count += 1
                print(
                    f"Info: Answer recorded. Progress "
                    f"{answered_count}/{total_questions}"
                )
            else:
                print("Info: Question skipped because no answer was provided")

    return answers


def run(
    config: Config,
    *,
    resume: bool = False,
    output: Optional[str] = None,
    questions_file: Optional[Path] = None,
) -> int:
    """CLI entry point for interactive interview ingestion."""
    if not config.profile.has_interview_ingest:
        print(
            f"Error: profile '{config.profile.name}' does not enable "
            "interview ingestion"
        )
        return 1
    if not config.profile.include_human_answers:
        print(
            f"Error: profile '{config.profile.name}' does not record human "
            "answers; interview ingestion would have nothing to write"
        )
        return 1

    print(f"{config.profile.display_name} - Human Interview")
    print("=" * 50)

    issues = config.validate()
    if issues:
        print("Error: Configuration issues found")
        for issue in issues:
            print(f"- {issue}")
        return 1

    questions_path = Path(questions_file) if questions_file else config.paths.QUESTIONS_CSV
    if not questions_path.exists():
        print(f"Error: Questions file not found at {questions_path}")
        return 1

    if output:
        output_file = config.paths.DATA_DIR / output
    elif resume:
        try:
            output_file = config.get_most_recent_file("human_interview_*.csv")
            print(f"Info: Resuming from {output_file}")
        except FileNotFoundError:
            print("Error: No previous interview file found to resume")
            return 1
    else:
        timestamp = datetime.now().strftime(config.output.TIMESTAMP_FORMAT)
        output_filename = config.output.HUMAN_INTERVIEW_PATTERN.format(
            timestamp=timestamp
        )
        output_file = config.paths.DATA_DIR / output_filename

    existing_answers: Dict[str, Dict[str, str]] = {}
    if resume and output_file.exists():
        existing_answers = _load_existing_answers(config, output_file)
        if existing_answers:
            print(f"Info: Loaded {len(existing_answers)} existing answer sets")

    print(f"Info: Reading questions from {questions_path}")
    questions_df = pd.read_csv(questions_path)

    answers = dict(existing_answers)
    try:
        answers = _conduct_interview(config, questions_df, existing_answers)
        _save_answers_to_csv(config, questions_df, answers, output_file)

        total_answers = sum(
            1
            for category_answers in answers.values()
            for value in category_answers.values()
            if value.strip()
        )
        print("\n" + "=" * 80)
        print("Info: Interview complete")
        print(f"Info: Results saved to {output_file}")
        print(f"Info: Total answers recorded {total_answers}")
        return 0
    except KeyboardInterrupt:
        print("\n\nWarning: Interview interrupted. Saving progress")
        _save_answers_to_csv(config, questions_df, answers, output_file)
        print(f"Info: Progress saved to {output_file}")
        print(
            "Info: Resume later with `python -m core ingest-interview "
            f"--profile {config.profile.name} --resume`"
        )
        return 0
    except Exception as exc:
        print(f"\nError: Interview failed: {exc}", file=sys.stderr)
        try:
            _save_answers_to_csv(config, questions_df, answers, output_file)
            print(f"Info: Emergency save completed: {output_file}")
        except Exception as save_error:
            print(f"Error: Could not save progress: {save_error}", file=sys.stderr)
        return 1


__all__ = ["run"]
