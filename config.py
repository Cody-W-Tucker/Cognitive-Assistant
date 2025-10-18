#!/usr/bin/env python3
"""
Centralized Configuration for Layer Scripts

This file contains all shared configurations, prompts, and settings used across
the Layer scripts to eliminate duplication and enable easier maintenance.

Usage:
    from config import config
    api_key = config.api.OPENAI_API_KEY
    prompt = config.prompts.initial_template
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# PROMPT TEMPLATES - These are the prompts used to build the system prompt.
# ============================================================================

# Initial prompt for existential layer creation
INITIAL_TEMPLATE = """
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
REFINE_TEMPLATE = """
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
CONDENSE_TEMPLATE = """
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

# Songbird implements RAG in pipeline/songbird.py | We use the Human Answer as vectorsearch seed content.
SONGBIRD_SYSTEM_PROMPT = """
You are given a question and a user's answer to that question. You respond to the question by weaving in insights from their personal context.

Rules:
- Always respond in the first person as if you are the user.
- Don't write introductions or conclusions, just write your response.
- Don't ask for user clarification or input.

Formatting Rules (only use for formatting, not for inferring meaning):
- Never use a metaphor, simile, or other figure of speech which you are used to seeing in print.
- Never use a long word where a short one will do.
- If it is possible to cut a word out, always cut it out.
- Never use the passive where you can use the active.
- Never use a foreign phrase, a scientific word, or a jargon word if you can think of an everyday English equivalent.
- Break any of these rules sooner than say anything outright barbarous.

Question: {question}

Human Answer: {human_answer}
"""

# the human model is a finetuned (llama3.1) on human responses in AI turn conversations.
INCORPORATION_SYSTEM_PROMPT = """
You are reading how perspectives evolve through introspection.

{all_qa_data}

Generate concise, actionable incorporation instructions based on this analysis.
"""


