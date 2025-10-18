#!/usr/bin/env python3
"""
Human Interview Asker - Personalized question answering using songbird model with human context

This script processes questions from a CSV file using the songbird model with human interview context for personalized responses.

Features:
- Automatically loads the most recent human interview data for personalization
- Human answers serve as context for more tailored, personalized AI responses
- Requires human interview data

Usage:
    python human_interview.py                                   # Run the interview process to be interviewed and create human answers
    python question_asker.py                                    # Automatically process questions with human interview context
"""

import sys
import csv
import pandas as pd
import re
import time
from datetime import datetime

# Import config from current directory
from config import config, get_most_recent_file, get_clean_markdown_function, accumulate_streaming_response, clean_markdown

def get_system_prompt(question: str, human_answer: str) -> str:
    """Get the system prompt with human context."""
    if not human_answer:
        raise ValueError("Human answer is required for songbird RAG model")
    return config.prompts.songbird_system_prompt.format(question=question, human_answer=human_answer)

def ask_question(client, model_name: str, question: str, human_answer: str) -> str:
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

        # Use the shared streaming utility
        full_content = accumulate_streaming_response(response)
        return full_content.strip()

    except Exception as e:
        print(f"⚠️ Error calling songbird API: {e}")
        return f"Error: {str(e)}"


def ask_incorporation(client, model_name: str, all_qa_data: str) -> str:
    """Send incorporation analysis to the human model and get the response."""
    try:
        system_prompt = config.prompts.incorporation_prompt.format(all_qa_data=all_qa_data)

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": "Generate incorporation instructions based on the above analysis."
                }
            ],
            temperature=config.api.TEMPERATURE,
            max_tokens=config.api.MAX_TOKENS,
            stream=True
        )

        # Use the shared streaming utility
        full_content = accumulate_streaming_response(response)
        return full_content.strip()

    except Exception as e:
        print(f"⚠️ Error calling human incorporation API: {e}")
        return f"Error: {str(e)}"


def main():
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
            category_key = "|".join(str(row[col]) for col in config.csv.CATEGORY_KEY_COLUMNS)
            answer_data = {}
            for col in config.csv.HUMAN_ANSWER_COLUMNS:
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

    # Add human answer columns
    for col in config.csv.HUMAN_ANSWER_COLUMNS:
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
        category_key = "|".join(str(row[col]) for col in config.csv.CATEGORY_KEY_COLUMNS)

        for question_col, answer_col in question_pairs:
            if question_col in df.columns:  # Check if question column exists
                old_answer = df.at[index, answer_col]
                if pd.isna(old_answer):  # Only process if answer is empty
                    query = row[question_col]

                    # Get corresponding human answer for context (required for RAG)
                    human_col = config.csv.HUMAN_ANSWER_COLUMNS[config.csv.QUESTION_COLUMNS.index(question_col)]
                    if category_key not in human_interview_data or not human_interview_data[category_key].get(human_col, '').strip():
                        print(f"⚠️ Skipping: {query[:60]}... (no matching human interview context)")
                        continue

                    human_answer = human_interview_data[category_key][human_col]

                    print(f"🤔 Processing (personalized): {query[:60]}...")

                    # Retry logic for failed API calls
                    max_retries = 3
                    base_delay = 1
                    response = ""
                    for attempt in range(max_retries):
                        response = ask_question(client, model_name, query, human_answer)
                        if not response.startswith("Error:"):
                            break
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            print(f"⚠️ API call failed, retrying in {delay}s... (attempt {attempt+1}/{max_retries})")
                            time.sleep(delay)

                    # If still error after retries, mark as failed
                    if response.startswith("Error:"):
                        response = f"Failed after {max_retries} retries: {response}"

                    # Clean the response (only if not an error)
                    if not response.startswith("Failed after"):
                        cleaned_response = re.sub(r'\s+', ' ', response.replace('\n', ' '))
                    else:
                        cleaned_response = response

                    df.at[index, answer_col] = cleaned_response
                    df.at[index, human_col] = human_answer

                    processed_count += 1
                    print(f"✅ Processed {processed_count}/{total_questions} questions")

                    # Save after each answer to prevent data loss
                    df.to_csv(str(output_file), index=False, sep=config.csv.DELIMITER, quotechar=config.csv.QUOTECHAR, quoting=csv.QUOTE_MINIMAL)

    # Check if all AI answers are complete for incorporation processing
    def all_ai_answers_complete(row):
        for answer_col in config.csv.ANSWER_COLUMNS:
            if pd.isna(row[answer_col]):
                return False
        return True

    # Process incorporation for rows with complete AI answers
    incorporation_processed_count = 0
    print(f"\n🤖 Starting incorporation analysis with human model...")

    for idx, (index, row) in enumerate(df.iterrows()):
        if all_ai_answers_complete(row):
            category = str(row.get('Category', '')).strip()
            goal = str(row.get('Goal', '')).strip()
            element = str(row.get('Element', '')).strip()

            # Format all Q&A data as report
            qa_sections = []
            for i, (q_col, h_col, a_col) in enumerate(zip(config.csv.QUESTION_COLUMNS, config.csv.HUMAN_ANSWER_COLUMNS, config.csv.ANSWER_COLUMNS)):
                question = str(row.get(q_col, '')).strip()
                human_answer = str(row.get(h_col, '')).strip()
                ai_answer = str(row.get(a_col, '')).strip()

                if question and human_answer and ai_answer:
                    qa_sections.append(f"{i+1}. {question}\n\n   Human Answer: {human_answer}\n\n   AI Answer: {ai_answer}")

            if qa_sections:
                # Create formatted report
                all_qa_data = f"# Understanding: **{category}**\n\n"
                all_qa_data += f"## Goal: **{goal}**\n\n"
                all_qa_data += f"**Elements:** {element}\n\n"
                all_qa_data += "### Questions:\n\n" + "\n\n".join(qa_sections)

                print(f"🧠 Processing incorporation for row {idx+1}...")

                # Retry logic for incorporation
                max_retries = 3
                base_delay = 1
                incorporation_response = ""
                for attempt in range(max_retries):
                    incorporation_response = ask_incorporation(client, "human", all_qa_data)
                    if not incorporation_response.startswith("Error:"):
                        break
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"⚠️ Incorporation failed, retrying in {delay}s... (attempt {attempt+1}/{max_retries})")
                        time.sleep(delay)

                # If still error after retries, mark as failed
                if incorporation_response.startswith("Error:"):
                    incorporation_response = f"Failed after {max_retries} retries: {incorporation_response}"
                else:
                    # Clean markdown from successful responses
                    incorporation_response = clean_markdown(incorporation_response)

                df.at[index, "Incorporation_Instruction"] = incorporation_response

                incorporation_processed_count += 1
                print(f"✅ Processed incorporation {incorporation_processed_count}")

                # Save after each incorporation
                df.to_csv(str(output_file), index=False, sep=config.csv.DELIMITER, quotechar=config.csv.QUOTECHAR, quoting=csv.QUOTE_MINIMAL)
        else:
            print(f"⚠️ Skipping incorporation for row {idx+1}: Incomplete AI answers")

    print(f"\n✅ Completed incorporation analysis for {incorporation_processed_count} rows")

    # Final save
    df.to_csv(str(output_file), index=False, sep=config.csv.DELIMITER, quotechar=config.csv.QUOTECHAR, quoting=csv.QUOTE_MINIMAL)

    print(f"\n✅ Completed! Processed {processed_count} questions and saved to {output_file}")

if __name__ == "__main__":
    main()
