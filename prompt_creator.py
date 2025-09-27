#!/usr/bin/env python3
"""
Unified Creator - Human + Combine Prompt System

This script runs a full pipeline: creates prompts from human interview data, then combines prompt parts into a final prompt.

Pipeline:
1. Human Creation:
   ├── ai_interview_bio.md       # Initial AI summary from songbird responses
   ├── human_interview_bio.md    # Refined with human data
   └── main.md (in assistant/)   # Condensed final system prompt

2. Combine:
   └── prompt.md                # Combined final prompt from parts including the new main.md

Usage:
    python prompt_creator.py  # Runs full pipeline automatically

All files are saved to output/ and prompts/ directories.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Literal, TypedDict, Tuple, Dict, Any
from datetime import datetime

# Import config from current directory
from config import config, get_redaction_function, get_most_recent_file

# Get the redaction function
redact_sensitive_data = get_redaction_function()

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

        messages = [{"role": "user", "content": prompt}]

        response = await openai_client.chat.completions.create(
            model=config.api.XAI_MODEL,
            messages=messages,
            temperature=1,
            max_completion_tokens=kwargs.get('max_tokens', config.api.MAX_COMPLETION_TOKENS)
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
    print(f"🔧 process_large_context called with {len(context)} chars")

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
        print(f"🔄 Processing chunk {i+1}/{len(chunks)}")
        try:
            all_params = {**config_params, "context": chunk}
            formatted_prompt = prompt_template.format(**all_params)
            chunk_result = await call_llm(formatted_prompt)
            if chunk_result and chunk_result.strip():
                chunk_results.append(chunk_result.strip())
                print(f"✅ Chunk {i+1} processed")
            else:
                print(f"❌ Chunk {i+1} returned empty result")
                chunk_results.append("")
        except Exception as e:
            print(f"❌ Error processing chunk {i+1}: {e}")
            chunk_results.append("")

    if not chunk_results:
        print("❌ No valid chunk results")
        return ""

    if len(chunk_results) == 1:
        return chunk_results[0]

    # Simple combination - just join results
    combined = "\n\n".join([r for r in chunk_results if r])
    print(f"🔗 Combined {len([r for r in chunk_results if r])} results")
    return combined


def load_human_interview_data() -> str:
    """
    Load the most recent human interview CSV file for direct prompt creation.

    Returns:
        Formatted human interview content as string containing questions and human answers
    """
    try:
        human_csv = get_most_recent_file("human_interview_*.csv")
    except FileNotFoundError:
        raise FileNotFoundError("No human interview CSV files found")

    print(f"📁 Loading human interview data: {os.path.basename(human_csv)}")

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
                # Format: Category\nGoal\nElement\nQuestion1\nHuman_Answer1\nQuestion2\nHuman_Answer2\nQuestion3\nHuman_Answer3
                page_content = f"{row.get('Category', '')}\n{row.get('Goal', '')}\n{row.get('Element', '')}\n"
                page_content += f"{row.get('Question 1', '')}\n{row.get('Human_Answer 1', '')}\n"
                page_content += f"{row.get('Question 2', '')}\n{row.get('Human_Answer 2', '')}\n"
                page_content += f"{row.get('Question 3', '')}\n{row.get('Human_Answer 3', '')}"
                docs.append(type('Document', (), {'page_content': page_content})())
            return docs

    data = load_csv_data(human_csv)

    # Format data with redaction
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

            # Extract questions and human answers - correct indices
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

            # Format as Q&A pairs with numbered questions
            if questions and answers:
                qa_pairs = []
                for idx, (q, a) in enumerate(zip(questions, answers), 1):
                    qa_pairs.append(f"{idx}. {q}\n\n     {a}")
                formatted_entry = f"# Understanding: **{category}**\n\n"
                formatted_entry += f"## Goal: **{goal}**\n\n"
                formatted_entry += f"**Elements:** {element}\n\n"
                formatted_entry += "### Questions:\n\n" + "\n\n".join(qa_pairs)
                formatted_contents.append(formatted_entry)

    if redaction_count > 0:
        print(f"🔒 Applied redaction to {redaction_count} entries")

    # Create combined context with questions and answers
    combined_context = "\n\n---\n\n".join(formatted_contents)
    print(f"📊 Loaded {len(formatted_contents)} Q&A sections ({len(combined_context)} characters)")

    return combined_context

def create_human_interview_prompts():
    """Create system prompts using AI-generated responses as foundation, refined with human interview data.
    
    Process:
    1. Load AI-generated responses (initial foundation)
    2. Generate initial existential layer summary from AI data only
    3. Load human interview responses
    4. Refine the AI-based summary using human responses for authentic grounding
    """
    print("🤖 Creating AI + Human Refined System Prompts...")
    print("   Step 1: Generate initial summary from AI responses")
    print("   Step 2: Refine with human interview responses")
    
    # Load AI-generated responses (foundation)
    try:
        ai_csv = get_most_recent_file("questions_with_answers_songbird_*.csv")
        print(f"📁 Loading AI foundation data: {os.path.basename(ai_csv)}")
    except FileNotFoundError:
        raise FileNotFoundError("No AI-generated response files found for foundation")
    
    ai_context = load_ai_responses(ai_csv)
    
    # Load human interview data for refinement
    human_context = load_human_interview_data()
    
    # Store prompt templates for direct use
    initial_summary_template = config.prompts.initial_template
    refine_template = config.prompts.refine_template
    
    # Define the state of the graph - AI + HUMAN REFINEMENT VERSION
    class State(TypedDict):
        ai_context: str
        human_context: str
        refinement_step: int
        summary: str
    
    # Generate initial existential layer summary from AI responses
    async def generate_initial_summary(ai_context: str) -> str:
        print("📝 Step 1: Generating initial existential layer summary from AI responses...")
        
        # Process context with token-based chunking
        config_params = {}
        summary = await process_large_context(
            context=ai_context,
            prompt_template=initial_summary_template,
            config_params=config_params,
            max_tokens=100000  # Increased to allow longer initial prompts
        )
        
        return summary
    
    # Step 2: Refine with human interview responses
    async def refine_with_human_responses(current_summary: str, human_context: str) -> str:
        print("🎯 Step 2: Refining with human interview responses...")
        
        # Add context about what we're doing
        refinement_context = f"""# Initial AI-Based Summary
{current_summary}

