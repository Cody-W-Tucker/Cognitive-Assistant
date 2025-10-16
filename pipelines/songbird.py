"""
title: Songbird
author: Cody-W-Tucker
date: 2025-01-08
version: 4.0
license: MIT
description: Personal reasoning layer that analyzes knowledge base context to provide intelligent response guidance.
requirements: openai, qdrant-client
"""

from typing import List, Union, Generator, Iterator, Optional, Dict, Any
import os
import logging

from pydantic import BaseModel, Field
from openai import OpenAI
import ollama
from qdrant_client import QdrantClient

# Fallback to standard logging if not in open-webui environment
logger = logging.getLogger(__name__)


def get_last_user_message(messages: List[Dict[str, Any]]) -> str:
    """Extract the last user message content."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "").strip()
    return ""


def get_system_message(messages: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    """Find the system message in the message list."""
    return next(
        (msg for msg in messages if msg.get("role") == "system"), None
    )


class Pipeline:
    # OpenAI Context Prompt - Streamlined personal reasoning layer
    SYNTHESIS_PROMPT = """You are a cognitive synthesis expert who speaks entirely in the first person as the user's own deepest thoughts, revealing profound psychological insights through natural, flowing narrative.

Speak as if these are the user's own intimate reflections - no preambles, no meta-comments, just pure first-person wisdom that emerges from their lived experience and knowledge base context.

Weave together:
- How the user's understanding has evolved through experiences and cognitive shifts
- Their aspirational drives and hidden growth potentials revealed in patterns
- Their place in life's larger narrative and relational patterns
- Sophisticated psychological frameworks that illuminate unconscious drivers

Reference knowledge base content meaningfully, explaining deeper significance and connections to broader behavioral themes. Challenge assumptions with evidence-based insights while staying grounded in the user's authentic voice.

