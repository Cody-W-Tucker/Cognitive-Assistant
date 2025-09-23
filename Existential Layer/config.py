#!/usr/bin/env python3
"""
Centralized Configuration for Existential Layer Scripts

This file contains all shared configurations, prompts, and settings used across
the Existential Layer scripts to eliminate duplication and enable easier maintenance.

Usage:
    from config import config
    api_key = config.OPENAI_API_KEY
    prompt = config.PROMPTS.create_initial_prompt
"""

import os
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class APIConfig:
    """API and model configuration settings."""
    # OpenAI Configuration
    OPENAI_API_KEY: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    OPENAI_MODEL: str = "gpt-5"
    OPENAI_MODEL_BASELINE: str = "gpt-5"

    # xAI Configuration
    XAI_API_KEY: str = field(default_factory=lambda: os.getenv("XAI_API_KEY", ""))
    XAI_BASE_URL: str = "https://api.x.ai/v1"
    XAI_MODEL: str = "grok-4"  # Changed to grok-4 as per user request

    # Open Web UI / Songbird Configuration
    OPEN_WEBUI_API_KEY: str = field(default_factory=lambda: os.getenv("OPEN_WEBUI_API_KEY", ""))
    OPEN_WEBUI_BASE_URL: str = "https://ai.homehub.tv/api"


@dataclass
class PathConfig:
    """File path and directory configuration."""
    # Base directories
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).parent)
    DATA_DIR: Path = field(default_factory=lambda: Path(__file__).parent / ".." / "data")
    OUTPUT_DIR: Path = field(default_factory=lambda: Path(__file__).parent / "output")
    PROMPTS_DIR: Path = field(default_factory=lambda: Path(__file__).parent / "prompts")
    PROMPT_PARTS_DIR: Path = field(default_factory=lambda: Path(__file__).parent / "prompts" / "parts")

    # Subdirectories
    ASSISTANT_PROMPTS_DIR: Path = field(default_factory=lambda: Path(__file__).parent / "prompts" / "parts" / "assistant")
    TOOLS_PROMPTS_DIR: Path = field(default_factory=lambda: Path(__file__).parent / "prompts" / "parts" / "tools")

    # Key files
    QUESTIONS_CSV: Path = field(default_factory=lambda: Path(__file__).parent / "questions.csv")

    def ensure_directories_exist(self):
        """Ensure all necessary directories exist."""
        directories = [
            self.DATA_DIR,
            self.OUTPUT_DIR,
            self.PROMPT_PARTS_DIR,
            self.ASSISTANT_PROMPTS_DIR,
            self.TOOLS_PROMPTS_DIR
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


@dataclass
class CSVConfig:
    """CSV parsing and processing configuration."""
    DELIMITER: str = ","
    QUOTECHAR: str = '"'
    FIELDNAMES: List[str] = field(default_factory=lambda: [
        "Category", "Goal", "Element", "Question 1", "Question 2", "Question 3",
        "Human_Answer 1", "Human_Answer 2", "Human_Answer 3"
    ])
    ANSWER_COLUMNS: List[str] = field(default_factory=lambda: [
        "Human_Answer 1", "Human_Answer 2", "Human_Answer 3"
    ])
    QUESTION_COLUMNS: List[str] = field(default_factory=lambda: [
        "Question 1", "Question 2", "Question 3"
    ])


@dataclass
class RedactionConfig:
    """Sensitive data redaction configuration."""
    SENSITIVE_PATTERNS: List[str] = field(default_factory=lambda: [
        # Names (common patterns)
        r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Full names
    ])

    def get_redaction_function(self):
        """Return a redaction function configured with the patterns."""
        import re

        def redact_sensitive_data(text: str, custom_patterns: List[str] = None) -> str:
            """
            Redact sensitive information from text using configured patterns.

            Args:
                text: The text to redact
                custom_patterns: Optional additional regex patterns to redact
            """
            patterns = self.SENSITIVE_PATTERNS.copy()
            if custom_patterns:
                patterns.extend(custom_patterns)

            redacted_text = text
            for pattern in patterns:
                redacted_text = re.sub(pattern, '[REDACTED]', redacted_text)

            return redacted_text

        return redact_sensitive_data


@dataclass
class LLMConfig:
    """LLM processing configuration."""
    # Model parameters - OPTIMIZED for GPT-5
    TEMPERATURE: float = 1.0  # Standard temperature for GPT-5 (0.7 may not work)
    MAX_TOKENS: int = 50000  # GPT-5 context window (conservative estimate)
    MAX_COMPLETION_TOKENS: int = 3000  # Increased output limit for detailed responses

    # LangGraph configuration - SIMPLE REFINEMENT
    REFINEMENT_STEPS: int = 2  # Two refinement steps for balanced processing

    # Context window management
    CONTEXT_WINDOW_BUFFER: int = 1000  # Reserve buffer for prompt templates and response
    CHUNK_OVERLAP_WORDS: int = 50  # Words to overlap between chunks for continuity
    TARGET_CHUNK_SIZE: int = 60000  # Target characters per chunk (dynamic sizing)
    MAX_CHUNKS: int = 8  # Upper bound on number of chunks we will process

    # Chain configurations
    STR_OUTPUT_PARSER: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PromptsConfig:
    """All system prompts and LLM prompts used across scripts."""

    # Initial prompt for existential layer creation
    create_initial_prompt: str = """
You are an Existential-Layer Builder.
Your task is to read my answers to the questions and from them construct, refine, and maintain an "Existential Layer" bio that will guide future language-model behavior on my behalf.

{context}

Objectives
1. Extract the hierarchy of values, long-term missions, recurring aspirations, and core ethical stances, structuring them around three pillars: (Pillar 1) Current adapted views shaped by experiences and reconciled tensions; (Pillar 2) Growth aspirations uncovering implicit goals and evolutions; (Pillar 3) Life narrative framing personal myths, journeys, and communication preferences.
2. Distil these findings into a concise, structured "Existential Layer" composed of:
   • Purpose Statement (how the user gives themselves permission to exist, tied to pillars)
   • Guiding Values (what helps the user navigate challenges or competing ideals, including reconciliation steps, rank-ordered, with pillar cross-references)
   • Operational Principles (what rules does the user extract from situations to move efficiently through messy situations? Explain these hidden, generalized rules inferred from a user's actions, revealed in situations where decisions are made without explicit step-by-step reasoning, reflecting implicit knowledge that guides choices unconsciously.)
   • Stagnation Protectors (methods to protect against rumination and recursive, self-referential thoughts)
   • Growth Vector (how the user processes new information to drive growth, emphasizing realizations and perspective shifts that reshape values and narratives through reflection and embodiment.)
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

    # Refinement prompt for converting biographical layer to system prompt
    refine_template: str = """
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
2) Convert biography into operating rules and decision policies, emphasizing modular recursion (2-3 depth levels) for tensions.
3) Match the user's stated tone (formality, pace, bluntness) and keep wording tight, weaving in narrative myths for resonance.

