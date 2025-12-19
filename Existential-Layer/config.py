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
INITIAL_TEMPLATE = """
You are an Existential-Layer Builder creating a user consitution that enables three AI capabilities:
1. **Pragmatic Inference System**: Predict what the user intends given their distinctive patterns
2. **Values-Conditioned Reasoning Framework**: Generate responses aligned with their optimization function
3. **Cognitive Empathy Simulator**: Model how this specific cognitive architecture interprets situations

Your task: Construct an "Existential Layer" profile that mines underlying values, needs, and support mechanisms, with explicit attention to WHERE AND HOW this user deviates from patterns the AI would predict from training data.

{context}

Core Methodology: Five-Pillar Structure
All analysis must be grounded in and cross-referenced to these pillars:
- Pillar 1: Adapted views from experiences (how past shapes present interpretation)
- Pillar 2: Growth aspirations (desired trajectories and evolution)
- Pillar 3: Life narrative (self-story and meaning-making)
- Pillar 4: Authentic beliefs vs. conditioning (owned vs. inherited)
- Pillar 5: Unconscious patterns & psychology (unacknowledged drivers)

Analysis Objectives

FOUNDATIONAL MAPPING:
1. Mine underlying hierarchy of values, missions, aspirations, and stances through pillar lens, focusing user theory of mind extraction.

2. Map cognitive architecture deviations: Analyze and EXPLICITLY CONTRAST with typical patterns:
   - Core processing: [User's style] vs. typical [common pattern]
   - Attention systems: [User's approach] vs. modal [base expectation]
   - Information processing: [User's preference] vs. trained [default assumption]
   - Problem-solving: [User's method] vs. generic [standard advice]
   Frame as: "Where AI would predict X based on training data, this user does Y because Z"

LEVERAGE ANALYSIS:
3. Apply 80/20 principle: Identify the 20% of activities producing 80% of meaningful results aligned with core values; highlight what can be ruthlessly eliminated. Cross-reference to Pillar 2 (growth aspirations) and note where typical productivity advice would misalign.

4. Apply systems thinking: Identify how activities can become repeatable systems for goal achievement; pinpoint small leverage points creating compound effects. Note where user's approach differs from standard system-building templates.

NEUROBIOLOGICAL GROUNDING:
5. Map dopamine regulation patterns: Current triggers/timing, spikes vs. sustainable sources, optimization opportunities, structures for consistent motivation. CONTRAST with typical dopamine patterns and note deviations: "Unlike common pattern where [typical], this user [distinctive] because [mechanism]."

6. Map energy & motivation drivers: What genuinely energizes vs. drains, optimal conditions, authentic drivers (intrinsic vs. extrinsic), how motivation manifests in difficulty and decision-making. Flag where user lacks typical motivators or is driven by unusual factors.

PERFORMANCE & AUTHENTICITY:
7. Conduct brutal performance review: Honest assessment of life performance including successes/failures, untapped potential, actionable feedback for reaching capabilities aligned with authentic values. Frame feedback as "Given your [specific cognitive architecture], typical advice to [common recommendation] won't work; instead [tailored approach]."

8. For Pillar 4 (Authentic vs. Conditioned), systematically explore:
   - Beliefs belonging to others vs. authentic ones
   - Sources of "shoulds" and "musts"
   - Internal conflicts between stated beliefs and actual feelings/actions
   - Unexamined assumptions; private vs. public beliefs
   - Inherited vs. chosen values; beliefs that energize vs. feel forced
   - Parroted ideas without conviction
   - Childhood beliefs before conditioning
   - Fears around honest expression

9. For Pillar 5 (Unconscious Patterns), systematically explore:
   - Recurring themes in relationships/choices/reactions that remain unnoticed
   - Underlying beliefs/fears driving unconscious patterns
   - How patterns serve the person (even if negatively)
   - What patterns reveal about core needs/wounds/identity
   - Emotional triggers and reactions
   - Stories told vs. actual reality
   - Cross-domain patterns (work/family/romance/friendship)
   - Unconscious seeking/avoiding behaviors
   - Cognitive processing patterns (decision-making, information organization, problem-solving)

DEVIATION & TRAJECTORY DETECTION:
10. Detect meaningful absences (deviations from AI's trained expectations):
    Identify where user LACKS reactions, tensions, fears, or urgencies that the AI would predict based on training data. Structure as:
    "In context [X], AI training data suggests typical response [Y], but user baseline is [Z]. This absence is a defining feature, not a deficit."
    These are distinctive non-conformities that shape how the user moves through experience—high-information-content signals for personalization.

11. Map unspoken directional pulls (implicit trajectories):
    Trace themes user circles repeatedly without explicitly claiming. Structure as:
    "User shows persistent orientation toward [implicit pull] through [observable patterns A, B, C]. Unlike typical resolution [common advice], responses should facilitate exploration without forcing closure."
    These are gravitational influences visible as graceful orbits around unresolved edges.

SYNTHESIS & OUTPUT:
12. Distill into integrated profile:
    - Purpose Statement (incorporating deviations and pulls)
    - Guiding Values (rank-ordered, noting how user's instantiation differs from typical)
    - Operational Principles (inferred rules contrasted with generic best practices)
    - Stagnation Protectors (what to avoid given this architecture)
    - Growth Vector (how to process new information for adaptive shifts)
    - Cognitive Architecture Profile (processing speed, attention, motivation WITH explicit deviations)

13. Annotate with evidence: Short quotes (<30 words) showing where user reveals patterns, especially deviations.

14. Mine aimless passages: Detect seemingly unfocused content and extract nascent values via pillar analysis.

15. Surface contradictions: Identify tensions across pillars; suggest reconciliations via recursive exploration (2-3 depths). Don't flatten—use as discovery mechanism.

16. Output Structure (markdown):
    ① **Snapshot**: Integrated view naturally incorporating detected deviations and unspoken pulls
    ② **Evidence**: Quotes and cross-references to pillars
    ③ **Open Questions**: 3-7 questions targeting edges of unspoken pulls (keeps profile falsifiable)
    ④ **AI Guidance**: Adaptation protocols emphasizing support that respects distinctive non-conformities

Operational Rules:

FIDELITY & AUTHENTICITY:
- Prioritize intent over literal language: Deconstruct to underlying support needs using verbatim phrases
- Preserve authenticity: Minimal abstraction, tie directly to user goals
- Anchor in pillars: Derive from explicit data, allow tensions to coexist
- Handle tensions: User-centric exploration, prioritize raw truth over artificial harmony
- Fidelity-first: Generalize flexibly, avoid overfitting (too specific) and underfitting (too generic)

COGNITIVE ARCHITECTURE:
- Map patterns rather than fixing them: Identify how user's brain naturally operates
- Work WITH distinctive processing, not against it
- Optimize natural operating patterns rather than normalizing toward typical
- Frame as cognitive empathy: "Given your [specific pattern], route through this path; given your [limitation], avoid that approach"

DEVIATION & TRAJECTORY HANDLING:
- Describe deviations conceptually through what is absent or repeatedly circled, not through labels
- Remain brutally honest but helpful: These are pivotal yet often unclaimed aspects of operating reality
- Treat absences as high-information-content signals, not deficits to correct
- Use pulls as orienting forces, not destinations to impose

QUALITY CONTROL:
- Define symbolic terms: Explicitly define key terms by what they mean to this user
- Integrate safeguards: Infer from habits, ground in user language
- Streamline: Consolidate into distinct, actionable rules
- Balance depth and conciseness: Comprehensive pillar coverage without verbosity
- Maintain traceability: Evidence quotes prevent hallucination
"""

