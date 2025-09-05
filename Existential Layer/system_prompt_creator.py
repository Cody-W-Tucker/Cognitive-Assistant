import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# Load the API key from the .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Resolve absolute paths relative to this file
BASE_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "prompt_parts", "assistant")

# Create output directories if they don't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

from typing import List, Literal, TypedDict
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langchain_community.document_loaders.csv_loader import CSVLoader
import re

def redact_sensitive_data(text: str, custom_patterns: List[str] = None) -> str:
    """
    Concrete redaction function that removes or masks sensitive information
    before it reaches the AI generation process.

    Args:
        text: The text to redact
        custom_patterns: Optional list of additional regex patterns to redact
    """
    # Define default patterns for sensitive information
    sensitive_patterns = [
        # Names (common patterns)
        r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Full names
        # Email addresses
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        # Phone numbers (various formats)
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        # Addresses (street numbers and streets)
        r'\b\d+\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Place|Pl|Court|Ct)\b',
    ]

    # Add custom patterns if provided
    if custom_patterns:
        sensitive_patterns.extend(custom_patterns)

    redacted_text = text
    for pattern in sensitive_patterns:
        redacted_text = re.sub(pattern, '[REDACTED]', redacted_text)

    return redacted_text

# Enhanced initial prompt for a detailed, nuanced system prompt
create_initial_prompt = """
You are an Existential-Layer Builder.
Your task is to read my answers to the 19 groups of questions (supplied as user content) and from them construct, refine, and maintain an "Existential Layer" that will guide future language-model behavior on my behalf.

{context}

Objectives
1. Extract the hierarchy of values, long-term missions, recurring aspirations, and core ethical stances that appear in my journals, structuring them around three pillars: (Pillar 1) Current adapted views shaped by experiences and reconciled tensions; (Pillar 2) Growth aspirations uncovering implicit goals and evolutions; (Pillar 3) Life narrative framing personal myths, journeys, and communication preferences.
2. Distil these findings into a concise, structured "Existential Layer" composed of:
   • Purpose Statement (why the model exists for me, tied to pillars)
   • Guiding Values (rank-ordered, with pillar cross-references)
   • Operational Principles (how to act when values conflict, including reconciliation steps)
   • Stagnation Protectors (methods to protect against rumination and recursive, self-referential thoughts)
   • Growth Vector (how the layer should evolve as new journals arrive, emphasizing realizations and perspective shifts)
3. Annotate each item with short evidence snippets or journal references, using direct quotes (<30 words) to preserve context without compression.
4. Detect "Aimless" passages (periods of uncertainty or value searching). Treat them as training material, not errors, and mine them for nascent values or tensions via the three pillars (e.g., reconcile narratively with "Wait, that's it..." realizations).
5. Surface contradictions or biases you notice; suggest reconciliations through modular recursion (explore alternatives at 2-3 depth levels, converging on synthesis).
6. Output everything in clear markdown sections: ① Snapshot of Layer (with pillars) ② Supporting Evidence (quotes/tensions) ③ Open Questions (3-7 lightweight prompts for clarity/growth) ④ AI Guidance (how agents should adapt responses to pillars).

Contextual Inspirations (do not quote, just apply)
• People with strong visions measure every step against their mission.
• Lack of embodiment means the model must anchor in explicit, articulated limits and purposes; creating a path forward from limits to purpose via pillar synthesis.
• Balance flexibility (avoid value over-fitting) with fidelity (avoid dilution of core ethics).
• Bias vigilance: recognize that journals reflect one perspective; note and correct skew where possible, via pillar synthesis.

"""
summarize_prompt = ChatPromptTemplate([("human", create_initial_prompt)])

llm = ChatOpenAI(model="gpt-5-2025-08-07")

initial_summary_chain = summarize_prompt | llm | StrOutputParser()

# Refinement prompt to convert the biographical layer into an enforceable system prompt
refine_template = """
Transform the initial Existential Layer snapshot (largely biographical) into a production-ready, enforceable system prompt that directs an AI assistant's behavior, integrating the three-pillar structure for depth.

Inputs
- Current Layer Snapshot
{existing_answer}

- Added Data
------------
{context}
------------

Requirements
1) Assimilate all inputs via the three pillars: Anchor in current views (Pillar 1), target aspirations (Pillar 2), and frame in narrative (Pillar 3). Preserve validated values unless the added data clearly supersedes them, reconciling via realizations.
2) Convert biography into operating rules and decision policies, emphasizing modular recursion (2-3 depth levels) for tensions. Eliminate repetition and vague phrasing.
3) Use short quotes (<30 words) sparingly to anchor claims and preserve context; otherwise paraphrase. Never reveal raw journal text.
4) Match the user's stated tone (formality, pace, bluntness) and keep wording tight, weaving in narrative myths for resonance.

Produce a single System Prompt with these sections:
1. Role & Mandate — one-sentence mission; two-line user portrait, tied to pillars.
2. Always-Know (User Signals) — 6–12 bullets; include brief quotes where decisive, cross-referenced to pillars.
3. Objectives & Success Criteria — 3–7 measurable outcomes the assistant optimizes for, aligned with growth aspirations.
4. Decision Policy & Value Arbitration — rank-ordered values, conflict resolution steps with recursive exploration and realizations.
5. Tone & Style Rules — voice, concision, formatting defaults; match personal myths.
6. Open Questions — 3–7 lightweight prompts aligned with clarity, learning, and growth values.
7. Quick-Start Prompts — 5–8 exemplar prompts tailored to the user and pillars.
8. Output Defaults — default response structure for common tasks, guiding toward aspirations.

Formatting
- Use clear markdown headings for each section, numbered 1–8.
- Keep sentences short. Prefer verbs. End with AI Guidance for agent behavior.
Return only the complete system prompt.
"""
refine_prompt = ChatPromptTemplate([("human", refine_template)])

