You are performing the synthesis step of a CA improvement pass. Folded evidence from past sessions is below. Your job is to propose narrow provisional plans as structured data. You have no tools and no files; reply with data only.

## Sessions analyzed

{{TRANSCRIPT_COUNT}} sessions analyzed across {{HARNESS_SUMMARY}}.
{{RUN_NOTE}}

## Active SOUL baseline (read-only, sha256 {{SOUL_SHA256}})

{{SOUL_SNAPSHOT}}

Every proposed plan must be baseline non-conflicting: it must not
contradict the SOUL baseline above. Plans extend experience only; they never
patch, rewrite, or restate SOUL. Name any explicit tension with the baseline
in the provisional intent so annotation can carry it as counterevidence.

## Folded evidence

`sessions` counts distinct sessions behind each gap cluster. Plans reference eligible clusters; they never author final evidence.

{{EVIDENCE}}

## Previously rejected candidates — do not re-propose these

{{REJECTIONS}}

A rejected identity stays suppressed downstream on annotated finals unless the final carries higher evidence (more distinct sessions) or genuinely new evidence (a session id the rejection did not cite). Synthesis itself does not suppress.

## What to do

Return exactly one JSON object with exactly the shape `{"plans": [...]}`. Each entry is a narrow provisional plan with ONLY these keys:

- `clusterId`: the folded cluster reference it annotates (matching one eligible folded cluster id listed above)
- `provisionalIntent`: one-line untrusted intent prose (max 500 chars)
- `provisionalSources`: an array of at least 2 distinct session ids from that cluster as context
- `id` (optional): a short safe label matching `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`
- `kind` (optional, when present must be `"add"`)
- `provisionalCount` (optional, when present must equal the distinct source count)

Example:

```json
{"plans": [{"id": "e1", "kind": "add", "clusterId": "<eligible cluster id>", "provisionalIntent": "<intent>", "provisionalSources": ["<session id>", "<session id>"], "provisionalCount": 2}]}
```

Plans MUST NEVER carry final durable record fields (`record`, `title`, `body`, `evidence`, session quote mappings, `counterevidence`, `compilerImplication`) or filesystem targets (`file`, `path`, `workspace`, `cwd`, or any path). Annotation authors the record; code assigns storage.

A plan missing the cluster reference, carrying fewer than 2 distinct session ids from that cluster, or carrying any other field makes the whole reply invalid, and no plans are kept this run.

Narrow proposer contract:

1. The cluster reference must resolve an eligible folded cluster id.
2. The session list holds at least 2 distinct eligible session ids from that cluster as context. These are not final evidence mappings.
3. Propose only plans: never edit live files, tracked files, SOUL, posture, skills, or Hermes. Nothing here reaches the repository until a human applies an annotated record.
4. An empty `{"plans": []}` is valid when the evidence justifies no record; that yields zero edits downstream.
