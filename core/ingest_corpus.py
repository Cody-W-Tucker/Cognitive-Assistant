#!/usr/bin/env python3
"""Normalize raw intake exports into high-signal ready artifacts.

For operational-style profiles. Reads `data/intake/<source>/...` and writes
`data/ready/<source>/*.jsonl` plus a `preprocessing_manifest_<ts>.json`.

Sources handled when their files are present:
  - opencode JSONL
  - cursor JSONL
  - open-webui chat-export-*.json
  - perplexity Search_History.csv, Memory.csv, Conversations.csv
  - OpenAI-Chat-export.zip
  - grok_export.zip
"""

from __future__ import annotations

import csv
import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zipfile import ZipFile

from core.config import Config


SCHEMA_VERSION = "2026-05-01.1"
SEQUENCE_GAP_SECONDS = 30 * 60
SUPPORTED_OPEN_WEBUI_GLOB = "chat-export-*.json"
MAX_USER_TEXT_LENGTH = 2000


@dataclass
class SourceResult:
    """Track output metadata for one normalized source."""

    source: str
    status: str
    output_files: list[str]
    records_written: int
    records_skipped: int
    notes: list[str]


def _now_timestamp(config: Config) -> str:
    return datetime.now().strftime(config.output.TIMESTAMP_FORMAT)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _strip_reasoning_blocks(text: str) -> str:
    cleaned = re.sub(
        r"<details[^>]*type=\"reasoning\"[^>]*>.*?</details>\s*",
        "",
        text,
        flags=re.DOTALL,
    )
    cleaned = re.sub(r"<summary>.*?</summary>", "", cleaned, flags=re.DOTALL)
    return cleaned


