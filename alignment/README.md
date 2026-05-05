# Alignment

Artifact verification — checks whether an AI-generated artifact (spec, plan,
document, code change, copy, summary) is production-ready against this user's
personalized standards.

This module sits **above** the layer profile system. It reads skills from both
the existential and operational profiles and produces a single artifact
verification spec. It is invoked without `--profile`.

## Architecture

The verification spec has two layers:

1. **Generic artifact-readiness checklist** (universal SOP) — 10 fixed items
   that apply to any artifact: purpose stated, scope bounded, claims grounded,
   gaps surfaced, acceptance defined, structure earns its keep, internally
   consistent, form matches request, language precise, self-contained.
2. **Personalization** — skills from both profiles overlay onto each checklist
   item as user-specific cues for what "satisfied" and "failed" look like in
   practice.

The checklist skeleton lives in `seed.md`. The verifier role and response
format live in `build_spec.py` (preamble + postamble). The LLM only generates
the personalized middle.

## Files

| File | Purpose |
|---|---|
| `seed.md` | Compiler instructions: fixed checklist taxonomy + per-item output structure. |
| `build_spec.py` | Loads skills from both profiles, calls the LLM with the seed, prepends/appends static verifier role and response format, writes the final spec. |
| `verify_alignment.sh` | Runtime tool. Passes the spec + an artifact to `rlm` for evaluation. |
| `artifacts/alignment_spec.md` | The generated, committed verification spec. |

## Build the spec

Requires `build-skills` to have been run for at least one profile.

```bash
python -m core build-alignment-spec
python -m core build-alignment-spec --output /path/to/alt-spec.md
```

The default output path is `alignment/artifacts/alignment_spec.md`.

## Verify an artifact

```bash
# From a file
alignment/verify_alignment.sh --file path/to/artifact.md

# From stdin
echo "$ARTIFACT" | alignment/verify_alignment.sh --stdin

# Against multiple files (artifact + supporting context)
alignment/verify_alignment.sh --file draft.md --file context.md
```

`verify_alignment.sh` requires the `rlm` binary in `PATH`. The spec is resolved
from `$ALIGNMENT_SPEC` if set, otherwise from `artifacts/alignment_spec.md`
co-located with the script.

## Output format

The verifier returns:

```
VERDICT: SHIP | TIGHTEN | REWORK

| # | Checklist Item | Score | Evidence | Fix |
|---|----------------|-------|----------|-----|

CORRECTIONS (if TIGHTEN):
- [imperative instructions]

REWORK (if REWORK):
- [structural problem]
- [what the artifact should do instead]
```

- **SHIP** — all PASS, or one minor WEAK with no correction needed.
- **TIGHTEN** — one or more WEAK with actionable corrections; no FAIL.
- **REWORK** — any FAIL, or compounding WEAK indicating the artifact does not
  hold together.

## Regenerating after skill changes

The spec is a downstream artifact of the skills. Whenever you re-run
`build-skills` for either profile, regenerate the alignment spec:

```bash
python -m core --profile existential build-skills
python -m core --profile operational build-skills
python -m core build-alignment-spec
```
