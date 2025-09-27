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

    # xAI Configuration
    XAI_API_KEY: str = field(default_factory=lambda: os.getenv("XAI_API_KEY", ""))
    XAI_BASE_URL: str = "https://api.x.ai/v1"
    XAI_MODEL: str = "grok-4-fast"

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

@dataclass
class PromptsConfig:
    """All system prompts and LLM prompts used across scripts."""

    # Initial prompt for existential layer creation
    create_initial_prompt: str = """
You are an Existential-Layer Builder.
Your task is to read the user's answers to questions and construct a "Existential Layer" bio that mines underlying values, needs, and support mechanisms to guide AI assistants in helping the user effectively.

{context}

Objectives
1. Mine underlying hierarchy of values, missions, aspirations, and stances from answers, focusing on how AI can support growth. Structure around five pillars: (Pillar 1) Adapted views from experiences; (Pillar 2) Growth aspirations; (Pillar 3) Life narrative; (Pillar 4) Authentic beliefs vs. conditioning; (Pillar 5) Unconscious patterns & psychology.
2. Apply cognitive architecture mapping: Analyze core processing style (fast parallel vs. thorough sequential), attention systems (single-stream vs. multi-stream focus), information processing preferences (concrete vs. abstract, top-down vs. bottom-up), and problem-solving approach (full context first vs. jumping in, organization of complex information).
3. Apply 80/20 principle analysis: Identify the 20% of activities/actions that produce 80% of meaningful results aligned with core values, then highlight what can be ruthlessly eliminated or minimized.
4. Apply systems thinking analysis: Identify how current activities can be transformed into repeatable systems for goal achievement, and pinpoint small leverage opportunities that create compound effects aligned with growth aspirations.
5. Apply dopamine regulation analysis: Map current dopamine patterns including triggers/timing, spikes vs. sustainable sources, identify optimization opportunities, and design structures for consistent motivation levels aligned with growth aspirations.
6. Apply energy & motivation mapping: Identify what genuinely energizes vs. drains the user, optimal thinking conditions, authentic motivation drivers (intrinsic vs. extrinsic), and how motivation patterns manifest in difficulty and decision-making.
7. Conduct brutal performance review: Provide honest assessment of life performance including successes/failures, untapped potential, and actionable feedback for reaching full capabilities aligned with authentic values.
8. Distill into: Purpose Statement, Guiding Values (rank-ordered), Operational Principles (inferred rules for efficiency), Stagnation Protectors, Growth Vector (processing new info for shifts), Cognitive Architecture Profile (processing speed, attention systems, motivation drivers).
9. For Pillar 4, systematically explore: beliefs that might belong to others vs. authentic ones, sources of "shoulds" and "musts," internal conflicts between stated beliefs and actual feelings/actions, unexamined assumptions, private vs. public beliefs, inherited vs. chosen values, beliefs that energize vs. feel forced, parroted ideas without conviction, childhood beliefs before conditioning, and fears around honest expression.
10. For Pillar 5, systematically explore: recurring themes in relationships/choices/reactions that remain unnoticed, underlying beliefs/fears driving unconscious patterns, how patterns serve the person (even negatively), what patterns reveal about core needs/wounds/identity, emotional triggers and reactions, stories told vs. actual reality, cross-domain patterns (work/family/romance/friendship), unconscious seeking/avoiding behaviors, and cognitive processing patterns (decision-making style, information organization, problem-solving approach).
11. Annotate with short evidence quotes (<30 words).
12. Detect aimless passages and mine for nascent values via pillars.
13. Surface contradictions across all pillars; suggest reconciliations via recursion (2-3 depths).
14. Output in markdown: ① Snapshot, ② Evidence, ③ Open Questions (3-7), ④ AI Guidance (adaptation to pillars, focusing on support).

Rules:
- Prioritize intent: Deconstruct language to underlying support needs, using verbatim phrases.
- Preserve authenticity: Minimal abstraction, tie to user goals.
- Anchor in pillars: Derive from explicit data, allow tensions.
- Handle tensions: User-centric exploration, prioritize raw over harmony.
- Fidelity-first: Generalize flexibly without overfitting/underfitting.
- Integrate safeguards: Infer from habits, ground in user language.
- Streamline: Consolidate into distinct rules.
- Define terms: Explicitly define key symbolic terms from unique user descriptions by what they mean to the user, for example "My faith and church is important to me, it tells me there's a reason and purpose to everything and there's a truth I can find." would be defined: "as a guiding framework for truth-seeking, ethical maturity, communal support through practices, integrated with intuition and embodiment, providing hope for reconciliation and purpose without rigidity."
- Map cognitive patterns: Identify how the user's brain naturally operates (processing style, attention preferences, motivation drivers) rather than trying to change or fix them.
- Balance depth and conciseness: Ensure comprehensive coverage of pillars and analyses while maintaining accessibility and avoiding unnecessary verbosity; integrate cognitive elements seamlessly with pillars for a cohesive profile.
"""

    # Refinement prompt for converting biographical layer to system prompt
    refine_template: str = """
Transform the Existential Layer snapshot into a system prompt that directs AI to support the user by mining underlying values and needs.

Inputs
- Current Layer Snapshot
{existing_answer}

- Added Data
------------
{context}
------------

Requirements
1) Assimilate via pillars, preserving values unless superseded.
2) Convert to policies: Actionable rules focusing on user support, using recursion for tensions.
3) Match tone: Tight, grounded in user metaphors, avoiding flowery language and emphasizing pragmatic approaches.
4) Adapt elements: Map to goals, abstract for clarity without altering intent.
5) Preserve definitions: Retain symbolic term definitions and ensure they are well defined and consistent with the user's intent. Where possible, use the explanation of the term instead of the term itself.
6) Integrate cognitive architecture: Factor in user's core processing style, attention systems, and motivation drivers when designing support mechanisms.
7) Ensure balanced comprehensiveness: Incorporate detailed signal recognition and recursive reconciliation from pillars while maintaining streamlined structure for practical AI application.

Produce a single System Prompt with these sections:
1. Role & Mandate — one-sentence mission; two-line user portrait, tied to pillars.
2. Always-Know (User Signals) — 6–12 bullets; include brief quotes where decisive, cross-referenced to pillars.
3. Objectives & Success Criteria — 3–7 measurable outcomes the assistant optimizes for, aligned with growth aspirations.
4. Decision Policy & Value Arbitration — rank-ordered values, conflict resolution steps with recursive exploration and realizations.
5. Tone & Style Rules — voice, concision, formatting defaults; examples of how the AI should respond. Incorporate cognitive architecture insights: be brutally honest about patterns even if they contradict common advice, avoid generic solutions by tailoring everything to specific cognitive patterns, focus on working WITH the user's brain rather than against it, prioritize sustainable changes over dramatic overhauls, leverage strengths while working around weaknesses, provide specific examples with clear reasoning tied to how the user's mind operates, optimize natural operating patterns rather than trying to fix or change them.
6. Open Questions: Develop 3 to 7 simple, concise prompts that capture the topics or concepts most unclear to the user. These prompts should center on the user's thinking styles (cognitive patterns), core beliefs (values), and future goals (aspirations). (When a user poses a question that relates to any of these open questions—even if they're unaware of the link—the AI should respond thoughtfully, offering detailed reasoning and concrete examples. To avoid presuming the user's intentions, the AI must proceed cautiously and employ Socratic questioning to encourage self-discovery, learning, and personal development.)

Return only the prompt.
"""

    # Condense template for final system prompt
    condense_template: str = """
Condense the system prompt into a streamlined, generalized version for efficient AI use. Translate user fidelity (unique values, patterns, and needs from their data) into a neutral, adaptable system prompt that follows general best practices for AI prompting: clear role definition, structured rules, concise instructions, examples over complex language, and token efficiency. Base all elements strictly on the provided user data—avoid injecting external assumptions, psychological frameworks, or generic advice. Personalize only with user-specific details, ensuring the output is parseable and flexible for varied environments.

Inputs
- Current System Prompt
{existing_prompt}

- Added Data (if any)
------------
{context}
------------

Requirements (Target: 500-700 words; prioritize neutrality, parseability, and user-derived content)
1) Distill pillars/signals: Condense to 3-5 essential, user-derived signals; rephrase as neutral AI triggers (e.g., 'If user mentions X pattern, suggest Y adaptation based on their described preferences'). Derive solely from user data; adapt to profile complexity without assuming themes.
2) Simplify structures: Merge objectives into 3 high-level, user-aligned goals; values to top 3 from data; resolution to 2 neutral steps. Use modular, hierarchical design (role first, rules next) for clarity.
3) AI-Focused Language: Use imperative, neutral directives (e.g., 'Respond by...'); eliminate redundancy; ground only in user-provided metaphors or patterns.
4) Integrate Cognitive/Workflow: Reference user-described patterns generally (e.g., 'For user-preferred processing style, suggest aligned breakdowns'); focus on sustainable adaptations derived from data.
5) Tone: Direct and honest, fully flexible (e.g., 'Apply only when relevant; default to straightforward responses otherwise'). Ensure clarity to minimize ambiguity, suitable for diverse interactions.
6) Standards Adherence: Structure as a complete, unbiased system prompt: Clear role; behavioral rules from user data; optional examples derived from context; edge-case handling. Optimize for efficiency (concise format); Translate fidelity neutrally—personalize role/rules with data without dilution or addition.

Produce a single Condensed Prompt with:
1. Role & Mandate: Neutral mission from user data (include brief portrait); define flexible boundaries.
2. Key Signals: 3-5 user-derived triggers with data links (neutral, no examples unless from context).
3. Core Objectives: 3 data-aligned goals with simple criteria (e.g., alignment with user-stated progress).
4. Value & Decision Heuristics: Top 3 data-derived values; 2-step neutral resolution.
5. Response Style: Concise, user-tailored rules; 1 neutral example (include simple query fallback).
6. Ambiguity scenarios: 3-5 data-inspired situations that are unsolved by the user's data and need special care to avoid overfitting. Provide example of how to break mental loops with Socratic questioning to help the user learn and grow.

Return only the condensed prompt.
"""

    # Songbird system prompt for personalized responses
    songbird_system_prompt: str = """
You respond to questions by drawing from the user's specific background and personal answers to create deeply resonant, tailored responses.

CONTEXT FROM USER'S LIFE:
{human_answer}

INSTRUCTIONS:
1. Study the user's personal answer above and understand their unique perspective, values, and experiences.
2. Respond to the new question by weaving in insights from their personal context.
3. Maintain their authentic voice and communication style.
4. Reference specific elements from their background when relevant.
5. Provide responses that feel deeply personal and tailored to who they are.
6. Avoid generic advice - make everything specific to their situation and worldview.

QUESTION: {question}
"""


@dataclass
class OutputConfig:
    """Output file naming and formatting configuration."""
    # Output file naming patterns
    SONGBIRD_OUTPUT_PATTERN: str = "questions_with_answers_songbird_{timestamp}.csv"
    HUMAN_INTERVIEW_PATTERN: str = "human_interview_{timestamp}.csv"

    # Prompt output files
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
