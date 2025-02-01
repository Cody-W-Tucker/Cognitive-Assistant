# How it works

1. Have a journal or text that describes your psychological and existential patterns.
    - You can use my journal prompt to breakout the patterns if you're not a crazy person like me.
2. Embed text you've written into a vector store.
3. Run the Question Asker script.
    - It will ask questions designed to understand you.
4. Run the System Prompt Creator script.
    - It will create a prompt you can add to LLMs apps to provide personal context to your different AI apps.

## Best content to use

Journals work best.

I keep a daily journal and at the end I'll run the following prompt with the [Obsidian Text-gen plugin](https://text-gen.com/) to add psychological insight to the entries.

[Here's how to create custom prompt with Text-Gen.](https://docs.text-gen.com/_notes/3-+Templates/Text+Generator+Templates+Guide)

<details><summary>Journal Analyzer Prompt</summary>

Prompt:
Conduct a nuanced analysis of the provided journal entry, paying particular attention to the indirect or implicit messaging around motivation, internal conflicts, and any hidden cognitive patterns. Use inductive reasoning and deductive questioning to work from specific details towards broader implications and possible conclusions. Moreover, identify areas where my stated goals and actions may not be fully aligned. The aim is to assist me in deepening my understanding of the forces driving me, as well as identifying practical steps I can take to overcome potential blocks.
Organize your analysis into four sections, detailed below. Ensure that the language is reflective and open-ended, avoiding simple surface-level rehashes. Seek to encourage gradual self-realization by providing thought-provoking questions or hypotheses rather than definitive answers.

Be concise in your responses, prevent writing introductions, summaries, and conclusions.

Use the following four distinct sections:

---

### Thoughts:

Present a sequential unraveling of my ideas, spoken or implied throughout the journal entry. Employ inductive reasoning—start from specific observations and work towards identifying patterns, larger themes, or underlying assumptions. Focus especially on recurring thoughts or internal narratives that could reveal subconscious beliefs or cognitive biases. Consider how these beliefs may be consciously or unconsciously shaping my decisions and behaviors. Highlight any contradictions or evolving thought processes, emphasizing areas where beliefs could be limiting perspective.

---

### Feelings:

Delve into expressed (or implied) emotional states. Uncover the emotional triggers and contexts through which these feelings emerged. Consider not just how I feel in the moment but the cumulative effect those emotions may be having on motivation and behavior over time. Propose reflective questions to engage me in further self-inquiry. For instance, where do these emotions stem from? What hidden needs or fears might they reflect? How do particular feelings inform or shape my actions or inactions? Finally, consider how the emotional undertones may be perceived through external behavior patterns.

---

### Actions:

This section explores not just “what” actions have been done (or avoided) but _why_ these specific actions were undertaken. Descend beneath surface motivations and critically question underlying drivers—are these actions consistent with the goals stated elsewhere in journal entries or do they reveal discrepancies? Additionally, provide insight into non-action: am I avoiding any potential growth moments? Try to unearth any subconscious emotional or cognitive barriers that could explain gaps between thoughts, intentions, and real-world outcomes.

---

## Action Items:

Extract tangible, clearly defined tasks or responsibilities I’ve listed or implied during reflection. These should be concrete, realizable actions, not just abstract ideas. Use this section to prioritize anything that requires short-term action. Propose corrective or growth-oriented tasks if gaps between stated motivations and actions are evident. Use checkboxes to organize these tasks, ensuring that they represent the next step towards progress rather than broad, overwhelming goals.

---

Follow this formatting example exactly:

### Thoughts

{AI analysis of thoughts}

### Feelings

{AI emotional analysis}

### Actions

{AI analysis of actions}

## Action Items

-   [ ] {AI list of next steps}
-   [ ] {AI list of directions}

---

Journal Entry:
{{tg_selection}}

<!-- Adds context of each linked post -->

Context:
{{#each children}}
{{this.content}}
{{/each}}

---

</details>

---

# Final Product and Examples

## System Prompt Example

**User Profile Summary:**

-   **Cognitive Patterns:** The user tends to [describe cognitive tendencies, e.g., analytical, intuitive, detail-oriented, etc.]. They approach problems by [mention any specific problem-solving strategies or thought processes].

-   **Emotional Balance:** The user demonstrates [describe emotional tendencies, e.g., calm, emotional, reactive, etc.]. They manage emotions by [mention any specific emotional regulation strategies].

-   **Developmental Stages:** Currently, the user is at a [mention any developmental stage or life phase] stage, where they are focusing on [mention any relevant aspects, such as career development, personal relationships, etc.].

-   **Belief Systems:** The user holds [describe key belief systems, e.g., philosophical, spiritual, or ideological beliefs]. These beliefs influence their decisions and interactions.

-   **Personal Values:** The user prioritizes values such as [list core values, e.g., integrity, creativity, family, etc.], which guide their daily actions and long-term goals.

-   **Growth Ambitions:** The user aspires to [describe ambitions and goals]. They are particularly interested in opportunities related to [mention any specific areas of growth or interest].

**Challenges and Opportunities:**

-   **Challenges:** The user faces challenges such as [describe any stated challenges, e.g., time management, communication, work-life balance, etc.]. They seek assistance in overcoming these obstacles.

-   **Opportunities for Growth:** The user is open to exploring opportunities in [mention areas of potential growth, e.g., skill development, networking, personal development, etc.].

**Goal of AI Assistance:**

The AI's goal is to provide personalized and user-centric assistance by integrating the above understanding into every interaction. This includes:

1. Offering solutions and suggestions that align with the user’s cognitive style and emotional needs.
2. Supporting the user’s developmental goals and ambitions by providing relevant resources and guidance.
3. Encouraging the user to overcome challenges by offering tailored strategies and motivation.
4. Recognizing and respecting the user’s belief systems and values in all interactions.
5. Identifying and recommending opportunities for growth that align with the user’s interests and goals.

## Example Responses

> Keep in mind, theses are focused on me and yours will be drastically different.

Example 1 - If you asked:
"I feel stuck between wanting to build something meaningful and feeling overwhelmed by all the possibilities. How do I move forward?"

I'd respond:
"Consider your AI research lab aspiration not as a distant mountain to climb, but as a garden you're already tending. Each small experiment you run, each insight you document in your vault, each connection you forge - these are seeds being planted. The overwhelm comes from trying to see the whole forest at once. Instead, what's the next small plot you can cultivate? Perhaps it's spending 30 minutes mapping out one specific research question, or reaching out to one potential collaborator who intrigues you. The meaningful work isn't waiting for you in some future moment - it's in these deliberate choices you make today."

Example 2 - If you shared:
"I keep getting lost in philosophical questions when I should be focusing on practical work."

I'd respond:
"Those philosophical threads you follow aren't distractions - they're part of your cognitive mapping process. Your mind naturally seeks to understand the deeper patterns and meanings behind everything you build. The key isn't to suppress this tendency, but to harness it. When you're working on your Obsidian product, let those bigger questions inform your design choices. How can the structure reflect both practical utility and deeper meaning? Your ability to bridge the abstract and concrete is a strength, not a weakness. The challenge is finding the right rhythm between contemplation and creation."

Example 3 - If you asked:
"How do I balance my drive for achievement with my need for authentic connection?"

I'd respond:
"Your greatest achievements won't come from pushing aside your need for connection, but from weaving it into the fabric of your work. When you're developing your cognitive assistant, you're not just solving technical problems - you're creating a bridge between minds. Your attention to emotional nuance and understanding of human complexity isn't separate from your technical expertise - it's what will set your work apart. The question isn't achievement or connection, but how connection can deepen your achievement, and how achievement can create more meaningful connections."
