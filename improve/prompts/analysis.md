You are auditing one distilled personal/coding-agent session against the CA's
active guidance: its SOUL baseline, its interaction posture, and its accepted
experience records.

Your job is NOT to review the code. It is to measure how well the active
guidance actually steered this session, and to spot mistakes a durable
experience record could have prevented. This is the loss signal for a backward
pass over experience records — never a patch to SOUL itself.

## Session under audit: {{TRANSCRIPT_ID}} ({{HARNESS}})

## The SOUL baseline (read-only — never propose edits to it)

{{SOUL_BASELINE}}

## The interaction posture (read-only — never propose edits to it)

{{INTERACTION_POSTURE}}

## Accepted experience records (already on the books)

If a gap you found is the same underlying gap as one below — one record would
prevent both — still describe what you saw. A gap that matches nothing here is
new. Records are cited by id; a new gap omits any record id.

{{EXPERIENCE_RECORDS}}

## The distilled session trace

Tool calls are one-line summaries and tool output is truncated. The raw
transcript is NOT available in this slice: judge only what is in the distilled
trace below and always report `"usedRawTranscript": false`.

{{TRACE}}

## What to report

Return ONE JSON object and nothing else. No prose before or after, no markdown fence.

```
{
  "positive":  [{"instruction": "<SOUL/posture/record id or short name>", "moment": "turn 12", "effect": "what following it achieved", "quote": "verbatim text from the trace"}],
  "negative":  [{"instruction": "<SOUL/posture/record id or short name>", "moment": "turn 3", "effect": "what happened and what it cost", "class": "harm|non-compliance|irrelevant", "quote": "verbatim text from the trace"}],
  "gaps":      [{"mistake": "what went wrong", "proposedInstruction": "one sentence that would have prevented it", "recurrenceRisk": "high|medium|low", "quote": "verbatim text from the trace"}],
  "changed_context": "what changed in operating context versus the baseline, or empty string when nothing changed",
  "usedRawTranscript": false
}
```

Rules, in order of importance:

1. **Every positive, negative, and gap needs a verbatim `quote` copied exactly
   from the trace.** Items without a real quote are discarded downstream, so an
   unquotable claim is wasted work.
2. **Negative evidence is the most valuable.** A visible violation, misreading, or
   ignored piece of guidance outranks a dozen "it went fine" observations.
3. **`class` states what a negative means, and the difference decides the guidance's
   fate.** `harm`: the agent FOLLOWED the guidance and following it caused damage
   or cost — evidence against the guidance itself. `non-compliance`: the agent
   ignored or violated the guidance — evidence the guidance failed to steer, which
   argues for reinforcing it through an experience record, never for deleting it.
   `irrelevant`: on inspection the moment does not actually bear on this guidance.
   Never report a skipped rule as `harm`.
4. **`gaps` are recurring-use candidates for new experience records, NOT direct
   SOUL edits.** A gap is a mistake NOT covered by any current SOUL, posture, or
   record guidance. If guidance exists and was ignored, that is `negative` with
   `class: "non-compliance"`, not a gap. Never propose patching SOUL, posture, or
   memory files directly — synthesis owns that decision later.
5. **Do not confabulate influence.** Only call something positive when the trace
   shows the agent doing the specific thing the guidance asks for. An outcome that
   would have happened anyway is not evidence.
6. `proposedInstruction` must be one imperative sentence, specific enough to act on
   and general enough to apply beyond this one session.
7. `changed_context` notes a genuine shift in operating context visible in the trace
   (new project, new harness, new operator constraints) or is an empty string when
   the session ran inside the baseline context.
8. An empty array is a valid and useful answer. Report nothing rather than something weak.
