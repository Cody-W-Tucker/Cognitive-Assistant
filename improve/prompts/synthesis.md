You are performing the synthesis step of a CA improvement pass. Folded evidence from past sessions is below. Your job is a text-only proposer: return narrow provisional plans as structured data on stdout. Do not inspect files, do not edit files, do not use a workspace.

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

Return exactly one JSON object on stdout with exactly the shape `{"plans": [...]}`. Each entry is a narrow provisional plan with ONLY these keys:

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

The stdout payload MUST NEVER carry final durable record fields: no `record`, `title`, `body`, `evidence`, session quote mappings, `counterevidence`, `compilerImplication`, staged artifact, or diff. Annotation authors all of those; any plan carrying a final durable field is invalid and dropped individually. Plans MUST NEVER carry filesystem targets: no `file`, `path`, `workspace`, `cwd`, or absolute/relative paths. Deterministic code assigns storage; model-controlled paths are rejected.

Plans missing the cluster reference, carrying fewer than 2 distinct session ids from that cluster, or carrying malformed/unexpected fields are invalid and dropped individually; valid siblings still proceed. Plans without an explicit eligible cluster association never borrow one: missing linkage is never invented.

Narrow proposer contract:

1. The cluster reference must resolve an eligible folded cluster id.
2. The session list holds at least 2 distinct eligible session ids from that cluster as context. These are not final evidence mappings.
3. NEVER emit final durable fields here: no `record`, `title`, `body`, `evidence`, session quote mappings, `counterevidence`, `compilerImplication`, staged artifact, or diff. Annotation authors all durable fields; any plan carrying them is invalid and dropped individually.
4. The staged artifact and its informational diff are rendered downstream from the ANNOTATED final record — do not paste record text here.
5. Propose only plans: never edit live files, tracked files, SOUL, posture, skills, or Hermes. Nothing here reaches the repository until a human applies an annotated final. Apply remains the sole durable writer of the real experience surface.
6. The proposer output is not authoritative pre-apply: it is input for deterministic materialization plus private stage/measure and the annotate step, which is the sole full-record origin. The human apply gate consumes only annotated finals.
7. An empty `{"plans": []}` is valid when the evidence justifies no record; that yields zero edits downstream.
