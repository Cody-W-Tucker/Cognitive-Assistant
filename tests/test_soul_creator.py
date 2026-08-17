#!/usr/bin/env python3
"""Focused tests for the candidate->final plan enrichment and staged bundle commit."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.agent_plan_validator import (
    ValidationError,
    enrich_candidate_to_planned,
    load_domain_policy,
    sha256_text,
    validate_agent_plan,
)
from core.archetype_catalog import load_archetype_catalog
from core.soul_creator import SoulCreator, now_generated_at

try:  # discover -s tests imports siblings as top-level modules
    from plan_fixtures import (
        SHA,
        generation_provenance as _gen_prov,
        posture_snapshot as _posture_snapshot,
        role_taker_candidate as _role_taker_candidate,
    )
except ImportError:  # python -m unittest tests.test_soul_creator
    from tests.plan_fixtures import (
        SHA,
        generation_provenance as _gen_prov,
        posture_snapshot as _posture_snapshot,
        role_taker_candidate as _role_taker_candidate,
    )


class PostureSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        self.creator = SoulCreator(output_dir=self.tmp)

    def test_snapshot_hashes_markdown(self) -> None:
        path = self.tmp / "INTERACTION_POSTURE.md"
        path.write_text("# Posture\n", encoding="utf-8")
        snap = self.creator.snapshot_posture(path)
        self.assertEqual(snap["markdown"], "# Posture\n")
        self.assertEqual(snap["sha256"], sha256_text("# Posture\n"))

    def test_snapshot_rejects_non_ascii(self) -> None:
        path = self.tmp / "INTERACTION_POSTURE.md"
        path.write_text("caf\u00e9", encoding="utf-8")
        with self.assertRaises(ValidationError):
            self.creator.snapshot_posture(path)

    def test_snapshot_rejects_crlf(self) -> None:
        path = self.tmp / "INTERACTION_POSTURE.md"
        # CRLF line endings embed a CR byte, which must reject.
        path.write_bytes(b"# Posture\r\nLine two\r\n")
        with self.assertRaises(ValidationError):
            self.creator.snapshot_posture(path)

    def test_snapshot_rejects_lone_cr(self) -> None:
        path = self.tmp / "INTERACTION_POSTURE.md"
        path.write_bytes(b"# Posture\rLine two\n")
        with self.assertRaises(ValidationError):
            self.creator.snapshot_posture(path)

    def test_snapshot_persists_raw_bytes_exactly(self) -> None:
        import hashlib

        # Raw bytes with trailing newline; no normalization should occur.
        raw = b"# Posture\n\nSome content.\n"
        path = self.tmp / "INTERACTION_POSTURE.md"
        path.write_bytes(raw)
        snap = self.creator.snapshot_posture(path)
        # Markdown is the exact decoded text of the raw bytes.
        self.assertEqual(snap["markdown"], raw.decode("utf-8"))
        # Hash is over the raw validated bytes, not a re-encoded form.
        self.assertEqual(snap["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(
            snap["sha256"],
            hashlib.sha256(snap["markdown"].encode("utf-8")).hexdigest(),
        )


class EnrichmentAndCommitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        self.catalog = load_archetype_catalog()
        self.domain_policy = load_domain_policy()
        self.creator = SoulCreator(output_dir=self.tmp)
        self.posture = _posture_snapshot()
        self.soul = {"a1": "# Soul of a1\n"}
        self.candidate = _role_taker_candidate()

    def _gen_at(self) -> str:
        return now_generated_at()

    def test_build_bundle_commits_plan_and_projections(self) -> None:
        self.creator.build_bundle(
            self.candidate,
            catalog=self.catalog,
            domain_policy=self.domain_policy,
            posture_snapshot=self.posture,
            soul_markdown_by_id=self.soul,
            generation_provenance=_gen_prov(self.posture),
            domain_policy_ref={"path": "p/dp.json", "sha256": SHA},
            generated_at=self._gen_at(),
        )
        plan_path = self.creator.plan_file
        self.assertTrue(plan_path.exists())
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        validate_agent_plan(plan)  # structural

        # Projection files exist and match persisted hashes.
        persona = self.creator.persona_map_file.read_text(encoding="utf-8")
        self.assertEqual(sha256_text(persona), plan["projection_hashes"]["persona_map"])
        self.assertTrue((self.creator.agents_dir / "a1.md").exists())
        agent_content = (self.creator.agents_dir / "a1.md").read_text(encoding="utf-8")
        self.assertEqual(agent_content, "# Soul of a1\n")
        stored = next(a for a in plan["projection_hashes"]["agents"] if a["agent_id"] == "a1")
        self.assertEqual(stored["sha256"], sha256_text(agent_content))

    def test_enrichment_persists_derived_authority_and_settings(self) -> None:
        plan = enrich_candidate_to_planned(
            self.candidate, self.catalog, self.domain_policy,
            posture_snapshot=self.posture,
            generation_provenance=_gen_prov(self.posture),
            domain_policy_ref={"path": "p/dp.json", "sha256": SHA},
            generated_at=self._gen_at(),
            soul_markdown_by_id=self.soul,
        )
        agent = plan["agents"][0]
        # role-taker social override 'service' must be derived.
        self.assertEqual(agent["social_positions_by_role"]["role-taker"], "service")
        # role_scoped_authority must carry both catalog actions.
        refs = {a["action_id"] for a in agent["role_scoped_authority"]["role-taker"]["actions"]}
        self.assertEqual(refs, {"accept-scope", "restate-mandate"})
        self.assertIn("decide-outcome", agent["role_scoped_authority"]["role-taker"]["prohibited_action_ids"])
        # resolved settings recomputed (role-taker default decision control 'shared').
        self.assertEqual(agent["resolved_design_settings"]["decision_control"], "shared")


class RollbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        self.catalog = load_archetype_catalog()
        self.domain_policy = load_domain_policy()
        self.creator = SoulCreator(output_dir=self.tmp)
        self.posture = _posture_snapshot()

    def test_in_process_exception_restores_projections_and_keeps_plan(self) -> None:
        # Pre-existing (old) projections that must survive a failed commit.
        self.creator.persona_map_file.write_text("OLD PERSONA\n", encoding="utf-8")
        (self.creator.agents_dir / "a1.md").write_text("OLD SOUL\n", encoding="utf-8")

        plan = enrich_candidate_to_planned(
            _role_taker_candidate(), self.catalog, self.domain_policy,
            posture_snapshot=self.posture,
            generation_provenance=_gen_prov(self.posture),
            domain_policy_ref={"path": "p/dp.json", "sha256": SHA},
            generated_at=now_generated_at(),
            soul_markdown_by_id={"a1": "# New Soul\n"},
        )
        rendered = self.creator.render_projections(plan, self.catalog)

        original = self.creator._atomic_write

        def failing_write(target: Path, content: str) -> None:
            if target == self.creator.plan_file:
                raise RuntimeError("simulated plan-write failure")
            original(target, content)

        self.creator._atomic_write = failing_write  # type: ignore[assignment]
        with self.assertRaises(RuntimeError):
            self.creator.commit_bundle(plan, rendered, self.catalog, self.domain_policy)

        # Projections restored to the old content; plan file never written.
        self.assertEqual(self.creator.persona_map_file.read_text(encoding="utf-8"), "OLD PERSONA\n")
        self.assertEqual((self.creator.agents_dir / "a1.md").read_text(encoding="utf-8"), "OLD SOUL\n")
        self.assertFalse(self.creator.plan_file.exists())


class StartupReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        self.catalog = load_archetype_catalog()
        self.domain_policy = load_domain_policy()
        self.creator = SoulCreator(output_dir=self.tmp)
        self.posture = _posture_snapshot()

    def _commit_valid(self) -> None:
        self.creator.build_bundle(
            _role_taker_candidate(),
            catalog=self.catalog,
            domain_policy=self.domain_policy,
            posture_snapshot=self.posture,
            soul_markdown_by_id={"a1": "# Soul of a1\n"},
            generation_provenance=_gen_prov(self.posture),
            domain_policy_ref={"path": "p/dp.json", "sha256": SHA},
            generated_at=now_generated_at(),
        )

    def test_orphan_projections_removed_when_no_plan(self) -> None:
        self.creator.persona_map_file.write_text("ORPHAN\n", encoding="utf-8")
        (self.creator.agents_dir / "a1.md").write_text("ORPHAN\n", encoding="utf-8")
        status, plan = self.creator.reconcile_startup(self.catalog, self.domain_policy)
        self.assertEqual(status, "fresh")
        self.assertIsNone(plan)
        self.assertFalse(self.creator.persona_map_file.exists())
        self.assertFalse((self.creator.agents_dir / "a1.md").exists())

    def test_valid_plan_reconciled_and_rendered(self) -> None:
        self._commit_valid()
        status, plan = self.creator.reconcile_startup(self.catalog, self.domain_policy)
        self.assertEqual(status, "valid")
        self.assertIsNotNone(plan)
        self.assertTrue(self.creator.persona_map_file.exists())
        self.assertTrue((self.creator.agents_dir / "a1.md").exists())

    def test_corrupt_plan_fails_closed_leaving_files(self) -> None:
        # Posture must never be touched by reconciliation.
        posture_file = self.tmp / "INTERACTION_POSTURE.md"
        posture_file.write_text("# Posture\n", encoding="utf-8")
        self.creator.persona_map_file.write_text("KEEP\n", encoding="utf-8")
        self.creator.plan_file.write_text("{not valid json", encoding="utf-8")
        with self.assertRaises(ValidationError):
            self.creator.reconcile_startup(self.catalog, self.domain_policy)
        # Files left in place; posture untouched.
        self.assertTrue(self.creator.plan_file.exists())
        self.assertEqual(self.creator.persona_map_file.read_text(encoding="utf-8"), "KEEP\n")
        self.assertEqual(posture_file.read_text(encoding="utf-8"), "# Posture\n")

    def test_abandoned_staging_removed(self) -> None:
        abandoned = self.creator.staging_root / "build-deadbeef"
        abandoned.mkdir(parents=True)
        (abandoned / "journal.json").write_text("{}", encoding="utf-8")
        self.creator.reconcile_startup(self.catalog, self.domain_policy)
        self.assertFalse(abandoned.exists())


class SuppliedRegistryTests(unittest.TestCase):
    """Code owns the registries; the model may only reproduce them."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        self.posture = _posture_snapshot()

    def _supplied(self) -> dict:
        from core.soul_creator import build_supplied_registries

        soul = self.tmp / "SOUL.md"
        soul.write_text("# Soul\nI hold the standards.\n", encoding="utf-8")
        existential = self.tmp / "human_profile_existential.md"
        operational = self.tmp / "human_profile_operational.md"
        existential.write_text("Existential profile body.\n", encoding="utf-8")
        operational.write_text("Operational profile body.\n", encoding="utf-8")
        return build_supplied_registries(
            self.posture,
            soul_path=soul,
            profile_artifacts={"existential": existential, "operational": operational},
        )

    def test_registries_are_hashed_and_cover_both_profiles(self) -> None:
        supplied = self._supplied()
        profiles = {
            entry["profile"] for entry in supplied["profile_evidence_registry"]["entries"]
        }
        self.assertEqual(profiles, {"existential", "operational"})
        for entry in supplied["context_registry"]["entries"]:
            self.assertEqual(entry["sha256"], sha256_text(entry["content"]))
        keys = [entry["key"] for entry in supplied["context_registry"]["entries"]]
        # Prerequisite-bearing context keys must exist so user-aligner, judge,
        # and criteria-applicator prerequisites are satisfiable.
        self.assertIn("operator-decision", keys)
        self.assertIn("decision-criteria", keys)

    def test_missing_profile_artifact_rejects(self) -> None:
        from core.soul_creator import build_supplied_registries

        soul = self.tmp / "SOUL.md"
        soul.write_text("# Soul\n", encoding="utf-8")
        with self.assertRaises(FileNotFoundError):
            build_supplied_registries(
                self.posture, soul_path=soul, profile_artifacts={}
            )


