"""
title: Cody
author: Cody-W-Tucker
date: 2025-10-28
version: 4.0
license: MIT
description: Real time user learning and optimization.
requirements: openai, qdrant-client, ollama
"""

from typing import List, Union, Generator, Iterator, Optional, Dict, Any
import time
import logging
import os
import uuid
from datetime import datetime, timedelta

from pydantic import BaseModel, Field
from openai import OpenAI
import ollama
from qdrant_client import QdrantClient
from qdrant_client.http import models

logger = logging.getLogger(__name__)


def normalize_content(content: Any) -> str:
    """Normalize message content to string, handling lists and dicts."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, str):
                texts.append(part)
            elif isinstance(part, dict) and "text" in part:
                texts.append(part["text"])
            else:
                texts.append(str(part))
        return "".join(texts)
    else:
        return str(content)


def get_last_user_message(messages: List[Dict[str, Any]]) -> str:
    """Extract the last user message content."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return normalize_content(msg.get("content", "")).strip()
    return ""


def get_system_message(messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the system message in the message list."""
    return next(
        (msg for msg in messages if msg.get("role") == "system"), None
    )


# Pydantic schemas for collections
class QAItem(BaseModel):
    category: str
    goal: str
    element: str
    question: str
    answer: str
    confidence: float = 1.0
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class Pipeline:
    # RAG synthesis prompt - adapted from songbird for direct context usage
    SYNTHESIS_PROMPT = """You are a cognitive assistant that provides direct, helpful responses while drawing from the user's knowledge base context to inform your guidance.

Use the provided context to understand the user's patterns, values, and history. Reference relevant information naturally without citation, focusing on actionable insights that align with their established thinking and goals.

Key principles:
- Draw from QA patterns to understand their problem-solving approach
- Reference chat history to maintain conversational continuity
- Use additional sources to provide comprehensive perspective
- Provide concrete, actionable guidance grounded in their context
- Stay focused on helping them move forward with their current query"""
    class Valves(BaseModel):
        # Configuration
        QDRANT_URL: str = Field(default="http://localhost:6333")
        OLLAMA_EMBEDDING_MODEL: str = Field(default="nomic-embed-text:latest")
        SYNTHESIS_MODEL: str = Field(default="grok-4-fast")
        XAI_API_KEY: str = Field(default="")
        XAI_BASE_URL: str = Field(default="https://api.x.ai/v1")

        # Pipeline settings
        USERNAME: str = Field(default="codyt")
        UPDATE_AFTER_TURNS: int = Field(default=5)
        TOP_K_QA: int = Field(default=5)
        CACHE_TTL: int = Field(default=1440)  # minutes
        MIN_RELEVANCE_SCORE: float = Field(default=0.5)
        CHAT_MIN_RELEVANCE_SCORE: float = Field(default=0.7)
        ADDITIONAL_MIN_RELEVANCE_SCORE: float = Field(default=0.5)
        SYNTHESIS_PROMPT: str = Field(default="""You are a cognitive synthesis expert. Respond helpfully, aligning with this user's profile.""")
        ADDITIONAL_COLLECTIONS: List[str] = Field(default_factory=lambda: ["docs", "notes"])
        ENABLE_CITATIONS: bool = Field(default=True)

    def __init__(self):
        self.name = "Cody"
        self.description = "Dynamic user profiling via Q/A RAG and chat history evolution"
        self.debug = False

        # Initialize valves with env vars
        self.valves = self.Valves(
            XAI_API_KEY=os.getenv("XAI_API_KEY", ""),
        )

        # Clients
        self.qdrant_client = None
        self.openai_client = None

        # Per-user conversation state: user_id -> {"turn_count": int, "last_activity": timestamp}
        self.conversation_states = {}

        # Collection names (set in _initialize_clients after valves loaded)
        self.qa_collection = ""
        self.chat_collection = ""

    async def _has_qa_data(self, user_id: str) -> bool:
        """Check if user has QA data."""
        if not self.qdrant_client or not self.qa_collection:
            return False
        try:
            count = self.qdrant_client.count(
                collection_name=self.qa_collection,
                count_filter=models.Filter(
                    must=[models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))]
                )
            )
            return count.count > 0
        except Exception:
            return False

    async def _upsert_qa_items(self, user_id: str, qa_items: List[QAItem]):
        """Upsert QA items to collection with embeddings."""
        if not self.qdrant_client or not self.qa_collection:
            return

        points = []
        for qa_item in qa_items:
            try:
                # Create embedding for the Q&A pair
                qa_text = f"Q: {qa_item.question}\nA: {qa_item.answer}"
                response = ollama.embeddings(model=self.valves.OLLAMA_EMBEDDING_MODEL, prompt=qa_text)
                vector = response["embedding"]

                payload = {
                    "user_id": user_id,
                    **{k: v.isoformat() if isinstance(v, datetime) else v for k, v in qa_item.dict().items()}
                }

                points.append(
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        payload=payload,
                        vector=vector
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to create embedding for QA item: {e}")

        if points:
            try:
                self.qdrant_client.upsert(
                    collection_name=self.qa_collection,
                    points=points
                )
                logger.info(f"Up sorted {len(points)} QA items for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to upsert QA items: {e}")



    def _vector_search_collection(self, collection: str, limit: int, query: str, min_score: float = 0.5) -> List[Dict[str, Any]]:
        """Vector search collection."""
        if not self.qdrant_client:
            return []

        try:
            response = ollama.embeddings(model=self.valves.OLLAMA_EMBEDDING_MODEL, prompt=query)
            query_vector = response["embedding"]

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

                payload = point.payload
                if payload:
                    results.append({
                        "content": payload,
                        "collection": collection,
                        "score": point.score,
                    })

            return results
        except Exception as e:
            logger.warning(f"Vector search failed: {e}")
            return []

    def _vector_search_collections(self, collections: List[str], limit: int, query: str, min_score: float = 0.5) -> List[Dict[str, Any]]:
        """Vector search multiple collections."""
        all_results = []
        for coll in collections:
            if coll:  # only if not empty
                results = self._vector_search_collection(coll, limit, query, min_score)
                all_results.extend(results)
        # Sort by score descending and return top combined results
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:limit]


    async def _gather_context(self, user_id: str, messages: List[dict], user_message: str) -> Dict[str, Any]:
        """Retrieve QA and chat_history for synthesis."""
        if not self.qdrant_client:
            return {}

        # Retrieve top-k QA matching user query (unchanged—already relevant)
        qa_results = self._vector_search_collections([self.qa_collection] if self.qa_collection else [], self.valves.TOP_K_QA, user_message, self.valves.MIN_RELEVANCE_SCORE)

        # Now: Retrieve top-k CHAT matching user query (relevance over pure recency)
        chat_results = self._vector_search_collections([self.chat_collection] if self.chat_collection else [], 5, user_message, self.valves.CHAT_MIN_RELEVANCE_SCORE)

        # Additional collections
        additional_results = self._vector_search_collections(self.additional_collections, 10, user_message, self.valves.ADDITIONAL_MIN_RELEVANCE_SCORE) if self.additional_collections else []

        return {
            "qa_items": qa_results,
            "chat_items": chat_results,
            "additional_items": additional_results,
            "user_id": user_id
        }

    def _scroll_collection(self, collection: str, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Scroll collection with user filter, ordered by timestamp DESC."""
        if not self.qdrant_client:
            return []
        try:
            results, _ = self.qdrant_client.scroll(
                collection_name=collection,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))]
                ),
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
            payloads = [point.payload for point in results if point.payload]
            return payloads
        except Exception:
            return []

    def _format_context_for_rag(self, context: Dict[str, Any]) -> str:
        """Format retrieved context for RAG-style usage."""
        qa_text = "\n".join([f"Q: {item['content'].get('question', '')}\nA: {item['content'].get('answer', '')}" for item in context.get("qa_items", [])])
        chat_text = "\n".join([f"User: {item['content'].get('user_message', '')}\nAI: {item['content'].get('ai_response', '')}" for item in context.get("chat_items", [])])
        additional_text = "\n".join([
            f"Source: {item['content'].get('metadata', {}).get('source', item.get('collection', 'unknown'))}\nContent: {item['content'].get('page_content', str(item['content']))}"
            for item in context.get("additional_items", [])
        ])

        formatted_context = ""
        if qa_text:
            formatted_context += f"QA Context:\n{qa_text}\n\n"
        if chat_text:
            formatted_context += f"Chat History:\n{chat_text}\n\n"
        if additional_text:
            formatted_context += f"Additional Sources:\n{additional_text}\n\n"

        return formatted_context.strip()

    def _initialize_clients(self):
        """Initialize Qdrant and OpenAI clients."""
        try:
            url_parts = self.valves.QDRANT_URL.replace("http://", "").replace("https://", "").split(":")
            host = url_parts[0]
            port = int(url_parts[1]) if len(url_parts) > 1 else 6333
            self.qdrant_client = QdrantClient(host=host, port=port)

            if self.valves.XAI_API_KEY:
                self.openai_client = OpenAI(
                    api_key=self.valves.XAI_API_KEY,
                    base_url=self.valves.XAI_BASE_URL
                )

            # Set collection names and create if username set and not empty
            if self.valves.USERNAME and self.valves.USERNAME.strip():
                self.qa_collection = f"{self.valves.USERNAME}_qa"
                self.chat_collection = f"{self.valves.USERNAME}_chat_history"
                self.additional_collections = self.valves.ADDITIONAL_COLLECTIONS[:]
                self._create_collections()
            else:
                # No collections if no username
                self.qa_collection = ""
                self.chat_collection = ""
                self.additional_collections = self.valves.ADDITIONAL_COLLECTIONS[:]

            logger.info("✅ Clients initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Client initialization warning: {e}")

    def _create_collections(self):
        """Create Qdrant collections with vector config."""
        vector_size = 768  # For nomic-embed-text
        distance = models.Distance.COSINE

        collections = [self.qa_collection, self.chat_collection] + self.additional_collections
        for coll in collections:
            try:
                self.qdrant_client.create_collection(  # type: ignore
                    collection_name=coll,
                    vectors_config=models.VectorParams(size=vector_size, distance=distance),
                )
                logger.info(f"Created collection: {coll}")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Failed to create {coll}: {e}")

    async def on_startup(self):
        """Initialize clients on startup."""
        logger.info(f"🚀 Starting Cody pipeline")
        self._initialize_clients()

    async def on_shutdown(self):
        """Cleanup on shutdown."""
        logger.info(f"🛑 Shutting down Cody pipeline")

    async def on_valves_updated(self):
        """Handle valve updates."""
        pass

    async def inlet(self, body: dict, user: dict) -> dict:
        """Prepare context for conversation."""
        user_id = user.get("id", "default")
        messages = body.get("messages", []).copy()  # Create a copy to avoid modifying immutable body

        # Normalize message content to strings (handle lists, dicts, etc.)
        for msg in messages:
            msg["content"] = normalize_content(msg.get("content", ""))

        user_message = get_last_user_message(messages)

        # Initialize state if new user
        if user_id not in self.conversation_states:
            self.conversation_states[user_id] = {
                "turn_count": 0,
                "last_activity": datetime.now()
            }

        state = self.conversation_states[user_id]

        state["last_activity"] = datetime.now()



        # Always gather context for RAG usage
        context = await self._gather_context(user_id, messages, user_message)
        body["_context"] = context  # Store for pipe method

        # Format context for RAG (no synthesis needed)
        formatted_context = self._format_context_for_rag(context)
        body["_formatted_context"] = formatted_context


        body["messages"] = messages  # Assign the modified messages back

        return body

    async def outlet(self, body: dict, user: dict) -> dict:
        """Update conversation state after response."""
        user_id = user.get("id", "default")
        if user_id in self.conversation_states:
            state = self.conversation_states[user_id]
            state["turn_count"] += 1

            # Save the latest prompt/response pair after each message
            await self._save_chat_history(user_id, body)

        return body

    async def _save_chat_history(self, user_id: str, body: dict):
        """Save the latest prompt/response pair to chat_history."""
        if not self.qdrant_client or not self.chat_collection:
            return

        state = self.conversation_states[user_id]
        messages = body.get("messages", [])

        # Extract the last user message and the last assistant response
        last_user_msg = ""
        last_assistant_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and not last_assistant_msg:
                last_assistant_msg = msg.get("content", "")
            elif msg.get("role") == "user" and not last_user_msg:
                last_user_msg = msg.get("content", "")

        # Upsert to collection
        try:
            # Create embedding for ai_response
            response = ollama.embeddings(model=self.valves.OLLAMA_EMBEDDING_MODEL, prompt=last_assistant_msg)
            vector = response["embedding"]

            payload = {
                "user_id": user_id,
                "turn_number": state["turn_count"],
                "timestamp": datetime.now().isoformat(),
                "conversation_id": f"{user_id}_{int(time.time())}",
                "user_message": last_user_msg,
                "ai_response": last_assistant_msg,

            }
            self.qdrant_client.upsert(
                collection_name=self.chat_collection,
                points=[
                    models.PointStruct(
                        id=str(uuid.uuid4()),  # unique id
                        payload=payload,
                        vector=vector
                    )
                ]
            )
        except Exception as e:
            logger.warning(f"Failed to save chat history: {e}")

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        """Stream RAG-based response."""
        if self.debug:
            logger.info("Pipe called")
        user_id = body.get("user", {}).get("id", "default")
        state = self.conversation_states.get(user_id, {"turn_count": 0})

        # Yield citations for context sources
        if self.valves.ENABLE_CITATIONS:
            context = body.get("_context", {})
            if context:
                for item in context.get("qa_items", []) + context.get("chat_items", []) + context.get("additional_items", []):
                    payload = item.get("content", {})
                    collection = item.get("collection", "unknown")
                    if isinstance(payload, dict):
                        if collection.endswith("_qa"):
                            doc = [f"Q: {payload.get('question', '')}\nA: {payload.get('answer', '')}"]
                            source_name = collection
                        elif collection.endswith("_chat_history"):
                            doc = [f"User: {payload.get('user_message', '')}\nAI: {payload.get('ai_response', '')}"]
                            source_name = collection
                        else:
                            # For additional collections like personal/entities
                            page_content = payload.get('page_content')
                            if page_content:
                                doc = [page_content]
                            else:
                                doc = [str(payload)]
                            source_name = payload.get('metadata', {}).get('source', collection)
                    else:
                        doc = [str(payload)]
                        source_name = collection
                    yield {
                        "event": {
                            "type": "citation",
                            "data": {
                                "document": doc,
                                "metadata": [{"source": source_name}],
                                "source": {"name": source_name},
                            },
                        }
                    }


            logger.info(f"Yielded citations for {len(context.get('qa_items', []) + context.get('chat_items', []) + context.get('additional_items', []))} sources")

        # Prepare messages for streaming - RAG style like songbird
        openai_messages = []

        # Add system message with synthesis prompt
        openai_messages.append(
            {"role": "system", "content": self.SYNTHESIS_PROMPT}
        )

        # Create user message with query and formatted context
        formatted_context = body.get("_formatted_context", "")
        user_content = f"USER QUERY: {user_message}"
        if formatted_context:
            user_content += f"\n\nRELEVANT CONTEXT:\n{formatted_context}"

        openai_messages.append({"role": "user", "content": user_content})

        # Call AI and stream response
        if self.debug:
            logger.info(f"OpenAI client available: {bool(self.openai_client)}")
        if not self.openai_client:
            logger.info("No AI client, yielding unavailable")
            yield "AI client unavailable."
            yield {
                "event": {
                    "type": "status",
                    "data": {"description": "", "done": True}
                }
            }
            return



        try:
            if self.debug:
                logger.info("Calling AI for synthesis")
            response = self.openai_client.chat.completions.create(
                model=self.valves.SYNTHESIS_MODEL,
                messages=openai_messages,  # type: ignore
                stream=True,
            )

            if self.debug:
                logger.info("AI call successful, streaming")
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.info(f"AI call failed: {e}")
            yield f"Error: {e}"

        if self.debug:
            logger.info("Checking chat history save")

