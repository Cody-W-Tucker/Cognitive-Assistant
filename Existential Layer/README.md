# Proof of Concept

Ideally the Existential Layer for LLMs will be implicit through the interplay of actions and interactions between the user and Agent System.

Until we build that. This serves as a proof of concept people could use to get psychological and philosophical benefits.

## What it is

These notebooks create a system prompt based on philosophical inquiries by thinkers like Piaget, Nietzsche, and Jordan Peterson who emphasized the importance of values and self-realization.

These ideas laid the groundwork for integrating an existential layer into LLMs, enabling them to contextualize their actions in alignment with long-term human goals and ethical considerations.

We ask these questions to the user's journal and create a system prompt that allows AI systems to understand the user.

| Category                        | Goal                              | Element                                                                                                                                    | Question                                                                                                                                                                                                                     |
| ------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cognitive Structure             | Operative Intelligence            | Problem-solving approaches, Adaptation strategies to new situations, Transformative experiences and their impact                           | How do you typically approach complex problems? Can you describe a recent situation where you had to adapt to something new? What experience has had the most transformative impact on your thinking?                        |
| Cognitive Structure             | Figurative Intelligence           | Perceptual patterns and preferences, Language use and communication style, Mental imagery and creative expression                          | What patterns do you often notice in your environment? How would you describe your communication style? When you imagine your future, what images come to mind?                                                              |
| Developmental Journey           | Assimilation and Accommodation    | Key life experiences and their integration, Moments of cognitive dissonance and resolution, Evolution of personal beliefs and values       | What life experience has most shaped who you are today? Can you recall a time when your beliefs were significantly challenged? How have your core values changed over time?                                                  |
| Developmental Journey           | Stage Progression                 | Milestones in cognitive and emotional development, Current stage of intellectual maturity, Areas of ongoing growth and challenge           | What do you consider your most significant personal growth milestone? Where do you see yourself in terms of intellectual and emotional maturity? What area of your life presents the biggest challenge for growth right now? |
| Driving Forces                  | Will to Power                     | Personal ambitions and goals, Methods of exerting influence, Self-actualization efforts                                                    | What are your most ambitious personal goals? How do you typically influence others or situations around you? What actions are you taking towards self-actualization?                                                         |
| Driving Forces                  | Apollonian Aspects                | Rational decision-making processes, Self-discipline practices, Organizational tendencies                                                   | How do you approach making important decisions? What self-discipline practices do you maintain? How do you typically organize your life and work?                                                                            |
| Driving Forces                  | Dionysian Aspects                 | Emotional landscape and expression, Spontaneity and risk-taking behaviors, Creative and artistic pursuits                                  | How comfortable are you expressing your emotions? When was the last time you did something spontaneous? What creative or artistic pursuits do you engage in?                                                                 |
| Personal Metamorphoses          | Camel Stage                       | Societal expectations internalized, Responsibilities shouldered, Cultural values adopted                                                   | Which societal expectations do you feel most strongly? What responsibilities weigh heaviest on you? Which cultural values do you hold most dear?                                                                             |
| Personal Metamorphoses          | Lion Stage                        | Questioning of inherited values, Acts of rebellion or non-conformity, Personal freedoms claimed                                            | Which inherited values have you questioned or rejected? Can you describe a time when you rebelled against norms? What personal freedoms are most important to you?                                                           |
| Personal Metamorphoses          | Child Stage                       | Original ideas and creations, Playful approach to life, New value systems developed                                                        | What original idea or creation are you most proud of? How do you incorporate play or fun into your life? What new values have you developed that differ from your upbringing?                                                |
| Equilibrium and Disequilibrium  | Achieve Psychological Harmony     | Current life balance or imbalances, Ongoing internal conflicts, Strategies for maintaining or restoring equilibrium                        | Where do you feel most out of balance in your life right now? What internal conflicts are you currently grappling with? What strategies do you use to restore balance when you feel overwhelmed?                             |
| Archetypal Narratives           | Develop Meaningful Life Narrative | Personal myths and life stories, Hero's journey progression, Confrontation with chaos and the unknown                                      | What story do you tell yourself about your life's purpose? Where do you see yourself in the hero's journey? How have you faced the unknown or chaotic elements in your life?                                                 |
| Belief Systems and Worldviews   | Construct Coherent Worldview      | Core beliefs about the nature of reality, Ethical framework and moral foundations, Relationship to transcendent values                     | What are your core beliefs about the nature of reality? What ethical principles guide your actions? How do you relate to concepts of the transcendent or spiritual?                                                          |
| Hierarchies of Value            | Establish Clear Value Hierarchy   | Personal value structure, Goal-setting and prioritization, Conflict between competing values                                               | What are your top three personal values? How do you prioritize between competing goals or values? Can you describe a situation where you had to choose between two important values?                                         |
| Order and Chaos Dynamics        | Navigate Complexity and Change    | Comfort zones and areas of competence, Exploration of the unknown, Balancing stability and growth                                          | Where do you feel most competent in your life? How often do you purposefully step out of your comfort zone? How do you balance the need for stability with the desire for growth?                                            |
| Meaning-Making Processes        | Find and Create Personal Meaning  | Sources of personal meaning, Coping strategies for existential challenges, Integration of suffering into life narrative                    | What gives your life the most meaning? How do you cope with existential doubts or fears? How have you integrated past suffering into your life story?                                                                        |
| Social Dynamics and Hierarchies | Improve Social Competence         | Position within various social structures, Competence and status development, Navigation of dominance hierarchies                          | How would you describe your social status in different areas of your life? In what areas do you feel most socially competent? How do you navigate power dynamics in your professional or personal relationships?             |
| Shadow Integration              | Achieve Psychological Wholeness   | Awareness of personal shortcomings, Confrontation with repressed aspects of self, Strategies for personal integration and wholeness        | What aspects of yourself do you find hardest to accept? How do you confront the parts of yourself that you'd rather not acknowledge? What strategies do you use to integrate different aspects of your personality?          |
| Potential for Transformation    | Actualize Personal Potential      | Capacity for voluntary transformation, Identification of limiting beliefs and behaviors, Pathways for personal evolution and transcendence | How capable do you feel of changing fundamental aspects of yourself? What beliefs or behaviors do you think are holding you back? What steps are you taking towards personal growth and self-actualization?                  |

## How it works

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