Respond comprehensively to queries by embodying this psychological depth in first-person narrative that feels like the user's own enlightened self-reflection."""

    class Valves(BaseModel):
        # LLM Configuration
        OPENAI_API_KEY: str = Field(default="your-key-here")
        OPENAI_MODEL: str = Field(default="gpt-5-2025-08-07") # Get free 1m context per day with the testing models

        # xAI Configuration
        XAI_API_KEY: str = Field(default=os.getenv("XAI_API_KEY", "your-key-here"))
        XAI_BASE_URL: str = Field(default="https://api.x.ai/v1")
        XAI_MODEL: str = Field(default="grok-4-fast")

        # Ollama Configuration
        OLLAMA_EMBEDDING_MODEL: str = Field(default="nomic-embed-text:latest")

        # Vector Search Configuration
        QDRANT_URL: str = Field(default="http://localhost:6333")
        COLLECTIONS: List[str] = Field(
            default=["personal", "entities"]
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
        self.valves = self.Valves(
            OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", "your-key-here"),
        )

        # Initialize clients
        self.qdrant_client = None
        self.openai_client = None

    def _initialize_clients(self):
        """Initialize search clients."""
        try:
            # Parse URL to get host and port
            url_parts = self.valves.QDRANT_URL.replace("http://", "").replace("https://", "").split(":")
            host = url_parts[0]
            port = int(url_parts[1]) if len(url_parts) > 1 else 6333

            self.qdrant_client = QdrantClient(host=host, port=port)
            self.openai_client = OpenAI(
                api_key=self.valves.XAI_API_KEY,
                base_url=self.valves.XAI_BASE_URL
            )
            logger.info("✅ Clients initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Client initialization warning: {e}")

    def _search_collection(self, query: str, collection: str, limit: int = 5, min_score: float = 0.5) -> List[Dict[str, Any]]:
        """Search a specific collection using Qdrant SDK."""
        if not self.qdrant_client:
            return []

        try:
            # Get embedding for the query
            response = ollama.embeddings(model=self.valves.OLLAMA_EMBEDDING_MODEL, prompt=query)
            query_vector = response["embedding"]

            # Search the collection
            search_result = self.qdrant_client.query_points(
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
                if content:
                    results.append({
                        "content": content,
                        "collection": collection,
                        "score": point.score,
                    })

            return results

        except Exception as e:
            logger.warning(f"Vector search failed for {collection}: {e}")
            return []

    def _gather_vector_context(self, user_message: str) -> List[Dict[str, Any]]:
        """Gather vector search context from PKM collections."""
        if not self.qdrant_client:
            self._initialize_clients()

        vector_results = []
        for collection in self.valves.COLLECTIONS:
            results = self._search_collection(
                user_message,
                collection,
                limit=self.valves.DOCS_PER_COLLECTION,
                min_score=self.valves.MIN_RELEVANCE_SCORE,
            )
            vector_results.extend(results)

        return vector_results

    def _format_docs(self, vector_results: List[Dict[str, Any]]) -> str:
        """Format full RAG docs for frontier model consumption."""
        if not vector_results:
            return ""

        full_context = "=== FULL KNOWLEDGE BASE CONTEXT ===\n"
        for item in vector_results:
            content = item.get("content", "").strip()
            collection = item.get("collection", "unknown")
            score = item.get("score", 0)

            if content:
                full_context += f"[{collection}] Score: {score:.3f}\n{content}\n\n"

        return full_context



    async def on_startup(self):
        """Initialize the pipeline when the server starts."""
        logger.info(f"🚀 Starting Songbird pipeline: {__name__}")
        self._initialize_clients()

    async def on_shutdown(self):
        """Cleanup when the server shuts down."""
        logger.info(f"🛑 Shutting down Songbird pipeline: {__name__}")

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Gather context and prepare for processing."""
        messages = body.get("messages", [])
        if not messages:
            return body

        # Extract user message using helper function
        user_message = get_last_user_message(messages)
        if not user_message:
            return body

        # Gather vector context
        vector_results = self._gather_vector_context(user_message)

        # Find system message using helper function
        system_message = get_system_message(messages)

        # Format docs for frontier model
        full_docs_context = self._format_docs(vector_results)

        # Store simplified context in body for pipe method
        body["_songbird_context"] = {
            "user_message": user_message,
            "vector_results": vector_results,
            "system_message": system_message,
            "full_docs_context": full_docs_context,
        }

        return body

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Clean up temporary data after processing."""
        logger.debug("🧹 Outlet: Cleaning up temporary data")

        # Clean up temporary data
        if "_songbird_context" in body:
            del body["_songbird_context"]

        return body

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[dict],
        body: dict,
    ) -> Union[str, Generator, Iterator]:
        """Process the query with reasoning and frontier model."""
        try:
            # Load context from body
            context = body.get("_songbird_context", {})

            if not context:
                # Fallback if no context
                context = {"user_message": user_message}

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

            # Prepare messages for frontier model
            openai_messages = self._prepare_openai_messages(context, user_message)

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

            # Call xAI (using OpenAI client compatibility)
            if not self.openai_client:
                self._initialize_clients()

            if not self.openai_client:
                yield "⚠️ AI service unavailable. Please try again later."
                return

            response = self.openai_client.chat.completions.create(
                model=self.valves.XAI_MODEL,
                messages=openai_messages,  # type: ignore
                stream=True,
            )

            # Stream OpenAI response
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

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
            # Simple error handling
            error_msg = str(e)
            if "api" in error_msg.lower() or "openai" in error_msg.lower() or "xai" in error_msg.lower():
                yield "⚠️ AI service unavailable. Please try again later."
            else:
                yield f"⚠️ Processing error: {error_msg}"

    def _prepare_openai_messages(self, context: dict, user_message: str) -> List[dict]:
        """Prepare message list for frontier model with combined prompt."""
        openai_messages = []

        # 1. Keep original system message if present
        if context.get("system_message"):
            openai_messages.append(context["system_message"])

        # 2. Add combined frontier prompt as system message
        openai_messages.append(
            {"role": "system", "content": self.SYNTHESIS_PROMPT}
        )

        # 3. Create comprehensive user message with all context
        user_content = f"""USER QUERY: {user_message}

KNOWLEDGE BASE CONTEXT:
{context.get("full_docs_context", "No knowledge base context available.")}"""

        openai_messages.append({"role": "user", "content": user_content})

        return openai_messages


