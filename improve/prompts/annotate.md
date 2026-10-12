<!--
  CA improvement runtime — annotate prompt.
  Adapted from Backpass src/prompts/annotate.md
  (Backpass MIT (c) 2026 Kun Chen, https://github.com/kunchenguid/backpass/blob/backpass-v0.1.32/src/prompts/annotate.md,
  commit 0268201c3896f45d3002de0d439b6cefccb39063, tag backpass-v0.1.32).
  CA-native changes: strict JSON annotation contract over the staged change
  plan (coverage-or-revert per candidate, exact quote/session binding,
  counterevidence, compilerImplication); the proposal stays non-authoritative
  until the human apply gate; the self-session sentinel is prepended by
  improve/src/prompts.js, not baked into this file. See improve/LICENSE.NOTICE.
-->
You are annotating the staged change plan of a CA improvement pass. The staged candidates below are proposals only — nothing here is authoritative until a human applies it.

## Run

{{RUN_ID}} — {{COUNT}} staged candidate(s) to annotate.

## Staged candidates

{{STAGED_CANDIDATES}}

## What to return

Return ONE JSON object and nothing else. No prose, no markdown fence.

```
{
  "annotations": [
    {"id": "<staged candidate id>", "verdict": "keep|drop", "reason": "one line"},
    {"id": "<staged candidate id>", "verdict": "revert", "reason": "measurement does not support this candidate"}
  ]
}
```

Annotation contract:

1. Coverage or revert: every staged candidate gets exactly one annotation. A `keep` or `drop` verdict covers the candidate; a `revert` verdict explicitly reverts it when measurement does not support it. No candidate is left without coverage or explicit revert.
2. Exact source quote and session binding: each `keep` verdict must rest on a verbatim `text` quote copied exactly from the staged evidence rows and its `source` session id. A paraphrase is not evidence; a quote cited against the wrong session fails.
3. `counterevidence` is required on the staged record: either the strongest observation against the record or the literal string `none observed` when nothing argues against it.
4. `compilerImplication` is required on the staged record: one line stating how the experience compiler consumes the record (appended to the experience block; never a live, tracked, SOUL, skill, or Hermes change).
5. Change only the annotation: never edit live files, tracked files, SOUL, posture, skills, or Hermes. Nothing here reaches the repository until a human applies it.
6. An empty `{"annotations": []}` is valid only when the staged set is empty.
