#!/usr/bin/env python3
"""The bootstrap pipeline: answers -> human profile -> skills / tool specs -> SOUL -> alignment spec."""

from __future__ import annotations

import asyncio
import contextlib
import csv
import io
import json
import os
import stat
from pathlib import Path
from unittest import mock

from core import alignment_spec, experience, living_soul, llm, paths, prompt_creator, question_asker
from core import skills_creator, tool_specs_creator, translation_layer_creator
from core.cli import main
from core.config import EXISTENTIAL_PROFILE, OPERATIONAL_PROFILE
from tests.fixtures import RepoSandboxTestCase


def _skill(slug: str, group: str, profile: str, body: str = "Body.") -> str:
    return (
        f"---\nname: {slug}\ndescription: d\nsource_group: {group}\nsource_profile: {profile}\n"
        f"compatibility: opencode\n---\n\n# {slug}\n\n{body}\n\n## When To Use\n\nWhen it applies.\n\n"
        f"## Do Not Use\n\nOtherwise.\n\n{'Detail. ' * 30}\n"
    )


def _human_profile(headings: list[str]) -> str:
    return "# Profile\n\n" + "".join(f"## {heading}\n\nAbout {heading}.\n\n" for heading in headings)


def _run(argv: list[str]) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = main(argv)
    return code, out.getvalue()


