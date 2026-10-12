You are consolidating the folded gap ledger of a CA improvement pass. Each entry below is a mistake some past session hit that no current SOUL, posture, or experience record covers, phrased as the instruction that would have prevented it. Different sessions phrase the same underlying gap differently, and a gap only graduates into a proposal once enough DISTINCT sessions have hit it — so paraphrases of one gap must be recognized as one entry, or real recurrence stays invisible.

## Open gap entries

{{GAP_ENTRIES}}

## What to return

Return ONE JSON object and nothing else. No prose, no markdown fence.

```
{"merges": [["<id>", "<id>", ...], ...]}
```

Each inner array lists two or more entry ids that are the SAME underlying gap. Rules:

1. Merge only when one instruction would prevent every entry in the group — the same mistake, not merely the same topic. Two gaps about the same subsystem that call for different instructions stay separate.
2. When unsure, do not merge. A wrong merge fabricates corroboration and can write a weakly-supported record into the proposal; a missed merge only waits for another sighting.
3. An id may appear in at most one group. Ids not listed stay untouched.
4. `{"merges": []}` is a valid and common answer.
