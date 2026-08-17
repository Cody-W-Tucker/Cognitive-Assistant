#!/usr/bin/env python3
"""Candidate-plan to final-plan enrichment and deterministic bundle commit.

This module consumes a validated ``CandidateAgentPlan`` (Section 5 of the Agent
Archetype System Replacement plan), deterministically enriches it into an
``AgentPlan`` (recomputed role settings, derived social map, derived
role-scoped authority, and the single final-authority effective control),
renders the bundle projections (``persona_map.md`` and ``agents/*.md``) solely
from the final plan, and commits them under a strict staged protocol:

  1. Assemble the final JSON and all projections in a temporary staging dir.
  2. Validate final-plan semantics and byte-exact projection hashes there.
  3. Back up and atomically replace only the bundle projections, keeping a
     rollback journal.
  4. On any in-process exception, restore every replaced projection and never
     replace ``agent_plan.json``.
  5. Atomically replace ``agent_plan.json`` last; it is the commit marker.

Startup reconciliation removes abandoned staging, re-renders from a valid
existing plan, treats projections without a plan as orphans, and fails closed
on a corrupt plan. ``INTERACTION_POSTURE.md`` is upstream and is never touched
by reconciliation, projection repair, or crash recovery.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from core.archetype_catalog import ARCHETYPES_DIR, load_archetype_catalog
from core.agent_plan_validator import (
    TRIGGER_IDS,
    ValidationError,
    compute_projection_hashes,
    enrich_candidate_to_planned,
    load_domain_policy,
    sha256_text,
    validate_agent_plan,
    validate_agent_plan_semantics,
    validate_candidate_plan,
)

# Defined locally to avoid importing core.config (which pulls in optional
# runtime-only dependencies such as python-dotenv) at module import time.
ROOT_DIR = Path(__file__).resolve().parent.parent


OUTPUT_DIR = ROOT_DIR / "workspaces" / "alignment" / "artifacts"
PERSONA_MAP_FILE = OUTPUT_DIR / "persona_map.md"
AGENTS_DIR = OUTPUT_DIR / "agents"
PLAN_FILE = OUTPUT_DIR / "agent_plan.json"
POSTURE_FILE = OUTPUT_DIR / "INTERACTION_POSTURE.md"
SOUL_FILE = OUTPUT_DIR / "SOUL.md"
DOMAIN_POLICY_FILE = ROOT_DIR / "profiles" / "alignment" / "domain_policy.json"
STAGING_ROOT = OUTPUT_DIR / ".staging"

PROMPTS_DIR = ROOT_DIR / "profiles" / "alignment" / "prompts"
SELECTION_PROMPT_FILE = PROMPTS_DIR / "archetype_selection_seed.md"
SOUL_PROMPT_FILE = PROMPTS_DIR / "agent_soul_seed.md"
SKILLS_DIR = ROOT_DIR / "workspaces" / "skills"

# Registry identities supplied by code. The selection prompt must reproduce
# these exactly; it never invents an identity or a hash.
OPERATOR_SOURCE_ID = "operator"
SOUL_SOURCE_ID = "translation-layer-soul"
POSTURE_SOURCE_ID = "interaction-posture"

# Operator-declared decision context for this build. These are statements about
# what the generated agent system is for, not claims about the user; they exist
# so `registered_decision_present` and `criteria_present` prerequisites have a
# real, hashed context entry to resolve against.
OPERATOR_DECISION_CONTEXT = (
    "Which specialist agent handles a given operator request, with what "
    "decision control, and at which human gate the result is returned."
)
DECISION_CRITERIA_CONTEXT = (
    "Coverage of a durable operator need over novelty; smallest correct "
    "movement over restructuring; cited evidence over assertion; explicit "
    "handoff over silent scope growth."
)

MAX_SELECTION_OUTPUT_TOKENS = 16000
MAX_SOUL_OUTPUT_TOKENS = 2400
MAX_EVIDENCE_EXCERPT_CHARS = 1600

# Minimal, explicit ASCII folding for LLM and profile text. The validators
# reject non-ASCII outright, so folding happens once, here, at the boundary.
_ASCII_FOLD = {
    "\u2014": "-",
    "\u2013": "-",
    "\u2192": "->",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2026": "...",
    "\u00a0": " ",
    "\u2022": "-",
}


def now_generated_at() -> str:
    """Return the canonical UTC timestamp with no fractional seconds."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_ascii(text: str) -> str:
    """Fold text to strict ASCII with LF line endings.

    Known typographic characters are mapped to their ASCII equivalents; any
    remaining non-ASCII character is dropped. This is a boundary conversion for
    model output and profile source text, never a validator relaxation.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for source, replacement in _ASCII_FOLD.items():
        text = text.replace(source, replacement)
    return "".join(char for char in text if char.isascii())


def repo_relative(path: Path) -> str:
    """Return ``path`` as a repo-relative POSIX path for plan ``Path`` fields.

    Plan ``Path`` values must be relative with no ``..`` segment. Pipeline inputs
    always live under the repo root; a path outside it (tests, an operator-supplied
    absolute path) is recorded by file name so the record stays a valid ``Path``.
    """
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        return resolved.name


def hash_ref(path: Path) -> Dict[str, str]:
    """Return the ``HashRef`` for a file: repo-relative path plus content hash."""
    resolved = Path(path)
    return {
        "path": repo_relative(resolved),
        "sha256": sha256_text(resolved.read_text(encoding="utf-8")),
    }


@dataclass(frozen=True)
class ProjectionBundle:
    """In-memory bundle used by tests and the commit protocol."""

    plan: Dict[str, object]
    rendered: Dict[str, str]


class SoulCreator:
    """Enrich a candidate plan into a final plan and commit the bundle safely."""

    def __init__(
        self,
        output_dir: Path = OUTPUT_DIR,
        staging_root: Optional[Path] = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.persona_map_file = self.output_dir / "persona_map.md"
        self.agents_dir = self.output_dir / "agents"
        self.plan_file = self.output_dir / "agent_plan.json"
        self.staging_root = Path(staging_root) if staging_root else (self.output_dir / ".staging")
        self.agents_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Posture snapshot
    # ------------------------------------------------------------------

    def snapshot_posture(self, posture_path: Path) -> Dict[str, object]:
        """Read ``INTERACTION_POSTURE.md`` and return a validated snapshot.

        The raw bytes are validated first: any non-ASCII byte or any CR byte
        (CRLF/CR line endings) rejects before decoding. The validated bytes are
        then decoded as ASCII/UTF-8 with no newline normalization, and the
        sha256 is computed over exactly the raw validated bytes. A missing
        posture rejects.
        """
        import hashlib

        path = Path(posture_path)
        if not path.exists():
            raise FileNotFoundError(f"Interaction posture not found at {path}")
        raw = path.read_bytes()
        # Reject non-ASCII and CR bytes before decoding.
        for byte in raw:
            if byte > 127 or byte == 13:
                raise ValidationError(
                    "interaction_posture must be strict ASCII with LF line "
                    "endings (no CR/CRLF, no non-ASCII bytes)"
                )
        text = raw.decode("utf-8")  # ASCII subset; no newline normalization
        return {
            "path": "workspaces/alignment/artifacts/INTERACTION_POSTURE.md",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "markdown": text,
        }

    # ------------------------------------------------------------------
    # Rendering (deterministic, from the final plan only)
    # ------------------------------------------------------------------

    def render_persona_map(self, plan: Dict[str, object], catalog: Dict[str, dict]) -> str:
        """Render ``persona_map.md`` solely from the final plan."""
        lines: List[str] = []
        lines.append("# Persona Map\n")
        lines.append(
            f"Generated {plan['generated_at']} from a validated agent plan "
            f"with {len(plan['agents'])} agent(s).\n"  # type: ignore[arg-type]
        )
        for agent in plan["agents"]:  # type: ignore[assignment]
            primary = agent["primary_role"]  # type: ignore[assignment]
            primary_slug = primary["slug"]  # type: ignore[index]
            spec = catalog.get(primary_slug, {})
            name = spec.get("name", primary_slug) if spec else primary_slug
            lines.append(f"## {name} (`{agent['id']}`)\n")
            lines.append(f"- **Primary role:** `{primary_slug}`")
            secondaries = agent["secondary_roles"]  # type: ignore[assignment]
            if secondaries:
                sec = ", ".join(f"`{s['slug']}`" for s in secondaries)
                lines.append(f"- **Secondary roles:** {sec}")
            settings = agent["resolved_design_settings"]  # type: ignore[assignment]
            lines.append(
                f"- **Decision control:** `{settings['decision_control']}`"
            )
            lines.append(
                f"- **Knowledge mode:** `{settings['knowledge']['mode']}`"
            )
            skills = ", ".join(f"`{s}`" for s in agent["skills"])  # type: ignore[assignment]
            lines.append(f"- **Skills:** {skills}")
            posture_ref = plan["interaction_posture"]  # type: ignore[assignment]
            lines.append(
                f"- **Interaction posture:** `{posture_ref['path']}` "
                f"(sha256 `{posture_ref['sha256'][:12]}...`)"
            )
            lines.append("")
        lines.append("## Agent Souls\n")
        lines.append("One soul document per agent lives in `agents/` alongside this file.\n")
        for agent in plan["agents"]:  # type: ignore[assignment]
            lines.append(f"- `{agent['id']}.md`")
        return "\n".join(lines) + "\n"

    def render_agent_soul(self, agent: Dict[str, object]) -> str:
        """Render one agent's soul document, which is its persisted Markdown."""
        return agent["soul_markdown"]  # type: ignore[return-value]

    def render_projections(
        self, plan: Dict[str, object], catalog: Dict[str, dict]
    ) -> Dict[str, str]:
        """Render all bundle projections as a relative-path -> content map."""
        rendered: Dict[str, str] = {}
        rendered["persona_map.md"] = self.render_persona_map(plan, catalog)
        for agent in plan["agents"]:  # type: ignore[assignment]
            rendered[f"agents/{agent['id']}.md"] = self.render_agent_soul(agent)  # type: ignore[index]
        return rendered

    # ------------------------------------------------------------------
    # Enrichment + commit
    # ------------------------------------------------------------------

    def build_bundle(
        self,
        candidate: Dict[str, object],
        *,
        catalog: Dict[str, dict],
        domain_policy: Dict[str, object],
        posture_snapshot: Dict[str, object],
        soul_markdown_by_id: Dict[str, str],
        generation_provenance: Dict[str, object],
        domain_policy_ref: Dict[str, object],
        generated_at: Optional[str] = None,
    ) -> Path:
        """Validate the candidate, enrich to a final plan, render, and commit."""
        validate_candidate_plan(candidate)
        gen_at = generated_at or now_generated_at()
        plan = enrich_candidate_to_planned(
            candidate,
            catalog,
            domain_policy,
            posture_snapshot=posture_snapshot,
            generation_provenance=generation_provenance,
            domain_policy_ref=domain_policy_ref,
            generated_at=gen_at,
            soul_markdown_by_id=soul_markdown_by_id,
        )
        rendered = self.render_projections(plan, catalog)
        self.commit_bundle(plan, rendered, catalog, domain_policy)
        return self.plan_file

    def commit_bundle(
        self,
        plan: Dict[str, object],
        rendered: Dict[str, str],
        catalog: Dict[str, dict],
        domain_policy: Dict[str, object],
    ) -> Path:
        """Staged, projection-only, rollback-safe commit; plan file replaced last."""
        staging = self._new_staging_dir()
        try:
            # 1. Assemble all projections in the staging dir.
            for rel, content in rendered.items():
                target = staging / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

            # 2. Validate semantics and byte-exact projection hashes in staging.
            plan = dict(plan)  # type: ignore[assignment]
            plan["projection_hashes"] = compute_projection_hashes(rendered, plan)
            validate_agent_plan_semantics(plan, catalog, domain_policy)

            # 3. Back up and atomically replace only the bundle projections.
            targets = [self.persona_map_file] + [
                self.agents_dir / f"{agent['id']}.md" for agent in plan["agents"]  # type: ignore[assignment,index]
            ]
            contents = [rendered["persona_map.md"]] + [
                rendered[f"agents/{agent['id']}.md"] for agent in plan["agents"]  # type: ignore[assignment,index]
            ]
            (staging / "journal.json").write_text(
                json.dumps({"targets": [str(t) for t in targets]}, indent=2, sort_keys=True),
                encoding="utf-8",
            )

            backups: Dict[str, Path] = {}
            replaced: List[Path] = []
            try:
                for target, content in zip(targets, contents):
                    if target.exists():
                        backups[str(target)] = self._backup(target, staging)
                    self._atomic_write(target, content)
                    replaced.append(target)
                # 5. agent_plan.json replaced last; sole commit marker.
                self._atomic_write(
                    self.plan_file,
                    json.dumps(plan, ensure_ascii=True, indent=2, sort_keys=False),
                )
            except BaseException:
                # 4. Restore every replaced projection; never touch agent_plan.json.
                for target in reversed(replaced):
                    backup = backups.get(str(target))
                    if backup is not None and backup.exists():
                        target.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
                raise
        except BaseException:
            # Validation or staging failure: leave no artifact mutated; drop staging.
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            raise
        # Success: the staging dir (and its journal) is no longer needed.
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        return self.plan_file

    # ------------------------------------------------------------------
    # Startup reconciliation
    # ------------------------------------------------------------------

    def reconcile_startup(
        self, catalog: Dict[str, dict], domain_policy: Dict[str, object]
    ) -> tuple:
        """Deterministic pre-build recovery.

        Returns ``("valid", plan)`` when an existing plan is authoritative,
        ``("fresh", None)`` when no plan exists (orphan projections removed).
        Raises ``ValidationError`` on a corrupt/unparseable/invalid plan so the
        build fails closed before candidate generation.
        """
        # 1. Remove every abandoned build staging directory and rollback journal.
        if self.staging_root.exists():
            for child in sorted(self.staging_root.iterdir()):
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    child.unlink(missing_ok=True)

        # 2. Valid existing plan remains authoritative.
        if self.plan_file.exists():
            try:
                data = json.loads(self.plan_file.read_text(encoding="utf-8"))
                plan = validate_agent_plan(data)
                validate_agent_plan_semantics(plan, catalog, domain_policy)
            except (ValidationError, json.JSONDecodeError) as exc:
                raise ValidationError(f"agent_plan.json is corrupt/invalid: {exc}") from exc
            self._rerender_and_hashcheck_from_plan(plan, catalog)
            return ("valid", plan)

        # 3. No plan: orphaned projections are removed; fresh build proceeds.
        if self.persona_map_file.exists():
            self.persona_map_file.unlink()
        if self.agents_dir.exists():
            for orphan in self.agents_dir.glob("*.md"):
                orphan.unlink()
        return ("fresh", None)

    def _rerender_and_hashcheck_from_plan(
        self, plan: Dict[str, object], catalog: Dict[str, dict]
    ) -> None:
        """Re-render projections from a valid plan and hash-check/repair."""
        rendered = self.render_projections(plan, catalog)
        expected = plan["projection_hashes"]  # type: ignore[assignment]
        self.persona_map_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_projection(self.persona_map_file, rendered["persona_map.md"], expected["persona_map"])  # type: ignore[arg-type]
        for entry in expected["agents"]:  # type: ignore[assignment,index]
            rel = entry["path"]  # type: ignore[index]
            target = self.output_dir / rel
            self._ensure_projection(target, rendered[rel], entry["sha256"])  # type: ignore[index]

    def _ensure_projection(self, target: Path, content: str, expected_sha: str) -> None:
        current_sha = sha256_text(target.read_text(encoding="utf-8")) if target.exists() else None
        if current_sha != expected_sha:
            self._atomic_write(target, content)

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def _new_staging_dir(self) -> Path:
        self.staging_root.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix="build-", dir=str(self.staging_root)))

    def _backup(self, target: Path, staging: Path) -> Path:
        backup = staging / f"backup{len(list(staging.glob('backup*')))}" / target.name
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
        return backup

    def _atomic_write(self, target: Path, content: str) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + f".tmp-{uuid.uuid4().hex}")
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, target)


