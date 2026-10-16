# Lineage Journal (bounded v1, private)

Private lineage at `<stateDir>/journal/` (default
`$XDG_DATA_HOME/cognitive-assistant/improve/journal/`).

- `events.jsonl` is append-only history (one JSON object per line).
- `current.json` and `bootstrap.md` are generated views; regenerate with
  `python -m core journal-compact --state-dir <dir>`.
- Events come from the actual lifecycle only: `run_completed`,
  `proposal_created`, `experience_accepted`, `proposal_rejected`,
  `artifact_compiled`.
- Every write is sanitized/validated: raw transcripts, prompts, evidence
  quotes, full SOUL, credentials, and absolute paths are rejected in events
  and excluded from views. Payloads may carry `sources` as short id refs
  only; views list refs as plain text (no KB Markdown rendering).
- Journal never applies, deploys, or alters SOUL/Hermes; it writes only
  under `<stateDir>/journal/` (dirs `0700`, files `0600` where supported).
- Retention: no prompt/evidence GC. Outside `journal/` with current
  behavior: `evidence/`, `prompts/<runId>__*.md` + sidecars, `proposal.json`,
  `ledger.json`/`open-gaps.json`, `synthesis-workspace/`, `cursor.json`,
  `rejections.jsonl`. `journal-compact` tolerates missing/malformed JSONL
  and never deletes those files; discovery scope and OpenCode/Hermes
  behavior are unchanged.
