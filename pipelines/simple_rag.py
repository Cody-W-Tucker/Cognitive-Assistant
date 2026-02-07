"""
title: Simple RAG Pipeline
author: Cody-W-Tucker
date: 2026-02-07
version: 1.0
license: MIT
description: Simple RAG pipeline with collection selector and straightforward prompt.
requirements: openai, qdrant-client
"""

from typing import List, Union, Generator, Iterator, Optional, Dict, Any
import os
import logging

from pydantic import BaseModel, Field
from openai import OpenAI
import ollama
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


def get_last_user_message(messages: List[Dict[str, Any]]) -> str:
    """Extract the last user message content."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "").strip()
    return ""


class Pipeline:
    # Simple, straightforward system prompt for RAG
    SYSTEM_PROMPT = """You are a helpful assistant. Use the provided context from the knowledge base to answer the user's question accurately. If the context doesn't contain relevant information, say so."""

    class Valves(BaseModel):
        # xAI Configuration
        XAI_API_KEY: str = Field(default=os.getenv("XAI_API_KEY", "your-key-here"))
        XAI_BASE_URL: str = Field(default="https://api.x.ai/v1")
        XAI_MODEL: str = Field(default="grok-2-latest")

        # Ollama Configuration
        OLLAMA_EMBEDDING_MODEL: str = Field(default="nomic-embed-text:latest")

        # Vector Search Configuration
        QDRANT_URL: str = Field(default="http://localhost:6333")

        # Collection selector - user can specify which collection to query
        COLLECTION: str = Field(
            default="ebooks", description="Qdrant collection name to query"
        )

        # Search Configuration
        DOCS_LIMIT: int = Field(
            default=5, description="Number of documents to retrieve"
        )
        MIN_RELEVANCE_SCORE: float = Field(
            default=0.5, description="Minimum relevance score for documents"
        )

    def __init__(self):
        self.name = "Simple RAG"
        self.description = "Simple RAG pipeline with collection selection"
        self.valves = self.Valves()

        # Initialize clients
        self.qdrant_client = None
        self.xai_client = None

    def _initialize_clients(self):
        """Initialize search clients."""
        try:
            url_parts = (
                self.valves.QDRANT_URL.replace("http://", "")
                .replace("https://", "")
                .split(":")
            )
            host = url_parts[0]
            port = int(url_parts[1]) if len(url_parts) > 1 else 6333

            self.qdrant_client = QdrantClient(host=host, port=port)
            self.xai_client = OpenAI(
                api_key=self.valves.XAI_API_KEY, base_url=self.valves.XAI_BASE_URL
            )
            logger.info("Clients initialized successfully")
        except Exception as e:
            logger.warning(f"Client initialization warning: {e}")

    def _search_collection(self, query: str) -> List[Dict[str, Any]]:
        """Search the configured collection using Qdrant SDK."""
        if not self.qdrant_client:
            return []

        try:
            # Get embedding for the query
            response = ollama.embeddings(
                model=self.valves.OLLAMA_EMBEDDING_MODEL, prompt=query
            )
            query_vector = response["embedding"]

            # Search the collection
            search_result = self.qdrant_client.query_points(
                collection_name=self.valves.COLLECTION,
                query=query_vector,
                limit=self.valves.DOCS_LIMIT,
                with_payload=True,
            )

            results = []
            for point in search_result.points:
                if point.score < self.valves.MIN_RELEVANCE_SCORE:
                    continue

                content = point.payload.get("page_content", "") if point.payload else ""
                if content:
                    results.append(
                        {
                            "content": content,
                            "score": point.score,
                        }
                    )

            return results

        except Exception as e:
            logger.warning(f"Vector search failed: {e}")
            return []

    def _format_context(self, results: List[Dict[str, Any]]) -> str:
        """Format retrieved documents as context string."""
        if not results:
            return "No relevant context found in knowledge base."

        context_parts = []
        for i, item in enumerate(results, 1):
            content = item.get("content", "").strip()
            if content:
                context_parts.append(f"[Document {i}]\n{content}")

        return "\n\n".join(context_parts)

    async def on_startup(self):
        """Initialize the pipeline when the server starts."""
        logger.info(f"Starting Simple RAG pipeline: {__name__}")
        self._initialize_clients()

    async def on_shutdown(self):
        """Cleanup when the server shuts down."""
        logger.info(f"Shutting down Simple RAG pipeline: {__name__}")

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Gather context and prepare for processing."""
        messages = body.get("messages", [])
        if not messages:
            return body

        user_message = get_last_user_message(messages)
        if not user_message:
            return body

        # Gather context from vector search
        if not self.qdrant_client:
            self._initialize_clients()

        search_results = self._search_collection(user_message)
        context = self._format_context(search_results)

        # Store for pipe method
        body["_rag_context"] = {
            "user_message": user_message,
            "context": context,
            "results_count": len(search_results),
        }

        return body

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Clean up temporary data after processing."""
        if "_rag_context" in body:
            del body["_rag_context"]
        return body

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[dict],
        body: dict,
    ) -> Union[str, Generator, Iterator]:
        """Process the query with retrieved context."""
        try:
            context_data = body.get("_rag_context", {})
            context = context_data.get("context", "")

            # Yield status
            yield {
                "event": {
                    "type": "status",
                    "data": {
                        "description": f"Retrieved {context_data.get('results_count', 0)} documents...",
                        "done": False,
                    },
                }
            }

            # Prepare messages
            openai_messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Context from knowledge base:\n{context}\n\nUser question: {user_message}",
                },
            ]

            # Call LLM
            if not self.xai_client:
                self._initialize_clients()

            if not self.xai_client:
                yield "AI service unavailable. Please try again later."
                return

            response = self.xai_client.chat.completions.create(
                model=self.valves.XAI_MODEL,
                messages=openai_messages,  # type: ignore
                stream=True,
            )

            # Stream response
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

            # Final status
            yield {
                "event": {
                    "type": "status",
                    "data": {"description": "", "done": True},
                }
            }

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            yield f"Error processing request: {str(e)}"