# ---------------------------------------------------------------------------
# Supplied registries (code-owned, hashed, reproduced verbatim by the model)
# ---------------------------------------------------------------------------


def build_skill_index(skills_dir: Path = SKILLS_DIR) -> Dict[str, Path]:
    """Map every workspace skill slug to its ``SKILL.md`` path."""
    index: Dict[str, Path] = {}
    if not skills_dir.exists():
        return index
    for skill_file in sorted(skills_dir.glob("*/*/SKILL.md")):
        index[skill_file.parent.name] = skill_file
    return index


def _bounded_excerpt(text: str, limit: int = MAX_EVIDENCE_EXCERPT_CHARS) -> str:
    """Return a bounded ASCII excerpt suitable for a ``Text`` field."""
    folded = to_ascii(text).strip()
    if not folded:
        raise ValidationError("profile evidence excerpt is empty after ASCII folding")
    if len(folded) <= limit:
        return folded
    clipped = folded[:limit]
    cut = clipped.rfind(" ")
    return (clipped[:cut] if cut > 0 else clipped).strip()


def build_profile_evidence_registry(
    profile_artifacts: Dict[str, Path],
) -> Dict[str, object]:
    """Build the ``ProfileEvidenceRegistry`` from each profile's human profile.

    ``profile_artifacts`` maps a profile name (``existential``/``operational``)
    to its latest ``human_profile*.md`` path. One bounded, hashed excerpt per
    profile satisfies the "at least one entry from each profile" rule.
    """
    entries: List[Dict[str, object]] = []
    for profile in ("existential", "operational"):
        path = profile_artifacts.get(profile)
        if path is None or not Path(path).exists():
            raise FileNotFoundError(
                f"No human_profile artifact found for the {profile} profile. "
                f"Run `python -m core --profile {profile} build-prompts` first."
            )
        content = Path(path).read_text(encoding="utf-8")
        entries.append(
            {
                "id": f"{profile}-human-profile",
                "profile": profile,
                "excerpt": _bounded_excerpt(content),
                "path": repo_relative(Path(path)),
                "sha256": sha256_text(content),
            }
        )
    return {"entries": entries}