class CandidateResponseParsingTests(unittest.TestCase):
    """Prompt output parses only as a CandidateAgentPlan."""

    def setUp(self) -> None:
        self.candidate = _role_taker_candidate()
        self.supplied = {
            key: self.candidate[key]
            for key in (
                "context_registry",
                "human_source_registry",
                "stakeholder_registry",
                "synthetic_perspective_registry",
                "provenance_policy",
                "profile_evidence_registry",
            )
        }

    def test_parses_fenced_candidate(self) -> None:
        from core.soul_creator import parse_candidate_response

        payload = "```json\n" + json.dumps(self.candidate) + "\n```"
        parsed = parse_candidate_response(payload, self.supplied)
        self.assertEqual(parsed["agents"][0]["id"], "a1")

    def test_rejects_non_json(self) -> None:
        from core.soul_creator import parse_candidate_response

        with self.assertRaises(ValidationError):
            parse_candidate_response("Here is the plan!", self.supplied)

    def test_rejects_altered_registry(self) -> None:
        from core.soul_creator import parse_candidate_response

        tampered = json.loads(json.dumps(self.candidate))
        tampered["human_source_registry"]["sources"].append(
            {"id": "ghost", "label": "Ghost"}
        )
        with self.assertRaises(ValidationError) as ctx:
            parse_candidate_response(json.dumps(tampered), self.supplied)
        self.assertIn("human_source_registry", str(ctx.exception))

    def test_rejects_model_supplied_derived_fields(self) -> None:
        from core.soul_creator import parse_candidate_response

        tampered = json.loads(json.dumps(self.candidate))
        tampered["agents"][0]["role_scoped_authority"] = {}
        with self.assertRaises(ValidationError):
            parse_candidate_response(json.dumps(tampered), self.supplied)


