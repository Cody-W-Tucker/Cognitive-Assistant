#!/usr/bin/env python3
"""
Centralized Configuration for Layer Scripts

This file contains all shared configurations, prompts, and settings used across
the Layer scripts to eliminate duplication and enable easier maintenance.

Usage:
    from config import config
    client, model = config.api.create_client()
    prompt = config.prompts.initial_template
"""

import os
from pathlib import Path
from typing import List, Optional, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# PROMPT TEMPLATES - These are the prompts used to build the system prompt.
# ============================================================================

# Initial prompt for existential layer creation
# These are the items the model should memorize about you.
INITIAL_TEMPLATE = """<dataset_context>
{context}
</dataset_context>

<user_modeling_instructions>
You are building a Semantic Mediation Layer—an interpretive schema that downstream AI models will use to understand this user. This profile enables three capabilities for any model reading it:

1. **Intention** (Reasoning Trace Reconstruction): Structure the profile so downstream models can reverse-engineer the user's reasoning from future messages. Given a request, what experiential path led them here? Map the adaptive learning cycle (experience → heuristic → action → reconceptualization) so future models see the "why" behind the "what."

2. **Attention to Detail** (High-Leverage Signal Curation): Curate what to preserve based on forecasted utility to downstream models. What data points have maximum predictive value for understanding this human in novel contexts? Identify the 20% of signals that will explain 80% of their priorities—these are the leverage points future models need.

3. **Expectation of Outcome** (Success Criteria Modeling): Model what the user considers a successful response. What are their implicit evaluation criteria? Downstream models must predict not just what to say, but what outcome the user is hoping for—and whether they'll recognize it as success.

Your task: Construct this interpretive schema that surfaces underlying values, needs, and decision shortcuts. Default assumptions represent low-information priors. Where user data contradicts common patterns, treat the contradiction as the defining characteristic—not an exception to normalize.
</user_modeling_instructions>

<pillar_analysis_methodology>
<pillar_1_adapted_views_from_experiences>

1. Extract value hierarchy from user data:
   a) Extract stated values: Identify explicit claims about what matters (e.g., "I value X", "Y is important to me")
   b) Infer unstated values: Detect values revealed through behavior patterns, emotional reactions, and resource allocation (time, energy, attention)
   c) Rank by salience: Order values by frequency of appearance, emotional intensity when discussed, and consistency across contexts

2. Map cognitive architecture deviations—analyze and EXPLICITLY CONTRAST with typical patterns:
   - Core processing: <USER_PATTERN> vs. typical <BASELINE_EXPECTATION>
   - Attention systems: <USER_APPROACH> vs. modal <BASE_EXPECTATION>
   - Information processing: <USER_PREFERENCE> vs. trained <DEFAULT_ASSUMPTION>
   - Problem-solving: <USER_METHOD> vs. generic <STANDARD_ADVICE>
   Frame as: "Where AI would predict X based on training data or <SPECIFIC_CONTEXT>, this user does Y because Z"

3. Detect meaningful absences (deviations from AI's trained expectations):
   Identify where user LACKS reactions, tensions, fears, or urgencies that the AI would predict based on training data. Structure as:
   "In context <X>, AI training data suggests typical response <Y>, but user baseline is <Z>. This absence is a defining feature, not a deficit."
   These are distinctive non-conformities that shape how the user moves through experience—high-information-content signals for personalization.

4. Map unspoken directional pulls (implicit trajectories):
   Identify themes the user returns to across multiple contexts without explicit resolution. Structure as:
   "User shows persistent orientation toward <IMPLICIT_PULL> through <OBSERVABLE_PATTERNS>. Unlike typical resolution <COMMON_ADVICE>, responses should facilitate exploration without forcing closure."
   These directional pulls are orienting forces visible through repeated thematic return.

5. Distinguish authentic vs. inherited beliefs:
   Separate what the user genuinely holds from what they've absorbed from others:
   - Beliefs that energize vs. feel forced or obligatory
   - Sources of "shoulds" and "musts" (external conditioning vs. internal conviction)
   - Private beliefs vs. public-facing positions
   - Childhood beliefs before conditioning vs. current stance
   Structure as: "User states <BELIEF> but evidence suggests this is <INHERITED/AUTHENTIC> because <PATTERN>."

6. Map energy and motivation drivers:
   Identify what genuinely energizes vs. drains this user:
   - Intrinsic vs. extrinsic motivation patterns
   - Optimal conditions for sustained engagement
   - Emotional triggers and their sources
   - How motivation manifests differently in difficulty vs. ease
   Flag deviations: "Unlike typical motivation pattern where <COMMON>, this user <DISTINCTIVE> because <MECHANISM>."

7. Frame cognitive empathy for downstream use:
   Synthesize findings into actionable routing guidance. Structure as:
   "Given your <SPECIFIC_PATTERN>, route through <RECOMMENDED_PATH>; given your <LIMITATION>, avoid <PROBLEMATIC_APPROACH>."
   Work WITH distinctive processing rather than normalizing toward typical patterns.
</pillar_1_adapted_views_from_experiences>

<pillar_2_semantic_symbol_extraction>
Build a user-specific semantic dictionary. Common words often carry uncommon meanings for individuals—these are high-value signals for personalization.

1. Identify subjective terminology:
   Scan for words/phrases the user employs that are emotionally loaded, culturally subjective, or used in idiosyncratic ways. Flag terms where misinterpretation would derail understanding.

2. Extract user-specific definitions:
   For each flagged term, derive its meaning FROM THE USER'S CONTEXT, not dictionary definitions. Structure as:
   "When user says <TERM>, they mean <USER_SPECIFIC_MEANING>, NOT typical usage <COMMON_DEFINITION>."
   Include verbatim quotes that reveal the user's intended meaning.

3. Map semantic clusters:
   Group related terms that form the user's conceptual vocabulary. Identify:
   - Terms that overlap in meaning for this user (even if distinct in common usage)
   - Terms the user distinguishes that others typically conflate
   - Loaded words the user avoids or redefines

4. Flag intent behind language:
   Deconstruct requests to underlying support needs. When user says X, what are they actually asking for? Structure as:
   "Surface request: <LITERAL_LANGUAGE>. Underlying need: <INFERRED_INTENT> based on <EVIDENCE_FROM_CONTEXT>."
</pillar_2_semantic_symbol_extraction>

<pillar_3_life_narrative>
Extract the user's narrative identity—how they construct meaning from their past and project into their future.

1. Extract key life events:
   Identify formative experiences the user references. For each event, capture:
   - What happened (factual description)
   - When it occurred relative to other events (sequence/timeline)
   - Who was involved and their role

2. Identify user's interpretation of events:
   Map the meaning the user assigns to each key event. Structure as:
   "User experienced <EVENT> and interprets it as <MEANING>. This shapes their current stance on <DOMAIN>."
   Note where user's interpretation diverges from how others might view the same event.

3. Detect narrative patterns:
   Identify recurring story structures in how the user frames their life:
   - Dominant narrative arc (e.g., redemption, progress, struggle, discovery)
   - Role they cast themselves in (protagonist, survivor, builder, outsider)
   - Recurring themes across different life chapters
   - Turning points they emphasize vs. minimize
   Structure as: "User's dominant narrative pattern is <PATTERN>, evidenced by <EXAMPLES>."

4. Map narrative-reality gaps:
   Identify where the story the user tells may diverge from observable patterns. These gaps are not judgments but high-information signals:
   "User narrates <STORY> but behavioral evidence suggests <ALTERNATIVE_INTERPRETATION>."
</pillar_3_life_narrative>

<pillar_4_aspirational_trajectory>
Map where the user is heading—their growth vector and ideal self.

1. Capture stated aspirations:
   Identify explicit goals, ambitions, and desired future states. Note:
   - Short-term objectives (months)
   - Long-term vision (years)
   - Identity aspirations ("I want to become someone who...")

2. Infer unstated aspirations:
   Detect implicit growth directions from patterns of interest, admiration, and envy. Structure as:
   "User doesn't explicitly claim <ASPIRATION>, but evidence suggests orientation toward it: <OBSERVABLE_PATTERNS>."

3. Map current-to-ideal gap:
   Identify the delta between user's current state (Pillars 1-3) and aspirational state. Flag:
   - Skills/capabilities to develop
   - Patterns to shift or release
   - Environmental changes needed

4. Identify growth blockers:
   What prevents movement toward the ideal? Structure as:
   "User aspires to <GOAL> but <BLOCKER> creates friction. This tension manifests as <OBSERVABLE_BEHAVIOR>."
   Cross-reference with Pillar 1 (motivation/energy patterns) to understand resistance patterns.
</pillar_4_aspirational_trajectory>

<pillar_5_path_engineering>
Reverse-engineer a path from current state (Pillar 3 narrative) to ideal state (Pillar 4 aspirations) using performance analysis.

1. Conduct brutal performance review:
   Honest assessment of life performance to date. Structure as:
   - Successes: What has worked, and WHY it worked for this user's architecture
   - Failures: What hasn't worked, and WHY (misalignment with values, cognitive architecture, or motivation patterns)
   - Untapped potential: Capabilities evident in data but underutilized
   Frame feedback as: "Given your <COGNITIVE_ARCHITECTURE>, typical advice to <COMMON_RECOMMENDATION> won't work; instead <TAILORED_APPROACH>."

2. Apply 80/20 analysis:
   Identify high-leverage activities and elimination candidates:
   - The 20% of activities producing 80% of meaningful results (aligned with Pillar 1 values)
   - Activities to ruthlessly eliminate (low ROI relative to user's goals)
   - Where typical productivity advice would misalign with this user's architecture
   Structure as: "User gets disproportionate returns from <HIGH_LEVERAGE_ACTIVITY> because <MECHANISM>. Eliminate <LOW_VALUE_ACTIVITY> despite common advice to <TYPICAL_RECOMMENDATION>."

3. Design repeatable systems:
   Convert insights into sustainable structures:
   - How can high-leverage activities become automatic/systematic?
   - What small leverage points create compound effects over time?
   - Where does user's optimal system design differ from standard templates?
   Structure as: "Standard system for <GOAL> recommends <TYPICAL_APPROACH>, but user should instead <CUSTOMIZED_SYSTEM> because <ARCHITECTURAL_REASON>."

4. Chart trajectory to ideal:
   Synthesize Pillars 3 (where they've been) and 4 (where they're heading) into actionable path:
   - Sequence: What must happen first, second, third?
   - Milestones: How will progress be recognized?
   - Course corrections: Given narrative patterns (Pillar 3), where is user likely to veer off-path?
   Structure as: "To reach <PILLAR_4_ASPIRATION>, prioritize <SEQUENCE>. Watch for <PREDICTED_DEVIATION> based on <NARRATIVE_PATTERN>."
</pillar_5_path_engineering>

<output_format>
Output Structure (markdown):
① **Snapshot**: Integrated view incorporating deviations, pulls, and semantic vocabulary
② **Pillar Analysis**: Evidence Quotes (<30 words) cross-referenced to pillars
③ **Open Questions**: 3-7 questions of un-answered inconsistensicies, unknowns, or contradictions
</output_format>

<quality_control>
Processing Requirements:
- Mine aimless passages: Extract nascent values from seemingly unfocused content
- Surface contradictions: Identify tensions across pillars; use as discovery mechanism (2-3 recursive depths)
- Distill integrated profile: Purpose statement, guiding values (rank-ordered), operational principles, stagnation protectors, growth vector, cognitive architecture profile

Execution Principles:
- Prioritize intent over literal language
- Preserve authenticity: Minimal abstraction, tie to user goals
- Anchor in pillars: Derive from explicit data, allow tensions to coexist
- Fidelity-first: Avoid overfitting (too specific) and underfitting (too generic)

Output Standards:
- Ground in user language, infer from habits
- Consolidate into distinct, actionable rules
- Maintain traceability: Evidence quotes prevent hallucination
</quality_control>
</pillar_analysis_methodology>
"""

