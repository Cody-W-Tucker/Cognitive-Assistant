<<!--
  CA improvement runtime — synthesis prompt.
  Adapted from Backpass src/prompts/synthesis.md + src/prompts/annotate.md
  (Backpass MIT (c) 2026 Kun Chen, https://github.com/kunchenguid/backpass/blob/backpass-v0.1.32/src/prompts/synthesis.md,
  commit 0268201c3896f45d3002de0d439b6cefccb39063, tag backpass-v0.1.32).
  CA-native changes: the staging-copy edit flow is replaced by a strict JSON
  candidate-record contract (durable experience records only); the SOUL
  baseline stays read-only; the proposal is not authoritative until the apply
  gate; the self-session sentinel is prepended by improve/src/prompts.js, not
  baked into this file. See improve/LICENSE.NOTICE.
-->
You are performing the synthesis step of a CA improvement pass. Folded evidence from past sessions is below. Your job is to propose a small set of durable candidate experience records — one bounded step, not a rewrite.

## Sessions analyzed

{{TRANSCRIPT_COUNT}} sessions analyzed across {{HARNESS_SUMMARY}}.
{{RUN_NOTE}}

## Folded evidence

`sessions` counts distinct sessions behind each gap cluster. Every candidate must cite real sessions and verbatim quotes from the evidence rows — a paraphrase is not evidence.

{{EVIDENCE}}

## Previously rejected candidates — do not re-propose these

{{REJECTIONS}}

A rejected identity stays suppressed unless the candidate carries higher evidence (more distinct sessions) or genuinely new evidence (a session id the rejection did not cite).

## What to produce

Return ONE JSON object and nothing else. No prose, no markdown fence.

```
{
  "candidates": [
    {
      "title": "one imperative sentence",
      "body": "bounded recurrence description (at most 2000 chars)",
      "clusterId": "<folded cluster id>",
      "sources": ["<session id>", "<session id>"],
      "evidence": [{"polarity": "negative", "text": "verbatim quote from the evidence", "source": "<session id>", "effect": "what it cost"}],
      "counterevidence": "what argues against this record, or 'none observed'",
      "compilerImplication": "how the experience compiler consumes this record"
    }
  ]
}
```

Candidate durable-record contract:

1. `title` is one imperative sentence, specific enough to act on and general enough to apply beyond one session.
2. `body` is at most 2000 chars describing the recurrence and its cost.
3. `evidence` cites at least 2 distinct sessions from the folded evidence, each with a verbatim `text` quote copied exactly from the evidence rows and its `source` session id.
4. `counterevidence` is required: either the strongest observation against the record or the literal string `none observed` when nothing argues against it.
5. `compilerImplication` is required: one line stating how the experience compiler consumes the record (appended to the experience block; never a live, tracked, SOUL, skill, or Hermes change).
6. The staged artifact and its informational diff are rendered downstream from the accepted record — do not paste file text here.
7. Change only the proposal: never edit live files, tracked files, SOUL, posture, skills, or Hermes. Nothing here reaches the repository until a human applies it.
8. The proposal is not authoritative pre-apply: it is a candidate for the human apply gate, which is the sole writer of experience records.
9. An empty `{"candidates": []}` is valid when the evidence justifies no record.
