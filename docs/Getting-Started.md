# Getting Started
Relevant source files
- [.envrc](https://github.com/Cody-W-Tucker/Cognitive-Assistant/blob/a77ddaf6/.envrc)
- [.gitignore](https://github.com/Cody-W-Tucker/Cognitive-Assistant/blob/a77ddaf6/.gitignore)
- [core/__main__.py](https://github.com/Cody-W-Tucker/Cognitive-Assistant/blob/a77ddaf6/core/__main__.py)
- [core/ingest_substrate.py](https://github.com/Cody-W-Tucker/Cognitive-Assistant/blob/a77ddaf6/core/ingest_substrate.py)
- [flake.lock](https://github.com/Cody-W-Tucker/Cognitive-Assistant/blob/a77ddaf6/flake.lock)
- [flake.nix](https://github.com/Cody-W-Tucker/Cognitive-Assistant/blob/a77ddaf6/flake.nix)
- [lib/config.py](https://github.com/Cody-W-Tucker/Cognitive-Assistant/blob/a77ddaf6/lib/config.py)

This page provides technical instructions for bootstrapping the Cognitive Assistant development environment, configuring the necessary LLM providers, and executing the initial ingestion pipeline. The system utilizes **Nix** for reproducible environments and a structured **Layer Profile** system to manage multi-stage agent synthesis.

## Environment Setup

The project uses a Nix flake to manage dependencies, including a specific Python 3.12 stack, the `rlm` retrieval engine, and the `ai-data-extractor` utility.

### Prerequisites

- **Nix** with Flakes enabled.
- **direnv** (recommended) for automatic shell loading.

### Bootstrapping

1. **Clone the repository** and enter the directory.
2. **Enable the environment**: If using `direnv`, the `.envrc` file automatically triggers `use flake`[[.envrc:1-1]](). Otherwise, run:

```
nix develop
```
3. **Dependency Verification**: The `devShell` provides Python 3.12 with `anthropic`, `openai`, `pandas`, and `python-dotenv`[[flake.nix:114-121]](). It also injects the `rlm` and `ai-data-extractor` binaries into the `PATH`[[flake.nix:122-123]]().

### Configuration (.env)

Create a `.env` file in the root directory. This file is ignored by git [[.gitignore:3-3]](). The `APIConfig` class in `lib/config.py` loads these variables to manage provider access and model selection [[lib/config.py:18-60]]().

| Variable | Description | Default |
| --- | --- | --- |
| `XAI_API_KEY` | API Key for xAI Grok | - |
| `ANTHROPIC_API_KEY` | API Key for Anthropic Claude | - |
| `OPENAI_API_KEY` | API Key for OpenAI GPT | - |
| `XAI_MODEL` | Model identifier for xAI | `grok-4.3` |

**Sources:**[[flake.nix:109-127]](), [[lib/config.py:18-60]](), [[.envrc:1-1]]()

---

## Code Entity Space: Environment & CLI Entry

The following diagram illustrates how the environment configuration flows into the core execution logic.

### System Initialization Flow

```

```

**Sources:**[[flake.nix:112-125]](), [[lib/config.py:11-21]](), [[core/**main**.py:1-8]]()

---

## Nix Flake Usage

The `flake.nix` serves two primary purposes: defining the development shell and exporting generated artifacts for downstream consumption.

### Development Shell

The `default` devShell ensures all developers use identical versions of the Python interpreter and native tools.

- **Python Packages**: `python-dotenv`, `anthropic`, `pandas`, `openai`[[flake.nix:116-120]]().
- **Native Binaries**: `rlm` (Retrieval Language Model) and `ai-data-extractor`[[flake.nix:122-123]]().

### Artifact Exports

The flake dynamically discovers "Skills" within `workspaces/skills` by reading the directory structure and mapping `SKILL.md` files to attributes [[flake.nix:40-66]](). It also exports paths to critical generated files like `human_profile.md` and the `alignment_spec.md`[[flake.nix:67-84]]().

**Sources:**[[flake.nix:32-92]]()

---

## Running the First Commands

Once the environment is active, the system is managed via `python -m core`. The first step is typically a health check to ensure API keys and tool paths are valid.

### 1. Health Check

```
python -m core health-check
```

This executes `core/health_check.py`, which validates `APIConfig` provider setups and checks for the existence of required directories [[lib/config.py:195-200]]().

### 2. Ingesting Substrate

The "Existential Profile" requires a substrate of data (usually a `graph.json` and focus bundles). The `core/ingest_substrate.py` module converts these into JSONL packets for the retrieval engine.

```
python -m core ingest-substrate --graph path/to/graph.json --focus path/to/focus_bundle.json
```

**Data Flow in Ingestion:**

- `_graph_page_records`: Extracts entities (people, projects, concepts) into `graph_pages.jsonl`[[core/ingest_substrate.py:44-63]]().
- `_mention_evidence_records`: Captures cross-references between entities [[core/ingest_substrate.py:66-88]]().
- `_focus_source_note_records`: Processes deep-dive notes from focus bundles [[core/ingest_substrate.py:91-115]]().

### Ingestion Data Mapping

```

```

**Sources:**[[core/ingest_substrate.py:14-25]](), [[core/ingest_substrate.py:147-185]]()

---

## Summary of Filesystem Conventions

| Path | Purpose | Git Status |
| --- | --- | --- |
| `.env` | API Keys and Model Config | Ignored [[.gitignore:3-3]]() |
| `.envrc` | Automatic Nix environment loading | Tracked [[.envrc:1-1]]() |
| `core/` | Pipeline logic and CLI | Tracked |
| `workspaces/` | Generated artifacts (SOUL, Skills, Specs) | Tracked (except `data/` subdirs) |
| `lib/` | Shared utilities (LLM, Health, Config) | Tracked |

**Sources:**[[.gitignore:1-16]](), [[flake.nix:40-40]]()