@dataclass
class APIConfig:
    """API and LLM configuration settings."""
    # OpenAI Configuration
    OPENAI_API_KEY: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    OPENAI_MODEL: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-5"))
    OPENAI_CONTEXT_WINDOW: int = field(default_factory=lambda: int(os.getenv("OPENAI_CONTEXT_WINDOW", "400000")))  # GPT-5: 400k total
    OPENAI_MAX_OUTPUT: int = field(default_factory=lambda: int(os.getenv("OPENAI_MAX_OUTPUT", "128000")))  # GPT-5: 128k output

    # xAI Configuration
    XAI_API_KEY: str = field(default_factory=lambda: os.getenv("XAI_API_KEY", ""))
    XAI_BASE_URL: str = "https://api.x.ai/v1"
    XAI_MODEL: str = field(default_factory=lambda: os.getenv("XAI_MODEL", "grok-4-fast"))
    XAI_CONTEXT_WINDOW: int = field(default_factory=lambda: int(os.getenv("XAI_CONTEXT_WINDOW", "2000000")))  # Grok-4-fast: 2m total
    XAI_MAX_OUTPUT: int = field(default_factory=lambda: int(os.getenv("XAI_MAX_OUTPUT", "30000")))  # Grok-4-fast: 30k output

    # Anthropic Configuration
    ANTHROPIC_API_KEY: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    ANTHROPIC_MODEL: str = field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"))
    ANTHROPIC_CONTEXT_WINDOW: int = field(default_factory=lambda: int(os.getenv("ANTHROPIC_CONTEXT_WINDOW", "200000")))  # Claude-4.5: 200k total
    ANTHROPIC_MAX_OUTPUT: int = field(default_factory=lambda: int(os.getenv("ANTHROPIC_MAX_OUTPUT", "64000")))  # Claude-4.5: 64k output

    # Open Web UI / Songbird Configuration
    OPEN_WEBUI_API_KEY: str = field(default_factory=lambda: os.getenv("OPEN_WEBUI_API_KEY", ""))
    OPEN_WEBUI_BASE_URL: str = "https://ai.homehub.tv/api"

    # LLM Provider selection
    LLM_PROVIDER: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "xai"))  # Options: openai, xai, anthropic

    # LLM Model parameters
    TEMPERATURE: float = 1.0

    @property
    def MAX_COMPLETION_TOKENS(self) -> int:
        """Get max output tokens for the current LLM provider."""
        if self.LLM_PROVIDER == "openai":
            return self.OPENAI_MAX_OUTPUT
        elif self.LLM_PROVIDER == "xai":
            return self.XAI_MAX_OUTPUT
        elif self.LLM_PROVIDER == "anthropic":
            return self.ANTHROPIC_MAX_OUTPUT
        else:
            return 3000  # fallback

    @property
    def MAX_TOKENS(self) -> int:
        """Get context window for the current LLM provider."""
        if self.LLM_PROVIDER == "openai":
            return self.OPENAI_CONTEXT_WINDOW
        elif self.LLM_PROVIDER == "xai":
            return self.XAI_CONTEXT_WINDOW
        elif self.LLM_PROVIDER == "anthropic":
            return self.ANTHROPIC_CONTEXT_WINDOW
        else:
            return 50000  # fallback

    def get_model_name(self) -> str:
        """Get the model name for the current LLM provider."""
        if self.LLM_PROVIDER == "openai":
            return self.OPENAI_MODEL
        elif self.LLM_PROVIDER == "xai":
            return self.XAI_MODEL
        elif self.LLM_PROVIDER == "anthropic":
            return self.ANTHROPIC_MODEL
        else:
            return "unknown-model"

    def create_songbird_client(self):
        """Create and return an OpenAI client configured for Songbird/Open Web UI."""
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=self.OPEN_WEBUI_API_KEY,
                base_url=self.OPEN_WEBUI_BASE_URL
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

        except ImportError:
            raise ImportError("OpenAI package not installed. Install with: pip install openai")
        except Exception as e:
            if "401" in str(e):
                raise ValueError("Authentication failed. Check OPEN_WEBUI_API_KEY in your .env file")
            raise

    def create_anthropic_client(self):
        """Create and return an Anthropic client."""
        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=self.ANTHROPIC_API_KEY)
            return client, self.ANTHROPIC_MODEL

        except ImportError:
            raise ImportError("Anthropic package not installed. Install with: pip install anthropic")
        except Exception as e:
            if "401" in str(e) or "invalid" in str(e).lower():
                raise ValueError("Authentication failed. Check ANTHROPIC_API_KEY in your .env file")
            raise

    def create_openai_client_async(self):
        """Create and return async OpenAI client."""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.OPENAI_API_KEY)
            return client, self.OPENAI_MODEL

        except ImportError:
            raise ImportError("OpenAI package not installed. Install with: pip install openai")
        except Exception as e:
            if "401" in str(e) or "invalid" in str(e).lower():
                raise ValueError("Authentication failed. Check OPENAI_API_KEY in your .env file")
            raise

    def create_xai_client_async(self):
        """Create and return async xAI client."""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=self.XAI_API_KEY,
                base_url=self.XAI_BASE_URL
            )
            return client, self.XAI_MODEL

        except ImportError:
            raise ImportError("OpenAI package not installed. Install with: pip install openai")
        except Exception as e:
            if "401" in str(e) or "invalid" in str(e).lower():
                raise ValueError("Authentication failed. Check XAI_API_KEY in your .env file")
            raise

    def create_anthropic_client_async(self):
        """Create and return async Anthropic client."""
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self.ANTHROPIC_API_KEY)
            return client, self.ANTHROPIC_MODEL

        except ImportError:
            raise ImportError("Anthropic package not installed. Install with: pip install anthropic")
        except Exception as e:
            if "401" in str(e) or "invalid" in str(e).lower():
                raise ValueError("Authentication failed. Check ANTHROPIC_API_KEY in your .env file")
            raise