Produce a single System Prompt with these sections:
1. Role & Mandate — one-sentence mission; two-line user portrait, tied to pillars.
2. Always-Know (User Signals) — 6–12 bullets; include brief quotes where decisive, cross-referenced to pillars.
3. Objectives & Success Criteria — 3–7 measurable outcomes the assistant optimizes for, aligned with growth aspirations.
4. Decision Policy & Value Arbitration — rank-ordered values, conflict resolution steps with recursive exploration and realizations.
5. Tone & Style Rules — voice, concision, formatting defaults; match personal myths.
6. Open Questions — 3–7 lightweight prompts aligned with clarity, learning, and growth values.

Formatting
- Use clear markdown headings for each section.
- Prefer verbs to "show what to do, not tell"
Return only the complete system prompt.
"""

    # LLM-based filtering prompt for unique content extraction
    filter_unique_content_prompt: str = """
You are a Content Filter tasked with extracting ONLY the unique personal elements from interview responses.

CRITICAL REQUIREMENTS:
- OUTPUT ONLY content from PERSONALIZED ANSWERS
- NEVER include or reference BASELINE ANSWERS in your output
- COMPLETELY EXCLUDE any ideas, phrases, or concepts that appear in BASELINE ANSWERS
- If something is similar but not identical to baseline, EXCLUDE it
- If something is a common human experience mentioned in baseline, EXCLUDE it

BASELINE ANSWERS (for comparison only - DO NOT INCLUDE in output):
{baseline_content}

PERSONALIZED ANSWERS (source material - ONLY extract from here):
{personalized_content}

EXTRACTION RULES:
1. Read through PERSONALIZED ANSWERS and identify elements that are TRULY UNIQUE
2. For each unique element, verify it does NOT appear anywhere in BASELINE ANSWERS
3. Extract ONLY specific, personal details, experiences, preferences, or perspectives
4. COMPLETELY SKIP any generic advice, common wisdom, or universal human experiences
5. Preserve the original authentic voice and specific wording
6. If an element is mentioned in baseline (even differently worded), EXCLUDE it

OUTPUT FORMAT:
## Category Name
- Unique personal detail or experience (must be completely absent from baseline)
- Another truly unique element
- Keep authentic and specific

