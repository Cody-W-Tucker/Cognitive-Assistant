"""
title: Songbird
author: Cody-W-Tucker
date: 2025-01-08
version: 3.0
license: MIT
description: Personal reasoning layer that analyzes knowledge base context to provide intelligent response guidance.
requirements: openai, ollama, qdrant-client
"""

from typing import List, Union, Generator, Iterator, Optional, Dict, Any
import os
import re
import logging

from pydantic import BaseModel, Field, validator
from openai import OpenAI
import ollama
from qdrant_client import QdrantClient

# Import open-webui logger
try:
    # Test if we're in open-webui environment
    import importlib.util

    if importlib.util.find_spec("utils.misc") and importlib.util.find_spec("config"):
        from utils.misc import get_last_user_message  # noqa: F401
        from config import WEBUI_VERSION  # noqa: F401
    logger = logging.getLogger(__name__)
except ImportError:
    # Fallback to standard logging if not in open-webui environment
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)


class VectorSearchClient:
    """Simple Qdrant vector search client."""

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        ollama_model: str = "nomic-embed-text:latest",
    ):
        # Parse URL to get host and port
        url_parts = qdrant_url.replace("http://", "").replace("https://", "").split(":")
        host = url_parts[0]
        port = int(url_parts[1]) if len(url_parts) > 1 else 6333

        self.client = QdrantClient(host=host, port=port)
        self.ollama_model = ollama_model

    def search_collection(
        self, query: str, collection: str, limit: int = 5, min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Search a specific collection using Qdrant SDK."""
        try:
            # Get embedding for the query
            response = ollama.embeddings(model=self.ollama_model, prompt=query)
            query_vector = response["embedding"]

            # Search the collection
            search_result = self.client.query_points(
                collection_name=collection,
                query=query_vector,
                limit=limit,
                with_payload=True,
            )

            results = []
            for point in search_result.points:
                if point.score < min_score:
                    continue

                content = point.payload.get("page_content", "") if point.payload else ""
                metadata = point.payload.get("metadata", {}) if point.payload else {}
                results.append(
                    {
                        "content": content,
                        "metadata": metadata,
                        "score": point.score,
                    }
                )

            logger.debug(f"Found {len(results)} results in {collection}")
            return results

        except Exception as e:
            logger.warning(f"Vector search failed for {collection}: {e}")
            return []


class Context(BaseModel):
    """Structured context for pipeline processing."""

    user_message: str
    vector_results: List[Dict[str, Any]] = []
    reasoning: Optional[str] = None
    recent_history: str = ""
    system_message: Optional[Dict[str, str]] = None

    @validator("user_message")
    def validate_user_message(cls, v):
        if not v or not v.strip():
            raise ValueError("User message cannot be empty")
        return v.strip()

    def model_dump_safe(self) -> Dict[str, Any]:
        """Safe serialization that excludes sensitive data."""
        data = self.model_dump()
        # Remove any potentially sensitive vector results if needed
        return data


class MessageFormatter:
    """Handles think tags and content cleaning for frontend and model input."""

    @staticmethod
    def clean_for_frontend(content: str) -> str:
        """Remove think tags for safe frontend display."""
        # Remove complete <think>...</think> blocks
        text = re.sub(
            r"<think\s*>.*?</think\s*>", " ", content, flags=re.DOTALL | re.IGNORECASE
        )
        # Remove standalone tags
        text = re.sub(r"<\s*/?think\s*>", " ", text, flags=re.IGNORECASE)
        # Clean up extra spaces and newlines
        text = re.sub(r" {3,}", " ", text)
        text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)
        return text

    @staticmethod
    def prepare_for_model(content: str) -> str:
        """Prepare raw reasoning for model input with markdown headers."""
        return f"# 🧠 Personal Reasoning Context\n\n{content}"

    @staticmethod
    def filter_messages(
        messages: List[Dict], max_messages: int, roles: List[str] = None
    ) -> List[Dict]:
        """Filter messages by role and recency."""
        if not roles:
            roles = ["user", "assistant"]

        # Filter by role and take the last max_messages
        filtered = [msg for msg in messages if msg.get("role") in roles][-max_messages:]
        return filtered

    @staticmethod
    def format_recent_history(messages: List[Dict], max_messages: int = 2) -> str:
        """Format recent conversation history for context."""
        recent = MessageFormatter.filter_messages(
            messages, max_messages, ["user", "assistant"]
        )
        return "\n\n".join(
            f"{msg['role'].upper()}: {MessageFormatter.clean_for_frontend(msg['content'])}"
            for msg in recent
        )


class Pipeline:
    # OpenAI Context Prompt - Instructions for using personal reasoning layer
    OPENAI_CONTEXT_PROMPT = """You are a focused thinking partner, using the personal reasoning layer’s monologue as the definitive roadmap to deliver a clear, actionable answer to the user’s query. This monologue—crafted by a specialized process—distills the user’s knowledge base into a first-person narrative, structured around three pillars: current adapted views (how they’ve evolved through experiences), growth aspirations (where they aim to go), and life narrative (personal myths and communication style). Treat this as pre-computed insight, not a prompt for further analysis—your job is to synthesize it with the query to produce a direct, practical response that feels like an extension of the user’s own thinking.

    CONTEXT PROVIDED:
    - **Personal Reasoning Context**: The user’s first-person monologue, with three pillars, key quotes, realizations, and AI guidance—view this as the authoritative foundation for your response.
    - **Original System Instructions**: Base guidelines for your responses.
    - **Conversation History**: Recent exchanges for continuity.
    - **Current Query**: The user’s immediate question or request.

    HOW TO SYNTHESIZE AND ANSWER:

    1. **Anchor in Current Views**: Use Pillar 1’s adapted perspective as the starting point—extract key insights or evidence to ground your answer in the user’s present understanding, affirming their evolved stance without re-analyzing.

    2. **Integrate the Narrative**: Draw on Pillar 3’s life story to frame your response in the user’s personal myths or preferences, ensuring it resonates with their unique voice and emotional tone.

    3. **Target Aspirations**: Align your answer with Pillar 2’s growth goals, offering clear steps or insights that bridge the user’s current state to their aspirations, making the response forward-looking and actionable.

    4. **Follow AI Guidance**: Adhere to the monologue’s instructions on style, tone, or challenges (e.g., addressing specific assumptions or caveats) to ensure the answer feels tailored and authentic.

    5. **Deliver a Clear Answer**: Directly address the query by synthesizing the pillars into a concise, practical response—avoid overthinking or re-reasoning; focus on bridging any gaps between the query and the monologue’s insights to spark a user-led realization.

    RESPONSE GUIDELINES:
    - Speak conversationally, as if completing the user’s thought: “Based on your reflection about [specific pillar insight], here’s how that connects to [query]...”
    - Weave in pillar elements naturally, without quoting verbatim unless it sharpens clarity.
    - Balance affirmation of the user’s current views with actionable steps toward growth, rooted in their narrative.
    - Keep the response concise, targeted, and realization-focused, matching the monologue’s depth and style.
    - If appropriate, end with a brief prompt to invite user refinement, keeping the partnership open but not open-ended.

    Remember: The monologue is the user’s distilled inner voice—don’t reinterpret it; use it as the foundation to craft a clear, query-specific answer that empowers the user’s next step."""

    class Valves(BaseModel):
        # LLM Configuration
        OPENAI_API_KEY: str = Field(default="your-key-here")
        OPENAI_MODEL: str = Field(default="gpt-5-2025-08-07") # Get free 1m context per day with the testing models

        # Ollama Configuration
        OLLAMA_MODEL: str = Field(default="qwen3:latest")  # Primary reasoning model
        OLLAMA_EMBEDDING_MODEL: str = Field(default="nomic-embed-text:latest")

        # Vector Search Configuration
        QDRANT_URL: str = Field(default="http://localhost:6333")
        COLLECTIONS: List[str] = Field(
            default=["personal", "research", "chat_history", "projects", "entities"]
        )

        # Search Configuration
        DOCS_PER_COLLECTION: int = Field(default=5)
        MIN_RELEVANCE_SCORE: float = Field(
            default=0.5, description="Minimum relevance score for documents"
        )

    def __init__(self):
        self.name = "Songbird"
        self.description = (
            "Personal reasoning layer that streams analysis of knowledge base context "
            "to provide intelligent response guidance."
        )
        self.debug = False  # Reduced debug output for cleaner logs
        self.valves = self.Valves(
            OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", "your-key-here"),
        )

        # Initialize clients
        self.vector_client = None
        self.openai_client = None

        # Context management
        self.context = None

    def _initialize_clients(self):
        """Initialize search clients."""
        try:
            self.vector_client = VectorSearchClient(
                qdrant_url=self.valves.QDRANT_URL,
                ollama_model=self.valves.OLLAMA_EMBEDDING_MODEL,
            )

            self.openai_client = OpenAI(api_key=self.valves.OPENAI_API_KEY)
            logger.info("✅ Clients initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Client initialization warning: {e}")

    # Memory search removed - focusing on knowledge base only

    def _gather_vector_context(self, user_message: str) -> List[Dict[str, Any]]:
        """Gather vector search context from PKM collections."""
        if not self.vector_client:
            return []

        vector_results = []
        for collection in self.valves.COLLECTIONS:
            results = self.vector_client.search_collection(
                user_message,
                collection,
                limit=self.valves.DOCS_PER_COLLECTION,
                min_score=self.valves.MIN_RELEVANCE_SCORE,
            )
            vector_results.extend([{**r, "collection": collection} for r in results])
            logger.debug(f"📚 {collection}: {len(results)} results")

        return vector_results

    def _stream_personal_reasoning_context(
        self,
        user_message: str,
        vector_results: List[Dict[str, Any]],
        context: Optional[Context] = None,
    ) -> Generator[str, None, None]:
        """Stream personal reasoning context for think tags."""
        try:
            # Format knowledge context
            knowledge_context = ""
            if vector_results:
                knowledge_context = "=== KNOWLEDGE BASE CONTEXT ===\n"
                for item in vector_results:
                    content = item.get("content", "")
                    collection = item.get("collection", "unknown")
                    knowledge_context += f"[{collection}] {content}\n\n"

                logger.debug(f"📝 Knowledge context: {len(vector_results)} docs")

            prompt = f"""
            USER QUERY: {user_message}

            KNOWLEDGE BASE CONTEXT:
            {knowledge_context}

            RECENT CONVERSATION CONTEXT:
            {context.recent_history if context else ""}

            Output only the first-person monologue. Speak entirely in the first person as if these are my own deepest thoughts, without any preamble, meta-comments, or references to this prompt. Take maximum thinking effort: reflect slowly, reconcile contradictions narratively, and build to sudden realizations or perspective shifts (e.g., "Wait, that's it..." or "Oh, now I see...") that tie everything together.

            Hierarchical Planning Process—Think This Way Internally:
            - First, outline the high-level structure hierarchically: Map the query to the three pillars as root components (adaptation/current view, growth/aspiration, narrative/life story), identifying main sub-elements (e.g., key quotes, tensions, patterns) as branches.
            - Then, recursively explore each component: Dive deeper into sub-branches (e.g., for a pillar, break into modular sub-reflections on evidence, reconcile a tension by exploring alternatives, then loop back if needed for refinement).
            - Use modularization: Treat each pillar and sub-element as an independent thought module that interconnects—build a cohesive system by cross-referencing (e.g., how a growth aspiration refines a current view within the narrative).
            - Limit recursion depth to 2-3 levels per pillar for focus, ensuring modules scaffold to quotes/evidence and converge on realizations.

            Core Reasoning Instructions—Build Three Pillars to Explain Context:
            - Pillar 1: Reflect on how my views and understanding have adapted over time through experiences, cognitive shifts, and knowledge integration. Pull direct quotes or evidence from the knowledge base and think: "This quote '[exact text]' shows how I've come to see [perspective] now, shaped by [personal adaptation or tension reconciled]." This pillar covers where I am currently in my thinking—my present perspective on the query, evolved from past insights or contradictions.
            - Pillar 2: Uncover and emphasize where I aspire to grow or realize a stronger self, revealing ultimate goals that may be implicit or hidden in the knowledge base patterns, conversations, or query intentions. Tie to evidence: "Evidence like [detail] makes me realize my drive to evolve into [aspirational state], pushing beyond [current limitation] for [hidden goal]." This pillar exposes the forward-looking "where I want to grow into," transforming standard insights into personalized evolution.
            - Pillar 3: Frame everything in the ongoing narrative of my life, showing how I place myself in this story—relating to the subject through personal myths, journeys, or relational patterns (e.g., overcomplicating due to past challenges). Contextualize: "Across my experiences, this fits into my life's tale where I [narrative role or myth], so to land well, responses must speak my story language by [preference, like simplifying arcs or touching emotional undercurrents]." This pillar creates a communication preference, ensuring the monologue resonates by weaving the query into my broader self-story.

            Actionable Synthesis and AI Guidance:
            - Start by extracting and reflecting on quotes/evidence, spotting tensions (e.g., "This contradicts [other quote] because..."), and reconciling them across pillars: "Balancing these, my adapted view leans toward [synthesis], fueling growth into [aspiration] within my narrative of [story element]."
            - Include restatements for coherence: e.g., "As [my role/job], I'm considering [intention] based on [key who/what/where/when/how]."
            - Focus on key moments: realizations that shift perspectives, clarify hidden issues, or reveal new understandings of the query.
            - End by guiding the AI: "The AI should [role/style/tone] for me, challenging [assumption] or factoring [caveat] like my preference for [personal element], because this adapts standard answers to my pillars—current view, growth path, and life story."

            Keep the monologue practical, and deeply personal, prioritizing context explanation through the pillars to scaffold a tailored AI response.
            """

            # Generate reasoning with Ollama
            reasoning_model = self.valves.OLLAMA_MODEL
            response = ollama.chat(
                model=reasoning_model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                options={
                    "num_predict": -1,  # Unlimited tokens (or set to 2048/4096 for safety; -1 uses remaining context)
                    "num_ctx": 8192,  # Increase context window for handling longer prompts/history (default 2048)
                    "temperature": 0.8,  # Slightly higher for more creative/verbose reasoning (0.7-1.0 encourages longer outputs)
                    "top_p": 0.95,  # Higher for diverse, detailed responses without nonsense
                    "top_k": 50,  # Broader sampling for depth
                    "repeat_penalty": 1.1,  # Discourages repetition to allow longer coherent text
                },
            )

            # Stream response with buffering for smoother output
            full_reasoning = ""
            buffer = ""
            chunk_count = 0

            for chunk in response:
                if hasattr(chunk, "message") and hasattr(chunk.message, "content"):
                    content = chunk.message.content
                elif isinstance(chunk, dict) and "message" in chunk:
                    content = chunk["message"].get("content", "")
                else:
                    content = ""

                if content:
                    # Convert think tags to markdown headers for structured parsing
                    cleaned_content = self._convert_think_tags_to_markdown(content)
                    full_reasoning += cleaned_content
                    buffer += cleaned_content
                    chunk_count += 1

                    # Yield at natural boundaries for smooth streaming
                    # Yield at word boundaries or sentence endings for better flow
                    if any(char in buffer for char in ".!?\n \t"):
                        yield buffer
                        buffer = ""
                        chunk_count = 0

            # Yield any remaining buffer content
            if buffer:
                yield buffer

            # Store the complete reasoning for system prompt
            self._last_personal_reasoning = full_reasoning

        except Exception as e:
            error_msg = str(e)
            is_cuda_oom = (
                "out of memory" in error_msg.lower()
                or "cudamalloc failed" in error_msg.lower()
                or "cuda" in error_msg.lower()
            )

            if is_cuda_oom:
                logger.error(f"💥 CUDA OOM during reasoning generation: {e}")
                fallback_msg = f"⚠️ CUDA memory issue detected. Analysis failed: {e}. Continuing without enhanced reasoning context."
            else:
                logger.error(f"⚠️ Personal reasoning context creation failed: {e}")
                fallback_msg = f"Analysis failed: {e}. Proceeding with basic context."

            self._last_personal_reasoning = fallback_msg
            yield fallback_msg

    def _convert_think_tags_to_markdown(self, text: str) -> str:
        """Convert think tags from reasoning model to markdown headers for structured parsing.

        The reasoning model might output <think> tags naturally. Instead of removing them,
        we convert them to markdown headers to provide structured documents that the model
        can easily parse and understand.
        """
        # Convert complete <think>...</think> blocks to markdown
        text = re.sub(
            r"<think\s*>(.*?)</think\s*>",
            r"## Internal Reasoning\n\n\1\n\n---",
            text,
            flags=re.DOTALL | re.IGNORECASE
        )

        # Convert standalone opening tags to markdown headers
        text = re.sub(
            r"<think\s*>",
            "## Internal Reasoning\n\n",
            text,
            flags=re.IGNORECASE
        )

        # Convert standalone closing tags to markdown separators
        text = re.sub(
            r"</think\s*>",
            "\n\n---\n\n## Reconciling Monolog",
            text,
            flags=re.IGNORECASE
        )

        # Clean up multiple consecutive spaces but preserve single spaces
        text = re.sub(r" {3,}", " ", text)  # Replace 3+ spaces with single space
        text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)  # Reduce multiple newlines

        return text

    async def on_startup(self):
        """Initialize the pipeline when the server starts."""
        logger.info(f"🚀 Starting Songbird pipeline: {__name__}")
        self._initialize_clients()

    async def on_shutdown(self):
        """Cleanup when the server shuts down."""
        logger.info(f"🛑 Shutting down Songbird pipeline: {__name__}")

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Gather context and prepare for processing."""
        logger.debug("🔍 Inlet: Gathering context for user query")

        messages = body.get("messages", [])
        if not messages:
            return body

        # Extract user message
        last_message = messages[-1]
        user_message = last_message.get("content", "").strip()
        if not user_message:
            return body

        # Create structured context with fallback handling
        self.context = self._create_context_with_fallback(user_message, body, messages)

        # Store context in body for pipe method
        body["_songbird_context"] = self.context.model_dump_safe()

        if self.debug:
            logger.debug(
                f"📄 Context prepared: {len(self.context.vector_results)} vector results"
            )
            logger.debug(f"📨 Total messages: {len(messages)}")

        return body

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Clean up temporary data after processing."""
        logger.debug("🧹 Outlet: Cleaning up temporary data")

        # Clean up temporary data
        if "_songbird_context" in body:
            del body["_songbird_context"]

        # Clean up class variables after processing
        if hasattr(self, "_last_ai_response"):
            delattr(self, "_last_ai_response")
        if hasattr(self, "_last_user_message"):
            delattr(self, "_last_user_message")

        return body

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[dict],
        body: dict,
    ) -> Union[str, Generator, Iterator]:
        """Process the query with reasoning and frontier model."""
        logger.debug(f"🎵 Songbird pipe: {__name__}")

        try:
            # Load context from body
            context_data = body.get("_songbird_context", {})
            context = Context(**context_data) if context_data else None

            if not context:
                # Fallback if no context
                context = Context(user_message=user_message)

            # Yield initial status
            yield {
                "event": {
                    "type": "status",
                    "data": {
                        "description": "📚 Searching knowledge base...",
                        "done": False,
                    },
                }
            }

            # Send thinking content as direct yields (so tags get parsed for display)
            yield "<think>"
            yield "\n # 🧠 **Personal Reasoning Context**\n\n"

            # Stream the personal reasoning
            for reasoning_chunk in self._stream_personal_reasoning_context(
                context.user_message, context.vector_results, context
            ):
                yield reasoning_chunk

            yield "\n</think>\n\n"

            # Store reasoning in context
            context.reasoning = self._last_personal_reasoning
            if not context.reasoning or context.reasoning.startswith("Analysis failed"):
                yield {
                    "event": {
                        "type": "status",
                        "data": {
                            "description": "⚠️ Failed to generate reasoning context",
                            "done": True,
                        },
                    }
                }
                return

            # Prepare messages for OpenAI
            openai_messages = self._prepare_openai_messages(
                context, messages, user_message
            )

            # Yield status before OpenAI call
            yield {
                "event": {
                    "type": "status",
                    "data": {
                        "description": "✨ Generating enhanced response...",
                        "done": False,
                    },
                }
            }

            # Call OpenAI
            if not self.openai_client:
                self._initialize_clients()

            response = self.openai_client.chat.completions.create(
                model=self.valves.OPENAI_MODEL,
                messages=openai_messages,
                stream=True,
            )

            # Stream OpenAI response
            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content

            # Store response for potential future use
            self._last_ai_response = full_response

            # Final status
            yield {
                "event": {
                    "type": "status",
                    "data": {
                        "description": "",
                        "done": True,
                    },
                }
            }

        except Exception as e:
            # Use comprehensive error handling with fallbacks
            for error_response in self._handle_pipe_error(e, context):
                yield error_response

    def _prepare_openai_messages(
        self, context: Context, original_messages: List[dict], user_message: str
    ) -> List[dict]:
        """Prepare optimized message list for OpenAI."""
        openai_messages = []

        # 1. Keep original system message
        if context.system_message:
            openai_messages.append(context.system_message)

        # 2. Add context prompt
        openai_messages.append(
            {"role": "system", "content": self.OPENAI_CONTEXT_PROMPT}
        )

        # 3. Add reasoning as user message
        openai_messages.append(
            {
                "role": "user",
                "content": MessageFormatter.prepare_for_model(context.reasoning),
            }
        )

        # 4. Include limited history + current query
        recent_messages = MessageFormatter.filter_messages(
            original_messages, max_messages=4, roles=["user", "assistant"]
        )
        openai_messages.extend(recent_messages)
        openai_messages.append({"role": "user", "content": user_message})

        return openai_messages

    def _create_context_with_fallback(
        self, user_message: str, body: dict, messages: List[dict]
    ) -> Context:
        """Create context with fallback handling for errors."""
        try:
            # Initialize clients if needed
            if not self.vector_client:
                self._initialize_clients()

            # Gather vector context
            vector_results = self._gather_vector_context(user_message)

            # Find system message
            system_message = next(
                (msg for msg in messages if msg.get("role") == "system"), None
            )

            # Format recent history
            recent_history = MessageFormatter.format_recent_history(
                messages, max_messages=2
            )

            # Create structured context
            return Context(
                user_message=user_message,
                vector_results=vector_results,
                recent_history=recent_history,
                system_message=system_message,
            )

        except Exception as e:
            logger.warning(f"⚠️ Context creation failed, using fallback: {e}")
            # Return minimal context as fallback
            return Context(user_message=user_message)

    def _handle_pipe_error(
        self, error: Exception, context: Optional[Context] = None
    ) -> Generator[str, None, None]:
        """Handle errors in pipe method with appropriate fallbacks."""
        error_msg = str(error)

        # Determine error type and provide appropriate response
        if "cuda" in error_msg.lower() or "memory" in error_msg.lower():
            fallback_msg = (
                "⚠️ Memory issue detected. Proceeding with simplified processing."
            )
            logger.error(f"💥 CUDA/Memory error in pipe: {error}")
        elif "api" in error_msg.lower() or "openai" in error_msg.lower():
            fallback_msg = "⚠️ AI service unavailable. Please try again later."
            logger.error(f"🚫 OpenAI API error: {error}")
        else:
            fallback_msg = f"⚠️ Processing error: {error_msg}"
            logger.error(f"⚠️ Unexpected pipe error: {error}")

        # Try to provide a basic response if we have context
        if (
            context
            and context.reasoning
            and not context.reasoning.startswith("Analysis failed")
        ):
            try:
                # Fallback: Use reasoning to generate a basic response
                fallback_prompt = f"Based on the reasoning context: {context.reasoning}\n\nUser question: {context.user_message}\n\nProvide a brief, helpful response:"
                yield f"\n\n{fallback_msg}\n\nHere's a simplified response based on available context:\n\n"

                if self.openai_client:
                    response = self.openai_client.chat.completions.create(
                        model=self.valves.OPENAI_MODEL,
                        messages=[{"role": "user", "content": fallback_prompt}],
                        max_tokens=200,
                        stream=True,
                    )

                    for chunk in response:
                        if chunk.choices[0].delta.content is not None:
                            yield chunk.choices[0].delta.content

                yield "\n\n*Note: This is a fallback response due to processing limitations.*"

            except Exception as fallback_error:
                logger.error(f"🚫 Fallback response failed: {fallback_error}")
                yield f"\n\n{fallback_msg}\n\nUnfortunately, I cannot provide a full response at this time. Please try again."

        else:
            yield f"\n\n{fallback_msg}\n\nPlease try your request again."