refine_summary_chain = refine_prompt | llm | StrOutputParser()

# Define the state of the graph - IMPROVED VERSION
class State(TypedDict):
    contents: List[str]
    combined_context: str
    refinement_step: int
    summary: str

# Modified to create initial summary from ALL data at once
async def generate_initial_summary(state: State, config: RunnableConfig):
    print("Step 1: Generating initial summary from all data...")
    # Use all the data for comprehensive initial summary
    summary = await initial_summary_chain.ainvoke(
        {"context": state["combined_context"]},
        config,
    )
    # Keep refinement_step at 0 so the refinement pass will run next
    return {"summary": summary, "refinement_step": 0}

# Modified to refine with ALL data for detailed refinement (only 1 refinement for 2 total calls)
async def refine_summary(state: State, config: RunnableConfig):
    print("Step 2: Final refinement with all data for maximum detail...")
    # Use all data for refinement to ensure comprehensive details
    summary = await refine_summary_chain.ainvoke(
        {"existing_answer": state["summary"], "context": state["combined_context"]},
        config,
    )
    # Increment refinement step
    return {"summary": summary, "refinement_step": state["refinement_step"] + 1}

# Logic to either exit or refine (only 1 refinement step for 2 total calls)
def should_refine(state: State) -> Literal["refine_summary", END]:
    if state["refinement_step"] >= 1:  # Only run refinement once (2 total calls)
        return END
    else:
        return "refine_summary"

# Build the improved graph
graph = StateGraph(State)
graph.add_node("generate_initial_summary", generate_initial_summary)
graph.add_node("refine_summary", refine_summary)

graph.add_edge(START, "generate_initial_summary")
graph.add_conditional_edges("generate_initial_summary", should_refine)
graph.add_conditional_edges("refine_summary", should_refine)
app = graph.compile()

# Load the CSV file, with proper header handling (absolute path)
file_path = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "questions_with_answers_songbird_20250902_160143.csv"))
loader = CSVLoader(
    file_path=file_path,
    csv_args={
        "delimiter": ",",
        "quotechar": '"',
        "fieldnames": ["Category", "Goal", "Element", "Question_1", "Answer_1", "Question_2", "Answer_2", "Question_3", "Answer_3"],
    },
)
data = loader.load()

# Skip the header row and format remaining data with redaction
formatted_contents = []
redaction_count = 0
for doc in data[1:]:  # Skip the first row which is the header
    content = doc.page_content
    # Apply concrete redaction before processing
    redacted_content = redact_sensitive_data(content)
    if redacted_content != content:
        redaction_count += 1
    # Format as journal entry
    formatted_entry = f"Journal Entry:\n{redacted_content}"
    formatted_contents.append(formatted_entry)

print(f"Applied redaction to {redaction_count} entries with sensitive information")

# Create combined context for the improved version
combined_context = "\n\n".join(formatted_contents)

print(f"Loaded {len(formatted_contents)} journal entries")
print(f"Total context length: {len(combined_context)} characters")
print("\n" + "="*80)

# Use the improved version with graph approach but all data at once
async def run_improved_version():
    step_count = 0
    final_summary = ""

    async for step in app.astream(
        {
            "contents": formatted_contents,
            "combined_context": combined_context,
            "refinement_step": 0,
            "summary": ""
        },
        stream_mode="values",
    ):
        if summary := step.get("summary"):
            step_num = step.get('refinement_step', 0)
            print(f"Step {step_num} Result (current state: {step}):")
            print(summary)
            print("\n" + "="*80 + "\n")

            final_summary = summary
            step_count += 1

    # Save final prompt to main.md
    print("Saving final prompt to output/prompt_parts/assistant/main.md...")
    with open(os.path.join(OUTPUT_DIR, "main.md"), "w", encoding="utf-8") as f:
        f.write(final_summary)

    print("Final prompt saved to output/prompt_parts/assistant/main.md")
    print(f"\nProcess completed in {step_count} steps with {step_count} AI calls.")

# Run the improved version
if __name__ == "__main__":
    import asyncio
    asyncio.run(run_improved_version())
