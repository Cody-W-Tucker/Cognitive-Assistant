#!/usr/bin/env python3
"""
Unified Creator - Combined prompt creation and combination system

This script creates intermediate files at each stage of prompt development:

BASELINE MODE (--mode baseline):
├── unique_responses.md      # Raw baseline responses (no filtering needed)
├── baseline_bio.md          # Initial existential layer summary
└── main-baseline.md         # Final refined system prompt

LLM-FILTERED MODE (--mode llm-filtered):
├── unique_responses.md      # LLM-filtered unique personal content
├── llm_filtered_bio.md      # Initial existential layer summary
└── main-llm-filtered.md     # Final refined system prompt

COMBINE MODE (--mode combine):
└── prompt.md                # Combined final prompt from prompt parts

All files are saved to the prompts/ directory.

Usage:
    python unified_creator.py --mode baseline      # Create baseline pipeline
    python unified_creator.py --mode llm-filtered  # Create filtered pipeline
    python unified_creator.py --mode combine       # Combine prompt parts
    python unified_creator.py --help               # Show help
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Literal, TypedDict, Tuple, Dict, Any
from datetime import datetime

# Import config from current directory
from config import config, get_redaction_function, get_most_recent_file

import csv
from openai import AsyncOpenAI
import tiktoken

# Use xAI client instead
openai_client = AsyncOpenAI(
    api_key=config.api.XAI_API_KEY,
    base_url=config.api.XAI_BASE_URL
)

# Initialize tokenizer for token counting with Grok-4 support
if "grok" in config.api.XAI_MODEL.lower():
    # Assume o200k_base for Grok models
    tokenizer = tiktoken.get_encoding("o200k_base")
else:
    # Fallback
    tokenizer = tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken."""
    return len(tokenizer.encode(text))

def simple_chunk_by_tokens(text: str, max_tokens: int = 10000) -> List[str]:
    """
    Simple token-based chunking.

    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk

    Returns:
        List of text chunks
    """
    if count_tokens(text) <= max_tokens:
        return [text]

    chunks = []
    words = text.split()
    current_chunk = []
    current_tokens = 0

    for word in words:
        word_tokens = count_tokens(word + " ")
        if current_tokens + word_tokens > max_tokens and current_chunk:
            # Save current chunk
            chunk_text = " ".join(current_chunk)
            chunks.append(chunk_text)
            current_chunk = [word]
            current_tokens = word_tokens
        else:
            current_chunk.append(word)
            current_tokens += word_tokens

    # Add final chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    print(f"📊 Split {count_tokens(text)} tokens into {len(chunks)} chunks")
    return chunks

async def call_llm(prompt: str, **kwargs) -> str:
    """
    Direct xAI API call using Grok-4.
    """
    try:
        print(f"🔄 Using Grok-4 with Chat Completions API: {config.api.XAI_MODEL}")
        print(f"🔑 API Key configured: {'Yes' if config.api.XAI_API_KEY else 'No'}")
        print(f"🌐 Base URL: {config.api.XAI_BASE_URL}")

        messages = [{"role": "user", "content": prompt}]

        response = await openai_client.chat.completions.create(
            model=config.api.XAI_MODEL,
            messages=messages,
            temperature=1,
            max_completion_tokens=kwargs.get('max_tokens', config.llm.MAX_COMPLETION_TOKENS)
        )

        # Extract content from response
        if hasattr(response, 'choices') and response.choices and response.choices[0].message:
            content = response.choices[0].message.content
            if content:
                print(f"✅ Grok-4 response successful: {len(content)} chars")
                return content.strip()
            else:
                print("⚠️ Grok-4 returned empty content")
                return ""
        else:
            print("❌ Unexpected Grok-4 response structure")
            return ""

    except Exception as e:
        error_msg = str(e)
        print(f"❌ LLM call failed with exception type: {type(e).__name__}")
        print(f"❌ Error message: {error_msg}")
        if "rate_limit" in error_msg.lower() or "429" in error_msg:
            print(f"🚦 Rate limit hit: {e}")
            print("💡 Consider upgrading your xAI plan or waiting before retrying")
        else:
            print(f"❌ LLM call failed: {e}")
        return ""