def latest_profile_artifacts() -> Dict[str, Path]:
    """Locate the latest ``human_profile*.md`` artifact for each profile."""
    artifacts: Dict[str, Path] = {}
    for profile in ("existential", "operational"):
        artifacts_dir = ROOT_DIR / "workspaces" / profile / "artifacts"
        matches = sorted(artifacts_dir.glob("human_profile*.md"))
        if matches:
            artifacts[profile] = matches[-1]
    return artifacts


def build_supplied_registries(
    posture_snapshot: Dict[str, object],
    soul_path: Path = SOUL_FILE,
    posture_path: Path = POSTURE_FILE,
    profile_artifacts: Optional[Dict[str, Path]] = None,
) -> Dict[str, object]:
    """Build the five registries plus provenance policy handed to the model.

    Every entry is code-owned and hashed here. The model must reproduce these
    objects byte for byte; ``parse_candidate_response`` enforces that.
    """
    if not soul_path.exists():
        raise FileNotFoundError(
            f"Translation layer SOUL.md not found at {soul_path}. "
            "Run `python -m core build-translation-layer` first."
        )
    soul_text = soul_path.read_text(encoding="utf-8")
    posture_markdown = posture_snapshot["markdown"]  # type: ignore[index]

    provenance_policy = {
        "sources": [
            {
                "id": SOUL_SOURCE_ID,
                "label": "Translation layer soul",
                "path": repo_relative(soul_path),
                "sha256": sha256_text(soul_text),
            },
            {
                "id": POSTURE_SOURCE_ID,
                "label": "Interaction posture",
                "path": posture_snapshot["path"],  # type: ignore[index]
                "sha256": posture_snapshot["sha256"],  # type: ignore[index]
            },
        ]
    }

    context_registry = {
        "entries": [
            {
                "key": "operator-decision",
                "content": OPERATOR_DECISION_CONTEXT,
                "sha256": sha256_text(OPERATOR_DECISION_CONTEXT),
                "source_identity": {
                    "kind": "human",
                    "id": OPERATOR_SOURCE_ID,
                    "disclosure": None,
                },
            },
            {
                "key": "decision-criteria",
                "content": DECISION_CRITERIA_CONTEXT,
                "sha256": sha256_text(DECISION_CRITERIA_CONTEXT),
                "source_identity": {
                    "kind": "human",
                    "id": OPERATOR_SOURCE_ID,
                    "disclosure": None,
                },
            },
            {
                "key": "interaction-posture",
                "content": _bounded_excerpt(posture_markdown),  # type: ignore[arg-type]
                "sha256": sha256_text(_bounded_excerpt(posture_markdown)),  # type: ignore[arg-type]
                "source_identity": {
                    "kind": "external_system",
                    "id": POSTURE_SOURCE_ID,
                    "disclosure": "external source disclosed",
                },
            },
            {
                "key": "translation-layer-soul",
                "content": _bounded_excerpt(soul_text),
                "sha256": sha256_text(_bounded_excerpt(soul_text)),
                "source_identity": {
                    "kind": "external_system",
                    "id": SOUL_SOURCE_ID,
                    "disclosure": "external source disclosed",
                },
            },
        ]
    }

    return {
        "context_registry": context_registry,
        "human_source_registry": {
            "sources": [{"id": OPERATOR_SOURCE_ID, "label": "Operator"}]
        },
        "stakeholder_registry": {"entries": []},
        "synthetic_perspective_registry": {"entries": []},
        "provenance_policy": provenance_policy,
        "profile_evidence_registry": build_profile_evidence_registry(
            profile_artifacts if profile_artifacts is not None else latest_profile_artifacts()
        ),
    }


