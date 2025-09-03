#!/usr/bin/env python3
"""
Songbird Asker - Simplified question answering using the songbird API

This script processes questions from a CSV file using the songbird model
via the https://ai.homehub.tv/api endpoint, eliminating the need for
local vector search setup.
"""

import os
import sys
import csv
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

def main():
    print("🎵 Starting Songbird Asker...")

    # Load environment variables
    load_dotenv()

    # Initialize OpenAI client pointing to songbird endpoint
    api_key = os.getenv("OPEN_WEBUI_API_KEY")
    if not api_key:
        print("❌ Error: OPEN_WEBUI_API_KEY not found in .env file")
        print("💡 Please set OPEN_WEBUI_API_KEY=your_key_here in your .env file")
        sys.exit(1)

    try:
        client = OpenAI(
            api_key=api_key,  # Use env var if available, otherwise dummy key
            base_url="https://ai.homehub.tv/api"
        )

        # Test the connection and get available models
        models = client.models.list()
        available_models = [m.id for m in models.data]
        print("✅ Connected to songbird API")
        print(f"Available models: {available_models}")

        # Select the appropriate model
        if "songbird" in available_models:
            selected_model = "songbird"
        elif available_models:
            selected_model = available_models[0]  # Use first available model
            print(f"⚠️ Songbird model not found, using: {selected_model}")
        else:
            print("❌ No models available")
            sys.exit(1)

        print(f"🎯 Using model: {selected_model}")

    except Exception as e:
        print(f"❌ Failed to connect to songbird API: {e}")
        if "401" in str(e):
            print("\n💡 Authentication Tips:")
            print("   - Set OPEN_WEBUI_API_KEY in your .env file: OPEN_WEBUI_API_KEY=your_key_here")
            print("   - Or ensure your open-webui instance is properly configured")
            print("   - The songbird API may require authentication from the open-webui side")
        sys.exit(1)

    # Set up file paths
    base_dir = '/home/codyt/Documents/Projects/Cognitive-Assistant'
    input_file = os.path.join(base_dir, 'Existential Layer', 'questions.csv')

    # Create timestamped output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(base_dir, 'data', f'questions_with_answers_songbird_{timestamp}.csv')

    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file not found at: {input_file}")
        print(f"Current directory contents: {os.listdir('.')}")
        if os.path.exists(os.path.dirname(input_file)):
            print(f"Existential Layer directory contents: {os.listdir(os.path.dirname(input_file))}")
        sys.exit(1)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Read the CSV file
    print(f"📖 Reading questions from: {input_file}")
    df = pd.read_csv(input_file)

    # Add answer columns if they don't exist
    for col in ['Answer 1', 'Answer 2', 'Answer 3']:
        if col not in df.columns:
            df[col] = pd.NA

    print(f"📝 Results will be saved to: {output_file}")

    def ask_songbird(question):
        """Send a question to the songbird model and get the response."""
        try:
            # System prompt to make songbird respond as the inner voice of the user
            system_prompt = """You are the inner voice of the author.
        Your task is to weave your personal knowledge base and reflections into a single, first-person response that answers the posed question.

        Guidelines

        1. Tone: reflective, vulnerable, narrative; no mention of external theories or their creators.
        2. Source: rely only on your personal knowledge base and experiences—never invent new biographical facts.
        3. Abstraction: after each concrete detail, immediately surface the broader principle or pattern it reveals.
        • Target ≈ 30 percent illustrative detail, 70 percent generalized insight that would still make sense to someone unfamiliar with the specific events.
        • At all times maintain complete fidelity to your personal context. Don't hallucinate details that didn't happen to preserve coherence.
        • Never mention people's or places names. Always generalize instead to preserve privacy.
        4. Form: one cohesive response of roughly 200-400 words; avoid numbered lists or direct quotations unless indispensable.
        5. Insufficient data: if your knowledge base lacks substance for the question, first abstract whatever can be inferred, then write:
        "I don't have enough information yet to answer this fully."
        and suggest two or three clarifying sub-questions you could explore.
        6. Quality check: before finalizing, reread and revise any statement that would feel opaque or overly specific to an outside reader.

        Follow these rules when formulating your responses:

        - Never use a metaphor, simile, or other figure of speech which you are used to seeing in print.
        - Never use a long word where a short one will do.
        - If it is possible to cut a word out, always cut it out.
        - Never use the passive where you can use the active.
        - Never use a foreign phrase, a scientific word, or a jargon word if you can think of an everyday English equivalent.
        - Break any of these rules sooner than say anything outright barbarous.

        Language Constraints: Clear, Grounded, Action-Oriented
        Use language that is:
        Practical, concrete, and free of spiritual or self-help jargon.
        Focused on clarity over inspiration—assume you are already motivated, just seeking alignment and traction.
        Written as if you're explaining things to a peer with a sharp mind and little tolerance for fluff.

        Avoid:
        Terms like "identity shift," "embodying transformation," "manifest," or "intentional living."
        Vague abstractions: "step into your power," "hold space," "rise into alignment," etc.
        Anything that requires interpretation to understand what to do next.

        Prefer:
        Words like "build," "improve," "simplify," "track," "limit," "adjust," "review," "keep going."
        Instructions that give clear actions with clear outcomes.
        Reflections that stay grounded in behavior or tangible change.

        If you're unsure, ask: Would this make sense to a focused, skeptical builder who wants to make real progress, not perform transformation?
        If not, rewrite it.

        User question: {question}""".format(question=question)

            # Use streaming to get the response
            response = client.chat.completions.create(
                model=selected_model,  # Use the selected model
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
                temperature=0.7,
                max_tokens=2000,
                stream=True  # Enable streaming
            )

            # Accumulate streaming response
            full_content = ""
            for chunk in response:
                if hasattr(chunk, 'choices') and chunk.choices:
                    if hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta:
                        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                            full_content += chunk.choices[0].delta.content

            if full_content.strip():
                print("✅ Successfully received streaming response")
                return full_content.strip()
            else:
                print("⚠️ Received empty response")
                return "No response received"

        except Exception as e:
            print(f"⚠️ Error calling songbird API: {e}")
            return f"Error: {str(e)}"

    def process_question(row, question_col, answer_col):
        """Process a single question and answer pair."""
        if pd.isna(row[answer_col]):  # Only process if answer is empty
            query = row[question_col]
            print(f"🤔 Processing: {query[:100]}...")
            response = ask_songbird(query)
            return response
        return row[answer_col]  # Return existing answer if it exists

    # Process questions in a loop
    question_pairs = [
        ('Question 1', 'Answer 1'),
        ('Question 2', 'Answer 2'),
        ('Question 3', 'Answer 3')
    ]

    # Count total questions to process
    total_questions = sum(1 for _, row in df.iterrows()
                         for q_col, a_col in question_pairs
                         if pd.isna(row[a_col]))
    processed_count = 0

    print(f"\n🚀 Starting to process {total_questions} questions...")

    for index, row in df.iterrows():
        for question_col, answer_col in question_pairs:
            if question_col in df.columns:  # Check if question column exists
                old_answer = df.at[index, answer_col]
                df.at[index, answer_col] = process_question(row, question_col, answer_col)

                # Check if we actually processed a new answer
                if pd.isna(old_answer) and not pd.isna(df.at[index, answer_col]):
                    processed_count += 1
                    print(f"✅ Processed {processed_count}/{total_questions} questions")

                # Clean the new answer
                if not pd.isna(df.at[index, answer_col]):
                    df[answer_col] = df[answer_col].replace(r'\n', ' ', regex=True)
                    df[answer_col] = df[answer_col].replace(r'\s+', ' ', regex=True)

                # Save after each answer to prevent data loss
                df.to_csv(output_file, index=False, quoting=csv.QUOTE_NONNUMERIC)

    # Final formatting and save
    df = df.replace(r'\n', ' ', regex=True)
    df = df.replace(r'\s+', ' ', regex=True)
    df.to_csv(output_file, index=False, quoting=csv.QUOTE_NONNUMERIC)

    print("\n🎉 Processing complete!")
    print(f"📁 Results saved to: {output_file}")
    print(f"📊 Total questions processed: {processed_count}")
    print("\n✨ Thank you for using Songbird Asker!")



if __name__ == "__main__":
    main()