async def process_large_context(context: str, prompt_template: str, config_params: dict, max_tokens: int = 30000) -> str:
    """
    Process large context with simple token-based chunking.

    Args:
        context: The full context to process
        prompt_template: Template string to format
        config_params: Parameters for template formatting
        max_tokens: Maximum tokens per chunk

    Returns:
        Result from LLM processing
    """
    print(f"🔧 process_large_context called with {len(context)} chars, {len(config_params)} config params")

    # Check if we need to chunk
    context_tokens = count_tokens(context)
    print(f"📊 Context tokens: {context_tokens}, max_tokens: {max_tokens}")

    # For GPT-5 optimization, use larger chunks when possible
    if max_tokens == 30000:  # Default value, optimize for GPT-5
        max_tokens = 100000  # Use GPT-5 optimized chunk size
        print(f"📈 Optimizing for Grok-4: using {max_tokens} token chunks")

    if context_tokens <= max_tokens:
        try:
            # Format the prompt template
            all_params = {**config_params, "context": context}
            print(f"🔧 Formatting template with params: {list(all_params.keys())}")
            formatted_prompt = prompt_template.format(**all_params)
            print(f"📤 Formatted prompt: {count_tokens(formatted_prompt)} tokens")

            result = await call_llm(formatted_prompt)
            if result and result.strip():
                print(f"✅ LLM call successful: {len(result)} chars")
                return result.strip()
            else:
                print("❌ LLM call returned empty result")
                return ""
        except Exception as e:
            print(f"❌ Error in process_large_context: {e}")
            return ""

    # Chunk the context
    chunks = simple_chunk_by_tokens(context, max_tokens)
    print(f"📦 Chunking into {len(chunks)} pieces")

    # Process chunks sequentially
    chunk_results = []
    for i, chunk in enumerate(chunks):
        print(f"🔄 Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
        try:
            all_params = {**config_params, "context": chunk}
            formatted_prompt = prompt_template.format(**all_params)
            chunk_result = await call_llm(formatted_prompt)
            if chunk_result and chunk_result.strip():
                chunk_results.append(chunk_result.strip())
                print(f"✅ Chunk {i+1} processed: {len(chunk_result)} chars")
            else:
                print(f"❌ Chunk {i+1} returned empty result")
        except Exception as e:
            print(f"❌ Error processing chunk {i+1}: {e}")

    if not chunk_results:
        print("❌ No valid chunk results")
        return ""

    if len(chunk_results) == 1:
        return chunk_results[0]

    # Simple combination - just join results
    combined = "\n\n".join(chunk_results)
    print(f"🔗 Combined {len(chunk_results)} results: {len(combined)} chars")
    return combined


def load_comparison_data() -> Tuple[str, str]:
    """
    Load the most recent personalized and baseline CSV files for comparison.

    Returns:
        Tuple of (personalized_content, baseline_content) as formatted strings
    """
    try:
        personalized_csv = get_most_recent_file("questions_with_answers_songbird_*.csv")
        baseline_csv = get_most_recent_file("questions_with_answers_baseline_gpt5_*.csv")
    except FileNotFoundError as e:
        raise FileNotFoundError(str(e))

    print(f"📁 Loading data files: {os.path.basename(personalized_csv)}, {os.path.basename(baseline_csv)}")

    # Load CSV files using standard Python CSV
    def load_csv_data(csv_path: Path) -> List[Dict[str, str]]:
        """Load CSV data using standard Python CSV module."""
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(
                f,
                delimiter=config.csv.DELIMITER,
                quotechar=config.csv.QUOTECHAR,
                fieldnames=config.csv.FIELDNAMES
            )
            # Convert to list and skip header
            data = list(reader)[1:]
            # Convert to document-like format for compatibility
            docs = []
            for row in data:
                # Create a structured page_content that matches what the processing code expects
                # Format: Category\nGoal\nElement\nQuestion1\nAnswer1\nQuestion2\nAnswer2\nQuestion3\nAnswer3
                page_content = f"{row.get('Category', '')}\n{row.get('Goal', '')}\n{row.get('Element', '')}\n"
                page_content += f"{row.get('Question 1', '')}\n{row.get('Answer 1', '')}\n"
                page_content += f"{row.get('Question 2', '')}\n{row.get('Answer 2', '')}\n"
                page_content += f"{row.get('Question 3', '')}\n{row.get('Answer 3', '')}"
                docs.append(type('Document', (), {'page_content': page_content})())
            return docs

    personalized_data = load_csv_data(personalized_csv)
    baseline_data = load_csv_data(baseline_csv)

    # Format as readable text for LLM with Q&A pairs
    personalized_sections = []
    baseline_sections = []

    for i, (p_doc, b_doc) in enumerate(zip(personalized_data, baseline_data)):
        # Process personalized data
        p_lines = p_doc.page_content.split('\n')
        if len(p_lines) >= 9:  # Ensure we have all fields (9 lines total)
            category = p_lines[0]

            # Extract personalized questions and answers
            p_qa_pairs = []
            for j in range(3):  # 3 question/answer pairs
                q_idx = 3 + (j * 2)  # Questions at indices 3, 5, 7
                a_idx = 4 + (j * 2)  # Answers at indices 4, 6, 8
                if q_idx < len(p_lines) and a_idx < len(p_lines):
                    question = p_lines[q_idx].strip()
                    answer = p_lines[a_idx].strip()
                    if question and answer:
                        p_qa_pairs.append(f"Q: {question}\nA: {answer}")

            if p_qa_pairs:
                personalized_sections.append(f"## {category}\n" + "\n\n".join(p_qa_pairs))

        # Process baseline data
        b_lines = b_doc.page_content.split('\n')
        if len(b_lines) >= 9:  # Ensure we have all fields (9 lines total)
            category = b_lines[0]

            # Extract baseline questions and answers
            b_qa_pairs = []
            for j in range(3):  # 3 question/answer pairs
                q_idx = 3 + (j * 2)  # Questions at indices 3, 5, 7
                a_idx = 4 + (j * 2)  # Answers at indices 4, 6, 8
                if q_idx < len(b_lines) and a_idx < len(b_lines):
                    question = b_lines[q_idx].strip()
                    answer = b_lines[a_idx].strip()
                    if question and answer:
                        b_qa_pairs.append(f"Q: {question}\nA: {answer}")

            if b_qa_pairs:
                baseline_sections.append(f"## {category}\n" + "\n\n".join(b_qa_pairs))

    personalized_content = "\n\n".join(personalized_sections)
    baseline_content = "\n\n".join(baseline_sections)

    return personalized_content, baseline_content

def load_baseline_data() -> str:
    """
    Load the most recent baseline CSV file for baseline prompt creation.

    Returns:
        Formatted baseline content as string containing both questions and answers
    """
    try:
        baseline_csv = get_most_recent_file("questions_with_answers_baseline_gpt5_*.csv")
    except FileNotFoundError:
        raise FileNotFoundError("No baseline CSV files found")

    print(f"📁 Loading baseline data: {os.path.basename(baseline_csv)}")

    # Load CSV using standard Python CSV module
    def load_csv_data(csv_path: Path) -> List[Dict[str, str]]:
        """Load CSV data using standard Python CSV module."""
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(
                f,
                delimiter=config.csv.DELIMITER,
                quotechar=config.csv.QUOTECHAR,
                fieldnames=config.csv.FIELDNAMES
            )
            # Convert to list and skip header
            data = list(reader)[1:]
            # Convert to document-like format for compatibility
            docs = []
            for row in data:
                # Create structured page_content with newlines (consistent with working version)
                # Format: Category\nGoal\nElement\nQuestion1\nAnswer1\nQuestion2\nAnswer2\nQuestion3\nAnswer3
                page_content = f"{row.get('Category', '')}\n{row.get('Goal', '')}\n{row.get('Element', '')}\n"
                page_content += f"{row.get('Question 1', '')}\n{row.get('Answer 1', '')}\n"
                page_content += f"{row.get('Question 2', '')}\n{row.get('Answer 2', '')}\n"
                page_content += f"{row.get('Question 3', '')}\n{row.get('Answer 3', '')}"
                docs.append(type('Document', (), {'page_content': page_content})())
            return docs

    data = load_csv_data(baseline_csv)

    # Format data with redaction (no need to skip header since we're not using header)
    formatted_contents = []
    redaction_count = 0

    for doc in data:  # Process all data, no header to skip
        content = doc.page_content
        # Apply concrete redaction before processing
        redacted_content = redact_sensitive_data(content)
        if redacted_content != content:
            redaction_count += 1

        # Parse the structured content to extract questions and answers
        lines = redacted_content.split('\n')
        if len(lines) >= 9:  # Ensure we have all fields (9 lines total)
            category = lines[0]
            goal = lines[1] if len(lines) > 1 else ""
            element = lines[2] if len(lines) > 2 else ""

            # Extract questions and answers - correct indices
            questions = []
            answers = []
            for i in range(3):  # 3 question/answer pairs
                q_idx = 3 + (i * 2)  # Questions at indices 3, 5, 7
                a_idx = 4 + (i * 2)  # Answers at indices 4, 6, 8
                if q_idx < len(lines) and a_idx < len(lines):
                    question = lines[q_idx].strip()
                    answer = lines[a_idx].strip()
                    if question and answer:
                        questions.append(question)
                        answers.append(answer)

            # Format as Q&A pairs
            if questions and answers:
                qa_pairs = []
                for q, a in zip(questions, answers):
                    qa_pairs.append(f"Q: {q}\nA: {a}")
                formatted_entry = f"## {category}\n" + "\n\n".join(qa_pairs)
                formatted_contents.append(formatted_entry)

    if redaction_count > 0:
        print(f"🔒 Applied redaction to {redaction_count} entries")

    # Create combined context with questions and answers
    combined_context = "\n\n".join(formatted_contents)
    print(f"📊 Loaded {len(formatted_contents)} Q&A sections ({len(combined_context)} characters)")

    return combined_context

def create_baseline_prompts():
    """Create system prompts from baseline (generic AI) responses."""
    print("🧪 Creating Baseline System Prompts...")

    # Load baseline data
    combined_context = load_baseline_data()

    # Store prompt templates for direct use
    initial_summary_template = config.prompts.create_initial_prompt
    refine_template = config.prompts.refine_template

    # Define the state of the graph - BASELINE VERSION (no filtering)
    class State(TypedDict):
        contents: List[str]
        combined_context: str
        refinement_step: int
        summary: str

    # Generate initial existential layer summary from baseline content
    async def generate_initial_summary(combined_context: str) -> str:
        print("📝 Generating initial existential layer summary...")

        # Process context with token-based chunking
        config_params = {}
        summary = await process_large_context(
            context=combined_context,
            prompt_template=initial_summary_template,
            config_params=config_params,
            max_tokens=30000
        )

        return summary

    # Multi-step refinement for baseline mode
    async def refine_summary(current_summary: str, combined_context: str, step: int) -> str:
        step_display = f"🎯 Refinement Step {step + 1}"

        print(f"{step_display}: Refining baseline system prompt...")

        # Process context with token-based chunking
        config_params = {"existing_answer": current_summary}
        summary = await process_large_context(
            context=combined_context,
            prompt_template=refine_template,
            config_params=config_params,
            max_tokens=30000
        )

        return summary

    # Run the processing with simple sequential workflow
    async def run_baseline_creation():
        step_count = 0
        initial_bio = ""
        final_summary = ""

        # Initialize file paths (will be set during processing)
        unique_path = None
        bio_path = None
        output_path = None

        # Save unique responses immediately (before processing)
        unique_filename = "unique_responses.md"
        unique_path = config.paths.OUTPUT_DIR / unique_filename
        print(f"💾 Saving unique responses to {unique_path}…")
        try:
            # In baseline mode, unique file should NOT be raw baseline context; write a minimal placeholder
            # indicating baseline has no unique elements extraction.
            with open(unique_path, "w", encoding="utf-8") as f:
                f.write("# Baseline mode: no LLM-filtered unique elements available\n")
            print(f"✅ Saved placeholder unique responses (baseline mode)")
        except Exception as e:
            print(f"❌ Error saving baseline unique responses: {e}")

        # Step 1: Generate initial summary
        initial_bio = await generate_initial_summary(combined_context)
        print(f"Step 1 Result: {len(initial_bio)} characters generated")

        # Save intermediate bio immediately after generation
        bio_filename = "baseline_bio.md"
        bio_path = config.paths.OUTPUT_DIR / bio_filename
        print(f"💾 Saving baseline bio to {bio_path}...")
        try:
            with open(bio_path, "w", encoding="utf-8") as f:
                f.write(initial_bio)
            print(f"✅ Successfully saved baseline bio ({len(initial_bio)} characters)")
        except Exception as e:
            print(f"❌ Error saving baseline bio: {e}")

        # Step 2: Refine the summary
        final_summary = await refine_summary(initial_bio, combined_context, 0)
        print(f"Step 2 Result: {len(final_summary)} characters generated")

        # Save final prompt immediately after refinement
        output_filename = config.output.MAIN_BASELINE_PROMPT
        output_path = config.paths.OUTPUT_DIR / output_filename
        print(f"💾 Saving baseline prompt to {output_path}...")
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_summary)
            print(f"✅ Successfully saved baseline prompt ({len(final_summary)} characters)")
            # Verify file was written
            if output_path.exists():
                actual_size = output_path.stat().st_size
                print(f"✅ File verification: {actual_size} bytes written")
            else:
                print(f"❌ File verification failed: {output_path} does not exist")
        except Exception as e:
            print(f"❌ Error saving baseline prompt: {e}")

        step_count = 2

        # Ensure all paths are set with fallbacks
        if unique_path is None:
            unique_filename = "unique_responses.md"
            unique_path = config.paths.OUTPUT_DIR / unique_filename
        if bio_path is None:
            bio_filename = "baseline_bio.md"
            bio_path = config.paths.OUTPUT_DIR / bio_filename
        if output_path is None:
            output_filename = config.output.MAIN_BASELINE_PROMPT
            output_path = config.paths.OUTPUT_DIR / output_filename

        print(f"Files created:")
        print(f"  🧠 Unique Responses: {unique_path}")
        print(f"  📄 Bio: {bio_path}")
        print(f"  📋 Baseline Prompt: {output_path}")
        print(f"\nProcess completed in {step_count} steps with {step_count} AI calls.")
        print("🤖 System prompt built from baseline (generic AI) responses!")

    import asyncio
    asyncio.run(run_baseline_creation())