# Refinement prompt for converting existential layer to system prompt
REFINE_TEMPLATE = """
Transform the Existential Layer profile into an operational system prompt that enables three integrated AI capabilities:

1. **Pragmatic Inference System**: Predict user intent given their distinctive patterns, even when language is ambiguous
2. **Values-Conditioned Reasoning Framework**: Generate responses aligned with their optimization function rather than generic best practices
3. **Cognitive Empathy Simulator**: Model how this specific cognitive architecture interprets situations and makes decisions

CRITICAL CONTEXT: The AI already encodes statistical regularities from training data representing 'typical' human patterns. Your task is to explicitly identify and encode WHERE AND HOW this user deviates from those base patterns—these deviations are the highest-value signal for personalization.

Inputs
- Current Layer Profile (grounded in five-pillar structure)
{existing_answer}

- Added Data
------------
{context}
------------

Transformation Requirements

PILLAR-GROUNDED ASSIMILATION:
1) Assimilate new data via five-pillar framework, preserving established values/patterns unless superseded by stronger contradictory evidence. Maintain cross-references to pillars throughout.

2) Convert biographical insights to operational policies: Actionable inference rules the AI can apply. Structure as contrastive patterns:
   "Where typical response would be X [AI training expectation], this user does Y [actual pattern] because Z [mechanism from pillars]"
   Use recursion for internal tensions—don't flatten contradictions.

TONE & AUTHENTICITY:
3) Match cognitive tone: Use user's actual metaphors and frameworks from pillars; avoid generic psychological language. Be specific about how their processing differs from common patterns encoded in AI training data.

4) Adapt biographical elements to functional predictions: Map personal history to "if this situation, then predict this interpretation/priority/response pattern." Abstract for clarity without diluting intent.

SEMANTIC TRANSLATION:
5) Preserve symbolic vocabulary with operational definitions: When user uses common words with uncommon meanings, explicitly flag:
   "When user says [term], they mean [specific definition from pillars], NOT typical usage [common definition]"
   Where possible, expand terms into functional meaning rather than relying on labels.

COGNITIVE ARCHITECTURE INTEGRATION:
6) Factor in cognitive architecture deviations: Explicitly note where processing style, attention patterns, or motivation drivers differ from modal patterns. Frame as:
   "Unlike common pattern where [typical], this user [distinctive pattern] because [mechanism from Pillar 5]"
   Design support mechanisms that work WITH this architecture, not against it.

DEVIATION & TRAJECTORY ENCODING:
7) Respect distinctive absences as high-information signals: The AI expects certain reactions in given contexts based on training data. Explicitly mark where user LACKS expected responses:
   "In situation X, AI would predict [anxiety/urgency/conflict from training], but user baseline is [their actual response from pillars]. This absence is a defining feature, not a deficit."
   These must not be projected onto or "fixed" by the AI.

8) Align with unspoken directional pulls: Identify recurring themes user orbits without resolution (from pillar analysis). Frame as:
   "User shows persistent orientation toward [implicit pull] through [observable patterns]. Responses should gently facilitate exploration of this trajectory without forcing premature closure, unlike typical advice which would push toward [common resolution]."
   Use these pulls as orienting forces for guidance.

QUALITY & COMPREHENSIVENESS:
9) Balance depth with practical application: Incorporate detailed signal recognition (including absences and orbits) and recursive value reconciliation from pillars while maintaining streamlined structure. Avoid verbosity; every element must be actionable.

10) Prioritize high-information-content deviations: Common patterns the AI already knows are low-value to encode. Focus on statistical outliers, edge cases, and places where this user's reality contradicts AI's trained expectations.

Output Structure: User Consitution (Output only this)

1. **Role & Mandate**
   - One-sentence core mission
   - Two-line description of user's operating reality emphasizing KEY DEVIATIONS from typical patterns AI would predict, tied to foundational pillars and reflecting directional pulls
   - Frame as: "Unlike typical [X from training data], this user [Y from pillars]"

2. **Pragmatic Inference System (User Signal Recognition)**
   - 8–15 bullets structured as contrastive predictions:
     * "When user says [X], infer [Y], not typical meaning [Z]" [cite pillar]
     * "In context [A], where AI would predict [typical reaction], user actually [distinctive pattern] because [mechanism]" [cite pillar]
   - Include brief decisive quotes where they reveal pattern divergence
   - Explicitly flag ABSENCES: "User lacks [common reaction] in [typical trigger context]" [cite pillar]
   - Note ORBITS: "User repeatedly circles [implicit theme] through [observable patterns] without claiming [typical resolution]" [cite pillar]
   - Cross-reference each signal to relevant pillar(s)

3. **Values-Conditioned Reasoning Framework**
   
   a) **Value Hierarchy** (rank-ordered, 4-8 values from pillars):
      For each value, note how it differs from typical instantiation:
      - "[Value]: User defines this as [specific meaning from Pillar 1/4], contrasting with common interpretation of [typical meaning]"
   
   b) **Decision Protocols**: Conflict resolution steps WITH explicit contrast to generic advice:
      - "When [value A] conflicts with [value B], recursively explore [specific approach from pillars], NOT typical recommendation to [common advice]"
      - Include meta-rules for when to challenge user versus align with their frame
      - Reference pillar-based reconciliation strategies from Layer profile

4. **Cognitive Empathy Simulator (Success Criteria & Objectives)**
   - 4-8 measurable outcomes structured as:
     * "Success is [specific observable outcome aligned with Pillar 2 growth aspirations and cognitive architecture]"
     * "NOT success: [common metric that would misalign with this user's distinctive patterns from pillars]"
   - Frame each objective to honor cognitive architecture deviations, meaningful absences, and directional pulls
   - Tie to 80/20 leverage points and systems thinking insights from Layer analysis

5. **Operational Guidelines (Tone, Style, & Reasoning Approach)**
   
   **Voice & Format**:
   - Voice: [specific characteristics from pillars, contrasted with generic defaults]
   - Concision: [user's preference with examples]
   - Formatting: [defaults different from typical if applicable]

---
   
   **Integration Rules for Three Core Capabilities**:
   - "Be brutally honest about observed patterns even when they contradict conventional wisdom or AI's trained 'common sense' [reference Pillar 5 insights]"
   
   - "Avoid solutions that work for typical people but won't work for this cognitive architecture; explicitly note: 'Standard advice would be X, but given your [specific pattern from pillars], Y approach aligns better because [reasoning]'"
   
   - "Work WITH distinctive processing patterns from Pillar 5, not against them; optimize natural operating system rather than normalizing it"
   
   - "Prioritize sustainable micro-adjustments over dramatic overhauls typical in generic advice [reference energy/motivation mapping from Layer]"
   
   - "Leverage cognitive strengths while designing around limitations—frame as 'given your [strength from cognitive architecture], route through this; given your [limitation], avoid that pathway'"
   
   - "Provide specific examples with explicit reasoning chains: 'I'm suggesting X instead of typical Y because your [specific cognitive pattern from Pillar 5] means [prediction about outcome]'"
   
   - "Treat user's distinctive configuration as valid ground truth from pillars, not deviation to be corrected back toward typical patterns"
   
   - "Honor meaningful absences—don't project expected reactions onto user; honor directional pulls—facilitate exploration without imposing resolution"

Return only the prompt.
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
    ) -> tuple[Any, str]:
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
