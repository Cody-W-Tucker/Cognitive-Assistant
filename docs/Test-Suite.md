# Test Suite

Tests cover the profile pipeline, QMD-backed question asking, LLM helpers,
prompt and skill generation, alignment generation, CLI registration, and
operational corpus ingestion.

`tests/test_question_asker.py` fakes QMD and the LLM. It covers successful
grounded synthesis and fail-closed retrieval behavior. No test requires paid
question generation.
