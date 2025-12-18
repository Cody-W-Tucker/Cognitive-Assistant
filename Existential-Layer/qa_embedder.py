#!/usr/bin/env python3
"""
QA Embedder - Upload Q&A data to Qdrant vector database

This script processes the most recent human interview CSV file and uploads each Q&A pair
as an embedded point to a user-specific Qdrant collection for use by the existential pipeline.

Usage:
    python qa_embedder.py --username <username>

Requirements:
    - Qdrant server running (default: http://localhost:6333)
    - Ollama running with nomic-embed-text model
    - Recent human_interview_*.csv file in data directory
"""

import sys
import argparse
import pandas as pd
import ollama
import hashlib
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.http import models

# Import config from current directory
from config import config, get_most_recent_file


def get_embedding(text: str, model: str) -> list[float]:
    """Generate embedding for text using Ollama."""
    try:
        response = ollama.embeddings(model=model, prompt=text)
        return response["embedding"]
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        raise


def create_collection_if_not_exists(client: QdrantClient, collection_name: str):
    """Create Qdrant collection if it doesn't exist."""
    try:
        # Check if collection exists
        collections = client.get_collections()
        if collection_name in [c.name for c in collections.collections]:
            print(f"✅ Collection {collection_name} already exists")
            return

        # Create collection
        vector_size = 768  # nomic-embed-text
        distance = models.Distance.COSINE
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=vector_size, distance=distance),
        )
        print(f"✅ Created collection: {collection_name}")

    except Exception as e:
        print(f"❌ Error creating collection {collection_name}: {e}")
        raise


def generate_point_id(
    category: str, goal: str, element: str, question: str, answer: str
) -> str:
    """Generate a unique point ID based on content."""
    content = f"{category}|{goal}|{element}|{question}|{answer}"
    return hashlib.md5(content.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Embed and upload Q&A data to Qdrant")
    parser.add_argument(
        "--username", required=True, help="Username for the Qdrant collection"
    )
    args = parser.parse_args()

    username = args.username.strip()
    if not username:
        print("❌ Username cannot be empty")
        sys.exit(1)

    # Validate configuration
    issues = config.validate()
    if issues:
        print("❌ Configuration issues found:")
        for issue in issues:
            print(f"   - {issue}")
        sys.exit(1)

    # Set up Qdrant client
    try:
        qdrant_client = config.api.create_qdrant_client()
        print("✅ Connected to Qdrant")
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant: {e}")
        sys.exit(1)

    # Set collection name
    collection_name = f"{username}_qa"

    # Find most recent human interview file
    try:
        csv_file = get_most_recent_file("human_interview_*.csv")
        print(f"📖 Found latest Q&A file: {csv_file}")
    except FileNotFoundError:
        print("❌ No human_interview_*.csv files found in data directory")
        print("💡 Run human_interview.py first to generate Q&A data")
        sys.exit(1)

    # Load CSV
    try:
        df = pd.read_csv(csv_file)
        print(f"📖 Loaded {len(df)} rows from CSV")
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        sys.exit(1)

    # Create collection if needed
    create_collection_if_not_exists(qdrant_client, collection_name)

    # Process each row
    points = []
    processed_count = 0
    total_qa_pairs = 0

    for idx, row in df.iterrows():
        category = str(row.get("Category", "")).strip()
        goal = str(row.get("Goal", "")).strip()
        element = str(row.get("Element", "")).strip()

        if not category:
            continue

        # Process each Q&A pair (1, 2, 3)
        for human_answer_col in config.csv.HUMAN_ANSWER_COLUMNS:
            # Extract question number from column (e.g., "Human_Answer 1" -> "Question 1")
            question_num = human_answer_col.split()[-1]
            question_col = f"Question {question_num}"

            question = str(row.get(question_col, "")).strip()
            human_answer = str(row.get(human_answer_col, "")).strip()

            if not question or not human_answer or pd.isna(human_answer):
                continue

            total_qa_pairs += 1

            # Generate embedding
            text_to_embed = f"Q: {question}\nA: {human_answer}"
            try:
                vector = get_embedding(text_to_embed, config.api.OLLAMA_EMBEDDING_MODEL)
            except Exception as e:
                print(
                    f"⚠️ Skipping Q&A {idx+1}.{question_num} due to embedding error: {e}"
                )
                continue

            # Create point
            point_id = generate_point_id(
                category, goal, element, question, human_answer
            )
            now = datetime.now()

            payload = {
                "user_id": username,
                "category": category,
                "goal": goal,
                "element": element,
                "question": question,
                "answer": human_answer,
                "confidence": 1.0,
                "version": 1,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            point = models.PointStruct(id=point_id, vector=vector, payload=payload)

            points.append(point)
            processed_count += 1

            if processed_count % 10 == 0:
                print(f"📊 Processed {processed_count}/{total_qa_pairs} Q&A pairs...")

    # Upload points in batches
    if points:
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            try:
                qdrant_client.upsert(collection_name=collection_name, points=batch)
                print(
                    f"✅ Uploaded batch {i//batch_size + 1}/{(len(points) + batch_size - 1)//batch_size}"
                )
            except Exception as e:
                print(f"❌ Error uploading batch {i//batch_size + 1}: {e}")
                continue

    print(
        f"\n✅ Completed! Uploaded {processed_count} human Q&A pairs to collection '{collection_name}'"
    )

    # Verify upload
    try:
        count = qdrant_client.count(collection_name=collection_name)
        print(f"📊 Collection now contains {count.count} points")
    except Exception as e:
        print(f"⚠️ Could not verify collection count: {e}")


if __name__ == "__main__":
    main()
