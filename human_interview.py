#!/usr/bin/env python3
"""
Human Interview Process - Interactive Q&A Session

This script conducts an automated interview process using questions from a CSV file.
It prompts users to answer questions interactively and saves their responses to a
timestamped output file.

Features:
- Interactive question asking with category context
- Support for typing or dictation input
- Progress tracking and session resume
- Timestamped output files
- Integration with existing configuration system

Usage:
    python human_interview.py                    # Start new interview
    python human_interview.py --resume           # Resume previous session
    python human_interview.py --help             # Show help
"""

import os
import csv
import pandas as pd
import argparse
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path

# Import config from current directory
from config import config

def get_latest_interview_file() -> Optional[Path]:
    """Find the most recent interview output file."""
    try:
        pattern = "human_interview_*.csv"
        files = list(config.paths.DATA_DIR.glob(pattern))
        if files:
            return max(files, key=lambda f: f.stat().st_mtime)
        return None
    except Exception:
        return None

def load_existing_answers(output_file: Path) -> Dict[str, Dict[str, str]]:
    """Load existing answers from a previous interview session."""
    if not output_file.exists():
        return {}

    try:
        df = pd.read_csv(output_file)
        answers = {}

        for _, row in df.iterrows():
            category_key = f"{row['Category']}|{row['Goal']}|{row['Element']}"
            answers[category_key] = {
                'Answer 1': str(row.get('Human_Answer 1', '')).strip() if pd.notna(row.get('Human_Answer 1', '')) else '',
                'Answer 2': str(row.get('Human_Answer 2', '')).strip() if pd.notna(row.get('Human_Answer 2', '')) else '',
                'Answer 3': str(row.get('Human_Answer 3', '')).strip() if pd.notna(row.get('Human_Answer 3', '')) else ''
            }

        return answers
    except Exception as e:
        print(f"⚠️ Warning: Could not load existing answers: {e}")
        return {}

def save_answers_to_csv(questions_df: pd.DataFrame, answers: Dict[str, Dict[str, str]], output_file: Path):
    """Save the complete interview data to CSV."""
    # Create a copy of the questions dataframe
    output_df = questions_df.copy()

    # Add answer columns
    for col in config.csv.ANSWER_COLUMNS:
        if col not in output_df.columns:
            output_df[col] = ''

    # Fill in the answers
    for idx, row in output_df.iterrows():
        category_key = f"{row['Category']}|{row['Goal']}|{row['Element']}"
        if category_key in answers:
            for i, answer_col in enumerate(config.csv.ANSWER_COLUMNS, 1):
                answer_key = f'Answer {i}'
                if answer_key in answers[category_key] and answers[category_key][answer_key]:
                    output_df.at[idx, answer_col] = answers[category_key][answer_key]

    # Save to CSV
    output_df.to_csv(str(output_file), index=False, quoting=csv.QUOTE_NONNUMERIC)

def ask_question_interactive(question: str, category_context: str, question_number: int) -> str:
    """Ask a single question interactively and get user response."""
    print("\n" + "="*80)
    print(f"📂 Category: {category_context}")
    print(f"❓ Question {question_number}: {question}")
    print("="*80)

    print("\n💭 Take your time to think about your answer. When ready, type or dictate your response.")
    print("💡 Press Enter twice (blank line) to finish your answer.")
    print("📝 Your response:")

    # Collect multi-line input
    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "" and lines and lines[-1].strip() == "":
                # Two consecutive empty lines end input
                break
            lines.append(line)
        except KeyboardInterrupt:
            print("\n\n⏹️  Interview paused. You can resume later with --resume")
            return ""
        except EOFError:
            # Handle Ctrl+D
            break

    # Join lines and clean up
    answer = "\n".join(lines).strip()

    # Remove the extra blank line at the end if present
    if answer.endswith("\n\n"):
        answer = answer[:-1]

    return answer

