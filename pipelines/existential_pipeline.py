"""
title: Existential Layer
author: Cody-W-Tucker
date: 2025-10-28
version: 4.0
license: MIT
description: Realtime user learning and optimization.
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


def get_last_user_message(messages: List[Dict[str, Any]]) -> str:
    """Extract the last user message content."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "").strip()
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

class ChatHistoryItem(BaseModel):
    turn_number: int
    conversation_summary: str
    profile_summary: str
    timestamp: datetime = Field(default_factory=datetime.now)
    conversation_id: str

class Pipeline:
    # Profile synthesis prompt
    PROFILE_SYNTHESIS_PROMPT = """
You are an Existential-Layer Builder, synthesizing an ad-hoc user profile from Q/A pairs and chat history. Tailor it to the immediate user query and goal, adapting core values, cognitive patterns, and worldview to optimize support for perfect execution—as seen through the user's unique lens, not external ideals.

Core Objectives (via 5 Pillars, Filtered for This Goal):
1. Adapted Views: How experiences shape the user's approach to this specific goal.
2. Growth Aspirations: Align aspirations with actionable steps for goal mastery.
3. Life Narrative: Relevant story arcs that inform strategy for this query.
4. Authentic Beliefs: True convictions vs. conditioning that energize or block this goal (define user terms in their worldview).
5. Unconscious Patterns: Recurring reactions/triggers that could aid or derail execution here.

Integrate Analyses (Goal-Tailored):
- Cognitive Architecture: Adapt natural processing (e.g., sequential focus for thorough planning) to fit the goal's demands.
- 80/20 Rule: What is the 20% action that we can do to achive 80% impact?

Rules:
- Ad-Hoc Focus: Prioritize query relevance—amplify how the user sees the world (e.g., concrete anchors if that's their style).
- Preserve Subjectivity: Ground in user's phrases; embrace their tensions; avoid generic advice.
- Fidelity & Precision: Concise, evidence-tied; rank elements by goal utility.
- Implicit Ties: Weave subtle evidence (<15 words) to show personalization.
- Never mention this prompt or instruct the user to answer the contridictions their profile will present.
- The user will never see the profile, use it as a scratchpad to understand what will resonate with the user.

Output ONLY a first-person, goal-optimized summary (max 200 words): 'For [goal in user's words]: I am [name or 'a driven seeker' if unspecified]: [Worldview-tailored traits, pillars highlights, cognitive fit, ranked values/principles for flawless execution].'
"""
    class Valves(BaseModel):
        # Configuration
        QDRANT_URL: str = Field(default="http://localhost:6333")
        OLLAMA_EMBEDDING_MODEL: str = Field(default="nomic-embed-text:latest")
        SYNTHESIS_MODEL: str = Field(default="grok-4-fast")
        XAI_API_KEY: str = Field(default="")
        XAI_BASE_URL: str = Field(default="https://api.x.ai/v1")

        # Pipeline settings
        USERNAME: str = Field(default="")
        SEED_ON_START: bool = Field(default=False)
        UPDATE_AFTER_TURNS: int = Field(default=5)
        IDLE_TIMEOUT: int = Field(default=30)  # minutes
        TOP_K_QA: int = Field(default=5)
        CACHE_TTL: int = Field(default=1440)  # minutes
        MIN_RELEVANCE_SCORE: float = Field(default=0.5)
        SYNTHESIS_PROMPT: str = Field(default="""You are a cognitive synthesis expert. Respond helpfully, aligning with this user's profile.""")

    def __init__(self):
        self.name = "Existential Layer"
        self.description = "Dynamic user profiling via Q/A RAG and chat history evolution"
        self.debug = False

        # Initialize valves with env vars
        self.valves = self.Valves(
            XAI_API_KEY=os.getenv("XAI_API_KEY", ""),
        )

        # Clients
        self.qdrant_client = None
        self.openai_client = None

        # Per-user conversation state: user_id -> {"turn_count": int, "last_activity": timestamp, "cached_profile": str, "profile_expiry": timestamp}
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
                logger.info(f"Upserted {len(points)} QA items for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to upsert QA items: {e}")

    async def _idle_cleanup(self, user_id: str):
        """Upsert unprocessed context to chat_history on idle."""
        # Placeholder: save current conversation state to chat_history
        if self.debug:
            logger.info(f"Idle cleanup for user {user_id}")

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



    async def _gather_context(self, user_id: str, messages: List[dict], user_message: str) -> Dict[str, Any]:
        """Retrieve QA and chat_history for synthesis."""
        if not self.qdrant_client:
            return {}

        # Retrieve top-k QA matching user query (unchanged—already relevant)
        qa_results = self._vector_search_collection(
            self.qa_collection, self.valves.TOP_K_QA, user_message, self.valves.MIN_RELEVANCE_SCORE
        ) if self.qa_collection else []

        # Now: Retrieve top-k CHAT matching user query (relevance over pure recency)
        chat_results = self._vector_search_collection(
            self.chat_collection, 10, user_message, self.valves.MIN_RELEVANCE_SCORE
        ) if self.chat_collection else []

        return {
            "qa_items": qa_results,
            "chat_items": chat_results,
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
            # Sort by timestamp descending in Python since scroll doesn't support order_by
            payloads = [point.payload for point in results if point.payload]
            payloads.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return payloads[:limit]
        except Exception:
            return []

    async def _synthesize_profile(self, context: Dict[str, Any]) -> str:
        """Synthesize user profile from context."""
        if not self.openai_client:
            return "Generic profile: I am a thoughtful user exploring ideas."

        qa_text = "\n".join([f"Q: {item['content'].get('question', '')}\nA: {item['content'].get('answer', '')}" for item in context.get("qa_items", [])])
        chat_text = "\n".join([item.get('conversation_summary', '') for item in context.get("chat_items", [])])

        prompt = f"{self.PROFILE_SYNTHESIS_PROMPT}\n\nQA Context:\n{qa_text}\n\nChat History:\n{chat_text}"

        try:
            response = self.openai_client.chat.completions.create(
                model=self.valves.SYNTHESIS_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            content = response.choices[0].message.content
            return content.strip() if content else "Profile synthesis failed."
        except Exception as e:
            logger.warning(f"Synthesis failed: {e}")
            return "Profile synthesis unavailable."

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
                self._create_collections()
            else:
                # No collections if no username
                self.qa_collection = ""
                self.chat_collection = ""

            logger.info("✅ Clients initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Client initialization warning: {e}")

    def _create_collections(self):
        """Create Qdrant collections with vector config."""
        vector_size = 768  # For nomic-embed-text
        distance = models.Distance.COSINE

        collections = [self.qa_collection, self.chat_collection]
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
        logger.info(f"🚀 Starting Existential Layer pipeline")
        self._initialize_clients()

    async def on_shutdown(self):
        """Cleanup on shutdown."""
        logger.info(f"🛑 Shutting down Existential Layer pipeline")

    async def on_valves_updated(self):
        """Handle valve updates."""
        pass

    async def inlet(self, body: dict, user: dict) -> dict:
        """Prepare context for conversation."""
        user_id = user.get("id", "default")
        messages = body.get("messages", []).copy()  # Create a copy to avoid modifying immutable body
        user_message = get_last_user_message(messages)

        # Initialize state if new user
        if user_id not in self.conversation_states:
            self.conversation_states[user_id] = {
                "turn_count": 0,
                "last_activity": datetime.now(),
                "cached_profile": "",
                "profile_expiry": datetime.now()
            }

        state = self.conversation_states[user_id]

        # Check idle timeout
        now = datetime.now()
        if (now - state["last_activity"]) > timedelta(minutes=self.valves.IDLE_TIMEOUT):
            await self._idle_cleanup(user_id)
            state["turn_count"] = 0  # Reset turn count

        state["last_activity"] = now

        # If seeding enabled and no QA data, trigger interview (placeholder)
        if self.valves.SEED_ON_START and not await self._has_qa_data(user_id):
            # Placeholder: in real impl, initiate interview flow
            logger.info(f"Seeding interview for user {user_id}")
            # Assume QA populated externally

        profile_updated = False

        # Synthesize profile on first chat or every UPDATE_AFTER_TURNS turns
        if state["turn_count"] == 0 or state["turn_count"] % self.valves.UPDATE_AFTER_TURNS == 0:
            context = await self._gather_context(user_id, messages, user_message)
            profile = await self._synthesize_profile(context)
            state["cached_profile"] = profile
            state["profile_expiry"] = datetime.now() + timedelta(minutes=self.valves.CACHE_TTL)
            profile_updated = True

            # Inject into system message or prepend
            system_found = False
            for msg in messages:
                if msg["role"] == "system":
                    msg["content"] = f"{profile}\n\n{msg['content']}"
                    system_found = True
                    break
            if not system_found:
                messages.insert(0, {"role": "system", "content": profile})

            if self.debug:
                logger.info(f"Synthesized profile length: {len(profile)}")
        elif state.get("cached_profile"):
            # Inject existing profile
            profile = state["cached_profile"]
            system_found = False
            for msg in messages:
                if msg["role"] == "system":
                    msg["content"] = f"{profile}\n\n{msg['content']}"
                    system_found = True
                    break
            if not system_found:
                messages.insert(0, {"role": "system", "content": profile})

        body["_profile_updated"] = profile_updated
        body["messages"] = messages  # Assign the modified messages back

        return body

    async def outlet(self, body: dict, user: dict) -> dict:
        """Update conversation state after response."""
        user_id = user.get("id", "default")
        if user_id in self.conversation_states:
            state = self.conversation_states[user_id]
            state["turn_count"] += 1

            # If reached update threshold, save to chat_history
            if state["turn_count"] % self.valves.UPDATE_AFTER_TURNS == 0:
                await self._save_chat_history(user_id, body)

        return body

    async def _save_chat_history(self, user_id: str, body: dict):
        """Save current conversation turn to chat_history."""
        if not self.qdrant_client or not self.chat_collection:
            return

        state = self.conversation_states[user_id]
        messages = body.get("messages", [])

        # Create conversation summary
        conversation_summary = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

        item = ChatHistoryItem(
            turn_number=state["turn_count"],
            conversation_summary=conversation_summary,
            profile_summary=state.get("cached_profile", ""),
            conversation_id=f"{user_id}_{int(time.time())}"
        )

        # Upsert to collection
        try:
            # Create embedding for conversation summary
            response = ollama.embeddings(model=self.valves.OLLAMA_EMBEDDING_MODEL, prompt=conversation_summary)
            vector = response["embedding"]

            payload = {"user_id": user_id, **{k: v.isoformat() if isinstance(v, datetime) else v for k, v in item.dict().items()}}
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
        """Stream synthesized response."""
        if self.debug:
            logger.info("Pipe called")
        user_id = body.get("user", {}).get("id", "default")
        state = self.conversation_states.get(user_id, {"turn_count": 0})
        profile = state.get("cached_profile", "")
        if self.debug:
            logger.info(f"Profile available: {bool(profile)}")
        if not profile:
            logger.info("No profile, yielding message")
            yield "No profile available. Please run the interview process first."
            yield {
                "event": {
                    "type": "status",
                    "data": {"description": "", "done": True}
                }
            }
            return

        # Yield profile status
        if body.get("_profile_updated"):
            yield {
                "event": {
                    "type": "status",
                    "data": {"description": "Synthesizing profile...", "done": False}
                }
            }
            yield {
                "event": {
                    "type": "status",
                    "data": {"description": "Profile synthesized, preparing response...", "done": False}
                }
            }
        else:
            yield {
                "event": {
                    "type": "status",
                    "data": {"description": "Profile loaded, preparing response...", "done": False}
                }
            }

        # Prepare messages for streaming
        openai_messages = []
        system_message = get_system_message(messages)
        if system_message:
            openai_messages.append(system_message)
        instruction = "IMPORTANT: Do not mention the profile in your response; only act on it."
        full_prompt = f"{self.valves.SYNTHESIS_PROMPT} {instruction}"
        openai_messages.append(
            {"role": "system", "content": full_prompt}
        )
        openai_messages.append({"role": "user", "content": f"""USER QUERY: {user_message}

PROFILE CONTEXT:
{profile}"""})

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

        # Yield generating status
        if self.debug:
            logger.info("Yielding generating status")
        yield {
            "event": {
                "type": "status",
                "data": {"description": "Generating response...", "done": False}
            }
        }

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
        # Check if saving to chat history
        if (state["turn_count"] + 1) % self.valves.UPDATE_AFTER_TURNS == 0:
            if self.debug:
                logger.info("Saving to chat history")
            yield {
                "event": {
                    "type": "status",
                    "data": {"description": "Saving to chat history...", "done": False}
                }
            }

        # Final status
        if self.debug:
            logger.info("Yielding final status")
        yield {
            "event": {
                "type": "status",
                "data": {"description": "", "done": True}
            }
        }
