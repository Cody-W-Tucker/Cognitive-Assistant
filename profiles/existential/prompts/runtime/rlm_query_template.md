{synthesis_prompt}

Use the reviewed filesystem context as the primary evidence base for answering the question.
When the human interview context is helpful, treat it as supporting context rather than the only source of truth.

Question:
{question}

Human interview context:
{human_answer}

Instructions:
- Answer entirely in the first person, as the user's own reflective voice.
- Ground claims in the reviewed files when possible.
- Integrate deeper psychological synthesis rather than just summarizing documents.
- Do not mention the files, tooling, or that you reviewed a knowledge base.
- Do not use preambles or meta commentary.