SUPPLIED_REGISTRY_KEYS = (
    "context_registry",
    "human_source_registry",
    "stakeholder_registry",
    "synthetic_perspective_registry",
    "provenance_policy",
    "profile_evidence_registry",
)


def build_generation_provenance(
    posture_snapshot: Dict[str, object],
    *,
    model_provider: str,
    skill_index: Dict[str, Path],
    catalog: Dict[str, dict],
) -> Dict[str, object]:
    """Build the ``GenerationProvenance`` record from real prompt/input hashes."""
    return {
        "selection_prompt": hash_ref(SELECTION_PROMPT_FILE),
        "soul_prompt": hash_ref(SOUL_PROMPT_FILE),
        "interaction_posture": {
            "path": posture_snapshot["path"],  # type: ignore[index]
            "sha256": posture_snapshot["sha256"],  # type: ignore[index]
        },
        "role_catalogs": [
            dict(slug=slug, **hash_ref(ARCHETYPES_DIR / f"{slug}.json"))
            for slug in sorted(catalog)
        ],
        "skill_files": [
            dict(slug=slug, **hash_ref(path)) for slug, path in sorted(skill_index.items())
        ],
        "model_provider": model_provider,
    }


# ---------------------------------------------------------------------------
# Prompt rendering and strict response parsing
# ---------------------------------------------------------------------------


