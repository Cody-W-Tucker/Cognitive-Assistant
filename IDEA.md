# The idea

We are creating a system that reads journals and extracts the projection of a
person's lead AI improvements.

That sentence describes the bootstrap. This page describes what the project is
for once the bootstrap exists, and it is the goal the plans in `plans/` are
measured against.

## The goal

The agent's guidance should be trained on whether the person actually moved,
not on how closely the agent matched a document.

In machine learning terms, the project moves from imitation learning to
reinforcement learning, with a prompt as the thing being trained.

- **Imitation (where the loop started).** The SOUL is the label. Each session
  is scored on how closely the agent matched it. A student trained this way
  can approach its teacher and never exceed it, so the bootstrap is a ceiling.
- **Reinforcement (the ideal).** The SOUL is the parameters, not the label.
  The reward comes from what happened to the person after the session: the
  thing shipped, the terms got sent, the open conversation closed, the topic
  stopped coming back. The loop can then find guidance nobody wrote down,
  including guidance that contradicts the bootstrap.

It is not gradient descent. It is a hill climb with one mutation at a time: a
model proposes a text edit, the edit is deployed, and real sessions decide
whether it survives.

## The mapping

| In this project | Machine learning equivalent |
| --- | --- |
| Bootstrap SOUL | Pretrained base weights, frozen |
| Experience records | Small adapters layered on the base |
| Compiling a generation | A checkpoint built from base plus adapters, never from the last checkpoint |
| Rebootstrap | Merging the adapters back into the base |
| One agent session | One episode |
| Gaps turned into proposed records | The mutation proposal (a textual gradient) |
| Keep or revert verdict | Accept/reject step of an online A/B test |
| The outcome judge | A learned reward model |

## What is irreplaceable

The bootstrap half (notes into a SOUL, skills and a spec) is a rigorous
version of something a person could write by hand. The runtime half is not: a
controlled experiment on one's own agent, one change at a time, judged by the
sessions that followed it. Inside the runtime, the single most consequential
element is the reward: the per-session judgment of whether the session moved
the person. Everything downstream optimizes whatever that judgment measures.

When a change competes for effort, prefer the one that makes the reward more
true, more visible to the judge, or cheaper to collect.

## Positions we hold

1. **The reward is the person's movement on real work.** Evidence comes from
   outside the transcript: later sessions on the same work, commits, journal
   notes. Agent conformity is a source of proposals, not the reward.
2. **The learner is the agent's guidance.** The person and the work mix change
   too, but only the guidance is under test.
3. **The bootstrap is a starting point.** The loop is allowed to contradict
   it. Rebootstrapping stays the person's decision.
4. **The judge is blind to the policy.** The outcome is scored without the
   SOUL or the records, so both sides of a comparison are judged by the same
   text.
5. **Rejecting regressions is a safety constraint, not the objective.** A
   kept change is not a proven improvement until the test says so.

## Where the analogy breaks, and what that demands

- **The sample is tiny.** About 16 bounded interactive sessions a week from
  one person. Every session has to count for the right generation, and the
  sample size per test comes from a power calculation, not a guess.
- **The environment is not stationary.** The mix of work changes week to
  week, and the person adapts to the agent. Verdicts are evidence, not proof.
- **The reward can be gamed.** If commits count as progress, guidance that
  produces more commits wins. The judge names what the person was trying to
  reach and cites evidence for the label; a count is never the reward.

## Plans

- `plans/feature-1.md`: make the measurement valid (credit assignment and
  evaluation hygiene).
- `plans/feature-2.md`: replace the reward (delayed, blind outcome signal),
  then backtest and set the volume.
- `plans/feature-3.md`: make proposals reward-weighted.
