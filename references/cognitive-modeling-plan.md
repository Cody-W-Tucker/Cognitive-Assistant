# Cognitive Modeling Plan (Signatures + Lineage + Concept Triggers)

Date: 2026-05-17
Status: Initial spec for theory-of-mind layer
Related: existential profile, state files, skill curation, multi-type generalization

## Goal
Replace implicit, non-deterministic modeling of user cognition with an explicit but lightweight system that:
- Tracks stable signatures (operating principles)
- Uses repetition as an activation trigger (concepts for this user)
- Produces traceable lineage on outputs
- Supports provisional updates so the model evolves without locking in
- Parameterizes the unit of tracking (concepts vs people vs other) for future multi-type support

This is the first concrete archetype (Ti/Si + Ne jumper) before generalizing.

## Core Components (Minimal)

1. **Logic Tree** (one short Obsidian note or skill file)
   - Root layer: 3–5 non-negotiable principles
   - Pattern layer: observable signatures
   - Expression layer: current working version + last update reason

2. **Concept Trigger**
   - Count occurrences of a concept across outputs/notes in a rolling window (default: 3 mentions in last 10 items)
   - On threshold: promote to “active concept” list at top of logic tree
   - Next lineage line must reference how the output relates to or updates that concept

3. **Lineage Line** (one sentence appended to relevant outputs)
   Format: “This continues [signature] by [concrete way] and updates [signature] by [concrete way].”

4. **Adaptation Rules** (anti-lock-in)
   - All changes start as provisional (tagged with review window: e.g. 10 outputs or 30 days)
   - Mandatory revision proposal when an output strains 2+ patterns
   - Periodic re-inspection of accumulated lineage lines
   - Tracked concepts drop off automatically when they stop recurring

## Integration Points

- **Existential profile**: Load logic tree and active concepts into state file / judgment layer
- **Lineage**: Written by Hermes on outputs that touch project arcs, memory updates, or architecture decisions
- **CA upstream**: Later trains classifiers on introspective data to predict which unit type (concept/person/etc.) and which signatures matter for a given individual
- **Close-out ritual**: Review lineage lines and provisional items during evening crystallization

## Scope Guardrails

- Keep the tree under 5 roots and the tracked list under 8 items
- No scoring models or free-energy calculations in v1
- Human approves every root/pattern change
- Generalization (other cognitive stacks) happens by parameterizing the trigger unit and loading different trees, not by pre-mapping all archetypes

## First Concrete Steps

1. Draft the initial 5 roots from current known patterns (inspect-first, name-the-operator, directional forecasting, explicit lineage, collapse to simplest working structure).
2. Add the lineage-line instruction to the governing skill or existential prompt.
3. Test on next 3–5 outputs that extend the cognitive assistant work.
4. Capture results in lineage lines and review at next close-out.

This spec is the artifact. When ready, load it and begin with step 1.