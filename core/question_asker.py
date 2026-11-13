#!/usr/bin/env python3
"""Profile-aware question asker.

For each row in `questions.csv`, retrieves QMD evidence, synthesizes an answer
with the configured direct LLM client, and writes it into a timestamped CSV.
"""

from __future__ import annotations

import asyncio
import csv
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from typing import List

import pandas as pd

from core import llm
from core.config import ANSWER_COLUMNS, QUESTION_COLUMNS, TIMESTAMP_FORMAT, LayerProfile

QMD_COMMAND = "qmd"
QMD_RESULT_LIMIT = 6
QMD_PASSAGE_LIMIT = 1200
QMD_STALE_AFTER_DAYS = 14


class RetrievalUnavailable(RuntimeError):
    """QMD cannot supply current evidence, so the question must not be answered."""


def _check_freshness(collections: list[str]) -> None:
    """Raise unless every collection is indexed and the index is recent."""
    try:
        result = subprocess.run([QMD_COMMAND, "status"], capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RetrievalUnavailable(f"QMD status failed: {exc}") from exc
    if result.returncode != 0:
        raise RetrievalUnavailable(result.stderr.strip() or "QMD status command failed")
    found: set[str] = set()
    age_days: float | None = None
    for line in result.stdout.splitlines():
        collection_match = re.match(r"\s*(.+?)\s+\(qmd://[^/]+/\)", line)
        if collection_match:
            found.add(collection_match.group(1))
        index_match = re.match(r"\s*Updated:\s*(\d+)([hd])\s+ago", line, re.I)
        if index_match:
            value, unit = index_match.groups()
            age_days = int(value) if unit.lower() == "d" else int(value) / 24
    missing = sorted(set(collections) - found)
    if missing:
        raise RetrievalUnavailable("missing QMD collections: " + ", ".join(missing))
    if age_days is None:
        raise RetrievalUnavailable("QMD status did not report the index update age")
    if age_days > QMD_STALE_AFTER_DAYS:
        raise RetrievalUnavailable(f"QMD index was last updated {age_days:g} days ago")


def _format_passages(results: list[dict]) -> str:
    """A bounded, cited evidence block from QMD JSON result records."""
    passages: list[str] = ["Retrieved passages (cite labels are for grounding only):"]
    for position, result in enumerate(results[:QMD_RESULT_LIMIT], start=1):
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
    """Cited QMD passages for one question; raises when there is no current evidence."""
    if shutil.which(QMD_COMMAND) is None:
        raise RetrievalUnavailable("QMD command not found on PATH")
    command = [QMD_COMMAND, "query", "--format", "json", "--no-rerank", "-n", str(QMD_RESULT_LIMIT)]
    for collection in collections:
        command.extend(["-c", collection])
    command.append(question)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RetrievalUnavailable(str(exc)) from exc
    if result.returncode != 0:
        raise RetrievalUnavailable(result.stderr.strip() or "QMD query command failed")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RetrievalUnavailable(f"QMD returned invalid JSON: {exc}") from exc
    if not isinstance(payload, list):
        raise RetrievalUnavailable("QMD JSON response was not a result list")
    results = [item for item in payload if isinstance(item, dict)]
    if not results:
        raise RetrievalUnavailable("no QMD passages were retrieved from collections: " + ", ".join(collections))
    return _format_passages(results)


async def _answer(prompt: str, *, attempts: int = 3) -> str | None:
    """The model's answer on one line, or None after ``attempts`` failures (rate limits are common)."""
    for attempt in range(attempts):
        try:
            return re.sub(r"\s+", " ", await llm.complete(prompt, label="answer")).strip()
        except Exception as exc:
            print(f"Warning: answer failed ({exc}) (attempt {attempt + 1}/{attempts})", file=sys.stderr)
            if attempt < attempts - 1:
                await asyncio.sleep(2**attempt)
    return None


def requirements(profile: LayerProfile) -> List[str]:
    issues = llm.missing_config(llm.DEFAULT_PROVIDER)
    if not profile.questions_csv.exists():
        issues.append(f"Questions CSV not found at {profile.questions_csv}")
    if not profile.qmd_collections:
        issues.append(f"No QMD collections configured for profile '{profile.name}'")
    return issues


async def build(profile: LayerProfile) -> None:
    """Answer every question questions.csv leaves unanswered into a new timestamped CSV; failures stay empty."""
    print("Info: QMD collections: " + ", ".join(profile.qmd_collections))
    df = pd.read_csv(profile.questions_csv)
    for col in ANSWER_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    output = profile.answers_path(datetime.now().strftime(TIMESTAMP_FORMAT))
    output.parent.mkdir(parents=True, exist_ok=True)
    pending = [
        (index, question_col, answer_col)
        for index, row in df.iterrows()
        for question_col, answer_col in zip(QUESTION_COLUMNS, ANSWER_COLUMNS)
        if question_col in df.columns and pd.notna(row[question_col]) and pd.isna(row[answer_col])
    ]
    print(f"Info: Answering {len(pending)} questions with QMD evidence")
    if pending:
        try:
            if shutil.which(QMD_COMMAND) is None:
                raise RetrievalUnavailable("QMD command not found on PATH")
            _check_freshness(profile.qmd_collections)
        except RetrievalUnavailable as exc:
            raise RuntimeError(f"Cannot answer without current QMD evidence: {exc}") from exc
    failed = 0
    for done, (index, question_col, answer_col) in enumerate(pending, start=1):
        row = df.loc[index]
        question = str(row[question_col])
        print(f"Info: {question[:60]}...")
        try:
            passages = _retrieve_passages(question, profile.qmd_collections)
        except RetrievalUnavailable as exc:
            raise RuntimeError(f"Cannot answer without current QMD evidence: {exc}") from exc
        prompt = profile.prompt("qmd_query_template").format(
            synthesis_prompt=profile.prompt("synthesis_prompt"),
            category=str(row.get("Category", "")),
            goal=str(row.get("Goal", "")),
            element=str(row.get("Element", "")),
            question=question,
            retrieved_passages=passages,
        )
        answer = await _answer(prompt)
        if answer is None:
            failed += 1
        else:
            df.at[index, answer_col] = answer
        df.to_csv(output, index=False, quoting=csv.QUOTE_MINIMAL)
        print(f"Info: Processed {done}/{len(pending)} questions")
    df.to_csv(output, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"Info: Saved answers to {output}")
    if failed:
        raise RuntimeError(f"{failed} question(s) could not be answered and were left empty in {output.name}")