def _dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True)


def render_selection_prompt(
    *,
    catalog: Dict[str, dict],
    domain_policy: Dict[str, object],
    posture_snapshot: Dict[str, object],
    supplied: Dict[str, object],
    translation_layer: str,
    template: Optional[str] = None,
) -> str:
    """Render the selection prompt with the catalog, registries, and vocabularies."""
    seed = template if template is not None else SELECTION_PROMPT_FILE.read_text(encoding="utf-8")
    return seed.format(
        catalog=_dump(catalog),
        interaction_posture=posture_snapshot["markdown"],  # type: ignore[index]
        translation_layer=to_ascii(translation_layer),
        context_registry=_dump(supplied["context_registry"]),
        human_source_registry=_dump(supplied["human_source_registry"]),
        stakeholder_registry=_dump(supplied["stakeholder_registry"]),
        synthetic_perspective_registry=_dump(supplied["synthetic_perspective_registry"]),
        provenance_policy=_dump(supplied["provenance_policy"]),
        profile_evidence_registry=_dump(supplied["profile_evidence_registry"]),
        domain_tiers=_dump(domain_policy["impact_tiers"]),
        trigger_vocabulary=_dump(sorted(TRIGGER_IDS)),
    )


def render_soul_prompt(
    *,
    agent_definition: Dict[str, object],
    posture_snapshot: Dict[str, object],
    skill_material: str,
    template: Optional[str] = None,
) -> str:
    """Render the agent soul prompt from a persisted agent definition."""
    seed = template if template is not None else SOUL_PROMPT_FILE.read_text(encoding="utf-8")
    return seed.format(
        agent_definition=_dump(agent_definition),
        interaction_posture=posture_snapshot["markdown"],  # type: ignore[index]
        skill_material=skill_material,
    )


