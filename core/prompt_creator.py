#!/usr/bin/env python3
"""Turn a profile's answered questions into its human profile.

Each draft provider writes a candidate profile from the newest answers CSV;
the synthesis provider merges the candidates into ``human_profile.md``.
Candidates are kept beside it as ``profile_candidate_<provider>.md``.
"""

from __future__ import annotations

import asyncio
import csv
from typing import List

from core import llm
from core.config import ANSWER_COLUMNS, QUESTION_COLUMNS, LayerProfile

ENSEMBLE_DRAFT_PROVIDERS = ("xai", "anthropic", "openai")
ENSEMBLE_SYNTHESIS_PROVIDER = "anthropic"
PROVIDERS = tuple(dict.fromkeys([*ENSEMBLE_DRAFT_PROVIDERS, ENSEMBLE_SYNTHESIS_PROVIDER]))


def requirements(profile: LayerProfile) -> List[str]:
    issues = [issue for provider in PROVIDERS for issue in llm.missing_config(provider)]
    try:
        profile.latest_answers()
    except FileNotFoundError as exc:
        issues.append(str(exc))
    return issues


def load_dataset_context(profile: LayerProfile) -> str:
    """The newest answers CSV as redacted markdown sections, one per category row."""
    dataset = profile.latest_answers()
    print(f"Info: Loading dataset {dataset.name}")
    with open(dataset, "r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    sections: List[str] = []
    redactions = 0
    for row in rows:
        category = row.get("Category", "").strip()
        if not category:
            continue
        answered: List[str] = []
        for index, (question_col, answer_col) in enumerate(zip(QUESTION_COLUMNS, ANSWER_COLUMNS), start=1):
            question = (row.get(question_col) or "").strip()
            answer = (row.get(answer_col) or "").strip()
            if not question or not answer:
                continue
            redacted = profile.redact(answer)
            redactions += redacted != answer
            answered.append(f"{index}. {question}\n\n   {profile.answer_label}: {redacted}")
        if answered:
            sections.append(
                profile.section_header_template.format(category=category)
                + f"\n\n## Goal: **{row.get('Goal', '').strip()}**\n\n"
                + f"**Elements:** {row.get('Element', '').strip()}\n\n"
                + "### Questions:\n\n"
                + "\n\n".join(answered)
            )
    if redactions:
        print(f"Info: Applied redaction to {redactions} entries")
    context = "\n\n---\n\n".join(sections)
    print(f"Info: Loaded {len(sections)} sections ({len(context)} characters)")
    return context


async def build(profile: LayerProfile) -> None:
    prompt = profile.prompt("initial_template").format(context=load_dataset_context(profile))
    drafts = await asyncio.gather(
        *(llm.complete(prompt, provider=provider, label=f"{provider} draft") for provider in ENSEMBLE_DRAFT_PROVIDERS)
    )
    candidates = []
    for provider, draft in zip(ENSEMBLE_DRAFT_PROVIDERS, drafts):
        path = profile.artifacts_dir / f"profile_candidate_{provider}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(draft + "\n", encoding="utf-8")
        print(f"Info: Saved {provider} draft to {path}")
        candidates.append(
            f'<candidate provider="{provider}" model="{llm.model_name(provider)}">\n{draft}\n</candidate>'
        )
    final = await llm.complete(
        profile.prompt("ensemble_synthesis_template").format(candidate_profiles="\n\n".join(candidates)),
        provider=ENSEMBLE_SYNTHESIS_PROVIDER,
        label="synthesized profile",
    )
    profile.human_profile_path.write_text(final + "\n", encoding="utf-8")
    print(f"Info: Saved synthesized profile to {profile.human_profile_path}")
