<<!--
  CA improvement runtime — synthesis prompt.
  Adapted from Backpass src/prompts/synthesis.md + src/prompts/annotate.md
  (Backpass MIT (c) 2026 Kun Chen, https://github.com/kunchenguid/backpass/blob/backpass-v0.1.32/src/prompts/synthesis.md,
  commit 0268201c3896f45d3002de0d439b6cefccb39063, tag backpass-v0.1.32).
  CA-native changes: synthesis emits NARROW STAGED CHANGE PLANS ONLY
  (untrusted provisional cluster ref/intent/eligible sources). It never
  authors final title/body/evidence/session quote mappings/
  counterevidence/compilerImplication/stagedArtifact/diff — annotation is
  the sole full-record origin. The SOUL baseline stays read-only; the
  proposal is not authoritative until the human apply gate consumes
  annotated finals; the self-session sentinel is prepended by
  improve/src/prompts.js, not baked into this file. See improve/LICENSE.NOTICE.
-->
You are performing the synthesis step of a CA improvement pass. Folded evidence from past sessions is below. Your job is to propose a small set of NARROW STAGED CHANGE PLANS — provisional cluster references, not final records.

## Sessions analyzed

{{TRANSCRIPT_COUNT}} sessions analyzed across {{HARNESS_SUMMARY}}.
{{RUN_NOTE}}

## Folded evidence

`sessions` counts distinct sessions behind each gap cluster. Plans reference eligible clusters; they never author final evidence.

{{EVIDENCE}}

## Previously rejected candidates — do not re-propose these

{{REJECTIONS}}

A rejected identity stays suppressed downstream on annotated finals unless the final carries higher evidence (more distinct sessions) or genuinely new evidence (a session id the rejection did not cite). Synthesis itself does not suppress.

## What to produce

Return ONE JSON object and nothing else. No prose, no markdown fence.

```
{
  "plans": [
    {"clusterId": "<folded cluster id>", "provisionalIntent": "one imperative sentence (untrusted provisional)", "provisionalSources": ["<session id>", "<session id>"]}
  ]
}
```

Narrow change-plan contract:

1. `clusterId` must resolve an eligible folded cluster id.
2. `provisionalIntent` is one untrusted provisional sentence naming the gap direction. It is not the final title.
3. `provisionalSources` lists at least 2 distinct eligible session ids from that cluster as context. These are not final evidence mappings.
4. NEVER emit final durable fields here: no `record`, `title`, `body`, `evidence`, session quote mappings, `counterevidence`, `compilerImplication`, staged artifact, or diff. Annotation authors all of those; any plan carrying them is invalid and dropped.
5. The staged artifact and its informational diff are rendered downstream from the ANNOTATED final record — do not paste file text here.
6. Change only the plan: never edit live files, tracked files, SOUL, posture, skills, or Hermes. Nothing here reaches the repository until a human applies an annotated final.
7. The plan is not authoritative pre-apply: it is a provisional candidate for private stage/measure and the annotate step, which is the sole full-record origin. The human apply gate consumes only annotated finals.
8. An empty `{"plans": []}` is valid when the evidence justifies no record.