def conduct_interview(questions_df: pd.DataFrame, existing_answers: Dict[str, Dict[str, str]] = None) -> Dict[str, Dict[str, str]]:
    """Conduct the full interview process."""
    if existing_answers is None:
        existing_answers = {}

    answers = existing_answers.copy()
    total_questions = len(questions_df) * 3
    answered_count = sum(1 for category_answers in answers.values()
                        for answer in category_answers.values() if answer.strip())

    print("🎯 Human Interview Process")
    print(f"📊 Total questions: {total_questions}")
    print(f"✅ Already answered: {answered_count}")
    print(f"⏳ Remaining: {total_questions - answered_count}")
    print("\n💡 Instructions:")
    print("   - Take your time with each answer")
    print("   - Be honest and reflective")
    print("   - Press Ctrl+C at any time to pause and resume later")
    print("   - Press Enter twice on an empty line to finish an answer")
    print("\n🚀 Starting interview...\n")

    for idx, row in questions_df.iterrows():
        category = row['Category']
        goal = row['Goal']
        element = row['Element']

        category_context = f"{category} → {goal}"
        category_key = f"{category}|{goal}|{element}"

        # Initialize answers for this category if not exists
        if category_key not in answers:
            answers[category_key] = {'Answer 1': '', 'Answer 2': '', 'Answer 3': ''}

        print(f"\n🎯 Section {idx + 1}/{len(questions_df)}: {category}")

        # Ask each question in this category
        for q_num in range(1, 4):
            question_col = f'Question {q_num}'
            answer_col = f'Answer {q_num}'

            # Skip if already answered
            if answers[category_key][answer_col].strip():
                print(f"✅ Question {q_num}: Already answered (skipping)")
                continue

            question = row[question_col]
            answer = ask_question_interactive(question, category_context, q_num)

            if answer.strip():  # Only save non-empty answers
                answers[category_key][answer_col] = answer
                answered_count += 1
                print(f"✅ Answer recorded! Progress: {answered_count}/{total_questions}")
            else:
                print("⏭️  Question skipped (no answer provided)")

    return answers

def main():
    parser = argparse.ArgumentParser(
        description="Human Interview Process - Interactive Q&A Session",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python human_interview.py                    # Start new interview
  python human_interview.py --resume           # Resume previous session
  python human_interview.py --output my_answers.csv  # Custom output file

Instructions:
- Answer questions thoughtfully and honestly
- Press Enter twice (blank line) to finish each answer
- Press Ctrl+C to pause and resume later with --resume
        """
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume the most recent interview session"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Custom output filename (without path)"
    )
    parser.add_argument(
        "--questions-file",
        type=str,
        help="Path to questions CSV file (default: use config)"
    )

    args = parser.parse_args()

    print("🎯 Human Interview Process")
    print("=" * 50)

    # Validate configuration
    issues = config.validate()
    if issues:
        print("❌ Configuration issues found:")
        for issue in issues:
            print(f"   - {issue}")
        return

    # Set up file paths
    questions_file = Path(args.questions_file) if args.questions_file else config.paths.QUESTIONS_CSV

    # Check if input file exists
    if not questions_file.exists():
        print(f"❌ Error: Questions file not found at: {questions_file}")
        return

    # Determine output file
    if args.output:
        output_file = config.paths.DATA_DIR / args.output
    elif args.resume:
        latest_file = get_latest_interview_file()
        if latest_file:
            output_file = latest_file
            print(f"📂 Resuming from: {output_file}")
        else:
            print("❌ No previous interview file found to resume")
            return
    else:
        # Create new timestamped output file
        timestamp = datetime.now().strftime(config.output.TIMESTAMP_FORMAT)
        output_filename = config.output.HUMAN_INTERVIEW_PATTERN.format(timestamp=timestamp)
        output_file = config.paths.DATA_DIR / output_filename

    # Load existing answers if resuming
    existing_answers = {}
    if args.resume and output_file.exists():
        existing_answers = load_existing_answers(output_file)
        if existing_answers:
            print(f"📖 Loaded {len(existing_answers)} existing answer sets")

    # Read questions
    print(f"📖 Reading questions from: {questions_file}")
    questions_df = pd.read_csv(questions_file)

    # Conduct the interview
    answers = existing_answers.copy()  # Initialize answers variable
    try:
        answers = conduct_interview(questions_df, existing_answers)

        # Save final results
        save_answers_to_csv(questions_df, answers, output_file)

        # Count final statistics
        total_answers = sum(1 for category_answers in answers.values()
                           for answer in category_answers.values() if answer.strip())

        print("\n" + "="*80)
        print("🎉 Interview Complete!")
        print(f"📁 Results saved to: {output_file}")
        print(f"📊 Total answers recorded: {total_answers}")
        print("💡 You can now use these answers to build your Existential Layer!")

    except KeyboardInterrupt:
        print("\n\n⏹️  Interview interrupted. Saving progress...")
        save_answers_to_csv(questions_df, answers, output_file)
        print(f"💾 Progress saved to: {output_file}")
        print("🔄 You can resume later with: python human_interview.py --resume")

    except Exception as e:
        print(f"\n❌ Error during interview: {e}")
        print("💾 Attempting to save any progress...")
        try:
            save_answers_to_csv(questions_df, answers, output_file)
            print(f"💾 Emergency save completed: {output_file}")
        except Exception as save_error:
            print(f"❌ Could not save progress: {save_error}")

if __name__ == "__main__":
    main()