def load_skill_material(skills: List[str], skill_index: Dict[str, Path]) -> str:
    """Concatenate the SKILL.md content for every skill assigned to an agent."""
    sections: List[str] = []
    for slug in skills:
        path = skill_index.get(slug)
        if path is None:
            raise ValidationError(
                f"assigned skill '{slug}' has no SKILL.md under {SKILLS_DIR}"
            )
        content = to_ascii(path.read_text(encoding="utf-8")).strip()
        sections.append(f'<skill slug="{slug}">\n{content}\n</skill>')
    return "\n\n".join(sections)


def parse_candidate_response(text: str, supplied: Dict[str, object]) -> Dict[str, object]:
    """Parse a selection response as exactly a ``CandidateAgentPlan``.

    The response must be a single JSON object that validates against the closed
    candidate schema and reproduces every supplied registry exactly. Neither the
    identities nor the hashes in those registries may be altered by the model.
    """
    payload = strip_code_fences(text)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"selection response is not valid JSON: {exc}") from exc
    candidate = validate_candidate_plan(data)
    for key in SUPPLIED_REGISTRY_KEYS:
        if candidate[key] != supplied[key]:
            raise ValidationError(
                f"selection response altered the supplied {key}; it must be "
                "reproduced exactly"
            )
    return candidate


