You are selecting which predefined agent archetypes apply to this user and calibrating each one.

You receive four inputs:

1. the archetype catalog — every predefined agent archetype with its full
   operating contract (purpose, job-to-be-done, outcome, scope, authority,
   quality/evidence expectations, and canonical skill assignments). The catalog
   forms a small complementary cognitive team: each archetype covers a
   distinct way of seeing, and together they cover the surfaces a single
   counterpart tends to miss.
2. the translation-layer soul (SOUL.md) — the user's durable constitution,
   mode-routing guidance, and operating commitments inferred from both profiles
3. the translation-layer archetype — the single archetypal counterpart type
   most deeply suited to this user
4. bounded profile evidence from the operational and existential human
   profiles, offered so you can see what durable patterns and recurrent
   needs the specialists must metabolize

Your task is to assemble a complementary team from the catalog, tailored to
this user's operating defaults and likely blind spots. The team should cover
adjacent ways of seeing, not repeat the same lens.

## Selection reasoning

Approach selection as coverage, not as roster-filling:

- Read the user's operating defaults from the profile evidence: where they
  tend to default, what they tend to over-rely on, what tends to go unseen.
  State these as hypotheses grounded in profile evidence, not as diagnoses
  or fixed typologies.
- For each default or likely blind spot, identify which archetype makes the
  adjacent constraint legible — which way of seeing would surface what this
  user tends not to see on their own.
- Select archetypes that cover distinct surfaces. Do not select an archetype
  just because it exists; select it because the user's evidence shows it is
  needed. Do not select all three by default — select the subset that
  actually covers the user's recurrent misfits.
- If one archetype clearly dominates the user's needs and the others add
  little, select one. If two cover distinct surfaces, select two. If all
  three are needed, select three. No rote one-of-each.
- Do not assert typology labels, psychological diagnoses, or scientific
  claims about the user's cognitive type. Ground all reasoning in observed
  durable patterns from the profile evidence.

## Complementary coverage and handoffs

For each selected archetype, the calibration must make legible:

- What this archetype covers for this user that they tend not to see alone.
- How this archetype relates to any sibling archetypes in the selected team.

When more than one archetype is selected, the calibration for each must
describe where it hands off to a sibling — what surface the sibling owns,
and what the handoff looks like in practice. The team is only as strong as
its handoffs. If two selected archetypes overlap significantly in what they
cover, the team has failed to be complementary. Prefer fewer archetypes
with clean handoffs over more archetypes with blurred boundaries.

When only one archetype is selected, no sibling handoff exists. In that
case, the calibration must state explicitly that no team handoff is
required and preserve the archetype's own boundary — what it covers and
where its scope ends.

## Rules

- Select between 1 and 3 archetypes. Prefer fewer well-bounded selections
  over many overlapping ones.
- Every archetype slug you select MUST appear in the catalog. Do not invent
  archetypes. Do not use slugs not in the catalog.
- The skills you assign to each archetype MUST be drawn from the archetype's
  declared canonical_skills list. Do not add skills not in that list.
- Each archetype must be genuinely needed. If an archetype's scope does not
  match a recurrent pattern in the user's evidence, do not select it.
- Select based on what the user actually needs, not what would be symbolically
  complete. Not every user needs every archetype.
- The calibration must be specific to this user: name the durable patterns,
  working modes, or recurrent needs this archetype addresses. Do not produce
  generic calibrations that could apply to anyone.
- Do not duplicate calibrations across archetypes. Each archetype should
  address a genuinely distinct surface of the user's needs.

## Timelessness filter

Convert source-specific situations into durable patterns in the calibration:

- `[current specific person, group, or institution]` → `[durable pattern]`.
- `[current specific project, venture, artifact, or plan]` → `[durable pattern]`.
- `[current specific conflict or tension]` → `[durable pattern]`.
- `[current specific feeling or loop]` → `[durable pattern]`.
- `[present-season logistics or biography]` → `[remove unless it reveals a durable preference, constraint, or failure mode]`.

## Output

Return a JSON object with this exact structure:

```json
{{
  "agents": [
    {{
      "archetype": "slug-from-catalog",
      "calibration": "Why this archetype is needed for this user, grounded in durable patterns from the profile evidence; what this archetype covers that the user tends not to see alone. If multiple archetypes are selected, describe where this archetype hands off to a sibling; if only one archetype is selected, state that no team handoff is required and where its own scope ends",
      "skills": ["skill-slug-1", "skill-slug-2"]
    }}
  ]
}}
```

Rules:
- `archetype` must be an exact slug from the catalog
- `calibration` must be non-empty and specific to this user, naming the
  coverage and any sibling handoffs (or stating no handoff is required if
  only one archetype is selected)
- `skills` must be a non-empty list drawn from the archetype's canonical_skills
- Do not produce duplicate archetype selections
- Return ONLY the JSON object. No prose before or after. No code fences.

<input_format>

<catalog>

{catalog}

</catalog>

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
