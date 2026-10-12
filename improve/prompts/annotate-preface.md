You are opening the annotate step of a CA improvement pass. The staged change plans below already exist as a narrow provisional plan — this preface creates nothing new and authors no records. Its only job is to open a fresh logical session for the annotate call that follows, which is the sole full-record origin.

## Run

{{RUN_ID}} — {{COUNT}} staged change plan(s) under review.

## Staged change plans already existing (provisional, no records)

{{STAGED_SUMMARY}}

## What to return

Return ONE JSON object and nothing else. No prose, no markdown fence.

```
{"ready": true}
```

Rules:

1. The staged change plans already exist as provisional cluster ref/intent only; do not propose new records or final fields here.
2. This preface opens a fresh logical session: the annotate call that follows is a separate invocation with its own prompt, not a continuation of synthesis or measurement.
3. The preface outcome is revert-only metadata (`ready`): it never annotates, never authors records/evidence, never edits live files, tracked files, SOUL, posture, skills, or Hermes, and never reaches the repository.
4. An empty staged set (`{{COUNT}}` of zero) is valid: return readiness all the same so the run stays sequenced as annotate-preface then annotate.