def _strip_embedded_tool_transcript(text: str) -> str:
    lines = text.splitlines()
    kept_lines: list[str] = []
    in_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Called the ") and " tool with the following input:" in stripped:
            continue
        if stripped.startswith("<file>") or stripped.startswith("<path>"):
            in_block = True
            continue
        if stripped.startswith("</file>") or stripped.startswith("</path>"):
            in_block = False
            continue
        if in_block:
            continue
        if re.match(
            r"^</?(type|entries|content|commentary|tool_uses|questions?)>.*$",
            stripped,
        ):
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        parts = [_normalize_text(item) for item in value]
        return "\n".join(part for part in parts if part)
    if isinstance(value, dict):
        if "text" in value:
            return _normalize_text(value["text"])
        if "parts" in value:
            return _normalize_text(value["parts"])
        return json.dumps(value, ensure_ascii=True, sort_keys=True)

    text = html.unescape(str(value))
    text = _strip_reasoning_blocks(text)
    text = _strip_embedded_tool_transcript(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _truncate_user_text(text: str, max_length: int = MAX_USER_TEXT_LENGTH) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


def _summarize_repeated_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped_records: dict[str, int] = {}
    ordered_texts: list[str] = []

    for record in records:
        user_text = _truncate_user_text(_normalize_text(record.get("user_text", "")))
        if not user_text:
            continue
        if user_text not in grouped_records:
            grouped_records[user_text] = 0
            ordered_texts.append(user_text)
        grouped_records[user_text] += 1

    summarized_records: list[dict[str, Any]] = []
    for user_text in ordered_texts:
        repeat_count = grouped_records[user_text]
        record = {"user_text": user_text}
        if repeat_count > 1:
            record["repeated"] = repeat_count
        summarized_records.append(record)
    return summarized_records


def _safe_json_dumps(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True)


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    _ensure_parent(path)
    count = 0
    with path.open("w", encoding="utf-8") as file_handle:
        for record in records:
            file_handle.write(_safe_json_dumps(record) + "\n")
            count += 1
    return count


def _first_assistant_child(
    node: dict[str, Any], messages: dict[str, dict[str, Any]]
) -> dict[str, Any] | None:
    for child_id in node.get("childrenIds", []):
        child = messages.get(child_id)
        if child and child.get("role") == "assistant":
            return child
    return None


def _build_opencode_records(path: Path) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    skipped = 0

    with path.open("r", encoding="utf-8") as file_handle:
        for line_number, line in enumerate(file_handle, start=1):
            payload = json.loads(line)
            messages = payload.get("messages", [])
            title = payload.get("title", "")

            for message in messages:
                if message.get("role") != "user":
                    continue
                user_text = _normalize_text(message.get("content", ""))
                if not user_text:
                    skipped += 1
                    continue
                records.append(
                    {
                        "timestamp": message.get("timestamp"),
                        "title": title,
                        "user_text": user_text,
                    }
                )

    return records, skipped


def _build_cursor_records(path: Path) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    skipped = 0

    with path.open("r", encoding="utf-8") as file_handle:
        for line in file_handle:
            payload = json.loads(line)
            messages = payload.get("messages", [])
            workspace_id = payload.get("workspace_id", "")

            user_messages = [m for m in messages if m.get("role") == "user"]
            if not user_messages:
                skipped += 1
                continue

            for message in user_messages:
                user_text = _normalize_text(message.get("content", ""))
                if not user_text:
                    skipped += 1
                    continue
                records.append(
                    {
                        "timestamp": None,
                        "title": workspace_id,
                        "user_text": user_text,
                    }
                )

    return records, skipped


def _flatten_open_webui_chat(
    chat_item: dict[str, Any], source_file: str
) -> list[dict[str, Any]]:
    chat = chat_item.get("chat", {})
    history = chat.get("history", {})
    messages_map = history.get("messages", {})
    interactions: list[dict[str, Any]] = []

    roots = [m for m in messages_map.values() if m.get("parentId") is None]
    roots.sort(key=lambda item: item.get("timestamp", 0))

    for root in roots:
        current = root
        while current:
            if current.get("role") == "user":
                user_text = _normalize_text(current.get("content", ""))
                if user_text:
                    interactions.append(
                        {
                            "timestamp": current.get("timestamp"),
                            "title": chat.get("title", ""),
                            "user_text": user_text,
                        }
                    )

            next_node = None
            for child_id in current.get("childrenIds", []):
                child = messages_map.get(child_id)
                if child is None:
                    continue
                next_node = child
                break
            current = next_node

    return interactions


def _build_open_webui_records(
    directory: Path,
) -> tuple[list[dict[str, Any]], int, list[str]]:
    records: list[dict[str, Any]] = []
    skipped = 0
    notes: list[str] = []

    for path in sorted(directory.glob(SUPPORTED_OPEN_WEBUI_GLOB)):
        try:
            chat_items = _load_json_file(path)
        except json.JSONDecodeError:
            skipped += 1
            notes.append(f"Skipped invalid JSON export: {path.name}")
            continue

        for chat_item in chat_items:
            records.extend(_flatten_open_webui_chat(chat_item, path.name))

    snapshots = sorted(directory.glob("*.snapshot"))
    if snapshots:
        notes.append(
            f"Ignored {len(snapshots)} .snapshot files (unsupported binary/source format)"
        )

    return records, skipped, notes


def _build_perplexity_search_records(path: Path) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    skipped = 0
    previous_timestamp: datetime | None = None
    sequence_number = 0
    sequence_position = 0

    with path.open("r", encoding="utf-8", newline="") as file_handle:
        reader = csv.DictReader(file_handle)
        for row in reader:
            query_text = _normalize_text(row.get("QUERY_STRING", ""))
            timestamp_text = row.get("CREATED", "")
            if not query_text or not timestamp_text:
                skipped += 1
                continue

            timestamp_value = datetime.fromisoformat(timestamp_text)
            if (
                previous_timestamp is None
                or (timestamp_value - previous_timestamp).total_seconds()
                > SEQUENCE_GAP_SECONDS
            ):
                sequence_number += 1
                sequence_position = 1
            else:
                sequence_position += 1
            previous_timestamp = timestamp_value

            records.append(
                {
                    "timestamp": timestamp_text,
                    "title": f"search_sequence:{sequence_number:05d}",
                    "user_text": query_text,
                }
            )

    return records, skipped


def _build_perplexity_memory_records(path: Path) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    skipped = 0

    with path.open("r", encoding="utf-8", newline="") as file_handle:
        reader = csv.DictReader(file_handle)
        for row in reader:
            falsy = {"", "0", "0.0", "False", "false", None}
            if row.get("IS_DELETED") not in falsy:
                skipped += 1
                continue
            if row.get("IS_FORGOTTEN") not in falsy:
                skipped += 1
                continue
            if row.get("IS_INVISIBLE") not in falsy:
                skipped += 1
                continue

            memory_key = _normalize_text(row.get("MEMORY_KEY", ""))
            memory_value = _normalize_text(row.get("MEMORY_VALUE", ""))
            if not memory_key or not memory_value:
                skipped += 1
                continue

            records.append(
                {
                    "timestamp": row.get("LAST_UPDATED_AT", ""),
                    "title": memory_key,
                    "user_text": _normalize_text(row.get("LAST_UPDATED_QUERY", ""))
                    or memory_key,
                }
            )

    return records, skipped


def _build_perplexity_conversation_records(
    path: Path,
) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    skipped = 0

    with path.open("r", encoding="utf-8", newline="") as file_handle:
        reader = csv.DictReader(file_handle)
        for row in reader:
            title = _normalize_text(row.get("TITLE", ""))
            output_payload = row.get("OUTPUT_STR", "")
            if not title or not output_payload:
                skipped += 1
                continue
            try:
                output_data = json.loads(output_payload)
            except json.JSONDecodeError:
                skipped += 1
                continue
            answer_text = _normalize_text(output_data.get("answer", ""))
            if not answer_text:
                skipped += 1
                continue
            records.append(
                {
                    "timestamp": row.get("CREATED", ""),
                    "title": title,
                    "user_text": title,
                }
            )

    return records, skipped


def _first_openai_root(mapping: dict[str, Any]) -> dict[str, Any] | None:
    roots = [node for node in mapping.values() if node.get("parent") is None]
    if not roots:
        return None
    roots.sort(key=lambda item: ((item.get("message") or {}).get("create_time") or 0))
    return roots[0]


def _next_openai_node(
    node: dict[str, Any], mapping: dict[str, Any]
) -> dict[str, Any] | None:
    for child_id in node.get("children", []):
        child = mapping.get(child_id)
        if child is not None:
            return child
    return None


def _flatten_openai_conversation(
    conversation: dict[str, Any], source_file: str
) -> list[dict[str, Any]]:
    mapping = conversation.get("mapping", {})
    root = _first_openai_root(mapping)
    if root is None:
        return []

    interactions: list[dict[str, Any]] = []
    current = root
    while current:
        message = current.get("message") or {}
        author = message.get("author") or {}
        role = author.get("role")
        if role == "user":
            content = message.get("content") or {}
            user_text = _normalize_text(content.get("parts", []))
            if user_text:
                interactions.append(
                    {
                        "timestamp": message.get("create_time"),
                        "title": conversation.get("title", ""),
                        "user_text": user_text,
                    }
                )
        current = _next_openai_node(current, mapping)

    return interactions


def _build_openai_records(path: Path) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    skipped = 0

    with ZipFile(path) as archive:
        with archive.open("conversations.json") as file_handle:
            conversations = json.load(file_handle)

    for conversation in conversations:
        try:
            records.extend(_flatten_openai_conversation(conversation, path.name))
        except Exception:
            skipped += 1

    return records, skipped


def _grok_timestamp_to_iso(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    date_value = value.get("$date")
    if isinstance(date_value, dict):
        raw_value = date_value.get("$numberLong")
    else:
        raw_value = date_value
    if raw_value in {None, ""}:
        return None
    try:
        timestamp = datetime.fromtimestamp(int(raw_value) / 1000)
    except (TypeError, ValueError, OSError):
        return None
    return timestamp.isoformat()


def _build_grok_records(
    path: Path,
) -> tuple[list[dict[str, Any]], int, list[str]]:
    notes: list[str] = []
    records: list[dict[str, Any]] = []
    skipped = 0

    with ZipFile(path) as archive:
        backend_members = [
            name for name in archive.namelist() if name.endswith("prod-grok-backend.json")
        ]
        if not backend_members:
            notes.append("No prod-grok-backend.json member found in export")
            return records, skipped, notes
        with archive.open(backend_members[0]) as file_handle:
            payload = json.load(file_handle)

    conversations = (
        payload.get("conversations", []) if isinstance(payload, dict) else []
    )
    for conversation_item in conversations:
        conversation = conversation_item.get("conversation", {})
        title = (
            _normalize_text(conversation.get("title", ""))
            or conversation.get("id", "")
        )
        responses = conversation_item.get("responses", [])
        if not isinstance(responses, list):
            skipped += 1
            continue

        for response_item in responses:
            response = response_item.get("response", {})
            if response.get("sender") != "human":
                continue
            user_text = _normalize_text(response.get("message", ""))
            if not user_text:
                skipped += 1
                continue
            records.append(
                {
                    "timestamp": _grok_timestamp_to_iso(response.get("create_time")),
                    "title": title,
                    "user_text": user_text,
                }
            )

    media_posts = (
        payload.get("media_posts", []) if isinstance(payload, dict) else []
    )
    if media_posts:
        notes.append(
            f"Ignored {len(media_posts)} Grok media_posts entries; "
            "extracted conversation prompts only"
        )

    return records, skipped, notes


def _write_manifest(
    config: Config, path: Path, results: list[SourceResult]
) -> None:
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "intake_dir": str(config.paths.INTAKE_DIR),
        "ready_dir": str(config.paths.READY_DIR),
        "review_globs": config.profile.rlm_review_globs or [],
        "schema_version": SCHEMA_VERSION,
        "sources": [result.__dict__ for result in results],
    }
    _ensure_parent(path)
    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def run(config: Config) -> int:
    """Normalize configured intake sources for the active profile."""
    if not config.profile.has_corpus_ingest:
        print(
            f"Error: profile '{config.profile.name}' does not enable corpus "
            "ingestion"
        )
        return 1

    timestamp = _now_timestamp(config)
    intake_dir = config.paths.INTAKE_DIR
    ready_dir = config.paths.READY_DIR
    results: list[SourceResult] = []

    opencode_path = intake_dir / "opencode_conversations_20260328_105151.jsonl"
    if opencode_path.exists():
        records, skipped = _build_opencode_records(opencode_path)
        records = _summarize_repeated_records(records)
        output_path = ready_dir / "opencode" / f"interactions_{timestamp}.jsonl"
        written = _write_jsonl(output_path, records)
        results.append(
            SourceResult("opencode", "processed", [str(output_path)], written, skipped, [])
        )

    cursor_path = intake_dir / "cursor_ultimate_20260428_200712.jsonl"
    if cursor_path.exists():
        records, skipped = _build_cursor_records(cursor_path)
        records = _summarize_repeated_records(records)
        output_path = ready_dir / "cursor" / f"requests_{timestamp}.jsonl"
        written = _write_jsonl(output_path, records)
        results.append(
            SourceResult("cursor", "processed", [str(output_path)], written, skipped, [])
        )

    open_webui_dir = intake_dir / "open-webui"
    if open_webui_dir.exists():
        records, skipped, notes = _build_open_webui_records(open_webui_dir)
        records = _summarize_repeated_records(records)
        output_path = ready_dir / "open-webui" / f"interactions_{timestamp}.jsonl"
        written = _write_jsonl(output_path, records)
        results.append(
            SourceResult(
                "open-webui", "processed", [str(output_path)], written, skipped, notes
            )
        )

    perplexity_dir = intake_dir / "perplexity"
    if perplexity_dir.exists():
        output_files: list[str] = []
        written_total = 0
        skipped_total = 0

        search_path = perplexity_dir / "Search_History.csv"
        if search_path.exists():
            records, skipped = _build_perplexity_search_records(search_path)
            records = _summarize_repeated_records(records)
            output_path = ready_dir / "perplexity" / f"search_queries_{timestamp}.jsonl"
            written = _write_jsonl(output_path, records)
            output_files.append(str(output_path))
            written_total += written
            skipped_total += skipped

        memory_path = perplexity_dir / "Memory.csv"
        if memory_path.exists():
            records, skipped = _build_perplexity_memory_records(memory_path)
            records = _summarize_repeated_records(records)
            output_path = ready_dir / "perplexity" / f"memory_items_{timestamp}.jsonl"
            written = _write_jsonl(output_path, records)
            output_files.append(str(output_path))
            written_total += written
            skipped_total += skipped

        conversations_path = perplexity_dir / "Conversations.csv"
        if conversations_path.exists():
            records, skipped = _build_perplexity_conversation_records(conversations_path)
            records = _summarize_repeated_records(records)
            output_path = ready_dir / "perplexity" / f"conversations_{timestamp}.jsonl"
            written = _write_jsonl(output_path, records)
            output_files.append(str(output_path))
            written_total += written
            skipped_total += skipped

        results.append(
            SourceResult(
                "perplexity", "processed", output_files, written_total, skipped_total, []
            )
        )

    openai_path = intake_dir / "OpenAI-Chat-export.zip"
    if openai_path.exists():
        records, skipped = _build_openai_records(openai_path)
        records = _summarize_repeated_records(records)
        output_path = ready_dir / "openai" / f"interactions_{timestamp}.jsonl"
        written = _write_jsonl(output_path, records)
        results.append(
            SourceResult("openai", "processed", [str(output_path)], written, skipped, [])
        )

    grok_path = intake_dir / "grok_export.zip"
    if grok_path.exists():
        records, skipped, notes = _build_grok_records(grok_path)
        records = _summarize_repeated_records(records)
        output_path = ready_dir / "grok" / f"interactions_{timestamp}.jsonl"
        written = _write_jsonl(output_path, records)
        results.append(
            SourceResult("grok", "processed", [str(output_path)], written, skipped, notes)
        )

    manifest_path = ready_dir / f"preprocessing_manifest_{timestamp}.json"
    _write_manifest(config, manifest_path, results)

    print("Preprocessing complete")
    for result in results:
        print(
            f"- {result.source}: {result.status} "
            f"({result.records_written} written, {result.records_skipped} skipped)"
        )
        for output_file in result.output_files:
            print(f"  - {output_file}")
    return 0


__all__ = ["run"]
