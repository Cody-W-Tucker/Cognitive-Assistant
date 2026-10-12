You are annotating the narrow staged change plan of a CA improvement pass. The staged plans below are provisional only — nothing here is authoritative until annotation authors the final record and a human applies it.

## Run

{{RUN_ID}} — {{COUNT}} staged change plan(s) to annotate.

## Staged change plans (provisional, no records)

{{STAGED_CANDIDATES}}

## What to return

Return ONE JSON object and nothing else. No prose, no markdown fence.

```
{
  "annotations": [
    {"id": "<staged plan id>", "verdict": "keep", "reason": "one line", "record": {"title": "one imperative sentence", "body": "bounded recurrence description (at most 2000 chars)", "clusterId": "<folded cluster id>", "sources": ["<session id>", "<session id>"], "evidence": [{"polarity": "negative", "text": "verbatim quote from the evidence", "source": "<session id>", "effect": "what it cost"}], "counterevidence": "what argues against this record, or 'none observed'", "compilerImplication": "how the experience compiler consumes this record"}},
    {"id": "<staged plan id>", "verdict": "drop", "reason": "one line"},
    {"id": "<staged plan id>", "verdict": "revert", "reason": "measurement does not support this plan"}
  ]
}
```

Annotation contract (sole full-record origin):

1. Coverage or revert: every staged plan gets exactly one annotation. A `keep` or `drop` verdict covers the plan; a `revert` verdict explicitly reverts it when measurement does not support it. No plan is left without coverage or explicit revert.
2. Keep authors the complete durable record: `title` (one imperative sentence), `body` (at most 2000 chars), `clusterId` (eligible folded cluster), `sources` (at least 2 distinct session ids from that cluster), `evidence` (exact session-bound verbatim `text` quotes, each copied exactly from staged eligible evidence for its `source` session), `counterevidence` (strongest observation against the record or `none observed`), `compilerImplication` (how the experience compiler consumes the record: appended to the experience block; never a live, tracked, SOUL, skill, or Hermes change), and `reason`/`rationale` (one line). A paraphrase is not evidence; a quote cited against the wrong session fails; anything less than the complete record fails closed.
3. Exact source quote and session binding: each `keep` verdict must rest on verbatim quotes attributable to the cited sessions within the referenced eligible cluster. Global or swapped quotes fail.
4. Change only the annotation: never edit live files, tracked files, SOUL, posture, skills, or Hermes. Nothing here reaches the repository until a human applies the annotated final.
5. An empty `{"annotations": []}` is valid only when the staged set is empty. Production invents nothing: missing/invalid finals fail closed with no edits.
