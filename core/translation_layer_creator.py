#!/usr/bin/env python3
"""Build the bootstrap SOUL and interaction posture from every profile's human profile.

1. Posture: the profile sources and the posture seed produce INTERACTION_POSTURE.md.
2. SOUL: the profile sources, that posture, the soul seed and the full runtime
   lineage (every record adopted or withdrawn in use) produce SOUL.md.

The lineage records the new SOUL took into account are written to
``absorbed.json`` beside it, so the living SOUL does not add them again.
"""

from __future__ import annotations

from typing import List

from core import experience, living_soul, llm, paths
from core.config import all_profiles

def requirements() -> List[str]:
    issues = llm.missing_config(llm.DEFAULT_PROVIDER)
    issues.extend(
        f"Human profile not found at {profile.human_profile_path}; run build-prompts --profile {profile.name}"
        for profile in all_profiles()
        if not profile.human_profile_path.exists()
    )
    return issues


def load_profile_sources() -> str:
    """Every profile's human profile, tagged with its layer."""
    return "\n\n".join(
        f'<profile_source layer="{profile.name}" artifact="human_profile">\n'
        f"{profile.human_profile_path.read_text(encoding='utf-8').strip()}\n"
        "</profile_source>"
        for profile in all_profiles()
    )


async def build() -> None:
    sources = load_profile_sources()
    lineage = experience.lineage()

    posture = await llm.complete(
        (paths.ALIGNMENT_PROMPTS_DIR / "interaction_posture_seed.md").read_text(encoding="utf-8").format(profile_sources=sources),
        label="interaction posture",
    )
    paths.INTERACTION_POSTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    paths.INTERACTION_POSTURE_PATH.write_text(posture + "\n", encoding="utf-8")
    print(f"Info: Wrote interaction posture to {paths.INTERACTION_POSTURE_PATH}")

    soul = await llm.complete(
        (paths.ALIGNMENT_PROMPTS_DIR / "soul_seed.md").read_text(encoding="utf-8").format(
            profile_sources=sources, interaction_posture=posture, lineage=lineage["text"]
        ),
        label="translation soul",
    )
    paths.BOOTSTRAP_SOUL_PATH.write_text(soul + "\n", encoding="utf-8")
    print(f"Info: Wrote translation layer soul to {paths.BOOTSTRAP_SOUL_PATH}")
    absorbed = living_soul.write_absorbed(paths.BOOTSTRAP_SOUL_PATH, lineage["records"])
    print(f"Info: Bootstrap absorbed {len(lineage['records'])} lineage record(s); wrote {absorbed}")
