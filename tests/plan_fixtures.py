#!/usr/bin/env python3
"""Shared candidate/final agent-plan fixtures for the alignment test suite.

Not a test module: the ``test*.py`` discovery pattern skips it. It is imported
by ``tests/test_soul_creator.py`` and ``tests/test_alignment_spec.py`` so a
single minimal, schema-valid plan definition backs both.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from core.agent_plan_validator import (
    enrich_candidate_to_planned,
    load_domain_policy,
    sha256_text,
)
from core.archetype_catalog import load_archetype_catalog

SHA = "0" * 64


def posture_snapshot(markdown: str = "# Posture\n") -> dict:
    """Return a valid ``InteractionPostureSnapshot`` for ``markdown``."""
    return {
        "path": "workspaces/alignment/artifacts/INTERACTION_POSTURE.md",
        "sha256": sha256_text(markdown),
        "markdown": markdown,
    }


def generation_provenance(snapshot: dict) -> dict:
    """Return a minimal ``GenerationProvenance`` bound to ``snapshot``."""
    return {
        "selection_prompt": {"path": "p/s.md", "sha256": SHA},
        "soul_prompt": {"path": "p/so.md", "sha256": SHA},
        "interaction_posture": {
            "path": snapshot["path"],
            "sha256": snapshot["sha256"],
        },
        "role_catalogs": [],
        "skill_files": [],
        "model_provider": "m",
    }


def role_taker_agent(agent_id: str = "a1", node_id: str = "n1") -> dict:
    """A single role-taker ``CandidateAgent``."""
    return {
        "id": agent_id,
        "primary_role": {"slug": "role-taker", "variant": None},
        "secondary_roles": [],
        "profile_rationale": {
            "evidence_refs": ["e1", "e2"],
            "not_applicable": False,
            "not_applicable_rationale": None,
            "selection_reason": "r",
            "calibration_effect": "c",
        },
        "calibration": {"posture": "p", "notes": [], "constraints": []},
        "skills": ["bind-to-operator"],
        # Placeholder; enrichment recomputes and overwrites this.
        "resolved_design_settings": {
            "decision_control": "human",
            "knowledge": {"mode": "internal", "provenance_required": False,
                          "citations_required_for_external": False},
            "verification_diversity": {"orientation": "none", "obligations": []},
            "cognitive": {"modes": ["direct"], "forcing_triggers": []},
            "social_positions_by_role": {"role-taker": "service"},
            "group": {"group_facing": False, "independence_required": False,
                      "source_disclosure_required": False, "consensus_requirements": []},
            "agreement_disagreement": {"modes": ["none"], "required_triggers": []},
        },
        "claim_provenance": None,
        "graph_participation": {"node_id": node_id},
    }


def role_taker_graph(agent_id: str = "a1", node_id: str = "n1") -> dict:
    """A minimal acyclic graph: one agent node into one approval gate."""
    return {
        "nodes": [
            {
                "id": node_id, "kind": "agent", "agent_id": agent_id, "role": "role-taker",
                "visible_inputs": [],
                "source_identity": {"kind": "agent", "id": agent_id,
                                    "disclosure": "agent-generated input"},
                "phase": 0, "exec_group": "g",
                "declared_outputs": ["accepted role statement", "handoff"],
            },
            {
                "id": "g1", "kind": "human_gate", "mode": "approval", "condition": "c",
                "decision_owner": "operator",
                "required_inputs": [{"kind": "context", "key": "k1"}],
                "continuation": "end", "phase": 1,
            },
        ],
        "edges": [{"from": node_id, "to": "g1", "kind": "sequential", "handoff": "h"}],
        "independent_opinion_boundaries": [],
        "aggregation": [],
        "unresolved_disagreement": {"triggered": False, "reason": None,
                                    "gate_id": None, "output": None},
    }


def role_taker_candidate(final_authority: Optional[dict] = None) -> dict:
    """A minimal, schema- and semantics-valid ``CandidateAgentPlan``."""
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
        "agents": [role_taker_agent()],
        "final_authority": final_authority or {
            "agent_id": None, "action_refs": [], "domain_scope": "scope",
            "decision_control": "human", "terminal_gate_id": "g1", "rationale": "r",
        },
        "trigger_evaluations": [
            {"trigger_id": "ambiguous-ownership",
             "evidence_refs": [{"kind": "context", "key": "k1"}],
             "result": False, "rationale": "n/a"},
        ],
        "interaction_graph": role_taker_graph(),
    }


def minimal_agent_plan(
    *,
    agent_ids: Optional[List[str]] = None,
    generated_at: str = "2026-08-17T12:34:56Z",
) -> Dict[str, object]:
    """Return a structurally valid final ``AgentPlan``.

    ``agent_ids`` renames the single fixture agent, which is enough for callers
    that only need the plan's declared agent identities.
    """
    candidate = role_taker_candidate()
    snapshot = posture_snapshot()
    ids = agent_ids or ["a1"]
    candidate["agents"] = []
    nodes: List[dict] = []
    edges: List[dict] = []
    for index, agent_id in enumerate(ids):
        node_id = f"n{index + 1}"
        candidate["agents"].append(role_taker_agent(agent_id, node_id))  # type: ignore[union-attr]
        nodes.append(role_taker_graph(agent_id, node_id)["nodes"][0])
        edges.append({"from": node_id, "to": "g1", "kind": "sequential", "handoff": "h"})
    gate = role_taker_graph()["nodes"][1]
    candidate["interaction_graph"]["nodes"] = nodes + [gate]  # type: ignore[index]
    candidate["interaction_graph"]["edges"] = edges  # type: ignore[index]

    plan = enrich_candidate_to_planned(
        candidate,
        load_archetype_catalog(),
        load_domain_policy(),
        posture_snapshot=snapshot,
        generation_provenance=generation_provenance(snapshot),
        domain_policy_ref={"path": "p/dp.json", "sha256": SHA},
        generated_at=generated_at,
        soul_markdown_by_id={agent_id: f"# Soul of {agent_id}\n" for agent_id in ids},
    )
    plan["projection_hashes"] = {
        "persona_map": sha256_text("persona\n"),
        "agents": [
            {"agent_id": agent_id, "path": f"agents/{agent_id}.md",
             "sha256": sha256_text(f"# Soul of {agent_id}\n")}
            for agent_id in ids
        ],
    }
    return plan
