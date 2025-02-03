---
title: Consensus of Thoughts
createdDate: 2024-10-23
modifiedDate: 2024-01-15
---

# Consensus of Thoughts

## Original Idea

I write constantly so I should be able to parse my journals and bring out topics and extract semantically similar blocks of text. Then I'll create summaries of all the blocks.

I want to create an app that lists the consensus of each given topic. it will go and scrape or source opinions from various sources and congregate them around different topics and create some kind of summarized consensus description to show public opinion on each topic.

## Requirements

-   Take in markdown files
-   Display topics summaries and the snippets that led to that summary.
-   Show for and against snippets to get an accurate guess of the middle ground.
-   We shouldn't show one sided topics, those are established and don't need further analysis

## Workflow

1. Load docs using [Document Loaders](https://python.langchain.com/v0.2/docs/integrations/document_loaders/)
2. Extract blocks under headers
3. Extract topics from blocks using [Document Transformer](https://python.langchain.com/v0.2/docs/integrations/document_transformers/doctran_extract_properties/) or split text using [Semantic Text Splitting](https://python.langchain.com/v0.2/docs/integrations/document_transformers/ai21_semantic_text_splitter/) based on topics.
4. Summarize all blocks under topic
5. Return Topic, summary, and blocks in a json array.

## AI Agent Consensus System: Enhanced Technical Documentation

### 1. Overview

This document outlines a system for AI agents to create consensus through competitive idea evaluation, with a focus on narrative crafting and cognitive functions. The system aims to determine the true state of the environment, understand ideas more comprehensively, and prioritize areas for improvement.

### 2. System Components

2.1 AI Agents (including specialized cognitive functions)
2.2 Idea Pool
2.3 Evaluation Framework
2.4 Consensus Mechanism
2.5 Action Priority Queue
2.6 Narrative Crafting Module
2.7 Collaborative Network Interface

### 3. Process Flow

#### 3.1 Idea Generation and Narrative Crafting

-   Each AI agent, including specialized cognitive functions (e.g., Sophia, Evelyn), generates ideas based on its current understanding of the system.
-   Ideas are submitted to the Idea Pool.
-   The Narrative Crafting Module helps structure ideas into coherent narratives, bridging current realities with future aspirations.

#### 3.2 Idea Competition and Evaluation

-   Ideas in the pool compete against each other through the Evaluation Framework.
-   Evaluation criteria include:
    -   Logical consistency
    -   Supporting evidence
    -   Potential impact
    -   Alignment with system goals
    -   Narrative coherence and persuasiveness

#### 3.3 Consensus Building and Network Collaboration

-   Highest-scoring ideas are presented to all agents and shared within the Collaborative Network Interface.
-   Agents vote on the ideas, considering their own knowledge, evaluation results, and network feedback.
-   Ideas reaching a predefined threshold are added to the consensus.

#### 3.4 System State Update and Insight Automation

-   The consensus is used to update the understood state of the system.
-   Automated insights are generated based on the updated state and shared narratives.
-   This updated state and insights inform future idea generation and narrative crafting.

#### 3.5 Action Prioritization and Task Management

-   Based on the consensus, potential actions are ranked in the Action Priority Queue.
-   Top-ranked actions are broken down into manageable tasks and workflows.
-   The system provides guidance on task implementation, considering cognitive and emotional needs.

### 4. Key Features

4.1 Audience Pain Point Identification Tool
4.2 Goal Articulation Framework
4.3 Narrative Crafting Tools
4.4 Simplified Tech Solutions Repository
4.5 Actionable Task Management
4.6 Collaborative Network Facilitation

### 5. Benefits

-   Leverages collective intelligence of multiple AI agents and human users
-   Promotes continuous improvement through competitive idea evaluation
-   Provides a clear picture of the system's current state and desired future state
-   Identifies and prioritizes areas needing attention
-   Facilitates the creation of compelling narratives to drive action
-   Supports collaborative network building and knowledge sharing

### 6. Applications

-   Business strategy development
-   Marketing and content creation
-   Technology adoption and simplification
-   Team dynamics and collaboration enhancement
-   Personal and professional growth planning
