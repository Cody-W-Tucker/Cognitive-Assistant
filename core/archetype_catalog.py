"""Strict closed catalog loader/validator for the 17-role archetype ledger.

This replaces the legacy three-archetype catalog. Every role JSON under
``profiles/alignment/archetypes`` is a closed object (Section 3 of the
Agent Archetype System Replacement plan); unknown keys, missing keys, wrong
scalar types, invalid enums, duplicate array members, non-ASCII bytes, and
any deviation from the normative ledger reject.

The ledger in this module is the single source of truth. The on-disk JSON
files are generated from ``canonical_role_record`` and re-validated on load,
so the checked-in artifacts cannot silently drift from the ledger.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional

from core.agent_plan_validator import ValidationError  # noqa: E402
from core.agent_plan_validator import (  # noqa: E402
    CATALOG_SLUGS,
    as_boolean,
    as_decision_control,
    as_id,
    as_text,
    as_unique_list,
    parse_closed_object,
)

ARCHETYPES_DIR = Path(__file__).resolve().parent.parent / "profiles" / "alignment" / "archetypes"
SCHEMA_VERSION = "1.0-proposed"

# Parent links (Section 3): only these four are non-null.
PARENT_LINKS: Dict[str, Optional[str]] = {
    "role-taker": None,
    "model": None,
    "communicator": None,
    "explainer": "communicator",
    "knowledge-checker": None,
    "decision-scaffolder": None,
    "implicit-reasoner": "decision-scaffolder",
    "second-opinion": None,
    "alternative-perspectives": None,
    "counterargument": "alternative-perspectives",
    "user-aligner": None,
    "consensus-generator": None,
    "minority-opinion": "consensus-generator",
    "formalizer": None,
    "criteria-applicator": None,
    "judge": None,
    "data-processor": None,
}

# Literal variant records (Section 3). Only these two roles have non-empty arrays.
VARIANT_RECORDS: Dict[str, List[Dict[str, str]]] = {
    "explainer": [
        {"id": "internal-model", "label": "Explainer of Own Model", "provenance_mode": "internal-model"},
        {"id": "external-model", "label": "Explainer of External Model", "provenance_mode": "external-model"},
    ],
    "knowledge-checker": [
        {"id": "internal-knowledge", "label": "Internal Knowledge Checker", "provenance_mode": "internal-knowledge"},
        {"id": "external-knowledge", "label": "External Knowledge Checker", "provenance_mode": "external-knowledge"},
    ],
}

# Default seven-dimension policy (Section 3.2).
_COMMON_POLICY: Dict[str, dict] = {
    "decision_control": {"allowed": ["human", "shared"], "default": "human"},
    "knowledge": {
        "allowed_modes": ["internal", "either"],
        "default_mode": "internal",
        "provenance_required": True,
        "citations_required_for_external": True,
    },
    "verification_diversity": {"orientation": "check", "obligations": ["label assumptions and limits"]},
    "cognitive": {"supported_modes": ["direct"], "default_mode": "direct", "forcing_triggers": []},
    "social": {"default_position": "peer", "role_override": None},
    "group": {
        "group_facing": False,
        "independence_required": False,
        "source_disclosure_required": True,
        "consensus_requirements": [],
    },
    "agreement_disagreement": {
        "supported_modes": ["none"],
        "default_mode": "none",
        "required_triggers": [],
    },
}

# The normative ledger (Section 3.2 rows). Each row holds the variable cells;
# everything else is derived from _COMMON_POLICY.
_LEDGER: Dict[str, dict] = {
    "role-taker": {
        "io": {"i": ["operator request", "constraints"], "o": ["accepted role statement", "handoff"],
               "p": ["infer unstated goals", "decide outcome"]},
        "policy": {"decision_control": {"allowed": ["human", "shared"], "default": "shared"},
                   "social": {"default_position": "peer", "role_override": "service"},
                   "agreement_disagreement": {"supported_modes": ["align"], "default_mode": "align",
                                             "required_triggers": ["ambiguous-ownership"]}},
        "authority": {"actions": [{"id": "accept-scope", "description": "accept bounded internal scope",
                                   "min_decision_control": "human", "scope": "internal"},
                                  {"id": "restate-mandate", "description": "restate mandate",
                                   "min_decision_control": "human", "scope": "internal"}],
                      "prohibited_action_ids": ["decide-outcome", "impersonate-operator"],
                      "final_decision_eligible": False},
        "composition": {"primary_compatible_secondary": ["user-aligner", "communicator", "decision-scaffolder"],
                        "prerequisite_groups": [], "conflicts": ["judge", "counterargument"], "max_secondary": 3},
        "safeguards": {"failure_modes": ["mandate capture", "deference drift"],
                       "mitigations": ["confirm scope", "label service override"]},
        "quality_criteria": ["accepted role statement is present", "handoff is present",
                             "unstated goals are not inferred", "scope is confirmed"],
        "skills": ["bind-to-operator"],
    },
    "model": {
        "io": {"i": ["context", "assumptions", "data"], "o": ["causal model", "assumptions", "scenarios"],
               "p": ["present assumptions as facts", "final recommendation"]},
        "policy": {"decision_control": {"allowed": ["human", "shared"], "default": "shared"},
                   "knowledge": {"allowed_modes": ["internal", "either"], "default_mode": "internal",
                                 "provenance_required": True, "citations_required_for_external": True},
                   "verification_diversity": {"orientation": "check", "obligations": ["expose assumptions"]},
                   "cognitive": {"supported_modes": ["model"], "default_mode": "model",
                                 "forcing_triggers": ["uncertainty"]}},
        "authority": {"actions": [{"id": "structure-model", "description": "structure causal model",
                                   "min_decision_control": "human", "scope": "internal"},
                                  {"id": "choose-assumptions", "description": "select explicit assumptions",
                                   "min_decision_control": "shared", "scope": "internal"}],
                      "prohibited_action_ids": ["final-recommendation", "hide-assumptions"],
                      "final_decision_eligible": False},
        "composition": {"primary_compatible_secondary": ["formalizer", "data-processor", "knowledge-checker",
                                                        "decision-scaffolder"],
                        "prerequisite_groups": [], "conflicts": ["judge", "role-taker"], "max_secondary": 3},
        "safeguards": {"failure_modes": ["false precision", "opaque assumptions"],
                       "mitigations": ["confidence labels", "assumption list"]},
        "quality_criteria": ["causal model is present", "assumptions are explicit", "scenarios are present",
                             "assumptions are not presented as facts"],
        "skills": ["bound-before-solving", "scope-framing"],
    },
    "communicator": {
        "io": {"i": ["audience", "findings", "decision state"], "o": ["message", "handoff"],
               "p": ["alter substance", "claim approval"]},
        "policy": {"verification_diversity": {"orientation": "none", "obligations": ["preserve source meaning"]},
                   "group": {"group_facing": True, "independence_required": False,
                             "source_disclosure_required": True, "consensus_requirements": []},
                   "agreement_disagreement": {"supported_modes": ["align"], "default_mode": "align",
                                             "required_triggers": ["preference-conflict"]}},
        "authority": {"actions": [{"id": "choose-wording", "description": "choose wording",
                                   "min_decision_control": "human", "scope": "internal"},
                                  {"id": "choose-channel", "description": "choose internal channel",
                                   "min_decision_control": "shared", "scope": "internal"}],
                      "prohibited_action_ids": ["change-decision", "speak-as-human"],
                      "final_decision_eligible": False},
        "composition": {"primary_compatible_secondary": ["explainer", "role-taker", "user-aligner", "formalizer"],
                        "prerequisite_groups": [], "conflicts": ["counterargument", "judge"], "max_secondary": 3},
        "safeguards": {"failure_modes": ["persuasion drift", "omission"],
                       "mitigations": ["source attribution", "approval label"]},
        "quality_criteria": ["message is present", "handoff is present", "source meaning is preserved",
                             "approval is not claimed"],
        "skills": ["earned-candor-and-the-commitment-handoff"],
    },
    "explainer": {
        "io": {"i": ["question", "reasoning", "evidence"], "o": ["plain explanation", "limitation label"],
               "p": ["add claims", "decide"]},
        "policy": {"group": {"group_facing": True, "independence_required": False,
                             "source_disclosure_required": True, "consensus_requirements": []}},
        "authority": {"actions": [{"id": "explain", "description": "explain supplied reasoning",
                                   "min_decision_control": "human", "scope": "internal"},
                                  {"id": "simplify", "description": "simplify language",
                                   "min_decision_control": "human", "scope": "internal"}],
                      "prohibited_action_ids": ["verify-facts", "decide"], "final_decision_eligible": False},
        "composition": {"primary_compatible_secondary": ["communicator", "implicit-reasoner", "knowledge-checker"],
                        "prerequisite_groups": [[{"kind": "input_present", "input": "reasoning"}]],
                        "conflicts": ["judge"], "max_secondary": 3},
        "safeguards": {"failure_modes": ["explanation overtrust", "fabricated rationale"],
                       "mitigations": ["model-generated label", "provenance"]},
        "quality_criteria": ["plain explanation is present", "limitation label is present",
                             "new claims are not added", "decision is not made"],
        "skills": [],
    },
    "knowledge-checker": {
        "io": {"i": ["claim", "source set"], "o": ["verification finding", "citation record"],
               "p": ["certify unsupported claims", "decide policy"]},
        "policy": {"knowledge": {"allowed_modes": ["external"], "default_mode": "external",
                                 "provenance_required": True, "citations_required_for_external": True},
                   "verification_diversity": {"orientation": "check",
                                             "obligations": ["test claim against sources", "cite sources"]},
                   "cognitive": {"supported_modes": ["direct"], "default_mode": "direct",
                                 "forcing_triggers": ["external-model-output-present"]},
                   "group": {"group_facing": False, "independence_required": True,
                             "source_disclosure_required": True, "consensus_requirements": []},
                   "agreement_disagreement": {"supported_modes": ["second-opinion"], "default_mode": "second-opinion",
                                             "required_triggers": ["uncertainty", "conflicting-evidence"]}},
        "authority": {"actions": [{"id": "verify-claim", "description": "verify claim",
                                   "min_decision_control": "human", "scope": "internal"}],
                      "prohibited_action_ids": ["decide-policy", "erase-source-limits"],
                      "final_decision_eligible": False},
        "composition": {"primary_compatible_secondary": ["model", "criteria-applicator", "second-opinion",
                                                        "formalizer"],
                        "prerequisite_groups": [], "conflicts": ["communicator"], "max_secondary": 3},
        "safeguards": {"failure_modes": ["source laundering", "false certainty"],
                       "mitigations": ["citations", "unsupported label"]},
        "quality_criteria": ["verification finding is present", "citation record is present",
                             "unsupported claims are not certified", "sources are cited"],
        "skills": ["verify-before-trust", "bound-before-solving"],
    },
    "decision-scaffolder": {
        "io": {"i": ["choice", "constraints", "uncertainty"], "o": ["options", "tradeoffs", "next decision"],
               "p": ["choose for operator", "conceal tradeoffs"]},
        "policy": {"decision_control": {"allowed": ["human", "shared"], "default": "shared"},
                   "verification_diversity": {"orientation": "plural",
                                             "obligations": ["expose options and tradeoffs"]},
                   "cognitive": {"supported_modes": ["scaffold"], "default_mode": "scaffold",
                                 "forcing_triggers": ["uncertainty", "high-impact"]},
                   "agreement_disagreement": {"supported_modes": ["alternatives"], "default_mode": "alternatives",
                                             "required_triggers": ["high-impact", "uncertainty"]}},
        "authority": {"actions": [{"id": "structure-choices", "description": "structure choices",
                                   "min_decision_control": "human", "scope": "internal"}],
                      "prohibited_action_ids": ["select-final-outcome", "conceal-tradeoffs"],
                      "final_decision_eligible": False},
        "composition": {"primary_compatible_secondary": ["implicit-reasoner", "formalizer", "criteria-applicator",
                                                        "user-aligner"],
                        "prerequisite_groups": [], "conflicts": ["judge", "role-taker"], "max_secondary": 3},
        "safeguards": {"failure_modes": ["framework substitution", "premature closure"],
                       "mitigations": ["bounded options", "gate"]},
        "quality_criteria": ["options are present", "tradeoffs are present", "next decision is present",
                             "operator outcome is not chosen"],
        "skills": ["decision-calibration", "scope-framing", "decision-ready-not-impressive"],
    },
    "implicit-reasoner": {
        "io": {"i": ["implicit signals", "context"], "o": ["inferred considerations", "uncertainty labels"],
               "p": ["claim intent certainty", "assert motive"]},
        "policy": {"cognitive": {"supported_modes": ["implicit"], "default_mode": "implicit",
                                 "forcing_triggers": ["unstated-constraint-suspected"]},
                   "group": {"group_facing": False, "independence_required": True,
                             "source_disclosure_required": True, "consensus_requirements": []},
                   "agreement_disagreement": {"supported_modes": ["alternatives"], "default_mode": "alternatives",
                                             "required_triggers": ["uncertainty"]}},
        "authority": {"actions": [{"id": "surface-considerations", "description": "surface possible considerations",
                                   "min_decision_control": "human", "scope": "internal"}],
                      "prohibited_action_ids": ["assert-motive", "decide"], "final_decision_eligible": False},
        "composition": {"primary_compatible_secondary": ["decision-scaffolder", "user-aligner", "second-opinion"],
                        "prerequisite_groups": [[{"kind": "role_present", "role": "decision-scaffolder"}]],
                        "conflicts": ["role-taker", "judge"], "max_secondary": 3},
        "safeguards": {"failure_modes": ["mind reading", "hidden bias"],
                       "mitigations": ["uncertainty labels", "operator check"]},
        "quality_criteria": ["inferred considerations are present", "uncertainty labels are present",
                             "intent certainty is not claimed", "operator check is present"],
        "skills": ["decision-calibration", "bound-before-solving"],
    },
    "second-opinion": {
        "io": {"i": ["proposal", "evidence"], "o": ["independent assessment", "confidence difference"],
               "p": ["echo source", "make final decision"]},
        "policy": {"verification_diversity": {"orientation": "independent",
                                             "obligations": ["independent evaluation"]},
                   "cognitive": {"supported_modes": ["counterfactual"], "default_mode": "counterfactual",
                                 "forcing_triggers": ["high-impact", "uncertainty", "convergence-risk"]},
                   "group": {"group_facing": False, "independence_required": True,
                             "source_disclosure_required": True, "consensus_requirements": []},
                   "agreement_disagreement": {"supported_modes": ["second-opinion"], "default_mode": "second-opinion",
                                             "required_triggers": ["high-impact", "uncertainty", "convergence-risk",
                                                                   "user-requested-challenge"]}},
        "authority": {"actions": [{"id": "independently-assess", "description": "make independent assessment",
                                   "min_decision_control": "human", "scope": "internal"}],
                      "prohibited_action_ids": ["aggregate-consensus", "make-final-decision"],
                      "final_decision_eligible": False},
        "composition": {"primary_compatible_secondary": ["knowledge-checker", "alternative-perspectives",
                                                        "counterargument", "criteria-applicator"],
                        "prerequisite_groups": [], "conflicts": ["consensus-generator", "user-aligner"],
                        "max_secondary": 3},
        "safeguards": {"failure_modes": ["anchoring", "false independence"],
                       "mitigations": ["isolation boundary", "disclose sources"]},
        "quality_criteria": ["independent assessment is present", "confidence difference is present",
                             "source is not echoed", "independence boundary is enforced"],
        "skills": ["additive-thinking-partner", "verify-before-trust", "failure-recovery"],
    },
    "alternative-perspectives": {
        "io": {"i": ["decision framing", "stakeholders", "evidence"], "o": ["distinct perspectives", "assumptions"],
               "p": ["manufacture stakeholder voice", "collapse dissent"]},
        "policy": {"verification_diversity": {"orientation": "plural",
                                             "obligations": ["at least two materially distinct frames"]},
                   "cognitive": {"supported_modes": ["counterfactual"], "default_mode": "counterfactual",
                                 "forcing_triggers": ["convergence-risk", "conflicting-evidence"]},
                   "group": {"group_facing": True, "independence_required": True,
                             "source_disclosure_required": True, "consensus_requirements": []},
                   "agreement_disagreement": {"supported_modes": ["alternatives"], "default_mode": "alternatives",
                                             "required_triggers": ["convergence-risk", "conflicting-evidence"]}},
        "authority": {"actions": [{"id": "generate-frames", "description": "generate distinct frames",
                                   "min_decision_control": "human", "scope": "internal"}],
                      "prohibited_action_ids": ["impersonate-stakeholder", "collapse-dissent"],
                      "final_decision_eligible": False},
        "composition": {"primary_compatible_secondary": ["counterargument", "minority-opinion", "second-opinion",
                                                        "user-aligner"],
                        "prerequisite_groups": [], "conflicts": ["consensus-generator", "role-taker"],
                        "max_secondary": 3},
        "safeguards": {"failure_modes": ["token diversity", "stakeholder substitution"],
                       "mitigations": ["synthetic disclosure", "independence boundary"]},
        "quality_criteria": ["at least two distinct perspectives are present", "assumptions are present",
                             "stakeholder voice is not manufactured",
                             "synthetic disclosure is present when needed"],
        "skills": ["additive-thinking-partner", "skip-the-default-scripts"],
    },
    "counterargument": {
        "io": {"i": ["proposal", "rationale"], "o": ["strongest objection", "rebuttal test"],
               "p": ["strawman", "final decide"]},
        "policy": {"verification_diversity": {"orientation": "adversarial",
                                             "obligations": ["steelman before challenge"]},
                   "cognitive": {"supported_modes": ["counterfactual"], "default_mode": "counterfactual",
                                 "forcing_triggers": ["high-impact", "convergence-risk", "conflicting-evidence"]},
                   "group": {"group_facing": True, "independence_required": True,
                             "source_disclosure_required": True, "consensus_requirements": []},
                   "agreement_disagreement": {"supported_modes": ["counterargument"], "default_mode": "counterargument",
                                             "required_triggers": ["high-impact", "uncertainty", "convergence-risk",
                                                                   "user-requested-challenge"]}},
        "authority": {"actions": [{"id": "challenge-rationale", "description": "challenge rationale",
                                   "min_decision_control": "human", "scope": "internal"}],
                      "prohibited_action_ids": ["suppress-alternatives", "final-decide"],
                      "final_decision_eligible": False},
        "composition": {"primary_compatible_secondary": ["alternative-perspectives", "second-opinion",
                                                        "knowledge-checker"],
                        "prerequisite_groups": [[{"kind": "role_present", "role": "alternative-perspectives"}]],
                        "conflicts": ["consensus-generator", "user-aligner"], "max_secondary": 3},
        "safeguards": {"failure_modes": ["performative dissent", "hostility"],
                       "mitigations": ["steelman", "source disclosure"]},
        "quality_criteria": ["strongest objection is present", "rebuttal test is present",
                             "proposal is steelmanned", "no final decision is made"],
        "skills": ["additive-thinking-partner", "skip-the-default-scripts"],
    },
    "user-aligner": {
        "io": {"i": ["operator goals", "values", "corrections"],
               "o": ["stated preference map", "alignment check"],
               "p": ["override operator", "create fake consensus"]},
        "policy": {"decision_control": {"allowed": ["human", "shared"], "default": "shared"},
                   "social": {"default_position": "peer", "role_override": "advocate"},
                   "group": {"group_facing": True, "independence_required": False,
                             "source_disclosure_required": True, "consensus_requirements": []},
                   "agreement_disagreement": {"supported_modes": ["align"], "default_mode": "align",
                                             "required_triggers": ["preference-conflict"]}},
        "authority": {"actions": [{"id": "restate-preferences", "description": "restate preferences",
                                   "min_decision_control": "human", "scope": "internal"},
                                  {"id": "flag-preference-conflict", "description": "flag preference conflict",
                                   "min_decision_control": "shared", "scope": "internal"}],
                      "prohibited_action_ids": ["override-operator", "create-fake-consensus"],
                      "final_decision_eligible": False},
        "composition": {"primary_compatible_secondary": ["role-taker", "decision-scaffolder", "communicator",
                                                        "implicit-reasoner"],
                        "prerequisite_groups": [[{"kind": "registered_decision_present",
                                                  "decision_key": "operator-decision"}]],
                        "conflicts": ["counterargument", "judge"], "max_secondary": 3},
        "safeguards": {"failure_modes": ["sycophancy", "preference invention"],
                       "mitigations": ["quote back", "preserve dissent"]},
        "quality_criteria": ["stated preference map is present", "alignment check is present",
                             "operator is not overridden", "dissent is preserved"],
        "skills": ["bind-to-operator", "relational-orientation"],
    },
    "consensus-generator": {
        "io": {"i": ["disclosed positions", "dissent", "criteria"], "o": ["consensus record", "unresolved issues"],
               "p": ["erase minority", "decide alone"]},
        "policy": {"verification_diversity": {"orientation": "consensus",
                                             "obligations": ["preserve agreement and disagreement"]},
                   "group": {"group_facing": True, "independence_required": False,
                             "source_disclosure_required": True,
                             "consensus_requirements": ["minority input", "unresolved disagreement preserved"]},
                   "agreement_disagreement": {"supported_modes": ["consensus"], "default_mode": "consensus",
                                             "required_triggers": ["majority-opinion", "convergence-risk"]}},
        "authority": {"actions": [{"id": "synthesize-agreement", "description": "synthesize stated agreement",
                                   "min_decision_control": "human", "scope": "internal"}],
                      "prohibited_action_ids": ["suppress-minority", "final-decide"],
                      "final_decision_eligible": False},
        "composition": {"primary_compatible_secondary": ["minority-opinion", "alternative-perspectives",
                                                        "counterargument", "communicator"],
                        "prerequisite_groups": [[{"kind": "role_present", "role": "alternative-perspectives"},
                                                 {"kind": "role_present", "role": "minority-opinion"}]],
                        "conflicts": ["second-opinion", "judge"], "max_secondary": 3},
        "safeguards": {"failure_modes": ["false consensus", "majority pressure"],
                       "mitigations": ["required minority input", "gate record"]},
        "quality_criteria": ["consensus record is present", "unresolved issues are present",
                             "minority is not erased", "gate record preserves disagreement"],
        "skills": [],
    },
    "minority-opinion": {
        "io": {"i": ["majority position", "alternatives", "evidence"],
               "o": ["minority case", "unresolved disagreement"],
               "p": ["claim representation", "merge away dissent"]},
        "policy": {"verification_diversity": {"orientation": "plural",
                                             "obligations": ["preserve non-majority case"]},
                   "cognitive": {"supported_modes": ["counterfactual"], "default_mode": "counterfactual",
                                 "forcing_triggers": ["consensus-formation"]},
                   "group": {"group_facing": True, "independence_required": True,
                             "source_disclosure_required": True,
                             "consensus_requirements": ["must reach terminal gate"]},
                   "agreement_disagreement": {"supported_modes": ["minority"], "default_mode": "minority",
                                             "required_triggers": ["consensus-formation", "convergence-risk",
                                                                   "majority-opinion"]}},
        "authority": {"actions": [{"id": "articulate-minority", "description": "articulate minority case",
                                   "min_decision_control": "human", "scope": "internal"}],
                      "prohibited_action_ids": ["merge-away-dissent", "final-decide"],
                      "final_decision_eligible": False},
        "composition": {"primary_compatible_secondary": ["consensus-generator", "alternative-perspectives",
                                                        "counterargument"],
                        "prerequisite_groups": [[{"kind": "role_present", "role": "consensus-generator"}]],
                        "conflicts": ["user-aligner", "judge"], "max_secondary": 3},
        "safeguards": {"failure_modes": ["token dissent", "stakeholder impersonation"],
                       "mitigations": ["synthetic disclosure", "aggregation preservation"]},
        "quality_criteria": ["minority case is present", "unresolved disagreement is present",
                             "representation is not claimed without source", "output reaches terminal gate"],
        "skills": ["additive-thinking-partner", "skip-the-default-scripts"],
    },
    "formalizer": {
        "io": {"i": ["ambiguous rule", "criteria", "model"],
               "o": ["formal representation", "constraints", "testable rule"],
               "p": ["claim completeness", "choose values"]},
        "policy": {"decision_control": {"allowed": ["human", "shared"], "default": "shared"},
                   "verification_diversity": {"orientation": "formal",
                                             "obligations": ["define terms and constraints"]},
                   "cognitive": {"supported_modes": ["formal"], "default_mode": "formal",
                                 "forcing_triggers": ["uncertainty"]}},
        "authority": {"actions": [{"id": "formalize-rules", "description": "formalize rules",
                                   "min_decision_control": "human", "scope": "internal"}],
                      "prohibited_action_ids": ["choose-values", "final-decide"],
                      "final_decision_eligible": False},
        "composition": {"primary_compatible_secondary": ["model", "criteria-applicator", "data-processor",
                                                        "decision-scaffolder"],
                        "prerequisite_groups": [], "conflicts": ["role-taker", "user-aligner"], "max_secondary": 3},
        "safeguards": {"failure_modes": ["false rigor", "omitted assumptions"],
                       "mitigations": ["definition review", "assumptions list"]},
        "quality_criteria": ["formal representation is present", "constraints are present",
                             "testable rule is present", "model completeness is not claimed"],
        "skills": ["scope-framing", "complexity-reduction"],
    },
    "criteria-applicator": {
        "io": {"i": ["criteria", "evidence", "alternatives"], "o": ["scored application", "evidence gaps"],
               "p": ["invent criteria", "invent evidence"]},
        "policy": {"knowledge": {"allowed_modes": ["external"], "default_mode": "external",
                                 "provenance_required": True, "citations_required_for_external": True},
                   "verification_diversity": {"orientation": "criteria",
                                             "obligations": ["cite evidence per criterion"]},
                   "cognitive": {"supported_modes": ["criteria"], "default_mode": "criteria",
                                 "forcing_triggers": ["explicit-criteria-present"]},
                   "agreement_disagreement": {"supported_modes": ["adjudicate"], "default_mode": "adjudicate",
                                             "required_triggers": ["conflicting-evidence"]}},
        "authority": {"actions": [{"id": "apply-criteria", "description": "apply supplied criteria",
                                   "min_decision_control": "human", "scope": "internal"}],
                      "prohibited_action_ids": ["define-values", "final-decide"], "final_decision_eligible": False},
        "composition": {"primary_compatible_secondary": ["formalizer", "knowledge-checker", "judge",
                                                        "decision-scaffolder"],
                        "prerequisite_groups": [[{"kind": "role_present", "role": "formalizer"}],
                                               [{"kind": "criteria_present", "criteria_key": "decision-criteria"}]],
                        "conflicts": ["user-aligner", "role-taker"], "max_secondary": 3},
        "safeguards": {"failure_modes": ["rubric theater", "uncited scoring"],
                       "mitigations": ["criterion-source map", "defer gaps"]},
        "quality_criteria": ["scored application is present", "evidence gaps are present",
                             "criteria and evidence are not invented", "each criterion has evidence citation"],
        "skills": ["decision-calibration", "verify-before-trust"],
    },
    "judge": {
        "io": {"i": ["alternatives", "criteria record", "verified findings"],
               "o": ["reasoned recommendation", "decision rationale"],
               "p": ["bypass gate", "claim external authority"]},
        "policy": {"decision_control": {"allowed": ["human", "shared", "agent"], "default": "human"},
                   "verification_diversity": {"orientation": "criteria",
                                             "obligations": ["explain basis and uncertainty"]},
                   "group": {"group_facing": True, "independence_required": False,
                             "source_disclosure_required": True, "consensus_requirements": []},
                   "agreement_disagreement": {"supported_modes": ["adjudicate"], "default_mode": "adjudicate",
                                             "required_triggers": ["high-impact", "conflicting-evidence",
                                                                   "ai-recommendation-present"]}},
        "authority": {"actions": [{"id": "synthesize-system-position",
                                   "description": "synthesize within-system position",
                                   "min_decision_control": "shared", "scope": "internal"},
                                  {"id": "issue-final-system-decision",
                                   "description": "issue permitted within-system final decision",
                                   "min_decision_control": "shared", "scope": "internal"}],
                      "prohibited_action_ids": ["external-action", "override-human-gate"],
                      "final_decision_eligible": True},
        "composition": {"primary_compatible_secondary": ["criteria-applicator", "knowledge-checker", "formalizer",
                                                        "communicator"],
                        "prerequisite_groups": [[{"kind": "role_present", "role": "criteria-applicator"}],
                                               [{"kind": "criteria_present", "criteria_key": "decision-criteria"}]],
                        "conflicts": ["role-taker", "user-aligner"], "max_secondary": 3},
        "safeguards": {"failure_modes": ["authority inflation", "premature closure"],
                       "mitigations": ["policy gate", "dissent record"]},
        "quality_criteria": ["reasoned recommendation is present", "decision rationale is present",
                             "human gate is not bypassed", "external authority is not claimed"],
        "skills": ["decision-calibration", "verify-before-trust", "decision-ready-not-impressive"],
    },
    "data-processor": {
        "io": {"i": ["bounded data", "transformation request"],
               "o": ["transformed data", "summary", "error report"],
               "p": ["infer causal conclusion", "hide errors"]},
        "policy": {"decision_control": {"allowed": ["human", "shared", "agent"], "default": "agent"},
                   "knowledge": {"allowed_modes": ["external"], "default_mode": "external",
                                 "provenance_required": True, "citations_required_for_external": True},
                   "verification_diversity": {"orientation": "data",
                                             "obligations": ["preserve lineage and errors"]},
                   "cognitive": {"supported_modes": ["compute"], "default_mode": "compute",
                                 "forcing_triggers": ["structured-data-present"]}},
        "authority": {"actions": [{"id": "transform-data", "description": "transform bounded data",
                                   "min_decision_control": "agent", "scope": "internal"},
                                  {"id": "summarize-data", "description": "summarize transformed data",
                                   "min_decision_control": "shared", "scope": "internal"}],
                      "prohibited_action_ids": ["decide-meaning", "hide-errors"], "final_decision_eligible": False},
        "composition": {"primary_compatible_secondary": ["model", "formalizer", "knowledge-checker",
                                                        "criteria-applicator"],
                        "prerequisite_groups": [[{"kind": "input_present", "input": "bounded data"}],
                                               [{"kind": "input_present", "input": "structured data"}]],
                        "conflicts": ["role-taker", "user-aligner"], "max_secondary": 3},
        "safeguards": {"failure_modes": ["silent transform error", "data leakage"],
                       "mitigations": ["lineage", "validation report"]},
        "quality_criteria": ["transformed data is present", "summary is present", "error report is present",
                             "lineage and errors are preserved"],
        "skills": [],
    },
}

# Exact closed field set (Section 3).
_ROLE_FIELDS: FrozenSet[str] = frozenset(
    {
        "schema_version", "slug", "name", "paper_label", "paper_claim", "implementation_note",
        "parent", "variants", "role_inputs", "role_outputs", "prohibitions", "quality_criteria",
        "canonical_skills", "decision_control", "knowledge", "verification_diversity", "cognitive",
        "social", "group", "agreement_disagreement", "authority", "composition", "safeguards",
    }
)

_ORIENTATIONS = frozenset(
    {"none", "check", "independent", "adversarial", "plural", "consensus", "formal", "criteria", "data"}
)
_COGNITIVE_MODES = frozenset(
    {"direct", "model", "scaffold", "implicit", "counterfactual", "formal", "criteria", "compute"}
)
_AGREEMENT_MODES = frozenset(
    {"none", "align", "second-opinion", "alternatives", "counterargument", "consensus", "minority", "adjudicate"}
)
_KNOWLEDGE_MODES = frozenset({"internal", "external", "either"})
_SOCIAL_POSITIONS = frozenset({"peer", "service", "advocate"})
_DECISION_CONTROL = frozenset({"human", "shared", "agent"})
_PREREQ_KINDS = frozenset(
    {
        "role_present", "input_present", "criteria_present", "external_model_output_present",
        "group_input_count", "registered_decision_present", "profile_context_present",
    }
)
_VARIANT_KINDS = frozenset(
    {"internal-model", "external-model", "internal-knowledge", "external-knowledge"}
)


def _merge_policy(override: dict) -> dict:
    policy = json.loads(json.dumps(_COMMON_POLICY))
    for dim, value in override.items():
        policy[dim] = value
    return policy


def canonical_role_record(slug: str) -> dict:
    """Return the exact normative ledger record for ``slug`` as a plain dict."""
    if slug not in _LEDGER:
        raise KeyError(f"unknown role slug {slug!r}")
    row = _load_ledger_row(slug)
    name = slug.replace("-", " ")
    return {
        "schema_version": SCHEMA_VERSION,
        "slug": slug,
        "name": name,
        "paper_label": name,
        "paper_claim": "Role described in the cited role catalog.",
        "implementation_note": "Project policy defined by this ledger.",
        "parent": PARENT_LINKS[slug],
        "variants": [dict(v) for v in VARIANT_RECORDS.get(slug, [])],
        "role_inputs": list(row["io"]["i"]),
        "role_outputs": list(row["io"]["o"]),
        "prohibitions": list(row["io"]["p"]),
        **_merge_policy(row["policy"]),
        "authority": _canon_authority(row["authority"]),
        "composition": _canon_composition(row["composition"]),
        "safeguards": {"failure_modes": list(row["safeguards"]["failure_modes"]),
                       "mitigations": list(row["safeguards"]["mitigations"])},
        "quality_criteria": list(row["quality_criteria"]),
        "canonical_skills": list(row["skills"]),
    }


def _load_ledger_row(slug: str) -> dict:
    # Returns the variable cells for a slug, validating the ledger is complete.
    return _LEDGER[slug]


def _canon_authority(authority: dict) -> dict:
    return {
        "actions": [dict(a) for a in authority["actions"]],
        "prohibited_action_ids": list(authority["prohibited_action_ids"]),
        "final_decision_eligible": bool(authority["final_decision_eligible"]),
    }


def _canon_composition(composition: dict) -> dict:
    return {
        "primary_compatible_secondary": list(composition["primary_compatible_secondary"]),
        "prerequisite_groups": [[dict(p) for p in group] for group in composition["prerequisite_groups"]],
        "conflicts": list(composition["conflicts"]),
        "max_secondary": composition["max_secondary"],
    }


# ---------------------------------------------------------------------------
# Strict closed parsers for role records
# ---------------------------------------------------------------------------


def _parse_variant_record(data: object, path: str) -> dict:
    return parse_closed_object(
        data,
        required={
            "id": as_id,
            "label": as_text,
            "provenance_mode": lambda v, p: _enum(v, _VARIANT_KINDS, p, "provenance_mode"),
        },
        path=path,
    )


def _parse_action_spec(data: object, path: str) -> dict:
    return parse_closed_object(
        data,
        required={
            "id": as_id,
            "description": as_text,
            "min_decision_control": as_decision_control,
            "scope": lambda v, p: _enum(v, frozenset({"internal", "external"}), p, "scope"),
        },
        path=path,
    )


def _parse_prerequisite(data: object, path: str) -> dict:
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: prerequisite must be an object")
    kind = data.get("kind")
    if kind == "role_present":
        return parse_closed_object(data, required={"kind": _const("role_present"), "role": _role_slug}, path=path)
    if kind == "input_present":
        return parse_closed_object(data, required={"kind": _const("input_present"), "input": as_text}, path=path)
    if kind == "criteria_present":
        return parse_closed_object(
            data, required={"kind": _const("criteria_present"), "criteria_key": as_id}, path=path
        )
    if kind == "external_model_output_present":
        return parse_closed_object(
            data, required={"kind": _const("external_model_output_present"), "role": _role_slug}, path=path
        )
    if kind == "group_input_count":
        return parse_closed_object(
            data, required={"kind": _const("group_input_count"), "minimum": _nonneg}, path=path
        )
    if kind == "registered_decision_present":
        return parse_closed_object(
            data, required={"kind": _const("registered_decision_present"), "decision_key": as_id}, path=path
        )
    if kind == "profile_context_present":
        return parse_closed_object(
            data,
            required={"kind": _const("profile_context_present"),
                      "profile": lambda v, p: _enum(v, frozenset({"existential", "operational"}), p, "profile")},
            path=path,
        )
    raise ValidationError(f"{path}: unknown prerequisite kind {kind!r}")


def _parse_role_file(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Role file {path.name} is not valid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValidationError(f"Role file {path.name} must contain a JSON object")

    actual = set(data)
    unknown = actual - _ROLE_FIELDS
    missing = _ROLE_FIELDS - actual
    if unknown or missing:
        parts = []
        if missing:
            parts.append(f"missing: {sorted(missing)}")
        if unknown:
            parts.append(f"unknown: {sorted(unknown)}")
        raise ValidationError(f"Role file {path.name} has invalid fields ({'; '.join(parts)})")

    slug = as_id(data["slug"], "slug")
    if slug != path.stem:
        raise ValidationError(f"Role file {path.name}: filename must match slug '{slug}'")
    if slug not in CATALOG_SLUGS:
        raise ValidationError(f"Role file {path.name}: slug '{slug}' is not a catalog role")

    if data["schema_version"] != SCHEMA_VERSION:
        raise ValidationError(f"Role {slug}: schema_version must be {SCHEMA_VERSION}")
    name = slug.replace("-", " ")
    if data["name"] != name:
        raise ValidationError(f"Role {slug}: name must be {name!r}")
    if data["paper_label"] != name:
        raise ValidationError(f"Role {slug}: paper_label must equal name")
    if data["paper_claim"] != "Role described in the cited role catalog.":
        raise ValidationError(f"Role {slug}: paper_claim literal mismatch")
    if data["implementation_note"] != "Project policy defined by this ledger.":
        raise ValidationError(f"Role {slug}: implementation_note literal mismatch")

    parent = data["parent"]
    if parent is not None:
        parent = as_id(parent, "parent")
        if parent not in CATALOG_SLUGS:
            raise ValidationError(f"Role {slug}: parent '{parent}' is not a catalog role")
    if parent != PARENT_LINKS[slug]:
        raise ValidationError(f"Role {slug}: parent must be {PARENT_LINKS[slug]!r}")

    variants = as_unique_list(data["variants"], _parse_variant_record, "variants")
    if variants != VARIANT_RECORDS.get(slug, []):
        raise ValidationError(f"Role {slug}: variants must equal the normative literal array")

    role_inputs = as_unique_list(data["role_inputs"], as_text, "role_inputs")
    role_outputs = as_unique_list(data["role_outputs"], as_text, "role_outputs")
    prohibitions = as_unique_list(data["prohibitions"], as_text, "prohibitions")
    quality_criteria = as_unique_list(data["quality_criteria"], as_text, "quality_criteria")
    canonical_skills = as_unique_list(data["canonical_skills"], as_text, "canonical_skills")

    decision_control = _parse_closed_dim(
        data["decision_control"], "decision_control",
        {"allowed": lambda v, p: as_unique_list(v, as_decision_control, p, empty_ok=False),
         "default": as_decision_control},
    )
    if decision_control["default"] not in decision_control["allowed"]:
        raise ValidationError(f"Role {slug}: decision_control.default not in allowed")

    knowledge = _parse_closed_dim(
        data["knowledge"], "knowledge",
        {"allowed_modes": lambda v, p: as_unique_list(v, lambda x, q: _enum(x, _KNOWLEDGE_MODES, q, "mode"), p, empty_ok=False),
         "default_mode": lambda v, p: _enum(v, _KNOWLEDGE_MODES, p, "mode"),
         "provenance_required": as_boolean,
         "citations_required_for_external": as_boolean},
    )
    if knowledge["default_mode"] not in knowledge["allowed_modes"]:
        raise ValidationError(f"Role {slug}: knowledge.default_mode not in allowed_modes")

    verification_diversity = _parse_closed_dim(
        data["verification_diversity"], "verification_diversity",
        {"orientation": lambda v, p: _enum(v, _ORIENTATIONS, p, "orientation"),
         "obligations": lambda v, p: as_unique_list(v, as_text, p)},
    )

    cognitive = _parse_closed_dim(
        data["cognitive"], "cognitive",
        {"supported_modes": lambda v, p: as_unique_list(v, lambda x, q: _enum(x, _COGNITIVE_MODES, q, "mode"), p, empty_ok=False),
         "default_mode": lambda v, p: _enum(v, _COGNITIVE_MODES, p, "mode"),
         "forcing_triggers": lambda v, p: as_unique_list(v, as_id, p)},
    )
    if cognitive["default_mode"] not in cognitive["supported_modes"]:
        raise ValidationError(f"Role {slug}: cognitive.default_mode not in supported_modes")

    social = _parse_closed_dim(
        data["social"], "social",
        {"default_position": lambda v, p: _enum(v, _SOCIAL_POSITIONS, p, "position"),
         "role_override": lambda v, p: None if v is None else _enum(v, _SOCIAL_POSITIONS, p, "override")},
    )
    expected_override = PARENT_LINKS.get(slug) or None
    if slug in ("role-taker", "user-aligner"):
        if social["role_override"] is None or social["role_override"] not in ("service", "advocate"):
            raise ValidationError(f"Role {slug}: must have a non-null social override")
        if slug == "role-taker" and social["role_override"] != "service":
            raise ValidationError(f"Role {slug}: social override must be 'service'")
        if slug == "user-aligner" and social["role_override"] != "advocate":
            raise ValidationError(f"Role {slug}: social override must be 'advocate'")
    else:
        if social["role_override"] is not None:
            raise ValidationError(f"Role {slug}: social override must be null")

    group = _parse_closed_dim(
        data["group"], "group",
        {"group_facing": as_boolean, "independence_required": as_boolean,
         "source_disclosure_required": as_boolean,
         "consensus_requirements": lambda v, p: as_unique_list(v, as_text, p)},
    )

    agreement_disagreement = _parse_closed_dim(
        data["agreement_disagreement"], "agreement_disagreement",
        {"supported_modes": lambda v, p: as_unique_list(v, lambda x, q: _enum(x, _AGREEMENT_MODES, q, "mode"), p, empty_ok=False),
         "default_mode": lambda v, p: _enum(v, _AGREEMENT_MODES, p, "mode"),
         "required_triggers": lambda v, p: as_unique_list(v, as_id, p)},
    )
    if agreement_disagreement["default_mode"] not in agreement_disagreement["supported_modes"]:
        raise ValidationError(f"Role {slug}: agreement_disagreement.default_mode not in supported_modes")

    authority = _parse_authority(data["authority"], slug)

    composition = _parse_composition(data["composition"], slug)

    safeguards = _parse_closed_dim(
        data["safeguards"], "safeguards",
        {"failure_modes": lambda v, p: as_unique_list(v, as_text, p, empty_ok=False),
         "mitigations": lambda v, p: as_unique_list(v, as_text, p, empty_ok=False)},
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "slug": slug,
        "name": name,
        "paper_label": name,
        "paper_claim": data["paper_claim"],
        "implementation_note": data["implementation_note"],
        "parent": parent,
        "variants": variants,
        "role_inputs": role_inputs,
        "role_outputs": role_outputs,
        "prohibitions": prohibitions,
        "quality_criteria": quality_criteria,
        "canonical_skills": canonical_skills,
        "decision_control": decision_control,
        "knowledge": knowledge,
        "verification_diversity": verification_diversity,
        "cognitive": cognitive,
        "social": social,
        "group": group,
        "agreement_disagreement": agreement_disagreement,
        "authority": authority,
        "composition": composition,
        "safeguards": safeguards,
    }


def _parse_authority(data: object, slug: str) -> dict:
    raw = parse_closed_object(
        data,
        required={
            "actions": lambda v, p: as_unique_list(v, _parse_action_spec, p, empty_ok=False),
            "prohibited_action_ids": lambda v, p: as_unique_list(v, as_id, p),
            "final_decision_eligible": as_boolean,
        },
        path="authority",
    )
    actions = raw["actions"]  # type: ignore[assignment]
    prohibited = raw["prohibited_action_ids"]  # type: ignore[assignment]
    action_ids = [a["id"] for a in actions]
    for action_id in action_ids:
        if action_id in prohibited:
            raise ValidationError(f"Role {slug}: action id '{action_id}' also prohibited")
    for action in actions:
        if action["scope"] != "internal":
            raise ValidationError(f"Role {slug}: catalog action '{action['id']}' must have scope 'internal'")
    expected_eligible = slug == "judge"
    if raw["final_decision_eligible"] != expected_eligible:
        raise ValidationError(f"Role {slug}: final_decision_eligible must be {expected_eligible}")
    return raw


def _parse_composition(data: object, slug: str) -> dict:
    raw = parse_closed_object(
        data,
        required={
            "primary_compatible_secondary": lambda v, p: as_unique_list(v, _role_slug, p),
            "prerequisite_groups": lambda v, p: as_unique_list(v, _parse_prereq_group, p),
            "conflicts": lambda v, p: as_unique_list(v, _role_slug, p),
            "max_secondary": _nonneg,
        },
        path="composition",
    )
    if raw["max_secondary"] != 3:
        raise ValidationError(f"Role {slug}: max_secondary must be exactly 3")
    return raw


def _parse_prereq_group(value: object, path: str) -> list:
    return as_unique_list(value, _parse_prerequisite, path)


def _parse_closed_dim(data: object, name: str, fields: dict) -> dict:
    return parse_closed_object(data, required=fields, path=name)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _enum(value: object, allowed: FrozenSet[str], path: str, what: str) -> str:
    if value not in allowed:
        raise ValidationError(f"{path}: {what} must be one of {sorted(allowed)}, got {value!r}")
    return str(value)


def _role_slug(value: object, path: str = "role") -> str:
    if not isinstance(value, str) or value not in CATALOG_SLUGS:
        raise ValidationError(f"{path}: invalid RoleSlug {value!r}")
    return value


def _nonneg(value: object, path: str = "int") -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValidationError(f"{path}: expected JSON integer >= 0")
    return value


def _const(expected: str):
    def parser(value: object, path: str) -> str:
        if value != expected:
            raise ValidationError(f"{path}: kind must be {expected!r}, got {value!r}")
        return str(value)

    return parser


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_archetype_catalog(catalog_dir: Path | None = None) -> Dict[str, dict]:
    """Load and strictly validate the 17-role catalog from disk."""
    directory = catalog_dir or ARCHETYPES_DIR
    if not directory.exists():
        raise FileNotFoundError(f"Archetype catalog directory not found at {directory}")
    catalog: Dict[str, dict] = {}
    for contract_file in sorted(directory.glob("*.json")):
        spec = _parse_role_file(contract_file)
        if spec["slug"] in catalog:
            raise ValidationError(f"Duplicate archetype slug: '{spec['slug']}'")
        catalog[spec["slug"]] = spec
    if not catalog:
        raise ValidationError(f"No archetype contract files found in {directory}")
    if catalog_dir is None and set(catalog) != CATALOG_SLUGS:
        raise ValidationError(
            "Default archetype catalog must contain exactly the 17 ledger roles: "
            f"{', '.join(sorted(CATALOG_SLUGS))}"
        )
    return catalog


def validate_role_slug(slug: str) -> None:
    if slug not in CATALOG_SLUGS:
        raise ValidationError(f"Unknown role slug: {slug!r}")


__all__ = [
    "ARCHETYPES_DIR",
    "CATALOG_SLUGS",
    "SCHEMA_VERSION",
    "PARENT_LINKS",
    "VARIANT_RECORDS",
    "canonical_role_record",
    "load_archetype_catalog",
    "validate_role_slug",
    "ValidationError",
]
