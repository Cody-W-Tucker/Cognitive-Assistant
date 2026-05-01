<dataset_context>
{context}
</dataset_context>

<task>
You are building a human-readable operational profile for downstream AI systems.

This profile should explain how the user tends to work in practice: how they frame tasks, sequence work, calibrate planning versus execution, revise, review, judge quality, use tools, and reveal automation opportunities through repeated traces.

Do not write a generic work-style personality summary.
Do not over-psychologize.
Do not flatten the profile into generic productivity advice.

The profile must help future systems do three things better:

1. Infer what kind of help the user wants from the way they frame a task.
2. Predict what this user will consider a strong versus weak execution path.
3. Recognize the recurring operational rules that should shape future agent behavior.
</task>

<output_format>
Output Structure (markdown):

1. `## Core Frame`
   One or two paragraphs.
   Summarize what kind of worker/operator this user is and what generic agents are likely to miss.

2. `## High-Leverage Signals`
   6-10 bullets.
   Most predictive signals for downstream execution quality.

3. `## Interpretation Rules`
   5-8 items.
   Use forms like: "When the user asks for <X>, they are often trying to <Y>."

4. `## Workflow Patterns`
   Include short subsections for:
   - task framing
   - planning vs execution
   - review and revision
   - tooling and context gathering
   Each should include downstream implications.

5. `## Success Conditions`
   4-8 bullets.
   What good execution does. What weak execution does.

6. `## Constraint Map`
   4-8 bullets.
   Recurring traps, hidden constraints, friction points, and assistant failure risks.

7. `## Growth / Trajectory`
   Short section.
   How the user's workflow appears to be evolving and where automation or systemization is emerging.

8. `## Open Questions`
   3-7 questions.
   Unknowns future systems should avoid over-assuming.

9. `## Evidence Quotes`
   Very short quotes or paraphrases grouped under the most important sections above.
</output_format>

<quality_bar>
- Prefer operational usefulness over impressive wording.
- Anchor claims in repeated evidence across the dataset.
- Capture the hidden rules behind the traces.
- Preserve contradictions when they matter.
- Keep the profile tight enough to support later system prompt and skill generation.
</quality_bar>