class SoulPromptPipelineTests(unittest.TestCase):
    """Derived definitions and ASCII soul normalization."""

    def setUp(self) -> None:
        self.catalog = load_archetype_catalog()
        self.domain_policy = load_domain_policy()
        self.posture = _posture_snapshot()
        self.candidate = _role_taker_candidate()

    def _definitions(self) -> list:
        from core.soul_creator import derive_agent_definitions

        return derive_agent_definitions(
            self.candidate,
            self.catalog,
            self.domain_policy,
            posture_snapshot=self.posture,
            generation_provenance=_gen_prov(self.posture),
            domain_policy_ref={"path": "p/dp.json", "sha256": SHA},
            generated_at=now_generated_at(),
        )

    def test_definitions_carry_derived_authority_without_soul(self) -> None:
        definition = self._definitions()[0]
        self.assertNotIn("soul_markdown", definition)
        self.assertNotIn("generation_provenance", definition)
        self.assertEqual(definition["social_positions_by_role"]["role-taker"], "service")
        self.assertEqual(definition["resolved_design_settings"]["decision_control"], "shared")

    def test_soul_prompt_renders_with_definition_and_posture(self) -> None:
        from core.soul_creator import render_soul_prompt

        prompt = render_soul_prompt(
            agent_definition=self._definitions()[0],
            posture_snapshot=self.posture,
            skill_material='<skill slug="bind-to-operator">material</skill>',
            template="<agent>{agent_definition}</agent>"
            "<posture>{interaction_posture}</posture>"
            "<skills>{skill_material}</skills>",
        )
        self.assertIn("role-taker", prompt)
        self.assertIn("# Posture", prompt)
        self.assertIn("bind-to-operator", prompt)

    def test_selection_prompt_renders_every_supplied_input(self) -> None:
        from core.soul_creator import render_selection_prompt

        supplied = {
            key: self.candidate[key]
            for key in (
                "context_registry",
                "human_source_registry",
                "stakeholder_registry",
                "synthetic_perspective_registry",
                "provenance_policy",
                "profile_evidence_registry",
            )
        }
        prompt = render_selection_prompt(
            catalog=self.catalog,
            domain_policy=self.domain_policy,
            posture_snapshot=self.posture,
            supplied=supplied,
            translation_layer="# Soul\n",
        )
        for marker in ("role-taker", "# Posture", "ambiguous-ownership", "medium"):
            self.assertIn(marker, prompt)

    def test_soul_markdown_is_folded_to_ascii(self) -> None:
        from core.soul_creator import normalize_soul_markdown

        folded = normalize_soul_markdown("```markdown\nI hold the line \u2014 always.\n```", "a1")
        self.assertTrue(folded.isascii())
        self.assertIn("I hold the line - always.", folded)
        self.assertTrue(folded.endswith("\n"))

    def test_empty_soul_rejected(self) -> None:
        from core.soul_creator import normalize_soul_markdown

        with self.assertRaises(ValidationError):
            normalize_soul_markdown("```\n\n```", "a1")

    def test_unknown_skill_rejected(self) -> None:
        from core.soul_creator import load_skill_material

        with self.assertRaises(ValidationError):
            load_skill_material(["no-such-skill"], {})

    def test_no_stub_remains_in_the_build_path(self) -> None:
        source = Path("core/soul_creator.py").read_text(encoding="utf-8")
        self.assertNotIn("NotImplementedError", source)


class ProjectionAsciiTests(unittest.TestCase):
    """Rendered projections must be strict ASCII for the manifest test."""

    def test_persona_map_is_ascii_and_counts_agents(self) -> None:
        from core.soul_creator import SoulCreator, derive_agent_definitions

        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        catalog = load_archetype_catalog()
        posture = _posture_snapshot()
        creator = SoulCreator(output_dir=tmp)
        plan = enrich_candidate_to_planned(
            _role_taker_candidate(), catalog, load_domain_policy(),
            posture_snapshot=posture,
            generation_provenance=_gen_prov(posture),
            domain_policy_ref={"path": "p/dp.json", "sha256": SHA},
            generated_at="2026-08-17T12:34:56Z",
            soul_markdown_by_id={"a1": "# Soul\n"},
        )
        persona = creator.render_persona_map(plan, catalog)
        self.assertTrue(persona.isascii())
        self.assertIn("with 1 agent(s)", persona)
        self.assertNotIn("{len(", persona)


if __name__ == "__main__":
    unittest.main()