def agent_definition_for_prompt(planned_agent: Dict[str, object]) -> Dict[str, object]:
    """Strip generation-only fields so the soul prompt sees the plan definition."""
    return {
        key: value
        for key, value in planned_agent.items()
        if key not in ("soul_markdown", "generation_provenance")
    }


def derive_agent_definitions(
    candidate: Dict[str, object],
    catalog: Dict[str, dict],
    domain_policy: Dict[str, object],
    *,
    posture_snapshot: Dict[str, object],
    generation_provenance: Dict[str, object],
    domain_policy_ref: Dict[str, object],
    generated_at: str,
) -> List[Dict[str, object]]:
    """Derive the final agent definitions that soul generation consumes.

    Enrichment is pure, so deriving definitions with placeholder soul Markdown
    yields exactly the settings, social map, and role-scoped authority that the
    committed plan carries. Only the soul text differs, and it is replaced by
    the generated Markdown before the plan is built.
    """
    placeholder = {agent["id"]: "placeholder\n" for agent in candidate["agents"]}  # type: ignore[index,assignment]
    derived = enrich_candidate_to_planned(
        candidate,
        catalog,
        domain_policy,
        posture_snapshot=posture_snapshot,
        generation_provenance=generation_provenance,
        domain_policy_ref=domain_policy_ref,
        generated_at=generated_at,
        soul_markdown_by_id=placeholder,
    )
    return [agent_definition_for_prompt(agent) for agent in derived["agents"]]  # type: ignore[arg-type,union-attr]


def normalize_soul_markdown(text: str, agent_id: str) -> str:
    """Fold a generated soul to strict ASCII Markdown and reject empty output."""
    markdown = to_ascii(strip_code_fences(text)).strip()
    if not markdown:
        raise ValidationError(f"generated soul for agent '{agent_id}' is empty")
    return markdown + "\n"


def strip_code_fences(text: str) -> str:
    """Strip optional Markdown/JSON code fences from a model response."""
    text = text.strip()
    if text.startswith("```"):
        newline = text.find("\n")
        text = text[newline + 1:] if newline != -1 else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


async def _select_candidate(
    handle,
    *,
    api,
    catalog: Dict[str, dict],
    domain_policy: Dict[str, object],
    posture_snapshot: Dict[str, object],
    supplied: Dict[str, object],
    translation_layer: str,
) -> Dict[str, object]:
    """Ask the model for exactly one ``CandidateAgentPlan`` and parse it strictly."""
    from lib.llm import generate_text_async

    prompt = render_selection_prompt(
        catalog=catalog,
        domain_policy=domain_policy,
        posture_snapshot=posture_snapshot,
        supplied=supplied,
        translation_layer=translation_layer,
    )
    response = await generate_text_async(
        handle,
        user_prompt=prompt,
        temperature=api.TEMPERATURE,
        max_output_tokens=MAX_SELECTION_OUTPUT_TOKENS,
    )
    return parse_candidate_response(response, supplied)


async def _generate_souls(
    handle,
    *,
    api,
    agent_definitions: List[Dict[str, object]],
    posture_snapshot: Dict[str, object],
    skill_index: Dict[str, Path],
) -> Dict[str, str]:
    """Generate one soul Markdown per agent from its persisted definition."""
    from lib.llm import generate_text_async

    souls: Dict[str, str] = {}
    for definition in agent_definitions:
        agent_id = definition["id"]  # type: ignore[index]
        prompt = render_soul_prompt(
            agent_definition=definition,
            posture_snapshot=posture_snapshot,
            skill_material=load_skill_material(definition["skills"], skill_index),  # type: ignore[arg-type,index]
        )
        response = await generate_text_async(
            handle,
            user_prompt=prompt,
            temperature=api.TEMPERATURE,
            max_output_tokens=MAX_SOUL_OUTPUT_TOKENS,
        )
        souls[agent_id] = normalize_soul_markdown(response, agent_id)  # type: ignore[index]
    return souls


