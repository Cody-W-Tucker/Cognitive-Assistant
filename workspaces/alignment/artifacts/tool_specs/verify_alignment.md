# Verify Alignment

## Mission

Evaluate an artifact against the generated alignment spec before it ships. Use this tool when the question is not whether the artifact is plausible, but whether it satisfies the user's artifact-readiness standards.

## Use This Tool For

- Drafts, specs, plans, summaries, code-review notes, copy, or handoff documents that need a final alignment check.
- Outputs where failures should become concrete corrections rather than general feedback.
- Comparing an artifact to the user's standards for scope, grounding, structure, precision, request-fit, and operator usefulness.
- CI-like or local verification workflows where the artifact already exists as a file, directory, URL, inline text, or stdin stream.

## When to Not Use this Tool

- Avoid using this tool for simple artifacts that don't rely on the user's taste, preferences, or hard-to-assess expectations.

## Command

Run `verify-alignment` with the artifact to verify:

```bash
verify-alignment --file draft.md
verify-alignment --stdin < output.md
verify-alignment --text "artifact text"
verify-alignment --file docs --url https://example.com/context
```

## Flags

- `--file PATH`: Load a file, directory, or glob as artifact/context. May be repeated.
- `--url URL`: Load URL content as artifact/context. May be repeated.
- `--text TEXT`: Add inline artifact/context text. May be repeated.
- `--stdin`: Read artifact/context from stdin. Can be combined with other context flags.
- `--verbose`: Print RLM progress events to stderr.
- `--help`: Show wrapper help.

## Output

The verifier returns a structured judgment:

```text
VERDICT: SHIP | TIGHTEN | REWORK

| # | Checklist Item | Score | Evidence | Fix |
|---|----------------|-------|----------|-----|

CORRECTIONS (if TIGHTEN):
- [imperative instructions]

REWORK (if REWORK):
- [structural problem]
- [what the artifact should do instead]
```

## Handling Verification Results

### SHIP

No action needed. The artifact meets alignment standards.

### TIGHTEN

Apply the CORRECTIONS list directly to the artifact. How you incorporate fixes depends on the artifact type:

**For documents (markdown, specs, plans):**

- Rewrite sentences to address clarity issues
- Add missing details or examples
- Restructure sections for better flow
- The fixes should be woven into the content naturally, not appended as notes

**For code:**

- Apply fixes inline where the issues occur
- Add comments only if the fix itself isn't self-documenting
- Refactor structure if needed

**For metadata-rich artifacts:**

- Add alignment metadata to frontmatter (YAML/TOML) or structured comments
- Encode verification status, constraints, or decisions that aren't part of the public-facing content

### REWORK

The artifact has structural problems. Present a plan to the user:

1. Summarize the structural issues identified
2. Propose a new approach that addresses the root problems
3. Ask for approval before implementing the rework

If the critiques seem inapplicable or conflict with constraints you're aware of, explain the conflict to the user and wait for their decision.

## Examples

**Document needing TIGHTEN:**

```bash
verify-alignment --file proposal.md
# Returns: TIGHTEN with "Add concrete metrics for success"
# Action: Edit proposal.md to add specific KPIs in the success criteria section
```

**Code needing metadata:**

```bash
verify-alignment --file api_handler.py
# Returns: TIGHTEN with "Document rate limit assumptions"
# Action: Add docstring or structured comment explaining rate limit design decisions
```

**Artifact needing REWORK:**

```bash
verify-alignment --file architecture.md
# Returns: REWORK with "Scope exceeds stated constraints"
# Action: Present plan to user showing how to narrow scope before rewriting
```
