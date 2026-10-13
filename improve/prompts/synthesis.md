You are performing the synthesis step of a CA improvement pass. Folded evidence from past sessions is below. Your job is an edit-only turn: author or edit markdown records directly in ONLY the private workspace working directory.

## Sessions analyzed

{{TRANSCRIPT_COUNT}} sessions analyzed across {{HARNESS_SUMMARY}}.
{{RUN_NOTE}}

## Folded evidence

`sessions` counts distinct sessions behind each gap cluster. Edits reference eligible clusters; they never author final evidence.

{{EVIDENCE}}

## Previously rejected candidates — do not re-propose these

{{REJECTIONS}}

A rejected identity stays suppressed downstream on annotated finals unless the final carries higher evidence (more distinct sessions) or genuinely new evidence (a session id the rejection did not cite). Synthesis itself does not suppress.

## What to do

Inspect and edit ONLY the private workspace working directory provided as the invocation cwd (stateDir/synthesis-workspace). Do not treat structured data as the durable output; the durable output is ONLY the workspace file edits observed after this turn. A response with no workspace file edits yields zero edits downstream.

Every created or modified workspace record must open with structured YAML frontmatter carrying ONLY `clusterId` and `provisionalSources` — no other frontmatter keys:

- `clusterId`: the folded cluster reference it annotates (matching one eligible folded cluster id listed above)
- `provisionalSources`: a YAML sequence of at least 2 distinct session ids from that cluster as context (block `- ` list form)

Copy this scaffold exactly (fill the placeholders, keep ONLY these two keys):

```yaml
---
clusterId: <eligible cluster id>
provisionalSources:
  - <session id>
  - <session id>
---
```

followed by editable markdown content only (a `# <intent>` heading plus recurrence prose). The workspace file frontmatter AND body must NEVER carry final durable record fields: no `id`, `record`, `title`, `body`, `sources`, `evidence`, session quote mappings, `counterevidence`, `compilerImplication`, staged artifact, or diff. Annotation authors all of those; any workspace file carrying a final durable field in frontmatter or body is invalid and dropped individually.

Records missing either field, carrying fewer than 2 distinct session ids, or carrying malformed YAML are invalid and dropped individually; valid siblings still proceed. Files without explicit frontmatter gain no cluster association and never borrow one: missing linkage is never invented.

Narrow edit contract:

1. The cluster reference must resolve an eligible folded cluster id.
2. The session list holds at least 2 distinct eligible session ids from that cluster as context. These are not final evidence mappings.
3. NEVER emit final durable fields in frontmatter or body here: no `id`, `record`, `title`, `body`, `sources`, `evidence`, session quote mappings, `counterevidence`, `compilerImplication`, staged artifact, or diff — only the two-key provenance frontmatter above plus editable markdown heading and prose. Annotation authors all durable fields; any file carrying them in frontmatter or body text is invalid and dropped individually.
4. The staged artifact and its informational diff are rendered downstream from the ANNOTATED final record — do not paste file text elsewhere.
5. Edit only the workspace: never edit live files, tracked files, SOUL, posture, skills, or Hermes. Nothing here reaches the repository until a human applies an annotated final. Apply remains the sole durable writer of the real experience surface.
6. The edit turn is not authoritative pre-apply: it is a workspace author for private stage/measure and the annotate step, which is the sole full-record origin. The human apply gate consumes only annotated finals.
7. No workspace file edits is valid when the evidence justifies no record; that yields zero edits downstream.