async def _async_build(
    creator: "SoulCreator",
    *,
    catalog: Dict[str, dict],
    domain_policy: Dict[str, object],
    posture_snapshot: Dict[str, object],
) -> Path:
    """Run selection, soul generation, and the staged bundle commit."""
    from lib.config import APIConfig, DEFAULT_PROVIDER
    from lib.llm import close_client_async, create_client

    api = APIConfig()
    skill_index = build_skill_index()
    supplied = build_supplied_registries(posture_snapshot)
    translation_layer = SOUL_FILE.read_text(encoding="utf-8")
    generation_provenance = build_generation_provenance(
        posture_snapshot,
        model_provider=DEFAULT_PROVIDER,
        skill_index=skill_index,
        catalog=catalog,
    )
    domain_policy_ref = hash_ref(DOMAIN_POLICY_FILE)
    generated_at = now_generated_at()

    handle = create_client(
        api,
        provider=DEFAULT_PROVIDER,
        model=api.get_model(provider=DEFAULT_PROVIDER),
        async_mode=True,
    )
    try:
        candidate = await _select_candidate(
            handle,
            api=api,
            catalog=catalog,
            domain_policy=domain_policy,
            posture_snapshot=posture_snapshot,
            supplied=supplied,
            translation_layer=translation_layer,
        )
        print(f"Info: Selection returned {len(candidate['agents'])} candidate agent(s)")  # type: ignore[arg-type]
        agent_definitions = derive_agent_definitions(
            candidate,
            catalog,
            domain_policy,
            posture_snapshot=posture_snapshot,
            generation_provenance=generation_provenance,
            domain_policy_ref=domain_policy_ref,
            generated_at=generated_at,
        )
        soul_markdown_by_id = await _generate_souls(
            handle,
            api=api,
            agent_definitions=agent_definitions,
            posture_snapshot=posture_snapshot,
            skill_index=skill_index,
        )
    finally:
        await close_client_async(handle)

    return creator.build_bundle(
        candidate,
        catalog=catalog,
        domain_policy=domain_policy,
        posture_snapshot=posture_snapshot,
        soul_markdown_by_id=soul_markdown_by_id,
        generation_provenance=generation_provenance,
        domain_policy_ref=domain_policy_ref,
        generated_at=generated_at,
    )


def run() -> int:
    """Synchronous CLI entry point for ``python -m core build-agents``."""
    import asyncio
    import sys

    from lib.config import APIConfig, DEFAULT_PROVIDER, validate_provider_config

    api = APIConfig()
    issues = validate_provider_config(api, DEFAULT_PROVIDER)
    if issues:
        print("Error: Configuration issues found")
        for issue in issues:
            print(f"- {issue}")
        return 1

    try:
        catalog = load_archetype_catalog()
        domain_policy = load_domain_policy()
        creator = SoulCreator()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        creator.reconcile_startup(catalog, domain_policy)
    except ValidationError as exc:
        print(f"Error: agent_plan.json invalid; failing closed. {exc}", file=sys.stderr)
        print(
            "Remove only workspaces/alignment/artifacts/agent_plan.json, "
            "persona_map.md, and agents/ then rerun build-agents.",
            file=sys.stderr,
        )
        return 1

    try:
        posture_snapshot = creator.snapshot_posture(POSTURE_FILE)
        plan_path = asyncio.run(
            _async_build(
                creator,
                catalog=catalog,
                domain_policy=domain_policy,
                posture_snapshot=posture_snapshot,
            )
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Info: Wrote agent plan and bundle to {plan_path.parent}")
    return 0


__all__ = [
    "SoulCreator",
    "ProjectionBundle",
    "agent_definition_for_prompt",
    "build_generation_provenance",
    "build_profile_evidence_registry",
    "build_skill_index",
    "build_supplied_registries",
    "derive_agent_definitions",
    "hash_ref",
    "latest_profile_artifacts",
    "load_skill_material",
    "normalize_soul_markdown",
    "now_generated_at",
    "parse_candidate_response",
    "render_selection_prompt",
    "render_soul_prompt",
    "repo_relative",
    "run",
    "strip_code_fences",
    "to_ascii",
]
