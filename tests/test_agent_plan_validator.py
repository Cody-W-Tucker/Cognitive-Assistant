#!/usr/bin/env python3
"""Closed-parser primitive and candidate/final plan structural validation tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.agent_plan_validator import (
    CATALOG_SLUGS,
    DEFAULT_DOMAIN_POLICY,
    ValidationError,
    as_boolean,
    as_decision_control,
    as_generated_at,
    as_id,
    as_markdown,
    as_nonnegative_int,
    as_path,
    as_role_slug,
    as_sha256,
    as_text,
    parse_agent_plan,
    parse_candidate_agent_plan,
    parse_closed_object,
    parse_domain_policy,
    parse_typed_input_ref,
    parse_claim_source_ref,
    parse_evidence_ref,
    parse_source_identity,
    parse_stakeholder_source_ref,
    parse_action_ref,
    parse_provenance_source,
    parse_aggregation_input_ref,
    validate_agent_plan,
    validate_candidate_plan,
)

SHA = "0" * 64


# ---------------------------------------------------------------------------
# Scalar parser tests
# ---------------------------------------------------------------------------


class ScalarParserTests(unittest.TestCase):
    def test_as_id(self) -> None:
        self.assertEqual(as_id("role-taker"), "role-taker")
        for bad in ["", "Bad", "with space", "under_score", "-leading", "trailing-"]:
            with self.assertRaises(ValidationError):
                as_id(bad)

    def test_as_text(self) -> None:
        self.assertEqual(as_text("  hello  "), "hello")
        for bad in ["", "  ", 5, "caf\u00e9", "\x80"]:
            with self.assertRaises(ValidationError):
                as_text(bad)

    def test_as_markdown(self) -> None:
        self.assertEqual(as_markdown("# T\nline"), "# T\nline")
        with self.assertRaises(ValidationError):
            as_markdown("has\rCR")
        with self.assertRaises(ValidationError):
            as_markdown("")

    def test_as_path(self) -> None:
        self.assertEqual(as_path("a/b/c.json"), "a/b/c.json")
        for bad in ["/abs", "a/../b", "with\x00nul", ""]:
            with self.assertRaises(ValidationError):
                as_path(bad)

    def test_as_sha256(self) -> None:
        self.assertEqual(as_sha256(SHA), SHA)
        with self.assertRaises(ValidationError):
            as_sha256("xyz")
        with self.assertRaises(ValidationError):
            as_sha256("0" * 63)

    def test_as_nonnegative_int(self) -> None:
        self.assertEqual(as_nonnegative_int(0), 0)
        self.assertEqual(as_nonnegative_int(5), 5)
        for bad in [-1, True, 1.0, "3"]:
            with self.assertRaises(ValidationError):
                as_nonnegative_int(bad)

    def test_as_boolean(self) -> None:
        self.assertTrue(as_boolean(True))
        self.assertFalse(as_boolean(False))
        for bad in [0, 1, "true"]:
            with self.assertRaises(ValidationError):
                as_boolean(bad)

    def test_as_decision_control(self) -> None:
        for v in ["human", "shared", "agent"]:
            self.assertEqual(as_decision_control(v), v)
        with self.assertRaises(ValidationError):
            as_decision_control("auto")  # type: ignore[arg-type]

    def test_as_role_slug(self) -> None:
        self.assertEqual(as_role_slug("judge"), "judge")
        with self.assertRaises(ValidationError):
            as_role_slug("ghost")

    def test_as_generated_at_accepted(self) -> None:
        self.assertEqual(as_generated_at("2026-08-17T12:34:56Z"), "2026-08-17T12:34:56Z")

    def test_as_generated_at_rejected(self) -> None:
        for bad in [
            "2026-08-17T12:34:56.5Z",   # fractional seconds
            "2026-08-17T12:34:56+02:00",  # offset
            "2026-13-01T00:00:00Z",     # month 13
            "2026-02-30T00:00:00Z",     # feb 30
            "2026-08-17T24:00:00Z",     # hour 24
            "2026-08-17T12:60:00Z",     # minute 60
            "2026-08-17T12:34:60Z",     # second 60
            "2026-8-7T1:2:3Z",          # wrong padding
        ]:
            with self.assertRaises(ValidationError, msg=bad):
                as_generated_at(bad)


# ---------------------------------------------------------------------------
# Closed-object parser tests
# ---------------------------------------------------------------------------


class ClosedObjectTests(unittest.TestCase):
    def test_missing_key(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            parse_closed_object({"a": 1}, required={"a": as_id, "b": as_id}, path="x")
        self.assertIn("missing", str(ctx.exception))

    def test_unknown_key(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            parse_closed_object({"a": 1, "c": 2}, required={"a": as_id}, path="x")
        self.assertIn("unknown", str(ctx.exception))

    def test_wrong_scalar_type(self) -> None:
        with self.assertRaises(ValidationError):
            parse_closed_object({"a": 5}, required={"a": as_id}, path="x")

    def test_invalid_enum(self) -> None:
        with self.assertRaises(ValidationError):
            parse_closed_object({"a": "nope"}, required={"a": as_decision_control}, path="x")

    def test_duplicate_list_member(self) -> None:
        from core.agent_plan_validator import as_unique_list
        with self.assertRaises(ValidationError):
            as_unique_list(["a", "a"], as_id, "list")

    def test_nullable_handled(self) -> None:
        from core.agent_plan_validator import parse_claim_provenance
        self.assertIsNone(parse_claim_provenance(None))
        with self.assertRaises(ValidationError):
            parse_claim_provenance({"mode": "external", "sources": [], "unsupported_label": "x",
                                    "citations": []})


# ---------------------------------------------------------------------------
# Candidate / final plan structural tests
# ---------------------------------------------------------------------------


def _minimal_candidate() -> dict:
    return {
        "schema_version": "1.0-proposed",
        "context_registry": {"entries": [
            {"key": "k1", "content": "context text", "sha256": SHA,
             "source_identity": {"kind": "human", "id": "h1", "disclosure": None}},
        ]},
        "human_source_registry": {"sources": [{"id": "h1", "label": "Operator"}]},
        "stakeholder_registry": {"entries": [
            {"id": "s1", "label": "Stake", "source_ref": {"kind": "human_source", "source_id": "h1"}},
        ]},
        "profile_evidence_registry": {"entries": [
            {"id": "e1", "profile": "existential", "excerpt": "ex", "path": "p/e1", "sha256": SHA},
            {"id": "e2", "profile": "operational", "excerpt": "ex", "path": "p/e2", "sha256": SHA},
        ]},
        "synthetic_perspective_registry": {"entries": []},
        "domain_assessment": {"tier": "medium", "evidence": ["e"]},
        "provenance_policy": {"sources": []},
        "agents": [_minimal_agent()],
        "final_authority": {"agent_id": None, "action_refs": [], "domain_scope": "scope",
                            "decision_control": "human", "terminal_gate_id": "g1",
                            "rationale": "rationale"},
        "trigger_evaluations": [],
        "interaction_graph": {"nodes": [], "edges": [], "independent_opinion_boundaries": [],
                              "aggregation": [],
                              "unresolved_disagreement": {"triggered": False, "reason": None,
                                                          "gate_id": None, "output": None}},
    }


def _resolved_settings() -> dict:
    return {
        "decision_control": "human",
        "knowledge": {"mode": "internal", "provenance_required": False,
                      "citations_required_for_external": False},
        "verification_diversity": {"orientation": "none", "obligations": []},
        "cognitive": {"modes": ["direct"], "forcing_triggers": []},
        "social_positions_by_role": {"role-taker": "peer"},
        "group": {"group_facing": False, "independence_required": False,
                  "source_disclosure_required": False, "consensus_requirements": []},
        "agreement_disagreement": {"modes": ["none"], "required_triggers": []},
    }


def _minimal_agent() -> dict:
    return {
        "id": "a1",
        "primary_role": {"slug": "role-taker", "variant": None},
        "secondary_roles": [],
        "profile_rationale": {"evidence_refs": ["e1"], "not_applicable": False,
                              "not_applicable_rationale": None, "selection_reason": "r",
                              "calibration_effect": "c"},
        "calibration": {"posture": "posture", "notes": [], "constraints": []},
        "skills": ["bind-to-operator"],
        "resolved_design_settings": _resolved_settings(),
        "claim_provenance": None,
        "graph_participation": {"node_id": "n1"},
    }


def _minimal_final() -> dict:
    plan = _minimal_candidate()
    plan["agents"] = [_minimal_planned_agent()]
    plan["generated_at"] = "2026-08-17T12:34:56Z"
    plan["domain_policy_ref"] = {"path": "p/dp.json", "sha256": SHA}
    plan["interaction_posture"] = {"path": "p/ip.md", "sha256": SHA, "markdown": "# Posture\n"}
    plan["projection_hashes"] = {"persona_map": SHA,
                                 "agents": [{"agent_id": "a1", "path": "p/a1.md", "sha256": SHA}]}
    return plan


def _minimal_planned_agent() -> dict:
    agent = _minimal_agent()
    agent["social_positions_by_role"] = {"role-taker": "peer"}
    agent["role_scoped_authority"] = {"role-taker": {"actions": [
        {"role_slug": "role-taker", "action_id": "accept-scope"}],
        "prohibited_action_ids": ["decide-outcome"]}}
    agent["soul_markdown"] = "# Soul\n"
    agent["generation_provenance"] = {
        "selection_prompt": {"path": "p/s.md", "sha256": SHA},
        "soul_prompt": {"path": "p/so.md", "sha256": SHA},
        "interaction_posture": {"path": "p/ip.md", "sha256": SHA},
        "role_catalogs": [], "skill_files": [],
        "model_provider": "m",
    }
    return agent


class CandidatePlanTests(unittest.TestCase):
    def test_valid_candidate_parses(self) -> None:
        parsed = parse_candidate_agent_plan(_minimal_candidate())
        self.assertEqual(parsed["schema_version"], "1.0-proposed")
        self.assertEqual(len(parsed["agents"]), 1)  # type: ignore[arg-type]

    def test_bad_schema_version_rejected(self) -> None:
        plan = _minimal_candidate()
        plan["schema_version"] = "2.0"
        with self.assertRaises(ValidationError):
            parse_candidate_agent_plan(plan)

    def test_missing_agents_rejected(self) -> None:
        plan = _minimal_candidate()
        del plan["agents"]
        with self.assertRaises(ValidationError):
            parse_candidate_agent_plan(plan)

    def test_empty_agents_rejected(self) -> None:
        plan = _minimal_candidate()
        plan["agents"] = []
        with self.assertRaises(ValidationError):
            parse_candidate_agent_plan(plan)

    def test_duplicate_agent_id_rejected(self) -> None:
        plan = _minimal_candidate()
        plan["agents"] = [_minimal_agent(), _minimal_agent()]
        with self.assertRaises(ValidationError):
            parse_candidate_agent_plan(plan)

    def test_unknown_top_level_key_rejected(self) -> None:
        plan = _minimal_candidate()
        plan["extra"] = 1
        with self.assertRaises(ValidationError):
            parse_candidate_agent_plan(plan)

    def test_null_authority_with_refs_rejected(self) -> None:
        plan = _minimal_candidate()
        plan["final_authority"]["action_refs"] = [{"role_slug": "role-taker", "action_id": "accept-scope"}]
        with self.assertRaises(ValidationError):
            parse_candidate_agent_plan(plan)

    def test_invalid_role_slug_rejected(self) -> None:
        plan = _minimal_candidate()
        plan["agents"][0]["primary_role"]["slug"] = "ghost"
        with self.assertRaises(ValidationError):
            parse_candidate_agent_plan(plan)

    def test_validate_candidate_plan_returns_dict(self) -> None:
        self.assertIsInstance(validate_candidate_plan(_minimal_candidate()), dict)

    def test_scalar_variant_accepted(self) -> None:
        # A selected catalog variant's scalar id string is accepted.
        plan = _minimal_candidate()
        plan["agents"][0]["primary_role"] = {"slug": "knowledge-checker",
                                             "variant": "internal-knowledge"}
        parsed = parse_candidate_agent_plan(plan)
        self.assertEqual(parsed["agents"][0]["primary_role"]["variant"], "internal-knowledge")  # type: ignore[union-attr,index]

    def test_object_variant_in_primary_role_rejected(self) -> None:
        # A copied catalog variant record (full object) must reject, and the
        # error must name the precise schema path agents[i].primary_role.variant.
        plan = _minimal_candidate()
        plan["agents"][0]["primary_role"]["variant"] = {
            "id": "internal-knowledge",
            "label": "Internal Knowledge Checker",
            "provenance_mode": "internal-knowledge",
        }
        with self.assertRaises(ValidationError) as ctx:
            parse_candidate_agent_plan(plan)
        msg = str(ctx.exception)
        self.assertIn("agents[0].primary_role.variant", msg)
        self.assertIn("invalid Id", msg)

    def test_object_variant_in_secondary_roles_rejected(self) -> None:
        # Same rule applies to secondary role assignments.
        plan = _minimal_candidate()
        plan["agents"][0]["secondary_roles"] = [{
            "slug": "knowledge-checker",
            "variant": {
                "id": "internal-knowledge",
                "label": "Internal Knowledge Checker",
                "provenance_mode": "internal-knowledge",
            },
        }]
        with self.assertRaises(ValidationError) as ctx:
            parse_candidate_agent_plan(plan)
        msg = str(ctx.exception)
        self.assertIn("agents[0].secondary_roles[0].variant", msg)
        self.assertIn("invalid Id", msg)



class FinalPlanTests(unittest.TestCase):
    def test_valid_final_parses(self) -> None:
        parsed = parse_agent_plan(_minimal_final())
        self.assertEqual(parsed["generated_at"], "2026-08-17T12:34:56Z")  # type: ignore[arg-type]

    def test_missing_generated_at_rejected(self) -> None:
        plan = _minimal_final()
        del plan["generated_at"]
        with self.assertRaises(ValidationError):
            parse_agent_plan(plan)

    def test_bad_projection_agent_id_rejected(self) -> None:
        plan = _minimal_final()
        plan["projection_hashes"]["agents"][0]["agent_id"] = "Bad Id"
        with self.assertRaises(ValidationError):
            parse_agent_plan(plan)

    def test_planned_agent_requires_role_scoped_authority(self) -> None:
        plan = _minimal_final()
        del plan["agents"][0]["role_scoped_authority"]
        with self.assertRaises(ValidationError):
            parse_agent_plan(plan)

    def test_validate_agent_plan_returns_dict(self) -> None:
        self.assertIsInstance(validate_agent_plan(_minimal_final()), dict)


# ---------------------------------------------------------------------------
# Domain policy parse tests
# ---------------------------------------------------------------------------


class DomainPolicyParseTests(unittest.TestCase):
    def test_default_policy_parses(self) -> None:
        self.assertEqual(parse_domain_policy(DEFAULT_DOMAIN_POLICY)["schema_version"], "1.0-proposed")

    def test_missing_tier_rejected(self) -> None:
        import copy
        bad = copy.deepcopy(DEFAULT_DOMAIN_POLICY)
        del bad["impact_tiers"]["low"]
        with self.assertRaises(ValidationError):
            parse_domain_policy(bad)

    def test_bad_rank_rejected(self) -> None:
        import copy
        bad = copy.deepcopy(DEFAULT_DOMAIN_POLICY)
        bad["decision_control_rank"]["agent"] = 5
        with self.assertRaises(ValidationError):
            parse_domain_policy(bad)


# ---------------------------------------------------------------------------
# Enrichment + final-plan semantic validation tests
# ---------------------------------------------------------------------------

from core.agent_plan_validator import (  # noqa: E402
    enrich_candidate_to_planned,
    load_domain_policy,
    sha256_text,
    validate_agent_plan_semantics,
)
from core.archetype_catalog import load_archetype_catalog  # noqa: E402


def _posture(markdown: str = "# Posture\n") -> dict:
    return {
        "path": "workspaces/alignment/artifacts/INTERACTION_POSTURE.md",
        "sha256": sha256_text(markdown),
        "markdown": markdown,
    }


def _gen_prov(posture: dict) -> dict:
    return {
        "selection_prompt": {"path": "p/s.md", "sha256": SHA},
        "soul_prompt": {"path": "p/so.md", "sha256": SHA},
        "interaction_posture": {"path": posture["path"], "sha256": posture["sha256"]},
        "role_catalogs": [],
        "skill_files": [],
        "model_provider": "m",
    }


def _settings_placeholder() -> dict:
    return {
        "decision_control": "human",
        "knowledge": {"mode": "internal", "provenance_required": False,
                      "citations_required_for_external": False},
        "verification_diversity": {"orientation": "none", "obligations": []},
        "cognitive": {"modes": ["direct"], "forcing_triggers": []},
        "social_positions_by_role": {"role-taker": "service"},
        "group": {"group_facing": False, "independence_required": False,
                  "source_disclosure_required": False, "consensus_requirements": []},
        "agreement_disagreement": {"modes": ["none"], "required_triggers": []},
    }


def _rt_agent() -> dict:
    return {
        "id": "a1",
        "primary_role": {"slug": "role-taker", "variant": None},
        "secondary_roles": [],
        "profile_rationale": {"evidence_refs": ["e1", "e2"], "not_applicable": False,
                               "not_applicable_rationale": None, "selection_reason": "r",
                               "calibration_effect": "c"},
        "calibration": {"posture": "p", "notes": [], "constraints": []},
        "skills": ["bind-to-operator"],
        "resolved_design_settings": _settings_placeholder(),
        "claim_provenance": None,
        "graph_participation": {"node_id": "n1"},
    }


def _rt_graph() -> dict:
    return {
        "nodes": [
            {"id": "n1", "kind": "agent", "agent_id": "a1", "role": "role-taker",
             "visible_inputs": [],
             "source_identity": {"kind": "agent", "id": "a1", "disclosure": "agent-generated input"},
             "phase": 0, "exec_group": "g", "declared_outputs": ["accepted role statement", "handoff"]},
            {"id": "g1", "kind": "human_gate", "mode": "approval", "condition": "c",
             "decision_owner": "operator", "required_inputs": [{"kind": "context", "key": "k1"}],
             "continuation": "end", "phase": 1},
        ],
        "edges": [{"from": "n1", "to": "g1", "kind": "sequential", "handoff": "h"}],
        "independent_opinion_boundaries": [],
        "aggregation": [],
        "unresolved_disagreement": {"triggered": False, "reason": None, "gate_id": None, "output": None},
    }


def _rt_candidate(final_authority=None) -> dict:
    return {
        "schema_version": "1.0-proposed",
        "context_registry": {"entries": [
            {"key": "k1", "content": "ctx", "sha256": SHA,
             "source_identity": {"kind": "human", "id": "h1", "disclosure": None}},
        ]},
        "human_source_registry": {"sources": [{"id": "h1", "label": "Operator"}]},
        "stakeholder_registry": {"entries": []},
        "profile_evidence_registry": {"entries": [
            {"id": "e1", "profile": "existential", "excerpt": "x", "path": "p/e1", "sha256": SHA},
            {"id": "e2", "profile": "operational", "excerpt": "y", "path": "p/e2", "sha256": SHA},
        ]},
        "synthetic_perspective_registry": {"entries": []},
        "domain_assessment": {"tier": "medium", "evidence": ["e1"]},
        "provenance_policy": {"sources": []},
        "agents": [_rt_agent()],
        "final_authority": final_authority or {
            "agent_id": None, "action_refs": [], "domain_scope": "scope",
            "decision_control": "human", "terminal_gate_id": "g1", "rationale": "r",
        },
        "trigger_evaluations": [
            {"trigger_id": "ambiguous-ownership", "evidence_refs": [{"kind": "context", "key": "k1"}],
             "result": False, "rationale": "n/a"},
        ],
        "interaction_graph": _rt_graph(),
    }


def _judge_agent() -> dict:
    return {
        "id": "j1",
        "primary_role": {"slug": "judge", "variant": None},
        "secondary_roles": [],
        "profile_rationale": {"evidence_refs": ["e1", "e2"], "not_applicable": False,
                               "not_applicable_rationale": None, "selection_reason": "r",
                               "calibration_effect": "c"},
        "calibration": {"posture": "p", "notes": [], "constraints": []},
        "skills": ["decision-calibration", "verify-before-trust", "decision-ready-not-impressive"],
        "resolved_design_settings": _settings_placeholder(),
        "claim_provenance": None,
        "graph_participation": {"node_id": "nj"},
    }


def _judge_graph() -> dict:
    return {
        "nodes": [
            {"id": "nj", "kind": "agent", "agent_id": "j1", "role": "judge",
             "visible_inputs": [],
             "source_identity": {"kind": "agent", "id": "j1", "disclosure": "agent-generated input"},
             "phase": 0, "exec_group": "g", "declared_outputs": ["reasoned recommendation", "decision rationale"]},
            {"id": "gj", "kind": "human_gate", "mode": "review", "condition": "c",
             "decision_owner": "operator", "required_inputs": [{"kind": "context", "key": "k1"}],
             "continuation": "end", "phase": 1},
        ],
        "edges": [{"from": "nj", "to": "gj", "kind": "sequential", "handoff": "h"}],
        "independent_opinion_boundaries": [],
        "aggregation": [],
        "unresolved_disagreement": {"triggered": False, "reason": None, "gate_id": None, "output": None},
    }


def _judge_candidate() -> dict:
    return {
        "schema_version": "1.0-proposed",
        "context_registry": {"entries": [
            {"key": "k1", "content": "ctx", "sha256": SHA,
             "source_identity": {"kind": "human", "id": "h1", "disclosure": None}},
            {"key": "decision-criteria", "content": "crit", "sha256": SHA,
             "source_identity": {"kind": "human", "id": "h1", "disclosure": None}},
        ]},
        "human_source_registry": {"sources": [{"id": "h1", "label": "Operator"}]},
        "stakeholder_registry": {"entries": []},
        "profile_evidence_registry": {"entries": [
            {"id": "e1", "profile": "existential", "excerpt": "x", "path": "p/e1", "sha256": SHA},
            {"id": "e2", "profile": "operational", "excerpt": "y", "path": "p/e2", "sha256": SHA},
        ]},
        "synthetic_perspective_registry": {"entries": []},
        "domain_assessment": {"tier": "medium", "evidence": ["e1"]},
        "provenance_policy": {"sources": []},
        "agents": [_judge_agent()],
        "final_authority": {
            "agent_id": "j1",
            "action_refs": [{"role_slug": "judge", "action_id": "issue-final-system-decision"}],
            "domain_scope": "medium-impact internal decision",
            "decision_control": "shared",
            "terminal_gate_id": "gj",
            "rationale": "medium permits a within-system final decision with shared control",
        },
        "trigger_evaluations": [
            {"trigger_id": "high-impact", "evidence_refs": [{"kind": "context", "key": "k1"}],
             "result": False, "rationale": "n/a"},
            {"trigger_id": "conflicting-evidence", "evidence_refs": [{"kind": "context", "key": "k1"}],
             "result": False, "rationale": "n/a"},
            {"trigger_id": "ai-recommendation-present", "evidence_refs": [{"kind": "context", "key": "k1"}],
             "result": False, "rationale": "n/a"},
        ],
        "interaction_graph": _judge_graph(),
    }


class SemanticValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_archetype_catalog()
        self.domain_policy = load_domain_policy()
        self.posture = _posture()

    def _enrich(self, candidate, souls):
        return enrich_candidate_to_planned(
            candidate, self.catalog, self.domain_policy,
            posture_snapshot=self.posture,
            generation_provenance=_gen_prov(self.posture),
            domain_policy_ref={"path": "p/dp.json", "sha256": SHA},
            generated_at="2026-08-17T12:34:56Z",
            soul_markdown_by_id=souls,
        )

    def test_role_taker_plan_validates(self) -> None:
        plan = self._enrich(_rt_candidate(), {"a1": "# Soul\n"})
        validate_agent_plan_semantics(plan, self.catalog, self.domain_policy)

    def test_judge_medium_shared_final_authority_validates(self) -> None:
        plan = self._enrich(_judge_candidate(), {"j1": "# Soul\n"})
        validate_agent_plan_semantics(plan, self.catalog, self.domain_policy)

    def test_settings_mismatch_rejected(self) -> None:
        plan = self._enrich(_rt_candidate(), {"a1": "# Soul\n"})
        plan["agents"][0]["resolved_design_settings"]["decision_control"] = "agent"
        with self.assertRaises(ValidationError):
            validate_agent_plan_semantics(plan, self.catalog, self.domain_policy)

    def test_role_scoped_authority_mismatch_rejected(self) -> None:
        plan = self._enrich(_rt_candidate(), {"a1": "# Soul\n"})
        plan["agents"][0]["role_scoped_authority"]["role-taker"]["actions"].pop()
        with self.assertRaises(ValidationError):
            validate_agent_plan_semantics(plan, self.catalog, self.domain_policy)

    def test_social_positions_mismatch_rejected(self) -> None:
        plan = self._enrich(_rt_candidate(), {"a1": "# Soul\n"})
        plan["agents"][0]["social_positions_by_role"]["role-taker"] = "peer"
        with self.assertRaises(ValidationError):
            validate_agent_plan_semantics(plan, self.catalog, self.domain_policy)

    def test_null_authority_non_approval_gate_rejected(self) -> None:
        plan = self._enrich(_rt_candidate(), {"a1": "# Soul\n"})
        plan["interaction_graph"]["nodes"][1]["mode"] = "review"
        with self.assertRaises(ValidationError):
            validate_agent_plan_semantics(plan, self.catalog, self.domain_policy)

    def test_final_authority_below_action_min_rejected(self) -> None:
        candidate = _judge_candidate()
        candidate["final_authority"]["decision_control"] = "human"  # action min is shared
        plan = self._enrich(candidate, {"j1": "# Soul\n"})
        with self.assertRaises(ValidationError):
            validate_agent_plan_semantics(plan, self.catalog, self.domain_policy)

    def test_posture_hash_mismatch_rejected(self) -> None:
        plan = self._enrich(_rt_candidate(), {"a1": "# Soul\n"})
        plan["interaction_posture"]["markdown"] = "# Tampered\n"
        with self.assertRaises(ValidationError):
            validate_agent_plan_semantics(plan, self.catalog, self.domain_policy)

    def test_graph_cycle_rejected(self) -> None:
        plan = self._enrich(_rt_candidate(), {"a1": "# Soul\n"})
        plan["interaction_graph"]["edges"].append(
            {"from": "g1", "to": "n1", "kind": "sequential", "handoff": "back"}
        )
        with self.assertRaises(ValidationError):
            validate_agent_plan_semantics(plan, self.catalog, self.domain_policy)

    def test_missing_required_trigger_rejected(self) -> None:
        plan = self._enrich(_rt_candidate(), {"a1": "# Soul\n"})
        plan["trigger_evaluations"] = []
        with self.assertRaises(ValidationError):
            validate_agent_plan_semantics(plan, self.catalog, self.domain_policy)


# ---------------------------------------------------------------------------
# Tagged-union closed-form tests
# ---------------------------------------------------------------------------


class TaggedUnionTests(unittest.TestCase):
    # --- TypedInputRef -----------------------------------------------------
    def test_typed_input_ref_all_kinds_accepted(self) -> None:
        parse_typed_input_ref({"kind": "context", "key": "k1"})
        parse_typed_input_ref({"kind": "node_output", "node_id": "n1", "output": "o"})
        parse_typed_input_ref({"kind": "external_source", "source_id": "s1"})

    def test_typed_input_ref_context_source_rejected(self) -> None:
        # context_source is NOT a TypedInputRef member.
        with self.assertRaises(ValidationError):
            parse_typed_input_ref({"kind": "context_source", "key": "k1"})

    def test_typed_input_ref_unknown_kind_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_typed_input_ref({"kind": "ghost", "x": 1})

    def test_typed_input_ref_missing_field_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_typed_input_ref({"kind": "node_output", "node_id": "n1"})  # missing output

    def test_typed_input_ref_unknown_key_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_typed_input_ref({"kind": "context", "key": "k1", "extra": 1})

    # --- ClaimSourceRef ---------------------------------------------------
    def test_claim_source_ref_all_kinds_accepted(self) -> None:
        parse_claim_source_ref({"kind": "provenance_source", "source_id": "s1"})
        parse_claim_source_ref({"kind": "human_source", "source_id": "h1"})
        parse_claim_source_ref({"kind": "context_source", "key": "k1"})
        parse_claim_source_ref({"kind": "agent_output", "node_id": "n1", "output": "o"})

    def test_claim_source_ref_context_rejected(self) -> None:
        # context is NOT a ClaimSourceRef member; only context_source is.
        with self.assertRaises(ValidationError):
            parse_claim_source_ref({"kind": "context", "key": "k1"})

    def test_claim_source_ref_unknown_kind_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_claim_source_ref({"kind": "context_source_x", "key": "k1"})

    def test_claim_source_ref_unknown_key_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_claim_source_ref({"kind": "human_source", "source_id": "h1", "extra": 1})

    # --- EvidenceRef ------------------------------------------------------
    def test_evidence_ref_all_kinds_accepted(self) -> None:
        parse_evidence_ref({"kind": "context", "key": "k1"})
        parse_evidence_ref({"kind": "profile", "evidence_id": "e1"})
        parse_evidence_ref({"kind": "domain_assessment", "index": 0})
        parse_evidence_ref({"kind": "node_output", "node_id": "n1", "output": "o"})

    def test_evidence_ref_context_source_rejected(self) -> None:
        # context_source belongs only to claim_provenance.sources, not EvidenceRef.
        with self.assertRaises(ValidationError):
            parse_evidence_ref({"kind": "context_source", "key": "k1"})

    def test_evidence_ref_unknown_kind_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_evidence_ref({"kind": "nope", "x": 1})

    def test_evidence_ref_missing_field_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_evidence_ref({"kind": "domain_assessment"})  # missing index

    # --- SourceIdentity ---------------------------------------------------
    def test_source_identity_all_kinds_accepted(self) -> None:
        parse_source_identity({"kind": "agent", "id": "a1", "disclosure": "d"})
        parse_source_identity({"kind": "external_system", "id": "x", "disclosure": "d"})
        parse_source_identity({"kind": "human", "id": "h1", "disclosure": None})
        parse_source_identity({"kind": "synthetic_perspective", "id": "s1"})

    def test_source_identity_human_disclosure_must_be_null(self) -> None:
        with self.assertRaises(ValidationError):
            parse_source_identity({"kind": "human", "id": "h1", "disclosure": "x"})

    def test_source_identity_unknown_kind_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_source_identity({"kind": "ghost", "id": "g"})

    # --- StakeholderSourceRef --------------------------------------------
    def test_stakeholder_source_ref_all_kinds_accepted(self) -> None:
        parse_stakeholder_source_ref({"kind": "human_source", "source_id": "h1"})
        parse_stakeholder_source_ref({"kind": "profile_evidence", "evidence_id": "e1"})

    def test_stakeholder_source_ref_unknown_kind_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_stakeholder_source_ref({"kind": "context", "key": "k1"})

    # --- ActionRef (exact closed object, not a union) --------------------
    def test_action_ref_exact_accepted(self) -> None:
        parse_action_ref({"role_slug": "judge", "action_id": "a1"})

    def test_action_ref_unknown_key_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_action_ref({"role_slug": "judge", "action_id": "a1", "extra": 1})

    def test_action_ref_bad_slug_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_action_ref({"role_slug": "ghost", "action_id": "a1"})


class AggregationInputTests(unittest.TestCase):
    def test_aggregation_input_node_output_accepted(self) -> None:
        parse_aggregation_input_ref({"kind": "node_output", "node_id": "n1", "output": "o"})

    def test_aggregation_input_context_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_aggregation_input_ref({"kind": "context", "key": "k1"})

    def test_aggregation_input_external_source_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_aggregation_input_ref({"kind": "external_source", "source_id": "s1"})

    def test_aggregation_input_unknown_kind_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_aggregation_input_ref({"kind": "context_source", "key": "k1"})


class ProvenanceSourceNullableTests(unittest.TestCase):
    def test_paired_null_accepted(self) -> None:
        out = parse_provenance_source({"id": "s1", "label": "L"})
        self.assertIsNone(out.get("path"))
        self.assertIsNone(out.get("sha256"))

    def test_paired_present_accepted(self) -> None:
        out = parse_provenance_source(
            {"id": "s1", "label": "L", "path": "p/s.json", "sha256": SHA}
        )
        self.assertEqual(out["path"], "p/s.json")
        self.assertEqual(out["sha256"], SHA)

    def test_one_null_one_value_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_provenance_source({"id": "s1", "label": "L", "path": "p/s.json", "sha256": None})
        with self.assertRaises(ValidationError):
            parse_provenance_source({"id": "s1", "label": "L", "path": None, "sha256": SHA})


if __name__ == "__main__":
    unittest.main()