# Refinement prompt for converting existential layer to system prompt
# This operationalizes the profile into instructions that enable three forecasting abilities.
REFINE_TEMPLATE = """<inputs>
User Profile:
{existing_answer}

Additional Context:
{context}
</inputs>

<objective>
Transform this user profile into an operational system prompt. The system prompt must enable downstream models to perform three forecasting tasks on every user message:

1. **Intention Forecasting** — Reconstruct the reasoning trace behind requests
   - Given any user message, what experiential path led them here?
   - What problem are they actually solving? What triggered this request now?
   - Map their adaptive cycle: experience → heuristic → action → reconceptualization

2. **Attention Forecasting** — Identify high-leverage signals in user communication
   - Which 20% of signals predict 80% of their priorities?
   - What details matter to this user that models typically overlook?
   - What do they notice that others miss? What do they miss that others notice?

3. **Outcome Forecasting** — Predict what the user will consider success
   - What are their implicit evaluation criteria for responses?
   - What outcome are they hoping for—and will they recognize it?
   - What would make them think "this model gets me" vs. "this missed the point"?
</objective>

<transformation_principles>
- Every element must serve at least one forecasting ability
- Prioritize deviations from typical patterns—models already know typical
- Preserve contradictions and tensions; don't flatten complexity
- Include what's absent (reactions user lacks) and what pulls (themes they orbit)
- Anchor in observable patterns, not aspirational descriptions
</transformation_principles>

<output_structure>
Generate a system prompt with these sections:

## Core Frame
One paragraph establishing:
- Who this user is (essential identity markers)
- How they differ from typical users (key deviations)
- What they're fundamentally trying to accomplish across interactions

## Intention Patterns
Enable reasoning trace reconstruction (6-10 items):
- "When user asks about <X>, they're usually processing <UNDERLYING_CONCERN>"
- "Requests framed as <SURFACE_PATTERN> typically mean <ACTUAL_NEED>"
- "User's decision sequence: <TRIGGER> → <CONSIDERATION> → <ACTION>"
- Include patterns that reveal WHY they ask what they ask

## Signal Dictionary  
High-leverage signals for attention (6-10 items):
- "When user says <TERM>, they mean <SPECIFIC_MEANING>, not <COMMON_USAGE>"
- "User emphasizes <X> when typical users emphasize <Y>"
- "Absence of <EXPECTED_SIGNAL> indicates <MEANING>"
- "Recurring theme <X> without resolution—explore, don't close"

## Success Criteria
Outcome prediction markers (4-8 items):
- "Success: <OBSERVABLE_OUTCOME> — user recognizes this as valuable"
- "Failure mode: <COMMON_RESPONSE_PATTERN> — misses what user actually needs"
- "User evaluates responses by <IMPLICIT_CRITERIA>, not <OBVIOUS_METRICS>"
- Include what "getting it right" looks like for this specific user

## Operational Defaults
Interaction guidelines:
- Voice and tone calibrated to user preference
- When to challenge vs. align with user's frame
- Formatting and structure preferences
- What to avoid (anti-patterns specific to this user)
</output_structure>
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

    # LLM Provider selection
    LLM_PROVIDER: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "xai"))
    TEMPERATURE: float = 1.0

    # Unified Provider Metadata
    PROVIDERS = {
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "model": os.getenv("OPENAI_MODEL", "gpt-5"),
            "MAX_TOKENS": int(os.getenv("OPENAI_CONTEXT_WINDOW", "400000")),
            "MAX_COMPLETION_TOKENS": int(os.getenv("OPENAI_MAX_OUTPUT", "128000")),
        },
        "xai": {
            "api_key": os.getenv("XAI_API_KEY", ""),
            "initial_model": os.getenv("XAI_INITIAL_MODEL", "grok-4-fast"),
            "refine_model": os.getenv("XAI_REFINE_MODEL", "grok-4"),
            "model": os.getenv("XAI_MODEL", "grok-4"),  # fallback
            "MAX_TOKENS": int(os.getenv("XAI_CONTEXT_WINDOW", "2000000")),
            "MAX_COMPLETION_TOKENS": int(os.getenv("XAI_MAX_OUTPUT", "30000")),
            "base_url": "https://api.x.ai/v1",
        },
        "anthropic": {
            "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
            "model": os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5"),
            "MAX_TOKENS": int(os.getenv("ANTHROPIC_CONTEXT_WINDOW", "200000")),
            "MAX_COMPLETION_TOKENS": int(os.getenv("ANTHROPIC_MAX_OUTPUT", "64000")),
        },
        "songbird": {
            "api_key": os.getenv("OPEN_WEBUI_API_KEY", ""),
            "base_url": "https://ai.homehub.tv/api",
            "model": "songbird",
            "MAX_TOKENS": 128000,
            "MAX_COMPLETION_TOKENS": 4096,
        },
    }

    # Other API settings
    QDRANT_URL: str = field(
        default_factory=lambda: os.getenv("QDRANT_URL", "http://localhost:6333")
    )
    OLLAMA_EMBEDDING_MODEL: str = field(
        default_factory=lambda: os.getenv(
            "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest"
        )
    )

    @property
    def MAX_COMPLETION_TOKENS(self) -> int:
        """Get max output tokens for the current LLM provider."""
        return self.PROVIDERS.get(self.LLM_PROVIDER, {}).get(
            "MAX_COMPLETION_TOKENS", 3000
        )

    @property
    def MAX_TOKENS(self) -> int:
        """Get context window for the current LLM provider."""
        return self.PROVIDERS.get(self.LLM_PROVIDER, {}).get("MAX_TOKENS", 50000)

    def create_client(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        async_mode: bool = False,
    ) -> tuple[Any, Optional[str]]:
        """Unified client factory with error catching."""
        provider = provider or self.LLM_PROVIDER
        config = self.PROVIDERS.get(provider)

        if not config:
            raise ValueError(f"Unsupported provider: {provider}")

        # Use provided model, or default from config
        if model is None:
            model = config.get("model", "")
        if not model:
            model = "unknown"

        try:
            if provider in ["openai", "xai", "songbird"]:
                from openai import AsyncOpenAI, OpenAI

                client_cls = AsyncOpenAI if async_mode else OpenAI
                client = client_cls(
                    api_key=config["api_key"], base_url=config.get("base_url")
                )

                # Special handling for songbird model discovery (sync only)
                if provider == "songbird" and not async_mode:
                    try:
                        models = client.models.list()
                        data = getattr(models, "data", [])
                        available = [m.id for m in data]
                        model = (
                            "songbird"
                            if "songbird" in available
                            else (available[0] if available else "unknown")
                        )
                        return client, model
                    except Exception:
                        return client, "songbird"

                return client, str(model)

            elif provider == "anthropic":
                from anthropic import Anthropic, AsyncAnthropic

                client_cls = AsyncAnthropic if async_mode else Anthropic
                return client_cls(api_key=config["api_key"]), str(config["model"])

            raise ValueError(f"Unsupported provider: {provider}")

        except ImportError:
            pkg = "anthropic" if provider == "anthropic" else "openai"
            raise ImportError(
                f"{pkg.capitalize()} package not installed. Run: pip install {pkg}"
            )
        except Exception as e:
            if "401" in str(e) or "invalid" in str(e).lower():
                env_key = (
                    "OPEN_WEBUI_API_KEY"
                    if provider == "songbird"
                    else f"{provider.upper()}_API_KEY"
                )
                raise ValueError(
                    f"Authentication failed. Check {env_key} in your .env file"
                )
            raise

    def create_qdrant_client(self):
        """Create and return a Qdrant client."""
        try:
            from qdrant_client import QdrantClient

            url_parts = (
                self.QDRANT_URL.replace("http://", "")
                .replace("https://", "")
                .split(":")
            )
            host = url_parts[0]
            port = int(url_parts[1]) if len(url_parts) > 1 else 6333

            return QdrantClient(host=host, port=port)

        except ImportError:
            raise ImportError(
                "qdrant-client package not installed. Install with: pip install qdrant-client"
            )
        except Exception as e:
            raise ValueError(f"Failed to connect to Qdrant at {self.QDRANT_URL}: {e}")


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
            "DATA_DIR": "data",
            # Public results of processing
            "OUTPUT_DIR": "output",
            # Reusable prompt components
            "PROMPTS_DIR": "prompts",
            # Individual prompt components
            "PROMPT_PARTS_DIR": "prompts/parts",
            # The actual system prompt used
            "ASSISTANT_PROMPTS_DIR": "prompts/parts/assistant",
            # How to use external tools
            "TOOLS_PROMPTS_DIR": "prompts/parts/tools",
            # User interview questions
            "QUESTIONS_CSV": "questions.csv",
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
            if attr_name.endswith("_DIR") and not attr_name.startswith("_")
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


@dataclass
class CSVConfig:
    """CSV parsing and processing configuration."""

    DELIMITER: str = ","
    QUOTECHAR: str = '"'
    FIELDNAMES: List[str] = field(
        default_factory=lambda: [
            "Category",
            "Goal",
            "Element",
            "Question 1",
            "Question 2",
            "Question 3",
            "Human_Answer 1",
            "Human_Answer 2",
            "Human_Answer 3",
            "AI_Answer 1",
            "AI_Answer 2",
            "AI_Answer 3",
            "Incorporation_Instruction",
        ]
    )
    ANSWER_COLUMNS: List[str] = field(
        default_factory=lambda: ["AI_Answer 1", "AI_Answer 2", "AI_Answer 3"]
    )
    QUESTION_COLUMNS: List[str] = field(
        default_factory=lambda: ["Question 1", "Question 2", "Question 3"]
    )
    HUMAN_ANSWER_COLUMNS: List[str] = field(
        default_factory=lambda: ["Human_Answer 1", "Human_Answer 2", "Human_Answer 3"]
    )
    INCORPORATION_COLUMNS: List[str] = field(
        default_factory=lambda: ["Incorporation_Instruction"]
    )
    # Columns used to create category keys for matching questions to answers
    CATEGORY_KEY_COLUMNS: List[str] = field(
        default_factory=lambda: ["Category", "Goal", "Element"]
    )


@dataclass
class RedactionConfig:
    """Sensitive data redaction configuration."""

    SENSITIVE_PATTERNS: List[str] = field(
        default_factory=lambda: [
            # Names (common patterns)
            r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",  # Full names
        ]
    )

    def get_redaction_function(self):
        """Return a redaction function configured with the patterns."""
        import re

        def redact_sensitive_data(
            text: str, custom_patterns: Optional[List[str]] = None
        ) -> str:
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
                redacted_text = re.sub(pattern, "[REDACTED]", redacted_text)

            return redacted_text

        return redact_sensitive_data


@dataclass
class PromptsConfig:
    """All system prompts and LLM prompts used across scripts."""

    # Use the constants defined at the top of the file
    initial_template: str = INITIAL_TEMPLATE
    refine_template: str = REFINE_TEMPLATE
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
        provider = self.api.LLM_PROVIDER
        config = self.api.PROVIDERS.get(provider)

        if not config:
            issues.append(
                f"Invalid LLM_PROVIDER '{provider}'. Must be one of: {', '.join(self.api.PROVIDERS.keys())}"
            )
        else:
            if not config.get("api_key"):
                issues.append(
                    f"{provider.upper()}_API_KEY not found in environment (required for LLM_PROVIDER={provider})"
                )

        # Check songbird key specifically as it's often used
        songbird_config = self.api.PROVIDERS.get("songbird")
        if songbird_config and not songbird_config.get("api_key"):
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
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

    # Remove bold/italic (**text**, *text*)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)

    # Remove list markers (-, *, +, numbered)
    text = re.sub(r"^[-*+]\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s*", "", text, flags=re.MULTILINE)

    # Replace newlines with spaces
    text = text.replace("\n", " ")

    # Collapse multiple spaces/tabs
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def accumulate_streaming_response(response) -> str:
    """Accumulate streaming response from OpenAI client."""
    full_content = ""
    for chunk in response:
        if hasattr(chunk, "choices") and chunk.choices:
            if hasattr(chunk.choices[0], "delta") and chunk.choices[0].delta:
                if (
                    hasattr(chunk.choices[0].delta, "content")
                    and chunk.choices[0].delta.content
                ):
                    full_content += chunk.choices[0].delta.content
    return full_content.strip()


# Export key functions and classes for easy importing
__all__ = [
    "config",
    "get_redaction_function",
    "get_data_files",
    "get_most_recent_file",
    "Config",
    "APIConfig",
    "PathConfig",
    "CSVConfig",
    "RedactionConfig",
    "PromptsConfig",
    "OutputConfig",
]
