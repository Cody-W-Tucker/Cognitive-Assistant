#!/usr/bin/env python3
"""
Unified Asker - Combined question answering using baseline GPT-5 or songbird models

This script processes questions from a CSV file using either:
1. Baseline GPT-5: Uses OpenAI GPT-5 with minimal prompting for baseline comparison
2. Songbird: Uses the songbird model via OpenAI-compatible API for personalized responses

Usage:
    python unified_asker.py --model baseline    # Use GPT-5 baseline
    python unified_asker.py --model songbird    # Use songbird model (default)
    python unified_asker.py --help              # Show help
"""

import os
import csv
import pandas as pd
import argparse
from datetime import datetime
from typing import Optional

# Import config from current directory
from config import config

def setup_model_client(model_type: str):
    """Set up the appropriate model client based on type."""
    try:
        from openai import OpenAI

        if model_type == "baseline":
            client = OpenAI(api_key=config.api.OPENAI_API_KEY)
            return client, config.api.OPENAI_MODEL
        elif model_type == "songbird":
            client = OpenAI(
                api_key=config.api.OPEN_WEBUI_API_KEY,
                base_url=config.api.OPEN_WEBUI_BASE_URL
            )
            # Test connection and get available models
            models = client.models.list()
            available_models = [m.id for m in models.data]

            if "songbird" in available_models:
                selected_model = "songbird"
            elif available_models:
                selected_model = available_models[0]
                print(f"⚠️ Songbird model not found, using: {selected_model}")
            else:
                raise ValueError("No models available")

            return client, selected_model
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    except ImportError:
        print("❌ Error: OpenAI package not installed")
        print("Install with: pip install openai")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to initialize {model_type} client: {e}")
        if "401" in str(e) and model_type == "songbird":
            print("\n💡 Authentication Tips:")
            print("   - Set OPEN_WEBUI_API_KEY in your .env file")
            print("   - Or ensure your open-webui instance is properly configured")
        sys.exit(1)

def get_system_prompt(model_type: str, question: str) -> str:
    """Get the appropriate system prompt based on model type."""
    if model_type == "baseline":
        return config.prompts.baseline_system_prompt.format(question=question)
    elif model_type == "songbird":
        return config.prompts.songbird_system_prompt.format(question=question)
    else:
        raise ValueError(f"Unknown model type: {model_type}")

def ask_question(client, model_name: str, question: str, model_type: str) -> str:
    """Send a question to the specified model and get the response."""
    try:
        system_prompt = get_system_prompt(model_type, question)

        # Use streaming for songbird, direct API for baseline
        use_streaming = model_type == "songbird"

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
            temperature=config.llm.TEMPERATURE,
            max_tokens=config.llm.MAX_TOKENS if model_type == "songbird" else config.llm.MAX_COMPLETION_TOKENS,
            stream=use_streaming
        )

        if use_streaming:
            # Accumulate streaming response
            full_content = ""
            for chunk in response:
                if hasattr(chunk, 'choices') and chunk.choices:
                    if hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta:
                        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                            full_content += chunk.choices[0].delta.content
            return full_content.strip()
        else:
            # Direct response
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            else:
                return "No response received"

    except Exception as e:
        print(f"⚠️ Error calling {model_type} API: {e}")
        return f"Error: {str(e)}"

def main():
    parser = argparse.ArgumentParser(
        description="Unified Asker - Question answering with baseline or songbird models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python unified_asker.py --model baseline    # Use GPT-5 baseline
  python unified_asker.py --model songbird    # Use songbird model
  python unified_asker.py                     # Use default (songbird)
        """
    )
    parser.add_argument(
        "--model",
        choices=["baseline", "songbird"],
        default="songbird",
        help="Model type to use (default: songbird)"
    )
    parser.add_argument(
        "--questions-file",
        type=str,
        help="Path to questions CSV file (default: use config)"
    )

    args = parser.parse_args()

    print(f"🎯 Unified Asker - Using {args.model} model")
    print("=" * 50)

    # Validate configuration
    issues = config.validate()
    if issues:
        print("❌ Configuration issues found:")
        for issue in issues:
            print(f"   - {issue}")
        sys.exit(1)

    # Set up model client
    try:
        client, model_name = setup_model_client(args.model)
        print(f"✅ Connected to {args.model} API")
        print(f"🎯 Using model: {model_name}")
    except Exception as e:
        print(f"❌ Failed to set up {args.model} client: {e}")
        sys.exit(1)

    # Set up file paths
    questions_file = args.questions_file or config.paths.QUESTIONS_CSV

    # Check if input file exists
    if not questions_file.exists():
        print(f"❌ Error: Questions file not found at: {questions_file}")
        sys.exit(1)

    # Create timestamped output file
    timestamp = datetime.now().strftime(config.output.TIMESTAMP_FORMAT)
    if args.model == "baseline":
        output_filename = config.output.BASELINE_OUTPUT_PATTERN.format(timestamp=timestamp)
    else:
        output_filename = config.output.SONGBIRD_OUTPUT_PATTERN.format(timestamp=timestamp)

    output_file = config.paths.DATA_DIR / output_filename

    # Ensure output directory exists (handled by config initialization)
    print(f"📁 Using questions file: {questions_file}")
    print(f"📝 Results will be saved to: {output_file}")

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

    print(f"\n🚀 Starting to process {total_questions} questions with {args.model} model...")

    for index, row in df.iterrows():
        for question_col, answer_col in question_pairs:
            if question_col in df.columns:  # Check if question column exists
                old_answer = df.at[index, answer_col]
                if pd.isna(old_answer):  # Only process if answer is empty
                    query = row[question_col]
                    print(f"🤔 Processing {args.model}: {query[:100]}...")

                    response = ask_question(client, model_name, query, args.model)
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

    print("\n🎉 Processing complete!")
    print(f"📁 Results saved to: {output_file}")
    print(f"📊 Total questions processed: {processed_count}")
    if args.model == "baseline":
        print("\n🧪 Use this baseline data to compare with your personalized answers!")
    else:
        print("\n✨ Thank you for using Unified Asker with Songbird!")

if __name__ == "__main__":
    main()
