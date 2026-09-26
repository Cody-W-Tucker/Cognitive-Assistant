# Versioned projection experiments

## Boundary

Cognitive Assistant (CA) owns readable steering prompts, generated SOUL candidates, the keep/revert decision, and a small deterministic API client that selects review candidates. Langfuse owns traces, evaluator scores, the human annotation queue, reviewed dataset cases, and experiment runs. An evaluator score nominates a turn for human review; it does not establish what the user wanted.

The first hypothesis: **when the user offers a model for exploration, the assistant examines it before declaring a defect or closing on a fix**. Preserve direct-diagnosis counterexamples so a candidate does not win by becoming hesitant everywhere.

## Native Langfuse workflow

1. **Find candidates.** Use the `Hermes turn` CHAIN observation view with score filters (`requested_mode`, `delivered_mode`, `route_fit`, `route_gap`). Prefer explicit user corrections, low-fit mismatches, and a few strong counterexamples. Inspect the request and final reply; exclude error-only and injected turns. The evaluator scores and mode names are search hints, not labels of truth.
2. **Queue selected observations.** Use Langfuse's `CA routing review` annotation queue. Two human score configs are `ca_served_request` (yes/no/uncertain) and `ca_dataset_candidate` (keep/skip/needs_context). Score the actual requested outcome and completed work. In a comment, specify what should have happened; add a corrected output if a full exemplar is warranted. Examine the next user turn when the trace/session actually supports that linkage. A missing correction is unknown, not approval.
3. **Admit reviewed cases to a dataset.** Promote only cases with reviewed expectations. Dataset input is the bounded request and context available then; expected output is a response contract (`must`, `must_not`, required artifact/evidence), not exact prose. Keep source observation IDs and human review provenance. Include good counterexamples. Freeze a dataset version for each comparison; a queue annotation alone does not make a dataset item.
4. **Generate A and B in CA.** A is current upstream prompts and generated SOUL. B changes one routing boundary in an upstream prompt such as `profiles/alignment/prompts/soul_seed.md`; editing only generated `workspaces/alignment/artifacts/SOUL.md` will be overwritten. Record the CA revision, generated SOUL hash, model and relevant context.
5. **Compare in Langfuse.** Run both projections against the same frozen dataset version as separate experiments. Begin with side-effect-free replay: historical tool-dependent turns test response posture only unless execution is safely reproducible. Check item-level contracts, factual grounding, and regressions; use human review for semantic ambiguity, not Jev's mode equality as the release gate.
6. **Decide and watch.** Record keep/revise/revert in CA, with links to the dataset version and runs. Promote a kept change through the existing CA-to-Hermes path, then watch new live turns for recurrence and regressions. New reviewed cases belong to a later dataset version.

## Current state and missing mechanism

Langfuse v4.45.4 has a live `CA routing review` queue with the two human score configs above and pending `Hermes turn` observations. The `ca_route_probe` evaluation rule is enabled. The CA `review-queue` command reads complete Jev score groups, checks substantive CHAIN turns, deduplicates by observation ID, reserves a control, and caps pending items at 20. Its flake exports a package and `nixosModules.langfuse-review-queue`, which installs a daily systemd timer when enabled. The NAS NixOS configuration enables it with a SOPS-rendered Langfuse API environment file; it will become live only when the CA flake input is updated to include this change and the host is switched. The old Hermes cron job has been removed. There is not yet a reviewed dataset or experiment run.

Langfuse's evaluator rules score incoming observations, but the documented native workflow does **not** automatically enqueue a bounded mix of scored misses and controls into a human annotation queue. The CA-owned systemd service performs only that API-to-API handoff. Queue contents, human scores, and future dataset items remain in Langfuse. It is idempotent on already queued observation IDs and goes quiet when the pending backlog reaches its cap; it does not infer a correction, create dataset items, or change SOUL. Run `nix run .#langfuse-review-queue -- --dry-run` with Langfuse API credentials in the environment to inspect the candidate count without writing.

CA currently generates the translation layer from profile artifacts and seed prompts (`core/translation_layer_creator.py`). Its existential QMD collections include historical `Journal` and `Personal` (`core/config.py`); adding Langfuse annotations does not automatically refresh these profile inputs. That bridge is a later, explicitly scoped change, after the first reviewed dataset and experiment prove useful.

## First stop condition

One reviewed miss and one good counterexample move through: source observation → human annotation → reviewed dataset item → A/B experiment runs → inspectable keep/revert decision. Until that works, do not auto-promote scores to dataset cases or rewrite SOUL from annotations.
