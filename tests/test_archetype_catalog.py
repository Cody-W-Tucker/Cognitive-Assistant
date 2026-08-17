#!/usr/bin/env python3
"""Tests for the archetype catalog loader and validation."""

from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

from core.archetype_catalog import (
    ArchetypeSpec,
    load_archetype_catalog,
    validate_archetype_slugs,
    validate_skill_assignments,
)


class LoadArchetypeCatalogTests(unittest.TestCase):
    def test_loads_real_catalog(self) -> None:
        """The checked-in catalog must load without error."""
        catalog = load_archetype_catalog()
        self.assertGreaterEqual(len(catalog), 3)
        self.assertIn("pattern-scout", catalog)
        self.assertIn("constraint-reader", catalog)
        self.assertIn("commitment-anchor", catalog)

    def test_all_archetypes_have_required_fields(self) -> None:
        catalog = load_archetype_catalog()
        for slug, spec in catalog.items():
            self.assertEqual(spec.slug, slug)
            self.assertTrue(spec.name, f"{slug} missing name")
            self.assertTrue(spec.purpose, f"{slug} missing purpose")
            self.assertTrue(spec.job_to_be_done, f"{slug} missing job_to_be_done")
            self.assertTrue(spec.outcome, f"{slug} missing outcome")
            self.assertTrue(spec.scope_triggers, f"{slug} missing scope_triggers")
            self.assertTrue(spec.scope_outputs, f"{slug} missing scope_outputs")
            self.assertTrue(spec.out_of_scope, f"{slug} missing out_of_scope")
            self.assertTrue(spec.canonical_skills, f"{slug} missing canonical_skills")

    def test_contract_text_is_renderable(self) -> None:
        catalog = load_archetype_catalog()
        for spec in catalog.values():
            text = spec.contract_text()
            self.assertIn(spec.name, text)
            self.assertIn(spec.slug, text)

    def test_missing_directory_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_archetype_catalog(Path("/nonexistent/catalog"))

    def test_empty_directory_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                load_archetype_catalog(Path(tmp))

    def test_filename_slug_mismatch_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            (tmpdir / "wrong-name.json").write_text(
                json.dumps(_valid_contract("different-name")),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError) as ctx:
                load_archetype_catalog(tmpdir)
            self.assertIn("filename must match slug", str(ctx.exception))

    def test_rejects_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            (tmpdir / "test.json").write_text("{not json", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not valid JSON"):
                load_archetype_catalog(tmpdir)

    def test_rejects_scalar_where_list_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            contract = _valid_contract("test")
            contract["canonical_skills"] = "mode-detection"
            (tmpdir / "test.json").write_text(json.dumps(contract), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "canonical_skills.*list"):
                load_archetype_catalog(tmpdir)

    def test_rejects_empty_or_duplicate_skill_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            contract = _valid_contract("test")
            contract["canonical_skills"] = ["mode-detection", "mode-detection"]
            (tmpdir / "test.json").write_text(json.dumps(contract), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "canonical_skills.*duplicate"):
                load_archetype_catalog(tmpdir)

            contract["canonical_skills"] = [""]
            (tmpdir / "test.json").write_text(json.dumps(contract), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "canonical_skills.*non-empty"):
                load_archetype_catalog(tmpdir)

    def test_rejects_unknown_skill_identifier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            contract = _valid_contract("test")
            contract["canonical_skills"] = ["does-not-exist"]
            (tmpdir / "test.json").write_text(json.dumps(contract), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unknown canonical skill.*does-not-exist"):
                load_archetype_catalog(tmpdir)


def _valid_contract(slug: str) -> dict:
    return {
        "slug": slug,
        "name": "Test",
        "purpose": "Purpose",
        "job_to_be_done": "Job",
        "outcome": "Outcome",
        "scope": {
            "triggers": ["Trigger"],
            "outputs": ["Output"],
            "out_of_scope": ["Out"],
        },
        "authority": {"can_decide": ["Decide"], "must_defer": ["Defer"]},
        "approval_boundaries": "Approval",
        "quality_expectations": "Quality",
        "evidence_expectations": "Evidence",
        "canonical_skills": ["mode-detection"],
    }


class ValidateArchetypeSlugsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = {
            "a": ArchetypeSpec(
                slug="a", name="A", purpose="p", job_to_be_done="j",
                outcome="o", scope_triggers=[], scope_outputs=[],
                out_of_scope=[], authority_can_decide=[],
                authority_must_defer=[], approval_boundaries="",
                quality_expectations="", evidence_expectations="",
                canonical_skills=[],
            ),
        }

    def test_known_slugs_pass(self) -> None:
        validate_archetype_slugs(["a"], self.catalog)

    def test_unknown_slug_fails(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_archetype_slugs(["unknown"], self.catalog)
        self.assertIn("unknown archetype", str(ctx.exception).lower())
        self.assertIn("unknown", str(ctx.exception))


class ValidateSkillAssignmentsTests(unittest.TestCase):
    def test_valid_skill_slug_format_required(self) -> None:
        with self.assertRaises(ValueError):
            validate_skill_assignments("test", ["INVALID_SLUG"])

    def test_duplicate_skill_slug_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate canonical skill"):
            validate_skill_assignments("test", ["mode-detection", "mode-detection"])


if __name__ == "__main__":
    unittest.main()