class PromptCreatorTests(RepoSandboxTestCase):
    def _write_answers(self) -> None:
        profile = EXISTENTIAL_PROFILE
        profile.data_dir.mkdir(parents=True)
        with open(profile.answers_path("20260101_000000"), "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["Category", "Goal", "Element", "Question 1", "AI_Answer 1"])
            writer.writeheader()
            writer.writerow(
                {"Category": "Identity", "Goal": "Ground", "Element": "Values",
                 "Question 1": "What matters?", "AI_Answer 1": "Jane Doe said honesty matters."}
            )

    def test_drafts_are_merged_into_the_human_profile(self) -> None:
        self._write_answers()
        fake = self.fake_llm(lambda prompt, label: "FINAL PROFILE" if label == "synthesized profile" else f"draft:{label}")
        asyncio.run(prompt_creator.build(EXISTENTIAL_PROFILE))
        self.assertEqual(EXISTENTIAL_PROFILE.human_profile_path.read_text(encoding="utf-8"), "FINAL PROFILE\n")
        draft_prompt = fake.calls[0]["prompt"]
        self.assertIn("What matters?", draft_prompt)
        self.assertIn("[REDACTED]", draft_prompt)
        self.assertNotIn("Jane Doe", draft_prompt)
        synthesis = fake.calls[-1]
        self.assertEqual(synthesis["provider"], prompt_creator.ENSEMBLE_SYNTHESIS_PROVIDER)
        for provider in prompt_creator.ENSEMBLE_DRAFT_PROVIDERS:
            self.assertIn(f"draft:{provider} draft", synthesis["prompt"])

    def test_a_failed_draft_writes_no_profile(self) -> None:
        self._write_answers()
        self.fake_llm(lambda prompt, label: "" if label == "xai draft" else "text")
        with mock.patch.object(prompt_creator, "requirements", return_value=[]):
            code, out = _run(["--profile", "existential", "build-prompts"])
        self.assertEqual(code, 1)
        self.assertIn("unexpectedly short", out)
        self.assertFalse(EXISTENTIAL_PROFILE.human_profile_path.exists())


class QuestionAskerTests(RepoSandboxTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self._path = mock.patch.dict(os.environ, {"PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}"})
        self._path.start()
        self.addCleanup(self._path.stop)
        self.questions = self.root / "questions.csv"
        self.questions.write_text(
            "Category,Goal,Element,Question 1,Question 2,AI_Answer 2\n"
            "Quality,Verify,Grounded,What does the user protect?,,Existing answer\n",
            encoding="utf-8",
        )
        self._csv = mock.patch.object(type(OPERATIONAL_PROFILE), "questions_csv", property(lambda _: self.questions))
        self._csv.start()
        self.addCleanup(self._csv.stop)

    def _fake_qmd(self, status: str, results: list[dict]) -> None:
        (self.bin / "status.txt").write_text(status + "\n", encoding="utf-8")
        (self.bin / "results.json").write_text(json.dumps(results), encoding="utf-8")
        script = self.bin / "qmd"
        script.write_text(
            f'#!/bin/sh\nif [ "$1" = status ]; then cat "{self.bin}/status.txt"; else cat "{self.bin}/results.json"; fi\n',
            encoding="utf-8",
        )
        script.chmod(script.stat().st_mode | stat.S_IEXEC)

    def test_answers_are_grounded_in_retrieved_passages(self) -> None:
        self._fake_qmd(
            "Updated: 2h ago\nBase (qmd://Base/)\nConsulting (qmd://Consulting/)\nCustomers (qmd://Customers/)",
            [{"file": "qmd://Base/workflow.md", "line": 12, "title": "Workflow evidence",
              "snippet": "The user requires verification before trusting a fix."}],
        )
        fake = self.fake_llm(lambda prompt, label: "Grounded\n answer")
        asyncio.run(question_asker.build(OPERATIONAL_PROFILE))
        self.assertEqual(len(fake.calls), 1)
        self.assertIn("[1] Workflow evidence | qmd://Base/workflow.md:12", fake.calls[0]["prompt"])
        with open(OPERATIONAL_PROFILE.latest_answers(), encoding="utf-8") as handle:
            row = next(csv.DictReader(handle))
        self.assertEqual(row["AI_Answer 1"], "Grounded answer")
        self.assertEqual(row["AI_Answer 2"], "Existing answer")

    def test_no_model_call_without_current_evidence(self) -> None:
        self._fake_qmd("Updated: 30d ago\nBase (qmd://Base/)\nConsulting (qmd://Consulting/)\nCustomers (qmd://Customers/)",
                       [{"file": "f", "snippet": "s"}])
        fake = self.fake_llm(lambda prompt, label: "answer")
        with self.assertRaisesRegex(RuntimeError, "30 days ago"):
            asyncio.run(question_asker.build(OPERATIONAL_PROFILE))
        self.assertEqual(fake.calls, [])

    def test_an_unanswerable_question_stays_empty(self) -> None:
        self._fake_qmd("Updated: 1h ago\nBase (qmd://Base/)\nConsulting (qmd://Consulting/)\nCustomers (qmd://Customers/)",
                       [{"file": "f", "snippet": "s"}])
        self.fake_llm(lambda prompt, label: "")
        with mock.patch("core.question_asker.asyncio.sleep", mock.AsyncMock()):
            with self.assertRaisesRegex(RuntimeError, "1 question"):
                asyncio.run(question_asker.build(OPERATIONAL_PROFILE))
        with open(OPERATIONAL_PROFILE.latest_answers(), encoding="utf-8") as handle:
            self.assertEqual(next(csv.DictReader(handle))["AI_Answer 1"], "")


class SkillsTests(RepoSandboxTestCase):
    def setUp(self) -> None:
        super().setUp()
        headings = [h for spec in EXISTENTIAL_PROFILE.skill_specs for h in spec.source_headings] + ["Unrelated"]
        EXISTENTIAL_PROFILE.artifacts_dir.mkdir(parents=True)
        EXISTENTIAL_PROFILE.human_profile_path.write_text(_human_profile(headings), encoding="utf-8")

    def _reply(self, prompt: str, label: str) -> str:
        spec = next(s for s in EXISTENTIAL_PROFILE.skill_specs if f"declared_slug=\"{s.slug}\"" in prompt)
        content = _skill(spec.slug, spec.source_group, "existential", body=f"From {spec.source_headings[0]}.")
        return content if label.startswith("skill ") else json.dumps({spec.slug: content})

    def test_declared_skills_are_created_then_refined_and_stale_ones_removed(self) -> None:
        stale = paths.SKILLS_DIR / "existential" / "retired-skill" / "SKILL.md"
        imported = paths.SKILLS_DIR / "workflow" / "kept-skill" / "SKILL.md"
        hand_kept = paths.SKILLS_DIR / "existential" / "hand-kept" / "SKILL.md"
        for path, profile in ((stale, "existential"), (imported, "existential"), (hand_kept, "")):
            path.parent.mkdir(parents=True)
            path.write_text(_skill(path.parent.name, "g", profile), encoding="utf-8")
        fake = self.fake_llm(self._reply)
        asyncio.run(skills_creator.build(EXISTENTIAL_PROFILE))
        for spec in EXISTENTIAL_PROFILE.skill_specs:
            written = (paths.SKILLS_DIR / "existential" / spec.slug / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn(f"From {spec.source_headings[0]}.", written)
        self.assertNotIn("Unrelated", fake.calls[0]["prompt"])
        self.assertFalse(stale.exists())
        self.assertTrue(imported.exists())
        self.assertFalse(hand_kept.exists())

        asyncio.run(skills_creator.build(EXISTENTIAL_PROFILE))
        refine = fake.calls[-1]
        self.assertTrue(refine["label"].startswith("skill "))
        self.assertIn("<existing_canonical_skill>", refine["prompt"])

    def test_cleanup_uses_folder_ownership_for_both_profiles(self) -> None:
        for profile, other in ((EXISTENTIAL_PROFILE, OPERATIONAL_PROFILE),
                               (OPERATIONAL_PROFILE, EXISTENTIAL_PROFILE)):
            with self.subTest(profile=profile.name):
                owned = paths.SKILLS_DIR / profile.name
                incomplete = owned / "incomplete-skill"
                incomplete.mkdir(parents=True, exist_ok=True)
                stale = []
                for slug, metadata in (("no-metadata", ""), ("foreign-metadata", other.name)):
                    path = owned / slug / "SKILL.md"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(_skill(slug, "g", metadata), encoding="utf-8")
                    stale.append(path)
                preserved = [
                    paths.SKILLS_DIR / "workflow" / "manual-import" / "SKILL.md",
                    paths.SKILLS_DIR / other.name / "other-profile" / "SKILL.md",
                    owned / profile.skill_specs[0].slug / "SKILL.md",
                ]
                for path in preserved:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(_skill(path.parent.name, "g", profile.name), encoding="utf-8")
                before = {path: path.read_bytes() for path in preserved}
                skills_creator.remove_undeclared(profile)
                self.assertFalse(incomplete.exists())
                for path in stale:
                    self.assertFalse(path.parent.exists())
                for path, content in before.items():
                    self.assertEqual(path.read_bytes(), content)

    def test_a_skill_missing_its_headings_fails(self) -> None:
        EXISTENTIAL_PROFILE.human_profile_path.write_text(_human_profile(["Core Frame"]), encoding="utf-8")
        self.fake_llm(self._reply)
        with self.assertRaisesRegex(ValueError, "missing headings"):
            asyncio.run(skills_creator.build(EXISTENTIAL_PROFILE))


class ToolSpecsTests(RepoSandboxTestCase):
    def setUp(self) -> None:
        super().setUp()
        OPERATIONAL_PROFILE.artifacts_dir.mkdir(parents=True)
        OPERATIONAL_PROFILE.human_profile_path.write_text("# Profile\n", encoding="utf-8")

    @staticmethod
    def _spec(name: str) -> str:
        return f"# {name}\n\n## Mission\n\n## Use This Tool For\n\n## Decision Rules\n\n## Avoid\n\n" + "x" * 200

    def test_specs_are_written_and_retired_ones_removed(self) -> None:
        retired = OPERATIONAL_PROFILE.tool_specs_dir / "old.md"
        retired.parent.mkdir(parents=True)
        retired.write_text("old", encoding="utf-8")
        self.fake_llm(lambda prompt, label: json.dumps({name: self._spec(name) for name in OPERATIONAL_PROFILE.supported_tools}))
        asyncio.run(tool_specs_creator.build(OPERATIONAL_PROFILE))
        self.assertEqual(sorted(p.name for p in OPERATIONAL_PROFILE.tool_specs_dir.glob("*.md")), ["memory.md", "tasks.md"])

    def test_a_reply_missing_a_tool_writes_nothing(self) -> None:
        self.fake_llm(lambda prompt, label: json.dumps({"memory.md": self._spec("memory.md")}))
        with self.assertRaisesRegex(ValueError, "must be exactly"):
            asyncio.run(tool_specs_creator.build(OPERATIONAL_PROFILE))
        self.assertFalse(OPERATIONAL_PROFILE.tool_specs_dir.exists())

    def test_a_profile_without_tools_refuses(self) -> None:
        code, out = _run(["--profile", "existential", "build-tool-specs"])
        self.assertEqual(code, 1)
        self.assertIn("does not generate tool specs", out)


class TranslationLayerTests(RepoSandboxTestCase):
    def setUp(self) -> None:
        super().setUp()
        for profile in (EXISTENTIAL_PROFILE, OPERATIONAL_PROFILE):
            profile.artifacts_dir.mkdir(parents=True)
            profile.human_profile_path.write_text(f"{profile.name} human profile", encoding="utf-8")

    def test_posture_and_lineage_feed_the_soul_and_absorbed_records_are_declared(self) -> None:
        for record_id in ("exp-kept", "exp-dropped"):
            record = {"id": record_id, "title": record_id, "body": f"Do {record_id}.", "sources": ["s1"], "clusterId": "g-1",
                      "evidence": [{"source": "s1", "text": "q"}], "counterevidence": "none", "compilerImplication": "c"}
            experience.write(record, {"id": "e1"}, "prop-1")
        experience.withdraw(["exp-dropped"], "worse")
        fake = self.fake_llm(lambda prompt, label: "POSTURE TEXT" if label == "interaction posture" else "SOUL TEXT")
        asyncio.run(translation_layer_creator.build())

        posture_prompt, soul_prompt = (call["prompt"] for call in fake.calls)
        self.assertIn("existential human profile", posture_prompt)
        self.assertIn("operational human profile", posture_prompt)
        self.assertIn("POSTURE TEXT", soul_prompt)
        self.assertIn('<record id="exp-kept" status="adopted">', soul_prompt)
        self.assertIn('<record id="exp-dropped" status="withdrawn">', soul_prompt)
        self.assertEqual(paths.BOOTSTRAP_SOUL_PATH.read_text(encoding="utf-8"), "SOUL TEXT\n")
        self.assertEqual(living_soul.absorbed_ids(paths.BOOTSTRAP_SOUL_PATH), {"exp-kept"})

    def test_an_empty_soul_is_never_written(self) -> None:
        self.fake_llm(lambda prompt, label: "POSTURE" if label == "interaction posture" else "")
        with self.assertRaisesRegex(ValueError, "translation soul"):
            asyncio.run(translation_layer_creator.build())
        self.assertFalse(paths.BOOTSTRAP_SOUL_PATH.exists())


class AlignmentSpecTests(RepoSandboxTestCase):
    def test_spec_wraps_the_reply_and_tags_each_skill_with_its_group(self) -> None:
        for group, slug, profile in (("existential", "mode-detection", "existential"), ("workflow", "imported", "")):
            path = paths.SKILLS_DIR / group / slug / "SKILL.md"
            path.parent.mkdir(parents=True)
            path.write_text(_skill(slug, "g", profile), encoding="utf-8")
        fake = self.fake_llm(lambda prompt, label: "CHECKLIST " * 30)
        asyncio.run(alignment_spec.build())
        prompt = fake.calls[0]["prompt"]
        self.assertIn('<skill group="existential" source_profile="existential" name="mode-detection">', prompt)
        self.assertIn('<skill group="workflow" name="imported">', prompt)
        spec = paths.ALIGNMENT_SPEC_PATH.read_text(encoding="utf-8")
        self.assertTrue(spec.startswith(alignment_spec.SPEC_PREAMBLE))
        self.assertIn("CHECKLIST", spec)

    def test_no_skills_refuses(self) -> None:
        self.assertTrue(any("No skills found" in issue for issue in alignment_spec.requirements()))


class LLMTests(RepoSandboxTestCase):
    def test_only_a_fence_wrapping_the_whole_reply_is_removed(self) -> None:
        self.assertEqual(llm.strip_fence("```markdown\n# Title\n```"), "# Title")
        inner = "# Title\n\n```bash\nls\n```\n\nAfter."
        self.assertEqual(llm.strip_fence(inner), inner)

    def test_short_replies_raise_and_the_client_is_closed(self) -> None:
        client = mock.AsyncMock()
        with mock.patch.object(llm, "_client", return_value=client), mock.patch.object(
            llm, "_generate", mock.AsyncMock(return_value="```\nhi\n```")
        ):
            self.assertEqual(asyncio.run(llm.complete("p")), "hi")
            with self.assertRaisesRegex(ValueError, "spec from anthropic is unexpectedly short"):
                asyncio.run(llm.complete("p", min_chars=10, label="spec"))
        self.assertEqual(client.close.await_count, 2)

    def test_missing_keys_are_reported(self) -> None:
        with mock.patch.dict(os.environ, {"XAI_API_KEY": ""}):
            self.assertTrue(llm.missing_config("xai"))
        self.assertTrue(llm.missing_config("nope"))


class RepoHealthTests(RepoSandboxTestCase):
    def test_every_profile_and_alignment_prompt_is_a_valid_template(self) -> None:
        from core import health_check

        for profile in (EXISTENTIAL_PROFILE, OPERATIONAL_PROFILE):
            self.assertEqual(health_check.check_prompts(profile), [], profile.name)
        bad = self.root / "bad.md"
        bad.write_text("Use {0} here", encoding="utf-8")
        self.assertTrue(health_check.check_template(bad))

    def test_checked_in_skill_slugs_are_unique(self) -> None:
        skills_dir = Path(__file__).resolve().parents[1] / "workspaces" / "skills"
        slugs = [path.parent.name for path in skills_dir.glob("*/*/SKILL.md")]
        self.assertTrue(slugs)
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_list_profiles(self) -> None:
        code, out = _run(["list-profiles"])
        self.assertEqual((code, out.split()), (0, ["existential", "operational"]))


if __name__ == "__main__":
    import unittest

    unittest.main()


class SkillEnhancerTests(RepoSandboxTestCase):
    def test_a_path_to_one_hermes_skill_only_enhances_that_skill(self) -> None:
        import time

        from core import skill_enhancer

        for slug in ("alpha", "beta"):
            path = paths.SKILLS_DIR / "workflow" / slug / "SKILL.md"
            path.parent.mkdir(parents=True)
            path.write_text(_skill(slug, "g", ""), encoding="utf-8")
        time.sleep(0.01)
        hermes = self.root / "hermes" / "alpha" / "SKILL.md"
        hermes.parent.mkdir(parents=True)
        hermes.write_text(_skill("alpha", "g", "", body="Newer upstream body."), encoding="utf-8")
        fake = self.fake_llm(lambda prompt, label: _skill("alpha", "g", "", body="Enhanced."))
        with mock.patch.object(skill_enhancer, "DEFAULT_HERMES_SKILLS_DIR", self.root / "none"):
            self.assertEqual(skill_enhancer.run(hermes_path=hermes.parent, apply=True), 0)
        self.assertEqual([call["label"] for call in fake.calls], ["enhanced skill alpha"])
        self.assertIn("Enhanced.", (paths.SKILLS_DIR / "workflow" / "alpha" / "SKILL.md").read_text(encoding="utf-8"))
        self.assertNotIn("Enhanced.", (paths.SKILLS_DIR / "workflow" / "beta" / "SKILL.md").read_text(encoding="utf-8"))