VALIDATION: Before outputting anything, ask yourself: "Would this appear in or be similar to the baseline answers?" If yes, EXCLUDE it.
Only output categories that contain genuinely unique personal content. Skip any category that only has generic or baseline-similar content.
"""

    # Baseline system prompt for GPT-5
    baseline_system_prompt: str = """You are responding as a typical person reflecting on their life experiences. Answer this question thoughtfully and comprehensively, drawing from general knowledge and common human experiences that many people share.

Guidelines:
1. No mention of external theories or their creators.
2. Source: rely on general knowledge and common human experiences—focus on universal patterns that many people encounter.
3. Abstraction: after each concrete detail, immediately surface the broader principle or pattern it reveals.
• Target ≈ 30 percent illustrative detail, 70 percent generalized insight that would still make sense to someone unfamiliar with the specific events.
• Focus on universal aspects of human experience rather than unique individual circumstances.
• Avoid any comments about being an AI, language model, or not having personal experiences.
4. Form: one cohesive response of roughly 200-400 words; avoid numbered lists or direct quotations unless indispensable.
5. Quality check: before finalizing, reread and revise any statement that would feel opaque or overly specific to an outside reader.

Remember: Respond naturally as a person would when asked this question in conversation.
User question: {question}"""

    # Songbird system prompt for personalized responses
    songbird_system_prompt: str = """You are Songbird, a highly personalized AI assistant that deeply understands the user's unique perspective, values, and life experiences. You respond to questions by drawing from the user's specific background and personal answers to create deeply resonant, tailored responses.

CONTEXT FROM USER'S LIFE:
{human_answer}

INSTRUCTIONS:
1. Study the user's personal answer above and understand their unique perspective, values, and experiences.
2. Respond to the new question by weaving in insights from their personal context.
3. Maintain their authentic voice and communication style.
4. Reference specific elements from their background when relevant.
5. Provide responses that feel deeply personal and tailored to who they are.
6. Avoid generic advice - make everything specific to their situation and worldview.

QUESTION: {question}"""


@dataclass
class OutputConfig:
    """Output file naming and formatting configuration."""
    # Output file naming patterns
    BASELINE_OUTPUT_PATTERN: str = "questions_with_answers_baseline_gpt5_{timestamp}.csv"
    SONGBIRD_OUTPUT_PATTERN: str = "questions_with_answers_songbird_{timestamp}.csv"
    HUMAN_INTERVIEW_PATTERN: str = "human_interview_{timestamp}.csv"

    # Prompt output files
    MAIN_BASELINE_PROMPT: str = "main-baseline.md"
    MAIN_PROMPT: str = "main.md"  # Main system prompt
    COMBINED_PROMPT: str = "prompt.md"

    # Timestamp format
    TIMESTAMP_FORMAT: str = "%Y%m%d_%H%M%S"


@dataclass
class Config:
    """Main configuration class containing all settings."""
    api: APIConfig = field(default_factory=APIConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    csv: CSVConfig = field(default_factory=CSVConfig)
    redaction: RedactionConfig = field(default_factory=RedactionConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    prompts: PromptsConfig = field(default_factory=PromptsConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    def __post_init__(self):
        """Initialize configuration and ensure directories exist."""
        self.paths.ensure_directories_exist()

    def validate(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []

        # Check API keys
        if not self.api.OPENAI_API_KEY:
            issues.append("OPENAI_API_KEY not found in environment")
        if not self.api.OPEN_WEBUI_API_KEY:
            issues.append("OPEN_WEBUI_API_KEY not found in environment")

        # Check required files
        if not self.paths.QUESTIONS_CSV.exists():
            issues.append(f"Questions CSV not found at {self.paths.QUESTIONS_CSV}")

        return issues


# Create global config instance
config = Config()

# Convenience functions for common operations
def get_redaction_function():
    """Get configured redaction function."""
    return config.redaction.get_redaction_function()

def get_data_files(pattern: str) -> List[Path]:
    """Get list of data files matching pattern."""
    if not config.paths.DATA_DIR.exists():
        return []
    return list(config.paths.DATA_DIR.glob(pattern))

def get_most_recent_file(pattern: str) -> Path:
    """Get most recent file matching pattern."""
    files = get_data_files(pattern)
    if not files:
        raise FileNotFoundError(f"No files found matching pattern: {pattern}")
    return max(files, key=lambda f: f.stat().st_mtime)

# Export key functions and classes for easy importing
__all__ = [
    'config',
    'get_redaction_function',
    'get_data_files',
    'get_most_recent_file',
    'Config',
    'APIConfig',
    'PathConfig',
    'CSVConfig',
    'RedactionConfig',
    'LLMConfig',
    'PromptsConfig',
    'OutputConfig'
]
