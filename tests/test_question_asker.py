#!/usr/bin/env python3
"""Tests for QMD-backed question answering without external services."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from core.question_asker import _qmd_freshness, _retrieve_passages, run


class QuestionAskerTests(unittest.TestCase):
    """Exercise the retrieval and direct-LLM boundary with fakes."""

    def test_retrieval_reports_missing_qmd_explicitly(self) -> None:
        with patch("core.question_asker.shutil.which", return_value=None):
            passages = _retrieve_passages("What matters?", ["Journal"])

        self.assertEqual(
            passages, "Retrieval unavailable: QMD command not found on PATH."
        )

    def test_freshness_uses_index_age_not_source_note_age(self) -> None:
        status = "Updated: 2h ago\nBase (qmd://Base/)\n  Files: 5 (updated 160d ago)"
        with patch(
            "core.question_asker.subprocess.run",
            return_value=SimpleNamespace(returncode=0, stdout=status, stderr=""),
        ):
            self.assertIn("within the configured window", _qmd_freshness(["Base"]))

    def test_run_does_not_call_llm_without_evidence(self) -> None:
        config = SimpleNamespace(
            profile=SimpleNamespace(name="existential", qmd_collections=["Journal"]),
            paths=SimpleNamespace(QUESTIONS_CSV=Path("unused.csv"), DATA_DIR=Path("unused")),
            api=SimpleNamespace(),
            validate_question_answering=lambda: [],
        )
        with (
            patch("core.question_asker.create_client") as create,
            patch("core.question_asker.pd.read_csv", return_value=pd.DataFrame([{
                "Category": "Identity", "Goal": "Ground", "Element": "Evidence",
                "Question 1": "What matters?", "AI_Answer 1": pd.NA,
            }])) as read_csv,
            patch("core.question_asker._retrieve_passages", return_value="Retrieval unavailable: index missing"),
            patch("core.question_asker.generate_text") as generate,
        ):
            config.csv = SimpleNamespace(ANSWER_COLUMNS=["AI_Answer 1"], QUESTION_COLUMNS=["Question 1"])
            config.output = SimpleNamespace(QUESTIONS_WITH_ANSWERS_PATTERN="answers_{timestamp}.csv", TIMESTAMP_FORMAT="%Y%m%d")
            self.assertEqual(run(config), 1)
        create.assert_called_once()
        read_csv.assert_called_once()
        generate.assert_not_called()

    def test_run_uses_qmd_passages_and_direct_llm(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base_dir = Path(directory)
            questions_path = base_dir / "questions.csv"
            output_dir = base_dir / "data"
            output_dir.mkdir()
            pd.DataFrame(
                [
                    {
                        "Category": "Quality",
                        "Goal": "Verify evidence",
                        "Element": "Grounded answers",
                        "Question 1": "What does the user protect?",
                        "Question 2": "",
                        "Question 3": "",
                        "AI_Answer 2": "Existing answer",
                        "AI_Answer 3": "Existing answer",
                    }
                ]
            ).to_csv(questions_path, index=False)

            config = SimpleNamespace(
                profile=SimpleNamespace(name="operational", qmd_collections=["Base"]),
                paths=SimpleNamespace(QUESTIONS_CSV=questions_path, DATA_DIR=output_dir),
                csv=SimpleNamespace(
                    QUESTION_COLUMNS=["Question 1", "Question 2", "Question 3"],
                    ANSWER_COLUMNS=["AI_Answer 1", "AI_Answer 2", "AI_Answer 3"],
                    DELIMITER=",",
                    QUOTECHAR='"',
                ),
                output=SimpleNamespace(
                    QUESTIONS_WITH_ANSWERS_PATTERN="questions_with_answers_qmd_{timestamp}.csv",
                    TIMESTAMP_FORMAT="%Y%m%d_%H%M%S",
                ),
                api=SimpleNamespace(
                    TEMPERATURE=0.2,
                    get_max_completion_tokens=lambda *, provider: 100,
                ),
                prompts=SimpleNamespace(
                    qmd_query_template=(
                        "{synthesis_prompt}\n{category}\n{question}\n{retrieved_passages}"
                    ),
                    synthesis_prompt="Synthesize only supported claims.",
                ),
                validate_question_answering=lambda: [],
            )
            query_result = [
                {
                    "docid": "#abc123",
                    "file": "qmd://Base/workflow.md",
                    "line": 12,
                    "title": "Workflow evidence",
                    "snippet": "The user requires verification before trusting a fix.",
                }
            ]
            calls: list[list[str]] = []

            def fake_run(command: list[str], **_: object) -> SimpleNamespace:
                calls.append(command)
                if command[1] == "status":
                    return SimpleNamespace(
                        returncode=0,
                        stdout="Updated: 1h ago\nBase (qmd://Base/)\n  Files: 1 (updated: 1d ago)",
                        stderr="",
                    )
                return SimpleNamespace(
                    returncode=0, stdout=json.dumps(query_result), stderr=""
                )

            with (
                patch("core.question_asker.shutil.which", return_value="/fake/qmd"),
                patch("core.question_asker.subprocess.run", side_effect=fake_run),
                patch(
                    "core.question_asker.create_client",
                    return_value=SimpleNamespace(provider="anthropic"),
                ) as create,
                patch("core.question_asker.generate_text", return_value="Grounded answer") as generate,
            ):
                self.assertEqual(run(config), 0)

            create.assert_called_once_with(config.api, provider="anthropic")
            prompt = generate.call_args.kwargs["user_prompt"]
            self.assertIn("[1] Workflow evidence | qmd://Base/workflow.md:12", prompt)
            self.assertIn("The user requires verification before trusting a fix.", prompt)
            self.assertIn("-c", calls[0])
            self.assertIn("Base", calls[0])

            output_files = list(output_dir.glob("questions_with_answers_qmd_*.csv"))
            self.assertEqual(len(output_files), 1)
            with output_files[0].open(newline="", encoding="utf-8") as handle:
                output_row = next(csv.DictReader(handle))
            self.assertEqual(output_row["AI_Answer 1"], "Grounded answer")


if __name__ == "__main__":
    unittest.main()