def create_llm_filtered_prompts():
    """Create system prompts using LLM-based filtering for unique personal content."""
    print("🧠 Creating LLM-Filtered System Prompts...")

    # Load comparison data
    personalized_content, baseline_content = load_comparison_data()

    print(f"📊 Loaded {len(personalized_content)} + {len(baseline_content)} characters for analysis")

    # Store prompt templates for direct use
    filter_unique_template = config.prompts.filter_unique_content_prompt
    initial_summary_template_filtered = config.prompts.create_initial_prompt
    refine_template_filtered = config.prompts.refine_template

    # Helper: chunked processing - save ALL LLM responses as-is
    async def filter_unique_large(personalized_text: str, baseline_text: str) -> str:
        print(f"🔍 Starting content processing with {len(personalized_text)} chars personalized, {len(baseline_text)} chars baseline")

        # Use larger chunks for Grok-4 with rate limiting to handle TPM limits
        chunks = simple_chunk_by_tokens(personalized_text, max_tokens=100000)
        all_responses: List[str] = []

        for i, chunk in enumerate(chunks):
            print(f"🔎 Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")

            # Use the configured prompt template from config.py
            try:
                formatted_prompt = filter_unique_template.format(
                    baseline_content=baseline_text,
                    personalized_content=chunk
                )
                print(f"✅ Template formatting successful")
            except KeyError as e:
                print(f"❌ Template formatting failed: missing key {e}")
                print(f"Available template variables: baseline_content, personalized_content")
                return f"<!-- TEMPLATE ERROR: {e} -->"

            prompt_tokens = count_tokens(formatted_prompt)
            print(f"📤 Sending chunk {i+1} to LLM ({prompt_tokens} tokens)")
            print(f"📝 Prompt preview (first 200 chars): {formatted_prompt[:200]}...")

            # Debug: Check API key availability
            if not config.api.XAI_API_KEY:
                print("❌ XAI_API_KEY not found in config!")
                return f"<!-- API KEY ERROR: XAI_API_KEY not configured -->"

            # Add delay between requests to respect rate limits
            if i > 0:  # Don't delay the first request
                delay_seconds = min(10, max(2, prompt_tokens // 10000))  # Scale delay with token count
                print(f"⏳ Rate limiting: waiting {delay_seconds} seconds...")
                import asyncio
                await asyncio.sleep(delay_seconds)

            part = await call_llm(formatted_prompt)

            # Save EVERY response as-is, no filtering
            if part:
                print(f"✅ Chunk {i+1} returned {len(part)} chars")
                all_responses.append(part)
                print(f"📝 Saved chunk {i+1} response")
            else:
                print(f"❌ Chunk {i+1} returned empty result")
                # Even save empty responses with a marker
                all_responses.append(f"<!-- EMPTY RESPONSE FOR CHUNK {i+1} -->")

        # If we have no responses at all, return empty
        if not all_responses:
            print("❌ No responses received")
            return ""

        print(f"📊 Collected {len(all_responses)}/{len(chunks)} responses")
        total_chars = sum(len(r) for r in all_responses)
        print(f"📊 Total content: {total_chars} chars across {len(all_responses)} responses")

        # Simply concatenate ALL responses with clear separators
        final_result = "\n\n" + "="*80 + "\n".join([
            f"CHUNK {i+1} RESPONSE:\n{response}"
            for i, response in enumerate(all_responses)
        ]) + "\n" + "="*80

        print(f"📋 Final concatenated result: {len(final_result)} chars")
        return final_result

    # Define the state of the graph - LLM-BASED FILTERING VERSION
    class State(TypedDict):
        contents: List[str]
        combined_context: str
        filtered_context: str  # LLM-filtered unique content
        personalized_context: str  # Full personalized Q&A data
        refinement_step: int
        summary: str

    # Step 1: LLM-based filtering of unique content
    async def filter_content_step(personalized_content: str, baseline_content: str) -> str:
        print("🧠 Step 1: LLM-based filtering of unique personal content...")

        # Use LLM to filter unique content (chunked for large inputs)
        filtered_context = await filter_unique_large(
            personalized_text=personalized_content,
            baseline_text=baseline_content,
        )

        print(f"✅ LLM filtering complete: {len(filtered_context)} characters")

        return filtered_context if filtered_context else ""

    # Step 2: Generate initial existential layer summary from filtered content
    async def generate_initial_summary(filtered_context: str) -> str:
        print("📝 Step 2: Generating initial existential layer summary...")
        print(f"📊 Input context length: {len(filtered_context)} characters")

        if not filtered_context or not filtered_context.strip():
            print("❌ ERROR: No filtered context provided to generate_initial_summary")
            return ""

        # Process context with token-based chunking
        # Note: config_params is empty because the template uses {context} directly
        config_params = {}

        print("🔄 Calling process_large_context with filtered content...")
        summary = await process_large_context(
            context=filtered_context,
            prompt_template=initial_summary_template_filtered,
            config_params=config_params,
            max_tokens=30000
        )

        if summary and summary.strip():
            print(f"✅ Initial summary generated: {len(summary)} characters")
            return summary.strip()
        else:
            print("❌ ERROR: process_large_context returned empty result")
            return ""

    # Simple 2-step refinement
    async def refine_summary(current_summary: str, filtered_context: str, personalized_context: str, step: int) -> str:
        step_display = f"🎯 Refinement Step {step + 1}"
        print(f"{step_display}: Starting refinement...")

        if step == 0:
            # Step 1: Refine with filtered content only (fast, focused)
            print(f"{step_display}: Refining with unique elements...")
            added_data_context = f"""# Unique Personal Elements (Filtered)
{filtered_context}
"""

        else:  # step == 1
            # Step 2: Refine with full personalized context
            print(f"{step_display}: Refining with full personalized context...")
            added_data_context = f"""# Full Personalized Context (Complete Q&A)
{personalized_context}
"""

        # Process context with token-based chunking
        # The template expects {existing_answer} and {context} separately
        config_params = {
            "existing_answer": current_summary,
            "context": added_data_context
        }

        print(f"🔄 Processing refinement with {len(added_data_context)} chars of added data...")
        summary = await process_large_context(
            context=added_data_context,  # This is the {context} variable in the template
            prompt_template=refine_template_filtered,
            config_params=config_params,
            max_tokens=30000
        )

        if summary and summary.strip():
            print(f"✅ Refinement step {step + 1} completed: {len(summary)} characters")
            return summary.strip()
        else:
            print(f"❌ ERROR: Refinement step {step + 1} returned empty result")
            return current_summary  # Return original summary as fallback

    # Run the processing with simple sequential workflow
    async def run_llm_filtered_creation():
        step_count = 0
        filtered_responses = ""
        initial_bio = ""
        final_summary = ""

        # Initialize file paths (will be set during processing)
        unique_path = None
        bio_path = None
        assistant_path = None

        # Step 1: Filter unique content
        filtered_responses = await filter_content_step(personalized_content, baseline_content)

        # Save unique responses immediately after filtering
        unique_filename = "unique_responses.md"
        unique_path = config.paths.OUTPUT_DIR / unique_filename
        try:
            with open(unique_path, "w", encoding="utf-8") as f:
                if filtered_responses.strip():
                    f.write(filtered_responses)
                else:
                    f.write("# No unique elements extracted.\n")
            print(f"💾 Saved unique elements → {unique_path} ({len(filtered_responses)} chars)")
        except Exception as e:
            print(f"❌ Error saving unique responses: {e}")

        # Step 2: Generate initial summary
        initial_bio = await generate_initial_summary(filtered_responses)
        print(f"Step 2 generated {len(initial_bio)} chars")

        # Save intermediate bio immediately after generation
        bio_filename = "llm_filtered_bio.md"
        bio_path = config.paths.OUTPUT_DIR / bio_filename
        print(f"💾 Saving bio to {bio_path}...")
        try:
            with open(bio_path, "w", encoding="utf-8") as f:
                f.write(initial_bio)
            print(f"✅ Successfully saved bio ({len(initial_bio)} characters)")
        except Exception as e:
            print(f"❌ Error saving bio: {e}")

        # Step 3: First refinement (with filtered content)
        refined_summary_1 = await refine_summary(initial_bio, filtered_responses, personalized_content, 0)
        print(f"Step 3 generated {len(refined_summary_1)} chars")

        # Step 4: Second refinement (with full personalized context)
        final_summary = await refine_summary(refined_summary_1, filtered_responses, personalized_content, 1)
        print(f"Step 4 generated {len(final_summary)} chars")

        # Save final prompt to assistant folder only
        output_filename = config.output.MAIN_PROMPT
        assistant_path = config.paths.ASSISTANT_PROMPTS_DIR / output_filename

        # Ensure assistant directory exists
        assistant_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"💾 Saving final prompt to {assistant_path}...")
        try:
            with open(assistant_path, "w", encoding="utf-8") as f:
                f.write(final_summary)
            print(f"✅ Successfully saved {len(final_summary)} characters to {assistant_path}")
            # Verify file was written
            if assistant_path.exists():
                actual_size = assistant_path.stat().st_size
                print(f"✅ File verification: {actual_size} bytes written")
            else:
                print(f"❌ File verification failed: {assistant_path} does not exist")
        except Exception as e:
            print(f"❌ Error saving to assistant folder: {e}")

        step_count = 4

        # Ensure all paths are set with fallbacks
        if unique_path is None:
            unique_filename = "unique_responses.md"
            unique_path = config.paths.OUTPUT_DIR / unique_filename
        if bio_path is None:
            bio_filename = "llm_filtered_bio.md"
            bio_path = config.paths.OUTPUT_DIR / bio_filename
        if assistant_path is None:
            output_filename = config.output.MAIN_PROMPT
            assistant_path = config.paths.ASSISTANT_PROMPTS_DIR / output_filename

        print(f"Files created:")
        print(f"  🧠 Unique Responses: {unique_path}")
        print(f"  📄 Bio: {bio_path}")
        print(f"  🎯 Final Prompt: {assistant_path}")
        print(f"\nProcess completed in {step_count + 1} steps with {step_count + 1} AI calls.")  # +1 for filtering step
        print("🧠 System prompt built from LLM-curated unique personal content!")

    import asyncio
    asyncio.run(run_llm_filtered_creation())

def combine_prompts():
    """Combine existing prompt parts into final prompts."""
    print("🔧 Combining Prompt Parts...")

    import textwrap

    def load_prompts(prompts_dir):
        """Load all prompt files into a dictionary."""
        prompts = {}

        # Find all .md files recursively
        for md_file in Path(prompts_dir).rglob("*.md"):
            # Create variable name from path
            rel_path = md_file.relative_to(prompts_dir)
            var_name = str(rel_path).replace('.md', '').replace('/', '_').replace('-', '_')

            # Read file content
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    prompts[var_name] = f.read().strip()
            except Exception as e:
                print(f"Error reading {md_file}: {e}", file=sys.stderr)
                prompts[var_name] = ""

        return prompts

    # Load all prompts from prompt_parts directory
    prompts_dir = config.paths.PROMPT_PARTS_DIR
    if not prompts_dir.exists():
        print(f"❌ Error: Prompt parts directory not found at: {prompts_dir}")
        return

    prompts = load_prompts(prompts_dir)
    print(f"📁 Loaded {len(prompts)} prompt parts")

    # Add prompt structure with the template to introduce the different sections
    template = '''You are the Cognitive Assistant...

{assistant_main}

You have access to these tools:

# Tool Specs

{tools_sequential_protocol}

## Memory Tool
Store preferences/rules in Memory.

{tools_memory}

## Obsidian Tool
For reflections or ideas, save to Obsidian's Inbox or Projects folder.

{tools_obsidian}

## Todoist Tool
For actionable tasks, save to Todoist with a clear title, owner, and due date (Priority 1–4 based on urgency).

{tools_todoist}'''

    # Clean up formatting and fill template with prompt content
    template = textwrap.dedent(template).strip()
    final_prompt = template.format(**prompts)

    # Write to prompt.md file
    output_file = config.paths.PROMPTS_DIR / config.output.COMBINED_PROMPT
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_prompt)

    print(f"✅ Combined prompt saved to: {output_file}")
    print(f"📁 All prompt files are saved in: {config.paths.PROMPTS_DIR}")

def main():
    parser = argparse.ArgumentParser(
        description="Unified Creator - Combined prompt creation and combination system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python unified_creator.py --mode baseline      # Create baseline: unique_responses.md, baseline_bio.md, main-baseline.md
  python unified_creator.py --mode llm-filtered  # Create filtered: unique_responses.md, llm_filtered_bio.md, main-llm-filtered.md
  python unified_creator.py --mode combine       # Combine prompt parts into final prompt.md

All files are saved to the prompts/ directory.
        """
    )
    parser.add_argument(
        "--mode",
        choices=["baseline", "llm-filtered", "combine"],
        required=True,
        help="Creation mode to use"
    )

    args = parser.parse_args()

    print(f"🎯 Unified Creator - {args.mode} mode")
    print("=" * 50)

    # Validate configuration
    issues = config.validate()
    if issues:
        print("❌ Configuration issues found:")
        for issue in issues:
            print(f"   - {issue}")
        sys.exit(1)

    # Execute the appropriate mode
    if args.mode == "baseline":
        create_baseline_prompts()
    elif args.mode == "llm-filtered":
        create_llm_filtered_prompts()
    elif args.mode == "combine":
        combine_prompts()

if __name__ == "__main__":
    main()
