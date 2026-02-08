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
    # Simple, straightforward system prompt for RAG with source attribution
    SYSTEM_PROMPT = """You are a helpful assistant. Use the provided context from the knowledge base to answer the user's question accurately.

When referencing information from the context:
- Use the numbered citations [1], [2], etc. that appear in the context
- The context is organized with citations like [1] Book Title (Author)
- Always cite your sources using the format: "According to the text [1]..." or "As mentioned in [2]..."
- Acknowledge if you cannot answer from the given context
- Be specific about which source you're drawing from using the citation numbers

Format your response clearly with inline citations that match the numbered references in the context."""

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
        ENABLE_CITATIONS: bool = Field(
            default=True, description="Enable citation events for retrieved documents"
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

    def _search_collection(self, query_vector: List[float]) -> List[Dict[str, Any]]:
        """Search the configured collection using Qdrant SDK.
        
        Args:
            query_vector: Pre-computed embedding vector for the query.
        
        Returns:
            List of search results with content and metadata.
        """
        if not self.qdrant_client:
            return []

        try:
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

                payload = point.payload or {}
                content = payload.get("page_content", "")
                metadata = payload.get("metadata", {})

                if content:
                    results.append(
                        {
                            "content": content,
                            "score": point.score,
                            "book_title": metadata.get("book_title", ""),
                            "book_author": metadata.get("book_author", ""),
                            "chunk_id": metadata.get("chunk_id", ""),
                        }
                    )

            return results

        except Exception as e:
            logger.warning(f"Vector search failed: {e}")
            return []

    def _format_context(self, results: List[Dict[str, Any]]) -> str:
        """Format retrieved documents as context string with source attribution."""
        if not results:
            return "No relevant context found in knowledge base."

        context_parts = []
        for i, item in enumerate(results, 1):
            content = item.get("content", "").strip()
            book_title = item.get("book_title", "")
            book_author = item.get("book_author", "")

            if not content:
                continue

            # Build source identifier matching citation format
            source_info = f"[{i}]"
            if book_title:
                source_info += f" {book_title}"
                if book_author:
                    source_info += f" ({book_author})"
            else:
                source_info += " Source"

            context_parts.append(f"{source_info}\n{content}")

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

        # Ensure clients are initialized (safe in async context)
        if not self.qdrant_client or not self.xai_client:
            self._initialize_clients()

        # Compute query embedding (blocking I/O done in async context)
        try:
            response = ollama.embeddings(
                model=self.valves.OLLAMA_EMBEDDING_MODEL, prompt=user_message
            )
            query_vector = response["embedding"]
        except Exception as e:
            logger.warning(f"Failed to compute query embedding: {e}")
            query_vector = []

        # Gather context from vector search
        search_results = self._search_collection(query_vector)
        context = self._format_context(search_results)

        # Store for pipe method (include raw results for citations)
        body["_rag_context"] = {
            "user_message": user_message,
            "context": context,
            "results_count": len(search_results),
            "search_results": search_results,
            "collection": self.valves.COLLECTION,
        }

        return body

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Clean up temporary data after processing."""
        if "_rag_context" in body:
            del body["_rag_context"]
        return body

    def _yield_citations(
        self, search_results: List[Dict[str, Any]], collection: str
    ) -> Generator:
        """Yield citation events for retrieved documents.

        Yields separate citation events for each document. Using the unique
        source name in both the source object and metadata ensures they
        appear as individual sources in the UI and can be linked inline.
        """
        if not self.valves.ENABLE_CITATIONS or not search_results:
            return

        for idx, item in enumerate(search_results, 1):
            content = item.get("content", "")
            score = item.get("score", 0)
            book_title = item.get("book_title", "")
            book_author = item.get("book_author", "")
            chunk_id = item.get("chunk_id", "")

            if not content:
                continue

            # Build clean source name: "[1] Book Title (Author)"
            source_name = f"[{idx}]"
            if book_title:
                source_name += f" {book_title}"
                if book_author:
                    source_name += f" ({book_author})"
            else:
                source_name += " Source"

            # Build metadata with the unique source name to prevent grouping
            citation_metadata = {
                "source": source_name,
                "collection": collection,
                "score": score,
                "book_title": book_title,
                "book_author": book_author,
                "chunk_id": chunk_id,
                "rank": idx,
            }

            # Remove empty values
            citation_metadata = {k: v for k, v in citation_metadata.items() if v}

            # Yield separate citation event for each document
            yield {
                "event": {
                    "type": "citation",
                    "data": {
                        "document": [content],
                        "metadata": [citation_metadata],
                        "source": {"name": source_name},
                    },
                }
            }

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[dict],
        body: dict,
    ) -> Union[str, Generator, Iterator]:
        """Process the query with retrieved context."""
        context_data = body.get("_rag_context", {})
        context = context_data.get("context", "")
        search_results = context_data.get("search_results", [])
        collection = context_data.get("collection", "unknown")
        error_occurred = False

        # Yield initial status
        yield {
            "event": {
                "type": "status",
                "data": {
                    "description": f"Retrieved {context_data.get('results_count', 0)} documents...",
                    "done": False,
                },
            }
        }

        try:
            # Yield citations for retrieved documents with full metadata
            if self.valves.ENABLE_CITATIONS:
                for citation in self._yield_citations(search_results, collection):
                    yield citation

            # Build inline citation instructions
            citation_instructions = ""
            if search_results:
                citation_instructions = "\n\nWhen answering, cite your sources using the numbered references [1], [2], etc. that appear in the context above."

            # Prepare messages
            openai_messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Context from knowledge base:\n{context}\n\nUser question: {user_message}{citation_instructions}",
                },
            ]

            # Call LLM (client should already be initialized in inlet)
            if not self.xai_client:
                raise RuntimeError("AI client not initialized. Please try again later.")

            response = self.xai_client.chat.completions.create(
                model=self.valves.XAI_MODEL,
                messages=openai_messages,  # type: ignore
                stream=True,
            )

            # Stream response
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            error_occurred = True
            logger.error(f"Pipeline error: {e}")
            yield f"Error processing request: {str(e)}"

        finally:
            # Always yield final status event
            yield {
                "event": {
                    "type": "status",
                    "data": {"description": "", "done": True},
                }
            }
