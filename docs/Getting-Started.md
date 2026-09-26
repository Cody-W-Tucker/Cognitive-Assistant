# Getting Started

Enter the development shell:

```bash
nix develop
```

The shell provides Python dependencies, QMD, and `ai-data-extractor`. QMD is
packaged through the `llm-agents` shared overlay with Vulkan and CUDA disabled.

Run profile stages with an explicit profile:

```bash
python -m core --profile existential ask-questions
python -m core --profile operational ingest-corpus
python -m core --profile operational ask-questions
```

Existential questions retrieve from `Journal` and `Personal`. Operational
questions retrieve from `Base`, `Consulting`, and `Customers`. Both use the
configured direct LLM client only after successful current retrieval.

There is no schema graph export, `substrate-cli`, or RLM dependency.
