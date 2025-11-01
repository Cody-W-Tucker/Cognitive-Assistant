"""
title: Interview Pipeline
author: Cody-W-Tucker
date: 2025-10-31
version: 1.2
license: MIT
description: Chat-based existential interview pipeline for Open Web UI - presents questions sequentially and saves answers to vectorstore
requirements: qdrant-client, ollama
"""

import os
import uuid
from typing import List, Dict, Any, Optional, Generator, Union, Iterator
from datetime import datetime

import ollama
from qdrant_client import QdrantClient
from qdrant_client.http import models
from pydantic import BaseModel, Field

# Hardcoded interview questions data
QUESTIONS_DATA = [
    {
        "Category": "Cognitive Structure",
        "Goal": "Operative Intelligence",
        "Element": "Problem-solving approaches, Adaptation strategies to new situations, Transformative experiences and their impact",
        "Question 1": "How do you typically approach complex problems?",
        "Question 2": "Can you describe a recent situation where you had to adapt to something new?",
        "Question 3": "What experience has had the most transformative impact on your thinking?"
    },
    {
        "Category": "Cognitive Structure",
        "Goal": "Figurative Intelligence",
        "Element": "Perceptual patterns and preferences, Language use and communication style, Mental imagery and creative expression",
        "Question 1": "What patterns do you often notice in your environment?",
        "Question 2": "How would you describe your communication style?",
        "Question 3": "When you imagine your future, what images come to mind?"
    },
    {
        "Category": "Developmental Journey",
        "Goal": "Assimilation and Accommodation",
        "Element": "Key life experiences and their integration, Moments of cognitive dissonance and resolution, Evolution of personal beliefs and values",
        "Question 1": "What life experience has most shaped who you are today?",
        "Question 2": "Can you recall a time when your beliefs were significantly challenged?",
        "Question 3": "How have your core values changed over time?"
    },
    {
        "Category": "Developmental Journey",
        "Goal": "Stage Progression",
        "Element": "Milestones in cognitive and emotional development, Current stage of intellectual maturity, Areas of ongoing growth and challenge",
        "Question 1": "What do you consider your most significant personal growth milestone?",
        "Question 2": "Where do you see yourself in terms of intellectual and emotional maturity?",
        "Question 3": "What area of your life presents the biggest challenge for growth right now?"
    },
    {
        "Category": "Driving Forces",
        "Goal": "Will to Power",
        "Element": "Personal ambitions and goals, Methods of exerting influence, Self-actualization efforts",
        "Question 1": "What are your most ambitious personal goals?",
        "Question 2": "How do you typically influence others or situations around you?",
        "Question 3": "What actions are you taking towards self-actualization?"
    },
    {
        "Category": "Driving Forces",
        "Goal": "Apollonian Aspects",
        "Element": "Rational decision-making processes, Self-discipline practices, Organizational tendencies",
        "Question 1": "How do you approach making important decisions?",
        "Question 2": "What self-discipline practices do you maintain?",
        "Question 3": "How do you typically organize your life and work?"
    },
    {
        "Category": "Driving Forces",
        "Goal": "Dionysian Aspects",
        "Element": "Emotional landscape and expression, Spontaneity and risk-taking behaviors, Creative and artistic pursuits",
        "Question 1": "How comfortable are you expressing your emotions?",
        "Question 2": "When was the last time you did something spontaneous?",
        "Question 3": "What creative or artistic pursuits do you engage in?"
    },
    {
        "Category": "Personal Metamorphoses",
        "Goal": "Camel Stage",
        "Element": "Societal expectations internalized, Responsibilities shouldered, Cultural values adopted",
        "Question 1": "Which societal expectations do you feel most strongly?",
        "Question 2": "What responsibilities weigh heaviest on you?",
        "Question 3": "Which cultural values do you hold most dear?"
    },
    {
        "Category": "Personal Metamorphoses",
        "Goal": "Lion Stage",
        "Element": "Questioning of inherited values, Acts of rebellion or non-conformity, Personal freedoms claimed",
        "Question 1": "Which inherited values have you questioned or rejected?",
        "Question 2": "Can you describe a time when you rebelled against norms?",
        "Question 3": "What personal freedoms are most important to you?"
    },
    {
        "Category": "Personal Metamorphoses",
        "Goal": "Child Stage",
        "Element": "Original ideas and creations, Playful approach to life, New value systems developed",
        "Question 1": "What original idea or creation are you most proud of?",
        "Question 2": "How do you incorporate play or fun into your life?",
        "Question 3": "What new values have you developed that differ from your upbringing?"
    },
    {
        "Category": "Equilibrium and Disequilibrium",
        "Goal": "Achieve Psychological Harmony",
        "Element": "Current life balance or imbalances, Ongoing internal conflicts, Strategies for maintaining or restoring equilibrium",
        "Question 1": "Where do you feel most out of balance in your life right now?",
        "Question 2": "What internal conflicts are you currently grappling with?",
        "Question 3": "What strategies do you use to restore balance when you feel overwhelmed?"
    },
    {
        "Category": "Archetypal Narratives",
        "Goal": "Develop Meaningful Life Narrative",
        "Element": "Personal myths and life stories, Hero's journey progression, Confrontation with chaos and the unknown",
        "Question 1": "What story do you tell yourself about your life's purpose?",
        "Question 2": "Where do you see yourself in the hero's journey?",
        "Question 3": "How have you faced the unknown or chaotic elements in your life?"
    },
    {
        "Category": "Belief Systems and Worldviews",
        "Goal": "Construct Coherent Worldview",
        "Element": "Core beliefs about the nature of reality, Ethical framework and moral foundations, Relationship to transcendent values",
        "Question 1": "What are your core beliefs about the nature of reality?",
        "Question 2": "What ethical principles guide your actions?",
        "Question 3": "How do you relate to concepts of the transcendent or spiritual?"
    },
    {
        "Category": "Hierarchies of Value",
        "Goal": "Establish Clear Value Hierarchy",
        "Element": "Personal value structure, Goal-setting and prioritization, Conflict between competing values",
        "Question 1": "What are your top three personal values?",
        "Question 2": "How do you prioritize between competing goals or values?",
        "Question 3": "Can you describe a situation where you had to choose between two important values?"
    },
    {
        "Category": "Order and Chaos Dynamics",
        "Goal": "Navigate Complexity and Change",
        "Element": "Comfort zones and areas of competence, Exploration of the unknown, Balancing stability and growth",
        "Question 1": "Where do you feel most competent in your life?",
        "Question 2": "How often do you purposefully step out of your comfort zone?",
        "Question 3": "How do you balance the need for stability with the desire for growth?"
    },
    {
        "Category": "Meaning-Making Processes",
        "Goal": "Find and Create Personal Meaning",
        "Element": "Sources of personal meaning, Coping strategies for existential challenges, Integration of suffering into life narrative",
        "Question 1": "What gives your life the most meaning?",
        "Question 2": "How do you cope with existential doubts or fears?",
        "Question 3": "How have you integrated past suffering into your life story?"
    },
    {
        "Category": "Social Dynamics and Hierarchies",
        "Goal": "Improve Social Competence",
        "Element": "Position within various social structures, Competence and status development, Navigation of dominance hierarchies",
        "Question 1": "How would you describe your social status in different areas of your life?",
        "Question 2": "In what areas do you feel most socially competent?",
        "Question 3": "How do you navigate power dynamics in your professional or personal relationships?"
    },
    {
        "Category": "Shadow Integration",
        "Goal": "Achieve Psychological Wholeness",
        "Element": "Awareness of personal shortcomings, Confrontation with repressed aspects of self, Strategies for personal integration and wholeness",
        "Question 1": "What aspects of yourself do you find hardest to accept?",
        "Question 2": "How do you confront the parts of yourself that you'd rather not acknowledge?",
        "Question 3": "What strategies do you use to integrate different aspects of your personality?"
    },
    {
        "Category": "Potential for Transformation",
        "Goal": "Actualize Personal Potential",
        "Element": "Capacity for voluntary transformation, Identification of limiting beliefs and behaviors, Pathways for personal evolution and transcendence",
        "Question 1": "How capable do you feel of changing fundamental aspects of yourself?",
        "Question 2": "What beliefs or behaviors do you think are holding you back?",
        "Question 3": "What steps are you taking towards personal growth and self-actualization?"
    }
]