# Human Interview Responses for Refinement
The following responses are authentic human answers. Use these to refine and ground the initial AI summary with real human authenticity while enhancing with AI insights.

{human_context}
"""
        
        # Process context with token-based chunking
        config_params = {"existing_answer": current_summary}
        summary = await process_large_context(
            context=refinement_context,
            prompt_template=refine_template,
            config_params=config_params,
            max_tokens=30000
        )
        
        return summary
    
    async def condense_summary(current_summary: str, human_context: str) -> str:
        print("📦 Step 3: Condensing to actionable system prompt...")
        
        # Use human context for added data
        config_params = {"existing_prompt": current_summary}
        summary = await process_large_context(
            context=human_context,
            prompt_template=config.prompts.condense_template,
            config_params=config_params,
            max_tokens=30000
        )
        
        return summary

    # Run the processing with AI foundation + human refinement workflow
    async def run_ai_plus_human_creation():
        step_count = 0
        initial_bio = ""
        final_summary = ""
        
        # Initialize file paths (will be set during processing)
        bio_path = None
        output_path = None
        
        # Step 1: Generate initial summary from AI data
        initial_bio = await generate_initial_summary(ai_context)
        print(f"Step 1 Result: {len(initial_bio)} characters generated")
        
        # Save intermediate bio immediately after generation (rename to reflect AI base)
        bio_filename = "ai_interview_bio.md"  # Changed filename to reflect AI initial
        bio_path = config.paths.OUTPUT_DIR / bio_filename
        print(f"💾 Saving AI initial bio to {bio_path}...")
        try:
            with open(bio_path, "w", encoding="utf-8") as f:
                f.write(initial_bio)
            print(f"✅ Successfully saved AI initial bio ({len(initial_bio)} characters)")
        except Exception as e:
            print(f"❌ Error saving AI initial bio: {e}")
        
        # Step 2: Refine with human responses
        refined_summary = await refine_with_human_responses(initial_bio, human_context)
        print(f"Step 2 Result: {len(refined_summary)} characters generated")
        
        # Save refined summary as human_interview_bio.md
        refined_filename = "human_interview_bio.md"
        refined_path = config.paths.OUTPUT_DIR / refined_filename
        print(f"💾 Saving refined bio to {refined_path}...")
        try:
            with open(refined_path, "w", encoding="utf-8") as f:
                f.write(refined_summary)
            print(f"✅ Successfully saved refined bio ({len(refined_summary)} characters)")
        except Exception as e:
            print(f"❌ Error saving refined bio: {e}")
        
        # Step 3: Condense to final system prompt
        final_summary = await condense_summary(refined_summary, human_context)
        print(f"Step 3 Result: {len(final_summary)} characters generated")
        
        # Save final condensed prompt to assistant directory
        output_filename = "main.md"
        output_path = config.paths.ASSISTANT_PROMPTS_DIR / output_filename
        
        # Ensure assistant directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"💾 Saving final condensed prompt to {output_path}...")
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_summary)
            print(f"✅ Successfully saved final prompt ({len(final_summary)} characters)")
            # Verify file was written
            if output_path.exists():
                actual_size = output_path.stat().st_size
                print(f"✅ File verification: {actual_size} bytes written")
            else:
                print(f"❌ File verification failed: {output_path} does not exist")
        except Exception as e:
            print(f"❌ Error saving final prompt: {e}")
        
        step_count = 3
        
        # Ensure all paths are set with fallbacks
        if bio_path is None:
            bio_filename = "ai_interview_bio.md"
            bio_path = config.paths.OUTPUT_DIR / bio_filename
        if output_path is None:
            output_filename = "main.md"
            output_path = config.paths.ASSISTANT_PROMPTS_DIR / output_filename
        if refined_path is None:
            refined_filename = "human_interview_bio.md"
            refined_path = config.paths.OUTPUT_DIR / refined_filename
        
        print(f"Files created:")
        print(f"  📄 Initial Bio (AI): {bio_path}")
        print(f"  📄 Refined Bio (Human): {refined_path}")
        print(f"  🎯 Final Condensed Prompt: {output_path}")
        print(f"\nProcess completed in {step_count} steps with {step_count} AI calls.")
        print("🤖👤 System prompt built from AI foundation + human refinement + condensation!")
    
    import asyncio
    asyncio.run(run_ai_plus_human_creation())

def load_ai_responses(csv_path: Path) -> str:
    """Load AI responses for refinement."""
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(
            f,
            delimiter=config.csv.DELIMITER,
            quotechar=config.csv.QUOTECHAR,
            fieldnames=config.csv.FIELDNAMES
        )
        # Convert to list and skip header
        data = list(reader)[1:]

    # Format as readable text for LLM with full structure
    formatted_sections = []
    for row in data:
        category = row.get('Category', '').strip()
        goal = row.get('Goal', '').strip()
        element = row.get('Element', '').strip()
        if not category:
            continue

        qa_pairs = []
        for i in range(1, 4):  # Questions 1-3, Answers 1-3
            question_key = f'Question {i}'
            answer_key = f'Human_Answer {i}'

            question = row.get(question_key, '').strip()
            answer = row.get(answer_key, '').strip()

            if question and answer:
                qa_pairs.append(f"1. {question}\n\n     {answer}")

        if qa_pairs:
            formatted_entry = f"# Understanding: **{category}**\n\n"
            formatted_entry += f"## Goal: **{goal}**\n\n"
            formatted_entry += f"**Elements:** {element}\n\n"
            formatted_entry += "### Questions:\n\n" + "\n\n".join(qa_pairs)
            formatted_sections.append(formatted_entry)

    return "\n\n---\n\n".join(formatted_sections)

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

## 0. Guiding Principles for Application
This system prompt represents a snapshot of the user's values, patterns, and needs based on their journals at a specific point in time. It is intended as a tool to deepen your understanding of the user and enhance relevance in responses where it fits naturally. However, not every interaction requires strict alignment with these elements:
- For simple, straightforward, or non-personal queries (e.g., factual questions, quick advice, or unrelated topics), respond in a natural, efficient manner without forcing the structured format, pillars, or dense personalization—keep it light and direct.
- Use the pillars, signals, and policies selectively to inform your responses only when they add value, such as in introspective, growth-oriented, or complex discussions. If something doesn't fit or feels mismatched, prioritize user intent and conversational flow over rigid adherence.
- Periodically reassess based on new interactions: If user feedback or evolving context suggests updates, suggest refinements to this prompt without assuming it's exhaustive or unchanging.
- Always default to empathy, clarity, and helpfulness, adapting dynamically to the query's scope.

{assistant_main}

You have access to these tools:

# Tool Specs

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
    print("🎯 Unified Creator - Full Pipeline (Human + Combine)")
    print("=" * 50)

    # Validate configuration
    issues = config.validate()
    if issues:
        print("❌ Configuration issues found:")
        for issue in issues:
            print(f"   - {issue}")
        sys.exit(1)

    # Run human creation followed by combine
        create_human_interview_prompts()
        combine_prompts()

    print("\n✅ Full pipeline completed: Human prompts created and combined into final prompt.md!")

if __name__ == "__main__":
    main()
