#!/usr/bin/env python3
"""Profile-aware question asker.

For each row in `questions.csv`, retrieves QMD evidence, synthesizes an answer
with the configured direct LLM client, and writes it into a timestamped CSV.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from typing import Any

import pandas as pd

from core.config import Config
from lib.config import DEFAULT_PROVIDER
from lib.llm import LLMHandle, create_client, generate_text


QMD_COMMAND = "qmd"
QMD_RESULT_LIMIT = 6
QMD_PASSAGE_LIMIT = 1200
QMD_STALE_AFTER_DAYS = 14


def _build_prompt(
    config: Config,
    question: str,
    *,
    category: str,
    goal: str,
    element: str,
    retrieved_passages: str,
) -> str:
    return config.prompts.qmd_query_template.format(
        synthesis_prompt=config.prompts.synthesis_prompt,
        category=category,
        goal=goal,
        element=element,
        question=question,
        retrieved_passages=retrieved_passages,
    )


def _qmd_freshness(collections: list[str]) -> str:
    """Describe QMD index freshness without making a failed check invisible."""
    try:
        result = subprocess.run(
            [QMD_COMMAND, "status"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"Retrieval freshness unavailable: {exc}"

    if result.returncode != 0:
        detail = result.stderr.strip() or "QMD status command failed"
        return f"Retrieval freshness unavailable: {detail}"

    selected = set(collections)
    found: set[str] = set()
    index_age: int | None = None
    for line in result.stdout.splitlines():
        collection_match = re.match(r"\s*(.+?)\s+\(qmd://[^/]+/\)", line)
        if collection_match:
            found.add(collection_match.group(1))
        index_match = re.match(r"\s*Updated:\s*(\d+)([hd])\s+ago", line, re.I)
        if index_match:
            value, unit = index_match.groups()
            index_age = int(value) if unit.lower() == "d" else 0

    missing = sorted(selected - found)
    if missing:
        return "Retrieval freshness unavailable: missing QMD collections: " + ", ".join(missing)
    if index_age is None:
        return (
            "Retrieval freshness unavailable: QMD status did not report the index update age."
        )
    if index_age > QMD_STALE_AFTER_DAYS:
        return (
            f"Retrieval may be stale: QMD index was last updated {index_age} days ago."
        )
    return "Retrieval index freshness is within the configured window."


def _format_passages(results: list[Any], collections: list[str], freshness: str) -> str:
    """Format a bounded, cited evidence block from QMD JSON result records."""
    passages: list[str] = [f"Retrieval status: {freshness}"]
    valid_results = [result for result in results if isinstance(result, dict)]
    if not valid_results:
        passages.append(
            "No QMD passages were retrieved from collections: "
            + ", ".join(collections)
            + "."
        )
        return "\n\n".join(passages)

    passages.append("Retrieved passages (cite labels are for grounding only):")
    for position, result in enumerate(valid_results[:QMD_RESULT_LIMIT], start=1):
        title = str(result.get("title") or "Untitled")
        source = str(result.get("file") or "unknown source")
        line = result.get("line")
        citation = f"[{position}] {title} | {source}"
        if line is not None:
            citation += f":{line}"
        snippet = str(result.get("snippet") or "").strip()
        if not snippet:
            snippet = "[QMD returned this record without a passage.]"
        passages.append(f"{citation}\n{snippet[:QMD_PASSAGE_LIMIT]}")
    return "\n\n".join(passages)


def _retrieve_passages(question: str, collections: list[str]) -> str:
    """Retrieve bounded QMD passages, preserving retrieval failures as evidence state."""
    if shutil.which(QMD_COMMAND) is None:
        return "Retrieval unavailable: QMD command not found on PATH."

    command = [
        QMD_COMMAND,
        "query",
        "--format",
        "json",
        "--no-rerank",
        "-n",
        str(QMD_RESULT_LIMIT),
    ]
    for collection in collections:
        command.extend(["-c", collection])
    command.append(question)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"Retrieval unavailable: {exc}"
    if result.returncode != 0:
        detail = result.stderr.strip() or "QMD query command failed"
        return f"Retrieval unavailable: {detail}"
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return f"Retrieval unavailable: QMD returned invalid JSON: {exc}"
    if not isinstance(payload, list):
        return "Retrieval unavailable: QMD JSON response was not a result list."
    return _format_passages(payload, collections, _qmd_freshness(collections))


def _ask_with_retry(
    handle: LLMHandle,
    config: Config,
    prompt: str,
    *,
    label: str,
    max_retries: int = 3,
    base_delay: int = 1,
) -> str:
    """Send a synthesized prompt to the configured direct LLM with retries."""
    response = ""
    for attempt in range(max_retries):
        try:
            response = generate_text(
                handle,
                user_prompt=prompt,
                temperature=config.api.TEMPERATURE,
                max_output_tokens=config.api.get_max_completion_tokens(
                    provider=handle.provider
                ),
            )
            return response
        except Exception as exc:
            response = f"Error: {exc}"
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                print(
                    f"Warning: {label} LLM call failed, retrying in {delay}s "
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

    handle = create_client(config.api, provider=DEFAULT_PROVIDER)
    print("Info: QMD collections")
    for collection in config.profile.qmd_collections:
        print(f"- {collection}")

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
        f"QMD-backed direct LLM responses"
    )

    for index, row in df.iterrows():
        category = str(row.get("Category", ""))
        goal = str(row.get("Goal", ""))
        element = str(row.get("Element", ""))

        for question_col, answer_col in question_sets:
            if question_col not in df.columns or not row.isna()[answer_col]:
                continue

            query = str(row[question_col])
            print(f"Info: Processing with QMD + LLM ({mode_label}): {query[:60]}...")

            retrieved_passages = _retrieve_passages(
                query, config.profile.qmd_collections
            )
            if (
                retrieved_passages.startswith("Retrieval unavailable:")
                or "No QMD passages were retrieved" in retrieved_passages
                or "Retrieval freshness unavailable:" in retrieved_passages
                or "Retrieval may be stale:" in retrieved_passages
            ):
                print(f"Error: Cannot answer without current QMD evidence: {retrieved_passages}", file=sys.stderr)
                return 1

            prompt = _build_prompt(
                config,
                query,
                category=category,
                goal=goal,
                element=element,
                retrieved_passages=retrieved_passages,
            )

            response = _ask_with_retry(handle, config, prompt, label=mode_label)

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
