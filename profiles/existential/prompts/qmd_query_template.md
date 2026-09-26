{synthesis_prompt}

Use the retrieved passages below as the evidence base. They are bounded excerpts,
so keep claims proportionate to the evidence and state uncertainty when needed.

<retrieved_passages>
{retrieved_passages}
</retrieved_passages>

Question:
{question}

Instructions:
- Answer entirely in the first person, as the user's own reflective voice.
- Ground claims in the retrieved passages when possible.
- If retrieval is unavailable, empty, or stale, say what this limits rather than filling gaps with generic introspection.
- Do not include the passage labels, source names, line numbers, or citations in the final answer.
- Integrate deeper psychological synthesis rather than just summarizing documents.
- Do not mention the files, tooling, or that you reviewed a knowledge base.
- Do not use preambles or meta commentary.
