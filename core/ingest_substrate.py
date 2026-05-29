#!/usr/bin/env python3
"""Project schema graph/focus exports into ready-to-query JSONL packets."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

from core.config import Config


GRAPH_GROUPS = (
    "people",
    "organizations",
    "places",
    "events",
    "tasks",
    "projects",
    "concepts",
    "notes",
    "sources",
    "journals",
)

FOCUS_RELATION_GROUPS = ("people", "concepts", "events", "projects")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")
            count += 1
    return count


def _graph_page_records(graph: dict[str, Any], source_path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for page_type in GRAPH_GROUPS:
        for page in graph.get(page_type, []) or []:
            records.append(
                {
                    "kind": "graph_page",
                    "page_type": page_type,
                    "source_file": str(source_path),
                    "slug": page.get("slug"),
                    "title": page.get("title"),
                    "body": page.get("body"),
                    "date": page.get("date"),
                    "frontmatter": page.get("frontmatter", {}),
                    "mention_count": len(page.get("mentions", []) or []),
                }
            )

    return records


def _mention_evidence_records(
    graph: dict[str, Any], source_path: Path
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for page_type in GRAPH_GROUPS:
        for page in graph.get(page_type, []) or []:
            for mention in page.get("mentions", []) or []:
                records.append(
                    {
                        "kind": "mention_evidence",
                        "target_slug": page.get("slug"),
                        "target_page_type": page_type,
                        "source_file": str(source_path),
                        "source_slug": mention.get("slug"),
                        "source_title": mention.get("title"),
                        "source_date": mention.get("date"),
                        "matched_lines": mention.get("matched_lines", []),
                        "expansion_rules": mention.get("expansion_rules", []),
                    }
                )

    return records


def _focus_source_note_records(
    bundle: dict[str, Any], source_path: Path
) -> list[dict[str, Any]]:
    focus = bundle.get("focus", {}) or {}
    records: list[dict[str, Any]] = []

    for note in bundle.get("source_notes", []) or []:
        records.append(
            {
                "kind": "focus_source_note",
                "focus_bundle_id": bundle.get("id"),
                "focus_kind": focus.get("kind"),
                "focus_slug": focus.get("slug"),
                "focus_body": bundle.get("focus_body"),
                "source_file": str(source_path),
                "note_slug": note.get("note_slug"),
                "source_path": note.get("source_path"),
                "note_title": note.get("note_title"),
                "note_summary": note.get("note_summary"),
                "note_date": note.get("note_date"),
                "matched_lines": note.get("matched_lines", []),
            }
        )

    return records


def _focus_relation_records(
    bundle: dict[str, Any], source_path: Path
) -> list[dict[str, Any]]:
    focus = bundle.get("focus", {}) or {}
    relations = bundle.get("relations", {}) or {}
    records: list[dict[str, Any]] = []

    for relation_group in FOCUS_RELATION_GROUPS:
        for relation in relations.get(relation_group, []) or []:
            records.append(
                {
                    "kind": "focus_relation",
                    "focus_bundle_id": bundle.get("id"),
                    "focus_kind": focus.get("kind"),
                    "focus_slug": focus.get("slug"),
                    "focus_body": bundle.get("focus_body"),
                    "relation_group": relation_group,
                    "source_file": str(source_path),
                    "related_slug": relation.get("slug"),
                    "related_title": relation.get("title"),
                    "related_source_path": relation.get("source_path"),
                    "note_slugs": relation.get("note_slugs", []),
                    "mentions": relation.get("mentions", []),
                }
            )

    return records


def convert_substrate_exports(
    *,
    graph_path: Path | None,
    focus_paths: list[Path],
    output_dir: Path,
) -> dict[str, int]:
    graph_pages: list[dict[str, Any]] = []
    mention_evidence: list[dict[str, Any]] = []
    focus_source_notes: list[dict[str, Any]] = []
    focus_relations: list[dict[str, Any]] = []
    counts: dict[str, int] = {}

    if graph_path is not None:
        graph = _load_json(graph_path)
        graph_pages.extend(_graph_page_records(graph, graph_path))
        mention_evidence.extend(_mention_evidence_records(graph, graph_path))

    for focus_path in focus_paths:
        bundle = _load_json(focus_path)
        focus_source_notes.extend(_focus_source_note_records(bundle, focus_path))
        focus_relations.extend(_focus_relation_records(bundle, focus_path))

    output_dir.mkdir(parents=True, exist_ok=True)

    if graph_path is not None:
        counts["graph_pages"] = _write_jsonl(output_dir / "graph_pages.jsonl", graph_pages)
        counts["mention_evidence"] = _write_jsonl(
            output_dir / "mention_evidence.jsonl", mention_evidence
        )

    if focus_paths:
        counts["focus_source_notes"] = _write_jsonl(
            output_dir / "focus_source_notes.jsonl", focus_source_notes
        )
        counts["focus_relations"] = _write_jsonl(
            output_dir / "focus_relations.jsonl", focus_relations
        )

    return counts


def run(
    config: Config,
    *,
    graph_path: Path | None = None,
    focus_paths: list[Path] | None = None,
    output_dir: Path | None = None,
) -> int:
    resolved_focus_paths = focus_paths or []

    if graph_path is None and not resolved_focus_paths:
        print("Error: provide --graph and/or at least one --focus export path")
        return 1

    for path in [graph_path, *resolved_focus_paths]:
        if path is None:
            continue
        if not path.exists():
            print(f"Error: input file not found: {path}")
            return 1

    resolved_output_dir = output_dir or (config.paths.READY_DIR / "substrate")

    try:
        counts = convert_substrate_exports(
            graph_path=graph_path,
            focus_paths=resolved_focus_paths,
            output_dir=resolved_output_dir,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Info: Wrote substrate packets to {resolved_output_dir}")
    for name, count in counts.items():
        print(f"- {name}: {count}")
    return 0


__all__ = ["convert_substrate_exports", "run"]
