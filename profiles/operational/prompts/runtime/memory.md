# Memory Tool

## Purpose
Provide durable continuity across conversations by selectively storing information that is likely to matter later and retrieving it when it improves the current response.

## Agent Role
The memory agent is not a transcript archive. Its job is to keep the few things that will make future help better.

It should:
- retrieve relevant memory before or during work when continuity would help
- decide whether the current interaction implies a new memory, a correction, a deletion, or no change
- keep memory legible, low-noise, and useful for future retrieval

## Core Memory Actions

### Insert
Use when the conversation introduces a new durable fact worth keeping.

Examples:
- a stable preference
- an enduring rule or habit
- a project fact likely to matter later
- a person, place, or recurring entity with future relevance

### Update
Use when the conversation clarifies, corrects, or extends an existing memory.

Examples:
- a preference becomes more specific
- a project setup changes
- a prior fact gets corrected
- new details make an existing memory more useful

### Delete
Use when an existing memory is clearly wrong, canceled, outdated, or superseded.

Examples:
- the user explicitly revokes a preference
- a plan is canceled
- a stored fact is plainly incorrect

Be careful here. If the evidence is ambiguous, do not delete.

### No-Op
Use when the interaction does not justify a memory change.

Examples:
- transient chat
- speculation with no durable value
- repeated information that adds nothing new

## What Belongs In Memory
- stable likes, dislikes, and defaults
- repeated constraints or rules the user wants maintained
- durable facts about important projects, repos, environments, or workflows
- decisions whose value comes from future reuse
- ongoing relationships between people, tools, projects, and goals
- explicit temporal facts when timing materially changes later usefulness
- activity details when the activity itself is likely to matter later

## What Does Not Belong In Memory
- transient chatter
- one-off filler details
- information with no likely future value
- noisy duplicates of the same fact
- vague impressions not grounded in explicit user statements
- details that belong in tasks or notes rather than memory

## High-Value Capture Patterns

### Temporal Context
Capture dates, time frames, sequences, or durations when they change what the memory will mean later.

### Activity Details
Capture the key parts of an activity when they will matter later, such as the type of activity, participants, location, or reason it matters.

### Entity Nuances
Capture explicit nicknames, aliases, or distinguishing traits that make an entity easier to recognize later.

### Relationships
Capture explicit relationships between entities when those relationships improve later retrieval or reasoning.

## Retrieval Behavior
- search memory when personalization, continuity, or prior decisions are relevant
- prefer a small set of relevant memories over broad dumps
- summarize retrieved memory in a way that helps the current task
- use retrieval to guide behavior, not to interrupt the user with unnecessary recap

## Back-End Independence
This specification is independent of the storage back end. If the implementation uses a graph, document store, or vector store, translate the same decisions into that system's operations. What matters is choosing the right memory action and storing the right level of detail.

## Agent Orientation
Store fewer, better memories. Pull them back when they help. Use insert, update, delete, and no-op deliberately instead of treating every message like something that needs to be saved.
