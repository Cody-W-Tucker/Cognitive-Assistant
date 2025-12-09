#!/usr/bin/env python3
"""
Streamlit Interview App - Web-based Q&A Form

This script creates a web-based interview form using Streamlit, based on questions
from a CSV file. Users can fill out responses in a browser and save them to a CSV file.

Features:
- Web-based form interface with category organization
- Progress tracking and auto-save
- Timestamped output files
- Integration with existing configuration system

Usage:
    streamlit run streamlit_interview.py

"""

import os
import csv
import pandas as pd
import streamlit as st
from datetime import datetime
from pathlib import Path

# Import config from current directory
from config import config


def load_questions() -> pd.DataFrame:
    """Load questions from CSV file."""
    questions_file = config.paths.QUESTIONS_CSV
    if not questions_file.exists():
        st.error(f"Questions file not found at: {questions_file}")
        st.stop()
    return pd.read_csv(questions_file)


def save_answers_to_csv(questions_df: pd.DataFrame, answers: dict, output_file: Path):
    """Save the interview data to CSV."""
    # Create a copy of the questions dataframe
    output_df = questions_df.copy()

    # Add answer columns if not present
    for col in config.csv.ANSWER_COLUMNS:
        if col not in output_df.columns:
            output_df[col] = ""

    # Fill in the answers
    for idx, row in output_df.iterrows():
        category_key = f"{row['Category']}|{row['Goal']}|{row['Element']}"
        if category_key in answers:
            for i, answer_col in enumerate(config.csv.ANSWER_COLUMNS, 1):
                answer_key = f"Answer {i}"
                if (
                    answer_key in answers[category_key]
                    and answers[category_key][answer_key]
                ):
                    output_df.at[idx, answer_col] = answers[category_key][answer_key]

    # Save to CSV
    output_df.to_csv(
        str(output_file),
        index=False,
        sep=config.csv.DELIMITER,
        quotechar=config.csv.QUOTECHAR,
        quoting=csv.QUOTE_MINIMAL,
    )


def main():
    st.set_page_config(
        page_title="Existential Interview", page_icon="🎯", layout="centered"
    )

    st.title("Cognitive Assistant Interview")

    # Load questions
    questions_df = load_questions()

    # Initialize session state
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0
    if "answers" not in st.session_state:
        st.session_state.answers = {}

    # Flatten questions
    questions_list = []
    for idx, row in questions_df.iterrows():
        for q_num in 1, 2, 3:
            questions_list.append(
                {
                    "category": row["Category"],
                    "goal": row["Goal"],
                    "element": row["Element"],
                    "question_num": q_num,
                    "question": row[f"Question {q_num}"],
                    "key": f"{row['Category']}|{row['Goal']}|{row['Element']}|Answer {q_num}",
                }
            )

    total_questions = len(questions_list)
    current_q = questions_list[st.session_state.current_index]
    answer_key = current_q["key"]

    if answer_key not in st.session_state.answers:
        st.session_state.answers[answer_key] = ""

    # Progress
    st.progress((st.session_state.current_index + 1) / total_questions)
    st.caption(f"Question {st.session_state.current_index + 1} of {total_questions}")

    # Display current question
    st.markdown(f"### {current_q['question']}")

    # Answer input
    answer = st.text_area(
        "Your answer:",
        value=st.session_state.answers[answer_key],
        height=200,
        placeholder="Type your response here...",
    )
    st.session_state.answers[answer_key] = answer

    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "⬅️ Previous",
            disabled=st.session_state.current_index == 0,
            use_container_width=True,
        ):
            st.session_state.current_index -= 1
            st.rerun()
    with col2:
        if st.session_state.current_index < total_questions - 1:
            if st.button("Next ➡️", use_container_width=True):
                st.session_state.current_index += 1
                st.rerun()
        else:
            if st.button(
                "💾 Submit Interview", type="primary", use_container_width=True
            ):
                # Convert answers back to dict format
                answers_dict = {}
                for q in questions_list:
                    cat_key = f"{q['category']}|{q['goal']}|{q['element']}"
                    if cat_key not in answers_dict:
                        answers_dict[cat_key] = {}
                    answers_dict[cat_key][f'Answer {q["question_num"]}'] = (
                        st.session_state.answers[q["key"]]
                    )

                # Save
                timestamp = datetime.now().strftime(config.output.TIMESTAMP_FORMAT)
                output_filename = config.output.HUMAN_INTERVIEW_PATTERN.format(
                    timestamp=timestamp
                )
                output_file = config.paths.DATA_DIR / output_filename
                config.paths.DATA_DIR.mkdir(parents=True, exist_ok=True)
                save_answers_to_csv(questions_df, answers_dict, output_file)

                # Count answers
                total_answers = sum(
                    1 for ans in st.session_state.answers.values() if ans.strip()
                )

                st.success("🎉 Interview saved successfully!")
                st.write(f"📁 File saved to: `{output_file}`")
                st.write(f"📊 Total answers recorded: {total_answers}")

                # Download button
                with open(output_file, "rb") as f:
                    st.download_button(
                        label="📥 Download Results",
                        data=f,
                        file_name=output_filename,
                        mime="text/csv",
                    )


if __name__ == "__main__":
    main()