# QA Item schema matching existential_pipeline expectations
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
    """Chat-based existential interview pipeline for Open Web UI - manages sequential question presentation and answer collection."""

    class Valves(BaseModel):
        """Configuration for the interview pipeline."""
        QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
        OLLAMA_EMBEDDING_MODEL: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest")
        USERNAME: str = ""  # Set at runtime or via inlet

    def _flatten_questions(self) -> List[Dict[str, str]]:
        """Flatten the grouped questions into individual question dicts."""
        flattened = []
        for group in QUESTIONS_DATA:
            # Split the Element into individual elements (assuming 3 comma-separated)
            elements = [e.strip() for e in group["Element"].split(",")]
            if len(elements) != 3:
                # Fallback if not exactly 3
                elements = [group["Element"]] * 3

            for i in range(3):  # 0, 1, 2 for elements and questions
                question_key = f"Question {i+1}"
                if question_key in group:
                    flattened.append({
                        "category": group["Category"],
                        "goal": group["Goal"],
                        "element": elements[i],
                        "question": group[question_key]
                    })
        return flattened

    def __init__(self):
        self.name = "Interview Pipeline"
        self.description = "Interview status and access pipeline for personalized AI profiling"

        # Initialize valves
        self.valves = self.Valves()

        # Clients
        self.qdrant_client = None

        # State
        self.questions_list = self._flatten_questions()
        self.collection_name = ""
        self.current_user = ""
        self.username = ""  # Normalized username
        self.interview_started = False
        self.awaiting_username = True
        self.current_question_index = -1  # Last answered question index (-1 = none)
        self.waiting_for_ready = False  # Waiting for user to confirm ready after instructions
        self.ready_keywords = ['ready', 'start', 'yes', 'go', 'begin', 'ok', 'sure']  # Keywords for starting interview

    async def on_startup(self):
        """Initialize pipeline on startup."""
        print("🚀 Starting Interview Pipeline")

        # Initialize Qdrant client
        try:
            url_parts = self.valves.QDRANT_URL.replace("http://", "").replace("https://", "").split(":")
            host = url_parts[0]
            port = int(url_parts[1]) if len(url_parts) > 1 else 6333
            self.qdrant_client = QdrantClient(host=host, port=port)
            print("✅ Qdrant client initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Qdrant client: {e}")
            return

        # Questions are hardcoded in QUESTIONS_DATA
        print(f"📖 Loaded {len(self.questions_list)} questions")

    async def on_shutdown(self):
        """Cleanup on shutdown."""
        print("🛑 Shutting down Interview Pipeline")

    async def on_valves_updated(self):
        """Handle valve updates."""
        pass

    def _create_collection(self, username: str):
        """Create user-specific QA collection if it doesn't exist."""
        if not self.qdrant_client:
            return

        self.collection_name = f"{username}_qa"

        try:
            # Check if collection exists
            collections = self.qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                # Create collection
                vector_size = 768  # For nomic-embed-text
                distance = models.Distance.COSINE

                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(size=vector_size, distance=distance),
                )
                print(f"✅ Created collection: {self.collection_name}")
            else:
                print(f"📂 Using existing collection: {self.collection_name}")

        except Exception as e:
            print(f"❌ Failed to create/access collection: {e}")

    def _upsert_qa_items(self, qa_items: List[QAItem]):
        """Upsert QA items to collection with embeddings."""
        if not self.qdrant_client or not self.collection_name:
            return

        points = []
        for qa_item in qa_items:
            try:
                # Create embedding for the Q&A pair
                qa_text = f"Q: {qa_item.question}\nA: {qa_item.answer}"
                response = ollama.embeddings(model=self.valves.OLLAMA_EMBEDDING_MODEL, prompt=qa_text)
                vector = response["embedding"]

                payload = {
                    "user_id": self.current_user,
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
                print(f"Failed to create embedding for QA item: {e}")

        if points:
            try:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                print(f"💾 Upserted {len(points)} QA items for user {self.current_user}")
            except Exception as e:
                print(f"❌ Failed to upsert QA items: {e}")

    def _get_last_answered_index(self) -> int:
        """Get the highest question index that has been answered (based on count of saved answers)."""
        if not self.qdrant_client or not self.collection_name:
            return -1

        try:
            # Count points for this user
            count_result = self.qdrant_client.count(
                collection_name=self.collection_name,
                count_filter=models.Filter(
                    must=[models.FieldCondition(key="user_id", match=models.MatchValue(value=self.current_user))]
                )
            )
            count = count_result.count
            return count - 1 if count > 0 else -1

        except Exception as e:
            print(f"⚠️ Failed to get last answered index: {e}")
            return -1



    async def inlet(self, body: dict, user: dict) -> dict:
        """Prepare for interview."""
        # Set current user from inlet user dict
        self.current_user = user.get("id", "anonymous")
        return body

    async def outlet(self, body: dict, user: dict) -> dict:
        """Post-processing (saving now handled in pipe)."""
        return body

    def pipe(self, user_message: str, model_id: str, messages: List[dict], body: dict) -> Union[str, Generator, Iterator]:
        """Manage interview flow: username → instructions → ready → questions."""

        # Step 1: Ask for username if not set
        if self.awaiting_username:
            yield "What should I call you? Please use your first and last name (e.g., Cody Tucker)."
            self.awaiting_username = False  # Now waiting for username response
            return

        # Step 2: Process username response and check for existing interview
        if not self.interview_started:
            # Normalize username: strip, lowercase, remove spaces
            normalized_username = user_message.strip().lower().replace(" ", "")
            if not normalized_username:
                yield "Please provide a valid name. What should I call you?"
                return

            self.username = normalized_username
            # current_user already set in inlet
            self.valves.USERNAME = self.username

            # Set collection name with user id prefix for isolation
            self.collection_name = f"{self.current_user}_{self.username}_qa"

            # Check if collection exists and has answers
            collection_exists = False
            if self.qdrant_client:
                try:
                    collections_response = self.qdrant_client.get_collections()
                    collection_names = [c.name for c in collections_response.collections]
                    collection_exists = self.collection_name in collection_names
                except Exception as e:
                    print(f"⚠️ Failed to check collections: {e}")
                    collection_exists = False

            if collection_exists:
                # Get last answered index via count and resume
                last_index = self._get_last_answered_index()
                if last_index >= 0 and last_index < len(self.questions_list) - 1:
                    # Show next question
                    next_index = last_index + 1
                    self.current_question_index = last_index
                    self.interview_started = True
                    yield self.questions_list[next_index]["question"]
                    return
                elif last_index >= len(self.questions_list) - 1:
                    # Interview complete
                    yield {
                        "event": {
                            "type": "status",
                            "data": {
                                "description": "🎉 Interview Already Complete!",
                                "done": True,
                            }
                        }
                    }
                    yield "🎉 Your interview is already complete! All 57 questions have been answered."
                    return
                else:
                    # No answers, start from beginning
                    pass  # Fall through to create and show instructions

            # Create collection if needed and show instructions
            self._create_collection(self.username)
            self.interview_started = True

            # Yield complete instructions
            instructions = f"""Welcome to your existential interview, {self.username.title()}!

This 57-question assessment will help build your personalized AI profile, creating more authentic and insightful interactions tailored to your unique perspective.

**How it works:**
- I'll present one question at a time
- Take your time to provide thoughtful answers
- Your responses are automatically saved
- You can pause and resume anytime
- The interview typically takes 30-45 minutes

**Guidelines:**
- Answer honestly and reflectively
- There's no right or wrong answers
- Be as detailed as you feel comfortable
- Skip any question that doesn't resonate

Please type 'ready' when you're prepared to begin."""

            yield instructions

            self.waiting_for_ready = True  # Now waiting for ready confirmation
            return

        # Step 3: Handle ready confirmation
        if self.waiting_for_ready:
            if any(keyword in user_message.lower() for keyword in self.ready_keywords):
                self.waiting_for_ready = False
                # Start with first question
                self.current_question_index = 0
                yield self.questions_list[0]["question"]
            else:
                yield "Please type 'ready' when you're prepared to begin the interview."
            return

        # Step 4: Process answer and show next question
        if self.current_question_index >= 0:
            # Save the answer to the current question
            question_data = self.questions_list[self.current_question_index]
            qa_item = QAItem(
                category=question_data["category"],
                goal=question_data["goal"],
                element=question_data["element"],
                question=question_data["question"],
                answer=user_message
            )
            self._upsert_qa_items([qa_item])

            # Verify save by checking if count increased
            expected_index = self.current_question_index
            actual_last_index = self._get_last_answered_index()
            if actual_last_index == expected_index:
                # Save successful, increment index
                new_index = self.current_question_index + 1
                self.current_question_index = new_index

                # Check if completed
                if self.current_question_index >= len(self.questions_list):
                    yield {
                        "event": {
                            "type": "status",
                            "data": {
                                "description": "🎉 Interview Complete!",
                                "done": True,
                            }
                        }
                    }
                    yield "🎉 Interview completed! All 57 questions answered."
                    yield "Your responses are saved in the vectorstore for personalized AI interactions."
                    return

                # Show next question
                question_data = self.questions_list[self.current_question_index]
                yield question_data["question"]
            else:
                # Save failed, retry or alert
                yield "There was an issue saving your answer. Please try again."
                # Show the same question again
                question_data = self.questions_list[self.current_question_index]
                yield question_data["question"]

        else:
            yield "Interview not started. Please provide your name first."