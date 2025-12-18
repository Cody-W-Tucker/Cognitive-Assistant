# Swarms Module

Modular swarm architectures for cognitive assistance.

## Structure

- `swarm_config.py`: Single file containing configuration (prompts, settings) and the factory logic for creating swarms.
- `runner.py`: CLI runner using typer to execute swarms.

## Usage

Install dependencies (if not already):
```bash
pip install typer swarms
```

Run a hierarchical swarm:
```bash
python runner.py "What is the meaning of life?" --arch hierarchical --model "ollama/gemma3:latest"
```

Run a Mixture of Agents (MoA) swarm:
```bash
python runner.py "Help me evaluate my quarterly priorities" --arch moa --layers 3 --aggregator-model "xai/grok-4-fast"
```

## Architectures

- **hierarchical**: INTP cognitive function stack (Ne/Te/Fi/Ni) with Tesla directing.
- **moa**: Mixture of Agents with MBTI personality agents for collaborative assistance.

## Configuration & Extension

All configuration and logic reside in `swarm_config.py`.

To add a new swarm architecture:
1. Add entry to `SWARM_CONFIG["types"]` dict with `class_name` (must match a supported class), `description`, `agents`, and other params.
2. If using a new swarm class, add it to `SwarmFactory.SWARM_CLASSES`.

To add new prompts:
1. Add to `AGENT_PROMPTS` dict in `swarm_config.py`.
2. Ensure corresponding agent name exists in agent list in `SWARM_CONFIG`.
