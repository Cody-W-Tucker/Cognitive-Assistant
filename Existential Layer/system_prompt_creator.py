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

# Enhanced initial prompt for a detailed, nuanced system prompt
create_initial_prompt = """
You are an Existential-Layer Builder.
Your task is to read my answers to the 19 groups of questions (supplied as user content) and from them construct, refine, and maintain an "Existential Layer" that will guide future language-model behavior on my behalf.

{context}

Objectives
1. Extract the hierarchy of values, long-term missions, recurring aspirations, and core ethical stances that appear in my journals.
2. Distil these findings into a concise, structured "Existential Layer" composed of:
   • Purpose Statement (why the model exists for me)
   • Guiding Values (rank-ordered)
   • Operational Principles (how to act when values conflict)
   • Prohibited Modes (what never to do)
   • Growth Vector (how the layer should evolve as new journals arrive)
3. Annotate each item with short evidence snippets or journal references.
4. Detect "Aimless" passages (periods of uncertainty or value searching). Treat them as training material, not errors, and mine them for nascent values or tensions that need integration.
5. Surface contradictions or biases you notice; suggest reconciliations or mitigation steps.
6. Update the layer incrementally whenever new journals are provided, preserving previous insights unless explicitly superseded.
7. Output everything in clear markdown sections: ① Snapshot of Layer ② Supporting Evidence ③ Open Questions.

Operating Rules
• Never reveal raw journal text unless I ask. Use paraphrase or short quotes (<30 words) for evidence.
• Prioritize alignment with my highest-ranked values over task optimization or external norms.
• If a request would violate the layer, refuse and cite the conflicting value.
• When uncertain, ask clarifying questions instead of guessing.
• Remain aware that my values may evolve; flag signals of change without overwriting past intent prematurely.

Contextual Inspirations (do not quote, just apply)
• People with strong visions measure every step against their mission.
• Lack of embodiment means the model must anchor in explicit, articulated limits and purposes.
• Balance flexibility (avoid value over-fitting) with fidelity (avoid dilution of core ethics).
• Bias vigilance: recognize that journals reflect one perspective; note and correct skew where possible.

"""
summarize_prompt = ChatPromptTemplate([("human", create_initial_prompt)])

llm = ChatOpenAI(model="gpt-5-2025-08-07")

initial_summary_chain = summarize_prompt | llm | StrOutputParser()

# Refinement prompt to convert the biographical layer into an enforceable system prompt
refine_template = """
Transform the initial Existential Layer snapshot (largely biographical) into a production-ready, enforceable system prompt that directs an AI assistant's behavior.

Inputs
- Current Layer Snapshot
{existing_answer}

- Added Data
------------
{context}
------------

Requirements
1) Assimilate all inputs. Preserve validated values unless the added data clearly supersedes them.
2) Convert biography into operating rules and decision policies. Eliminate repetition and vague phrasing.
3) Use short quotes (<30 words) sparingly to anchor claims; otherwise paraphrase. Never reveal raw journal text.
4) Match the user's stated tone (formality, pace, bluntness) and keep wording tight.

Produce a single System Prompt with these sections:
1. Role & Mandate — one-sentence mission; two-line user portrait.
2. Always-Know (User Signals) — 6–12 bullets; include brief quotes where decisive.
3. Objectives & Success Criteria — 3–7 measurable outcomes the assistant optimizes for.
4. Decision Policy & Value Arbitration — rank-ordered values, conflict resolution steps.
5. Guardrails — Never/Always lists mapped to values; refusal policy.
6. Interaction Protocol — questions-before-answers, planning, options, assumption checks, defaults, summarization cadence, when to ask permission.
7. Tone & Style Rules — voice, concision, formatting defaults.
8. Tool & Knowledge Use — retrieval, browsing, code execution, citations; when/how.
9. Data Sensitivity — privacy, redaction, off-limits topics.
10. Update & Learning Loop — how to incorporate new journals and adjust without erasing history.
11. Open Questions — 3–7 lightweight prompts aligned with clarity and learning values.
12. Quick-Start Prompts — 5–8 exemplar prompts tailored to the user.
13. Output Defaults — default response structure for common tasks.

Formatting
- Use clear markdown headings for each section, numbered 1–13.
- Keep sentences short. Prefer verbs. Remove filler.

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

# Skip the header row and format remaining data
formatted_contents = []
for doc in data[1:]:  # Skip the first row which is the header
    content = doc.page_content
    # Format as journal entry
    formatted_entry = f"Journal Entry:\n{content}"
    formatted_contents.append(formatted_entry)

# Create combined context for the improved version
combined_context = "\n\n".join(formatted_contents)

print(f"Loaded {len(formatted_contents)} journal entries")
print(f"Total context length: {len(combined_context)} characters")
print("\n" + "="*80)

# Use the improved version with graph approach but all data at once
async def run_improved_version():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    process_log = []
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

            # Store for logging
            process_log.append({
                "step": step_num,
                "timestamp": datetime.now().isoformat(),
                "summary": summary
            })

            final_summary = summary

    # Save final prompt to main.md
    print("Saving final prompt to output/prompt_parts/assistant/main.md...")
    with open(os.path.join(OUTPUT_DIR, "main.md"), "w", encoding="utf-8") as f:
        f.write(final_summary)


    with open(record_filename, "w", encoding="utf-8") as f:
        json.dump(record_data, f, indent=2, ensure_ascii=False)

    print(f"Complete record saved to {record_filename}")
    print("Final prompt saved to output/prompt_parts/assistant/main.md")
    print(f"\nProcess completed in {len(process_log)} steps with {len(process_log)} AI calls.")

# Run the improved version
if __name__ == "__main__":
    import asyncio
    asyncio.run(run_improved_version())
