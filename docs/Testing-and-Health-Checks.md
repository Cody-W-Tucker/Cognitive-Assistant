# Testing And Health Checks

Run the suite in the development shell:

```bash
python -m unittest discover -s tests -v
```

The question-asker tests use fake QMD and fake LLM clients. They verify that
answers receive bounded passages and that retrieval failures do not invoke the
LLM. Health tests validate prompt rendering and QMD readiness without requiring
real provider calls.
