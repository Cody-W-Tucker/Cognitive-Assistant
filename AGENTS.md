# Agent Guidelines for Cognitive-Assistant

## Build/Lint/Test Commands

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Run full pipeline:**
```bash
python prompt_creator.py
```

**Run single test (no tests configured):**
```bash
# Add pytest configuration to pyproject.toml when tests are added
pytest tests/ -v
```

**Lint code:**
```bash
# Add black + isort + flake8 to requirements-dev.txt when configured
black .
isort .
flake8 .
```

## Code Style Guidelines

**Imports:** Standard library → third-party → local modules. Use absolute imports.

**Type hints:** Required for all function parameters and return values. Use `typing` module extensively.

**Naming:** snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants.

**Docstrings:** Google-style docstrings for all public functions and classes.

**Error handling:** Use specific exceptions, log errors with context, avoid bare except clauses.

**Data structures:** Prefer dataclasses for simple data, Pydantic models for validated data.

**Async:** Use async/await for I/O operations, proper error handling in async contexts.

**Configuration:** Use environment variables for secrets, config.py for shared settings.