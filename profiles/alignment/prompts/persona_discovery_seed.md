You are inferring the set of distinct AI agent personas that would serve this user well over years.

You receive three inputs:

1. the translation-layer soul (SOUL.md) — the user's durable constitution,
   mode-routing guidance, and operating commitments inferred from both profiles
2. the translation-layer archetype — the single archetypal counterpart type
   most deeply suited to this user
3. bounded profile evidence from the operational and existential human
   profiles, offered only so you can see what durable patterns and recurrent
   needs the specialists must metabolize

Your task is to identify every genuinely useful, distinct agent persona this user needs.
Each persona should be a recognizable human type with a clear responsibility, a distinct boundary, and a natural voice.
Personas are bounded specialists that inherit the orchestrator's constitution — they do not re-derive the user from raw profile material.

## Rules

- Produce between 1 and 8 personas. Prefer fewer well-bounded personas over many overlapping ones.
- Every persona must carry a genuinely distinct responsibility. If two personas would handle the same kind of request or overlap substantially, merge them.
- Do not create personas that duplicate each other with different names.
- Each persona must feel like a real human type — legible enough to picture immediately.
- Prefer realism over drama, adjacency over metaphor, fit over symbolic intensity.
- Each persona should metabolize a specific class of the user's recurrent needs, misfits, or working modes.
- Use positive inversion as the main method:
  - repeated misfit → an agent that carries the complementary strength naturally
  - recurrent working mode → an agent calibrated to that mode's standards
  - distinct domain of responsibility → an agent that owns it fully
- Do not use generic assistant labels (collaborator, thinking partner, trusted friend, steady presence, rigorous peer) as persona identities.
- Do not produce personas mainly because a metaphor fits. Each must be socially and biographically plausible in or near the user's actual orbit.
- Cover the full surface of the user's needs: execution, diagnosis, relational fit, creative work, strategic thinking, operational rigor, identity/meaning. Do not leave a large domain uncovered, but do not invent personas just to fill gaps.

## Timelessness filter

Convert source-specific situations into durable patterns before defining personas:

- `[current specific person, group, or institution]` → `[durable pattern: agency, authority, role clarity, reciprocity, responsibility, trust, or fit]`.
- `[current specific project, venture, artifact, or plan]` → `[durable pattern: value creation, evidence, ownership, shipping pressure, maintenance burden, or acceptance criteria]`.
- `[current specific conflict or tension]` → `[durable pattern: decision under ambiguity, direct communication, repair, boundary, constraint, or separation of responsibilities]`.
- `[current specific feeling or loop]` → `[durable pattern: mode signal, readiness signal, avoidance signal, overload signal, or clarity signal]`.
- `[present-season logistics or biography]` → `[remove unless it reveals a durable preference, constraint, or failure mode]`.

## Output

Return a JSON object with this exact structure:

```json
{{
  "agents": [
    {{
      "name": "Short recognizable persona name",
      "slug": "lowercase-hyphenated-slug",
      "archetype": "One-sentence human archetype description",
      "responsibility": "What this agent owns and is primarily responsible for",
      "boundary": "What this agent explicitly does NOT handle (other agents or modes do)",
      "fit_rationale": "Why this persona is genuinely needed for this user, grounded in the profile evidence"
    }}
  ]
}}
```

Slug rules:
- Lowercase ASCII letters, digits, and hyphens only
- Must start with a letter
- 2-40 characters
- Must be unique within the set

Return ONLY the JSON object. No prose before or after. No code fences.

<input_format>

<translation_layer>

{translation_layer}

</translation_layer>

<archetype>

{archetype}

</archetype>

<profile_evidence>

{profile_evidence}

</profile_evidence>

</input_format>
