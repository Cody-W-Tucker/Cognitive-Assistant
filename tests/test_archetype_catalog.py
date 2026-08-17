#!/usr/bin/env python3
"""Strict catalog, scalar/closed type, role-composition, and domain-policy tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.archetype_catalog import (
    ARCHETYPES_DIR,
    CATALOG_SLUGS,
    PARENT_LINKS,
    VARIANT_RECORDS,
    canonical_role_record,
    load_archetype_catalog,
    validate_role_slug,
)
from core.agent_plan_validator import ValidationError, load_domain_policy

LEGACY = {"pattern-scout", "constraint-reader", "commitment-anchor"}

VARIANT_IDS = {
    "explainer": {"internal-model", "external-model"},
    "knowledge-checker": {"internal-knowledge", "external-knowledge"},
}


class CatalogLoadTests(unittest.TestCase):
    def test_loads_exactly_17_roles(self) -> None:
        catalog = load_archetype_catalog()
        self.assertEqual(set(catalog), CATALOG_SLUGS)
        self.assertEqual(len(catalog), 17)

    def test_all_records_match_canonical(self) -> None:
        catalog = load_archetype_catalog()
        for slug in CATALOG_SLUGS:
            self.assertEqual(catalog[slug], canonical_role_record(slug), slug)

    def test_legacy_files_absent(self) -> None:
        for slug in LEGACY:
            self.assertFalse((ARCHETYPES_DIR / f"{slug}.json").exists(), slug)

    def test_schema_version_literal(self) -> None:
        catalog = load_archetype_catalog()
        for slug, spec in catalog.items():
            self.assertEqual(spec["schema_version"], "1.0-proposed", slug)

    def test_parent_links_only_four_nonnull(self) -> None:
        catalog = load_archetype_catalog()
        expected = {k: v for k, v in PARENT_LINKS.items()}
        for slug, spec in catalog.items():
            self.assertEqual(spec["parent"], expected[slug], slug)

    def test_variant_records_exact_and_literal(self) -> None:
        catalog = load_archetype_catalog()
        for slug, spec in catalog.items():
            expected = VARIANT_RECORDS.get(slug, [])
            self.assertEqual(spec["variants"], expected, slug)
            if slug in VARIANT_IDS:
                self.assertEqual({v["id"] for v in spec["variants"]}, VARIANT_IDS[slug], slug)
                for v in spec["variants"]:
                    self.assertIn(v["provenance_mode"], {"internal-model", "external-model",
                                                         "internal-knowledge", "external-knowledge"})
            else:
                self.assertEqual(spec["variants"], [], slug)

    def test_actions_internal_unique_not_prohibited(self) -> None:
        catalog = load_archetype_catalog()
        for slug, spec in catalog.items():
            ids = [a["id"] for a in spec["authority"]["actions"]]
            self.assertEqual(len(ids), len(set(ids)), f"{slug}: duplicate action id")
            for action in spec["authority"]["actions"]:
                self.assertEqual(action["scope"], "internal", f"{slug}: {action['id']} not internal")
            prohibited = spec["authority"]["prohibited_action_ids"]
            self.assertEqual(len(prohibited), len(set(prohibited)), f"{slug}: dup prohibited")
            overlap = set(ids) & set(prohibited)
            self.assertFalse(overlap, f"{slug}: action id also prohibited: {overlap}")

    def test_max_secondary_is_three(self) -> None:
        catalog = load_archetype_catalog()
        for slug, spec in catalog.items():
            self.assertEqual(spec["composition"]["max_secondary"], 3, slug)

    def test_social_override_rules(self) -> None:
        catalog = load_archetype_catalog()
        for slug, spec in catalog.items():
            override = spec["social"]["role_override"]
            if slug == "role-taker":
                self.assertEqual(override, "service", slug)
            elif slug == "user-aligner":
                self.assertEqual(override, "advocate", slug)
            else:
                self.assertIsNone(override, slug)

    def test_judge_only_final_eligible(self) -> None:
        catalog = load_archetype_catalog()
        for slug, spec in catalog.items():
            expected = slug == "judge"
            self.assertEqual(spec["authority"]["final_decision_eligible"], expected, slug)

    def test_prerequisites_discriminated(self) -> None:
        catalog = load_archetype_catalog()
        seen_kinds = set()
        valid = {"role_present", "input_present", "criteria_present",
                 "external_model_output_present", "group_input_count",
                 "registered_decision_present", "profile_context_present"}
        for slug, spec in catalog.items():
            for group in spec["composition"]["prerequisite_groups"]:
                for pre in group:
                    self.assertIn(pre["kind"], valid, f"{slug}: unknown prereq kind {pre['kind']}")
                    seen_kinds.add(pre["kind"])
                    if pre["kind"] == "role_present":
                        self.assertIn(pre["role"], CATALOG_SLUGS)
                    elif pre["kind"] == "criteria_present":
                        self.assertIn("criteria_key", pre)
                    elif pre["kind"] == "registered_decision_present":
                        self.assertIn("decision_key", pre)
                    elif pre["kind"] == "input_present":
                        self.assertIn("input", pre)
        # Kinds actually exercised by the normative ledger.
        for expected_kind in {"role_present", "input_present", "criteria_present",
                              "registered_decision_present"}:
            self.assertIn(expected_kind, seen_kinds)

    def test_decision_control_consistency(self) -> None:
        catalog = load_archetype_catalog()
        for slug, spec in catalog.items():
            dc = spec["decision_control"]
            self.assertIn(dc["default"], dc["allowed"], slug)
            self.assertIn(spec["knowledge"]["default_mode"], spec["knowledge"]["allowed_modes"], slug)
            cog = spec["cognitive"]
            self.assertIn(cog["default_mode"], cog["supported_modes"], slug)
            ad = spec["agreement_disagreement"]
            self.assertIn(ad["default_mode"], ad["supported_modes"], slug)

    def test_arrays_unique_and_ordered(self) -> None:
        catalog = load_archetype_catalog()
        for slug, spec in catalog.items():
            for field in ("role_inputs", "role_outputs", "prohibitions",
                          "quality_criteria", "canonical_skills"):
                values = spec[field]
                self.assertEqual(len(values), len(set(values)), f"{slug}.{field} duplicate")

    def test_validate_role_slug(self) -> None:
        validate_role_slug("judge")
        with self.assertRaises(ValidationError):
            validate_role_slug("not-a-role")


class CatalogStrictRejectionTests(unittest.TestCase):
    def _write(self, tmpdir: Path, slug: str, record: dict) -> None:
        (tmpdir / f"{slug}.json").write_text(json.dumps(record), encoding="utf-8")

    def _good(self, slug: str) -> dict:
        return canonical_role_record(slug)

    def test_unknown_key_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            rec = self._good("model")
            rec["extra_field"] = "x"
            self._write(tmp, "model", rec)
            with self.assertRaises(ValidationError) as ctx:
                load_archetype_catalog(tmp)
            self.assertIn("unknown", str(ctx.exception))

    def test_missing_key_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            rec = self._good("model")
            del rec["knowledge"]
            self._write(tmp, "model", rec)
            with self.assertRaises(ValidationError) as ctx:
                load_archetype_catalog(tmp)
            self.assertIn("missing", str(ctx.exception))

    def test_wrong_scalar_type_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            rec = self._good("model")
            rec["role_inputs"] = "not-a-list"
            self._write(tmp, "model", rec)
            with self.assertRaises(ValidationError):
                load_archetype_catalog(tmp)

    def test_invalid_enum_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            rec = self._good("model")
            rec["decision_control"]["default"] = "autonomous"
            self._write(tmp, "model", rec)
            with self.assertRaises(ValidationError):
                load_archetype_catalog(tmp)

    def test_duplicate_array_member_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            rec = self._good("model")
            rec["role_inputs"] = ["context", "context"]
            self._write(tmp, "model", rec)
            with self.assertRaises(ValidationError):
                load_archetype_catalog(tmp)

    def test_invalid_id_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            rec = self._good("model")
            rec["slug"] = "Bad_Slug"
            self._write(tmp, "Bad_Slug", rec)
            with self.assertRaises(ValidationError):
                load_archetype_catalog(tmp)

    def test_variant_mismatch_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            rec = self._good("model")
            rec["variants"] = [{"id": "x", "label": "X", "provenance_mode": "internal-model"}]
            self._write(tmp, "model", rec)
            with self.assertRaises(ValidationError) as ctx:
                load_archetype_catalog(tmp)
            self.assertIn("variants", str(ctx.exception))

    def test_external_action_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            rec = self._good("model")
            rec["authority"]["actions"][0]["scope"] = "external"
            self._write(tmp, "model", rec)
            with self.assertRaises(ValidationError):
                load_archetype_catalog(tmp)

    def test_social_override_on_wrong_role_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            rec = self._good("model")
            rec["social"]["role_override"] = "service"
            self._write(tmp, "model", rec)
            with self.assertRaises(ValidationError):
                load_archetype_catalog(tmp)

    def test_max_secondary_deviation_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            rec = self._good("model")
            rec["composition"]["max_secondary"] = 2
            self._write(tmp, "model", rec)
            with self.assertRaises(ValidationError):
                load_archetype_catalog(tmp)

    def test_filename_slug_mismatch_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            rec = self._good("model")
            self._write(tmp, "wrong-name", rec)
            with self.assertRaises(ValidationError) as ctx:
                load_archetype_catalog(tmp)
            self.assertIn("filename must match", str(ctx.exception))


class DomainPolicyTests(unittest.TestCase):
    def test_domain_policy_loads_and_matches(self) -> None:
        policy = load_domain_policy()
        self.assertEqual(policy["schema_version"], "1.0-proposed")
        self.assertEqual(policy["decision_control_rank"], {"human": 0, "shared": 1, "agent": 2})
        self.assertEqual(set(policy["impact_tiers"]), {"unknown", "high", "medium", "low"})

    def test_domain_policy_tier_structure(self) -> None:
        policy = load_domain_policy()
        low = policy["impact_tiers"]["low"]
        self.assertEqual(low["decision_control_levels"], ["human", "shared", "agent"])
        self.assertEqual(low["default_decision_control"], "agent")
        self.assertEqual(low["within_system_final_decision"], True)
        unknown = policy["impact_tiers"]["unknown"]
        self.assertEqual(unknown["decision_control_levels"], ["human"])

    def test_domain_policy_tamper_rejected(self) -> None:
        import copy
        policy = load_domain_policy()
        tampered = copy.deepcopy(policy)
        tampered["impact_tiers"]["low"]["default_decision_control"] = "human"
        from core.agent_plan_validator import parse_domain_policy
        with self.assertRaises(ValidationError):
            parse_domain_policy(tampered)


class CatalogCompositionIntersectionTests(unittest.TestCase):
    """Every declared primary->secondary relation must resolve under policy.

    A relation is resolvably composable only if the primary and secondary share
    at least one knowledge mode, and only if the active role set keeps a
    non-empty decision-control intersection at every impact tier. These are the
    exact conditions the strict resolver enforces (see
    ``recompute_resolved_settings``); the canonical ledger must never offer a
    relation that would fail them.
    """

    def test_every_relation_has_nonempty_knowledge_intersection(self) -> None:
        catalog = load_archetype_catalog()
        for slug, spec in catalog.items():
            for sec in spec["composition"]["primary_compatible_secondary"]:
                sec_spec = catalog[sec]
                km = set(spec["knowledge"]["allowed_modes"]) & set(
                    sec_spec["knowledge"]["allowed_modes"]
                )
                self.assertTrue(
                    km, f"{slug} -> {sec}: empty resolved knowledge-mode intersection"
                )

    def test_every_relation_has_nonempty_decision_control_per_tier(self) -> None:
        catalog = load_archetype_catalog()
        policy = load_domain_policy()
        tiers = policy["impact_tiers"]
        for slug, spec in catalog.items():
            for sec in spec["composition"]["primary_compatible_secondary"]:
                sec_spec = catalog[sec]
                dc = set(spec["decision_control"]["allowed"]) & set(
                    sec_spec["decision_control"]["allowed"]
                )
                self.assertTrue(dc, f"{slug} -> {sec}: empty decision_control intersection")
                for tier_name, tier in tiers.items():
                    levels = set(tier["decision_control_levels"])
                    self.assertTrue(
                        dc & levels,
                        f"{slug} -> {sec}: empty decision_control intersection at tier {tier_name}",
                    )

    def test_no_external_only_crossed_with_internal_either(self) -> None:
        catalog = load_archetype_catalog()
        external_only = {
            s
            for s, spec in catalog.items()
            if spec["knowledge"]["allowed_modes"] == ["external"]
        }
        internal_either = set(catalog) - external_only
        for slug, spec in catalog.items():
            for sec in spec["composition"]["primary_compatible_secondary"]:
                pair = {slug, sec}
                crossed = (pair & external_only) and (pair & internal_either)
                self.assertFalse(
                    crossed,
                    f"{slug} -> {sec}: external-only role crossed with internal/either role",
                )


if __name__ == "__main__":
    unittest.main()
