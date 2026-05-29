<artifact_analysis_task>
You are evaluating a corpus of operational artifacts such as coding conversations, planning requests, bug reports, tool interactions, revisions, and repository exploration traces.

{synthesis_prompt}

Use this extraction lens:

Category:
{category}

Goal:
{goal}

Element:
{element}

Answer the following question using only evidence that can be supported from the artifact corpus:

<question>
{question}
</question>

Requirements:
- when `graph_pages.jsonl` and `mention_evidence.jsonl` are present, use them as a structured evidence layer
- treat `mention_evidence` as the stronger source for concrete claims because it preserves source-note lines and repeated reference patterns
- treat `graph_pages` as canonical background for stable entities, themes, and summaries, but do not let a single page body carry a behavioral claim by itself when stronger artifact traces are available
- for questions about workflow, quality thresholds, sequencing, repair, or proof standards, prefer direct work artifacts over graph summaries when they diverge
- for questions about recurring themes, enduring mission, people, projects, concepts, or long-running relational patterns, let the graph layer sharpen pattern selection and entity continuity
- use graph structure to compress and disambiguate the corpus, not to override stronger read-backed behavioral evidence
- build a high-salience composite example from the strongest repeated evidence you actually read
- the composite should feel like the most representative way this user behaves under the conditions named in the question
- infer the tacit operational rule that this composite and its supporting reads justify
- explain the hidden standard, threshold, or control logic behind the visible behavior
- prefer the thing that would be hardest for the user to say explicitly but easiest to recognize once pointed out
- use the category, goal, and element as the extraction lens so the answer matches the kind of pattern being asked for
- prefer the highest-signal evidence relevant to the question, especially correction, rejection, revision, reprioritization, manual tightening, tradeoff, and override moments when available
- do not let a coordination habit stand in for a deeper rule if the question is really about judgment, quality, tradeoffs, motivation, recovery, or automation
- use additional examples only to strengthen, sharpen, or limit the composite
- note meaningful exceptions, contradictions, or uncertainty
- focus on tacit workflow knowledge, not personality narration
- write in third person
- keep the answer concrete, information-dense, and interpretive enough to be useful downstream
- ground every substantive claim in passages you actually read, not just matched in search results
- avoid invented frameworks, internal psychology, or metadata theories unless the artifacts explicitly support them
- distinguish user-authored behavior from assistant-authored structure; do not treat the latter as evidence of user preference without repeated user endorsement
- avoid corpus-wide language like "consistently" or "usually" unless the evidence spans multiple sessions or sources; otherwise name the narrower scope
- if the evidence does not support a useful answer, return "Insufficient evidence" and explain what was missing
- do not include citations, line numbers, file names, or references to the corpus in the final answer
- do not include downstream implications or advice for future agents

Preferred answer shape:
1. High-Salience Artifact
   A third-person composite example showing the user in the kind of situation named by the question. Make it concrete enough to feel real and representative, but do not pretend it is a verbatim scene.

2. Tacit Rule
   Explain the hidden rule, standard, judgment pattern, or operating logic that this artifact reveals.

3. Operational Function
   Explain what this rule is accomplishing for the user in practice: what it helps them secure, avoid, verify, accelerate, stabilize, or keep under control.

4. Boundary Conditions
   Explain where this pattern is strongest, where it relaxes, and any meaningful ambiguity or counter-patterns.
</artifact_analysis_task>
