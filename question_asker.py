#!/usr/bin/env python3
"""
Human Interview Asker - Personalized question answering using songbird model with human context

This script processes questions from a CSV file using the songbird model with human interview context for personalized responses.

Features:
- Automatically loads the most recent human interview data for personalization
- Human answers serve as context for more tailored, personalized AI responses
- Requires human interview data - no fallback to baseline mode

Usage:
    python question_asker.py                                    # Automatically process questions with human interview context
"""

import os
import sys
import csv
import pandas as pd
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path

# Import config from current directory
from config import config, get_most_recent_file

def get_system_prompt(question: str, human_answer: str = None) -> str:
    """Get the songbird system prompt with human context."""
    if human_answer:
        return config.prompts.songbird_system_prompt.format(question=question, human_answer=human_answer)
    else:
        # Fallback if no human answer provided
        return config.prompts.baseline_system_prompt.format(question=question)

def ask_question(client, model_name: str, question: str, human_answer: str = None) -> str:
    """Send a question to the songbird model and get the response."""
    try:
        system_prompt = get_system_prompt(question, human_answer)

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            temperature=config.api.TEMPERATURE,
            max_tokens=config.api.MAX_TOKENS,
            stream=True
        )

        # Accumulate streaming response
        full_content = ""
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices:
                if hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta:
                    if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        full_content += chunk.choices[0].delta.content
        return full_content.strip()

    except Exception as e:
        print(f"⚠️ Error calling songbird API: {e}")
        return f"Error: {str(e)}"

def main():
    # Always use songbird model (required for RAG with human interview context)
    model_type = "songbird"
    assert model_type == "songbird", "Only songbird model is supported for human interview RAG"

    # Validate configuration
    issues = config.validate()
    if issues:
        print("❌ Configuration issues found:")
        for issue in issues:
            print(f"   - {issue}")
        sys.exit(1)

    # Set up model client
    try:
        client, model_name = config.api.create_songbird_client()
        print(f"✅ Connected to songbird API (model: {model_name})")
    except Exception as e:
        print(f"❌ Failed to set up songbird client: {e}")
        sys.exit(1)

    # Set up file paths from config
    questions_file = config.paths.QUESTIONS_CSV

    # Auto-detect latest human interview file
    try:
        human_interview_file = get_most_recent_file("human_interview_*.csv")
        print(f"📖 Using latest human interview file: {human_interview_file}")
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
    output_filename = config.output.SONGBIRD_OUTPUT_PATTERN.format(timestamp=timestamp)
    output_file = config.paths.DATA_DIR / output_filename

    # Load human interview data (always required for RAG)
    try:
        human_interview_df = pd.read_csv(human_interview_file)
        if human_interview_df.empty:
            print("❌ Error: No human interview data loaded. Songbird model requires interview context for RAG.")
            sys.exit(1)

        # Create lookup dictionary using CSVConfig column names
        human_interview_data = {}
        for _, row in human_interview_df.iterrows():
            category_key = f"{row['Category']}|{row['Goal']}|{row['Element']}"
            answer_data = {}
            for col in config.csv.ANSWER_COLUMNS:
                answer_data[col] = str(row.get(col, '')).strip() if pd.notna(row.get(col, '')) else ''
            human_interview_data[category_key] = answer_data

    except Exception as e:
        print(f"❌ Error loading human interview data: {e}")
        sys.exit(1)

    print(f"📖 Loaded {len(human_interview_data)} interview sections for personalization")

    # Read the CSV file
    print(f"📖 Reading questions from: {questions_file}")
    df = pd.read_csv(questions_file)

    # Add answer columns if they don't exist using centralized configuration
    for col in config.csv.ANSWER_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    # Process questions
    question_pairs = list(zip(config.csv.QUESTION_COLUMNS, config.csv.ANSWER_COLUMNS))

    # Count total questions to process
    total_questions = sum(1 for _, row in df.iterrows()
                         for q_col, a_col in question_pairs
                         if pd.isna(row[a_col]))
    processed_count = 0

    print(f"\n🚀 Starting to process {total_questions} questions with personalized responses...")

    for index, row in df.iterrows():
        category_key = f"{row['Category']}|{row['Goal']}|{row['Element']}"

        for question_col, answer_col in question_pairs:
            if question_col in df.columns:  # Check if question column exists
                old_answer = df.at[index, answer_col]
                if pd.isna(old_answer):  # Only process if answer is empty
                    query = row[question_col]

                    # Get corresponding human answer for context (always available since required)
                    human_answer = None
                    human_answer_col = f"Human_{answer_col}"
                    if category_key in human_interview_data and human_interview_data[category_key].get(human_answer_col, '').strip():
                        human_answer = human_interview_data[category_key][human_answer_col]

                    context_indicator = " (personalized)" if human_answer else ""
                    print(f"🤔 Processing{context_indicator}: {query[:60]}...")

                    response = ask_question(client, model_name, query, human_answer)
                    df.at[index, answer_col] = response

                    processed_count += 1
                    print(f"✅ Processed {processed_count}/{total_questions} questions")

                    # Clean the answer
                    if not pd.isna(df.at[index, answer_col]):
                        df[answer_col] = df[answer_col].replace(r'\n', ' ', regex=True)
                        df[answer_col] = df[answer_col].replace(r'\s+', ' ', regex=True)

                    # Save after each answer to prevent data loss
                    df.to_csv(str(output_file), index=False, quoting=csv.QUOTE_NONNUMERIC)

    # Final formatting and save
    df = df.replace(r'\n', ' ', regex=True)
    df = df.replace(r'\s+', ' ', regex=True)
    df.to_csv(str(output_file), index=False, quoting=csv.QUOTE_NONNUMERIC)

    print(f"\n✅ Completed! Processed {processed_count} questions and saved to {output_file}")

if __name__ == "__main__":
    main()
