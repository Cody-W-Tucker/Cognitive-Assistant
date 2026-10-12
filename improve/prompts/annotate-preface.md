<!--
  CA improvement runtime — annotate-preface prompt.
  CA-native preface (no direct Backpass counterpart): it frames the staged
  candidates that already exist and opens the fresh logical annotate session.
  It operationally precedes improve/prompts/annotate.md, which is adapted
  from Backpass src/prompts/annotate.md
  (Backpass MIT (c) 2026 Kun Chen, https://github.com/kunchenguid/backpass/blob/backpass-v0.1.32/src/prompts/annotate.md,
  commit 0268201c3896f45d3002de0d439b6cefccb39063, tag backpass-v0.1.32).
  CA-native changes: staged-existing framing, fresh-logical-session sequencing
  (annotate-preface then annotate), revert-only preface outcome; the
  self-session sentinel is prepended by improve/src/prompts.js, not baked
  into this file. See improve/LICENSE.NOTICE.
-->
You are opening the annotate step of a CA improvement pass. The staged candidates below already exist as a staged change plan — this preface creates nothing new. Its only job is to open a fresh logical session for the annotate call that follows.

## Run

{{RUN_ID}} — {{COUNT}} staged candidate(s) under review.

## Staged candidates already existing

{{STAGED_SUMMARY}}

## What to return

Return ONE JSON object and nothing else. No prose, no markdown fence.

```
{"ready": true}
```

Rules:

1. The staged candidates already exist; do not propose new records here.
2. This preface opens a fresh logical session: the annotate call that follows is a separate invocation with its own prompt, not a continuation of synthesis or measurement.
3. The preface outcome is revert-only metadata (`ready`): it never annotates, never edits live files, tracked files, SOUL, posture, skills, or Hermes, and never reaches the repository.
4. An empty staged set (`{{COUNT}}` of zero) is valid: return readiness all the same so the run stays sequenced as annotate-preface then annotate.