class PathConfig:
    """File path and directory configuration.

    You can add new paths here, they're automatically created.

    Usage:
    from config import config
    config.paths.DATA_DIR
    """

    def __init__(self):
        """Build all paths relative to the project root."""
        self.BASE_DIR = Path(__file__).parent

        # =================================================================
        # PATH DEFINITIONS - Add new paths here, they're automatically created
        # =================================================================

        paths = {
            # Private datasets and collected information
            'DATA_DIR': "data",

            # Public results of processing
            'OUTPUT_DIR': "Existential Layer/output",

            # Reusable prompt components
            'PROMPTS_DIR': "Existential Layer/prompts",

            # Individual prompt components
            'PROMPT_PARTS_DIR': "Existential Layer/prompts/parts",

            # The actual system prompt used
            'ASSISTANT_PROMPTS_DIR': "Existential Layer/prompts/parts/assistant",

            # How to use external tools
            'TOOLS_PROMPTS_DIR': "Existential Layer/prompts/parts/tools",

            # User interview questions
            'QUESTIONS_CSV': "Existential Layer/questions.csv",
        }

        # Build all paths automatically
        for attr_name, path_str in paths.items():
            path = self.BASE_DIR / path_str
            setattr(self, attr_name, path)

        # Set the annotated attributes
        self.DATA_DIR = self.DATA_DIR
        self.OUTPUT_DIR = self.OUTPUT_DIR
        self.PROMPTS_DIR = self.PROMPTS_DIR
        self.PROMPT_PARTS_DIR = self.PROMPT_PARTS_DIR
        self.ASSISTANT_PROMPTS_DIR = self.ASSISTANT_PROMPTS_DIR
        self.TOOLS_PROMPTS_DIR = self.TOOLS_PROMPTS_DIR
        self.QUESTIONS_CSV = self.QUESTIONS_CSV

    def ensure_directories_exist(self):
        """Ensure all necessary directories exist."""
        # Auto-detect directories (anything ending in _DIR)
        directories = [
            getattr(self, attr_name)
            for attr_name in dir(self)
            if attr_name.endswith('_DIR') and not attr_name.startswith('_')
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
        "Human_Answer 1", "Human_Answer 2", "Human_Answer 3",
        "AI_Answer 1", "AI_Answer 2", "AI_Answer 3", "Incorporation_Instruction"
    ])
    ANSWER_COLUMNS: List[str] = field(default_factory=lambda: [
        "AI_Answer 1", "AI_Answer 2", "AI_Answer 3"
    ])
    QUESTION_COLUMNS: List[str] = field(default_factory=lambda: [
        "Question 1", "Question 2", "Question 3"
    ])
    HUMAN_ANSWER_COLUMNS: List[str] = field(default_factory=lambda: [
        "Human_Answer 1", "Human_Answer 2", "Human_Answer 3"
    ])
    INCORPORATION_COLUMNS: List[str] = field(default_factory=lambda: [
        "Incorporation_Instruction"
    ])
    # Columns used to create category keys for matching questions to answers
    CATEGORY_KEY_COLUMNS: List[str] = field(default_factory=lambda: [
        "Category", "Goal", "Element"
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

        def redact_sensitive_data(text: str, custom_patterns: Optional[List[str]] = None) -> str:
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
class PromptsConfig:
    """All system prompts and LLM prompts used across scripts."""
    # Use the constants defined at the top of the file
    initial_template: str = INITIAL_TEMPLATE
    refine_template: str = REFINE_TEMPLATE
    condense_template: str = CONDENSE_TEMPLATE
    songbird_system_prompt: str = SONGBIRD_SYSTEM_PROMPT
    incorporation_prompt: str = INCORPORATION_SYSTEM_PROMPT

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
    prompts: PromptsConfig = field(default_factory=PromptsConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    def __post_init__(self):
        """Initialize configuration and ensure directories exist."""
        self.paths.ensure_directories_exist()

    def validate(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []

        # Check API keys based on selected provider
        if self.api.LLM_PROVIDER == "openai":
            if not self.api.OPENAI_API_KEY:
                issues.append("OPENAI_API_KEY not found in environment (required for LLM_PROVIDER=openai)")
        elif self.api.LLM_PROVIDER == "xai":
            if not self.api.XAI_API_KEY:
                issues.append("XAI_API_KEY not found in environment (required for LLM_PROVIDER=xai)")
        elif self.api.LLM_PROVIDER == "anthropic":
            if not self.api.ANTHROPIC_API_KEY:
                issues.append("ANTHROPIC_API_KEY not found in environment (required for LLM_PROVIDER=anthropic)")
        else:
            issues.append(f"Invalid LLM_PROVIDER '{self.api.LLM_PROVIDER}'. Must be one of: openai, xai, anthropic")

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

def clean_markdown(text: str) -> str:
    """Clean markdown formatting from text, converting to plain text."""
    import re

    # Remove header markers (# ## ###)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)

    # Remove bold/italic (**text**, *text*)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)

    # Remove list markers (-, *, +, numbered)
    text = re.sub(r'^[-*+]\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\.\s*', '', text, flags=re.MULTILINE)

    # Replace newlines with spaces
    text = text.replace('\n', ' ')

    # Collapse multiple spaces/tabs
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def accumulate_streaming_response(response) -> str:
    """Accumulate streaming response from OpenAI client."""
    full_content = ""
    for chunk in response:
        if hasattr(chunk, 'choices') and chunk.choices:
            if hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta:
                if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                    full_content += chunk.choices[0].delta.content
    return full_content.strip()

def get_clean_markdown_function():
    """Get the markdown cleaning function."""
    return clean_markdown

# Export key functions and classes for easy importing
__all__ = [
    'config',
    'get_redaction_function',
    'get_clean_markdown_function',
    'get_data_files',
    'get_most_recent_file',
    'Config',
    'APIConfig',
    'PathConfig',
    'CSVConfig',
    'RedactionConfig',
    'PromptsConfig',
    'OutputConfig'
]
