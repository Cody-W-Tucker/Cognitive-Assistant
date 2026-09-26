"""Fill the Langfuse annotation queue from Hermes routing scores.

This module deliberately owns only the API handoff. Human labels and datasets
remain in Langfuse.
"""

from __future__ import annotations

import base64
import argparse
import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SCORE_NAMES = ("requested_mode", "delivered_mode", "route_fit", "route_gap")


class LangfuseError(RuntimeError):
    """Raised when Langfuse returns an unusable response."""


@dataclass(frozen=True)
class ReviewConfig:
    url: str = "https://cloud.langfuse.com"
    pending_cap: int = 20
    per_run: int = 8
    page_size: int = 100

    @classmethod
    def from_env(cls) -> "ReviewConfig":
        return cls(
            url=os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com").rstrip("/"),
            pending_cap=int(os.environ.get("LANGFUSE_PENDING_CAP", "20")),
            per_run=int(os.environ.get("LANGFUSE_PER_RUN", "8")),
            page_size=int(os.environ.get("LANGFUSE_PAGE_SIZE", "100")),
        )


class LangfuseClient:
    def __init__(self, public_key: str, secret_key: str, base_url: str, opener: Callable[..., Any] | None = None) -> None:
        token = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
        self._headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
        self.base_url = base_url.rstrip("/")
        self.opener = opener or urlopen
        self._injected_opener = opener is not None

    def request(self, method: str, path: str, query: dict[str, Any] | None = None, body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            url += "?" + urlencode({key: value for key, value in query.items() if value is not None})
        request = Request(url, method=method, headers=self._headers)
        if body is not None:
            request.data = json.dumps(body).encode()
        opened = self.opener(request) if self._injected_opener else self.opener(request, timeout=45)
        with opened as response:
            if response.status < 200 or response.status >= 300:
                raise LangfuseError(f"Langfuse {method} {path} returned {response.status}")
            return json.loads(response.read())

    def scores(self, cursor: str | None, limit: int) -> dict[str, Any]:
        return self.request(
            "GET",
            "/api/public/v3/scores",
            {"fields": "core,details,subject", "limit": limit, "cursor": cursor},
        )

    def observation(self, observation_id: str) -> dict[str, Any]:
        filter_value = json.dumps([{"type": "string", "column": "id", "operator": "=", "value": observation_id}])
        response = self.request(
            "GET",
            "/api/public/v2/observations",
            {"fields": "core,basic,io", "filter": filter_value},
        )
        observations = response.get("data", [])
        matches = [item for item in observations if item.get("id") == observation_id]
        if len(matches) != 1:
            raise LangfuseError(f"Observation filter did not return exactly {observation_id}")
        return matches[0]

    def queues(self) -> list[dict[str, Any]]:
        return self._paged("/api/public/annotation-queues")

    def queue_items(self, queue_id: str) -> list[dict[str, Any]]:
        return self._paged(f"/api/public/annotation-queues/{queue_id}/items")

    def _paged(self, path: str) -> list[dict[str, Any]]:
        page = 1
        result: list[dict[str, Any]] = []
        while True:
            response = self.request("GET", path, {"page": page, "limit": 100})
            data = response.get("data", [])
            result.extend(data)
            meta = response.get("meta", {})
            if not data or page >= int(meta.get("totalPages", page + (1 if len(data) == 100 else 0))):
                return result
            page += 1

    def add_item(self, queue_id: str, observation_id: str) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/api/public/annotation-queues/{queue_id}/items",
            body={"objectId": observation_id, "objectType": "OBSERVATION", "status": "PENDING"},
        )


def _value(score: dict[str, Any]) -> Any:
    return score.get("value", score.get("stringValue"))


def _metadata(score: dict[str, Any]) -> dict[str, Any]:
    metadata = score.get("metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def group_scores(scores: Iterable[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    groups: dict[str, dict[str, dict[str, Any]]] = {}
    conflicting_jobs: set[str] = set()
    subject_ids: dict[str, str] = {}
    for score in scores:
        if score.get("name") not in SCORE_NAMES:
            continue
        job_id = _metadata(score).get("job_execution_id")
        observation_id = (score.get("subject") or {}).get("id")
        if job_id and observation_id:
            group = groups.setdefault(str(job_id), {})
            existing_id = subject_ids.get(str(job_id))
            if existing_id is not None and existing_id != observation_id:
                conflicting_jobs.add(str(job_id))
                continue
            subject_ids[str(job_id)] = observation_id
            group[score["name"]] = {"score": score, "observation_id": observation_id}
    return {job_id: group for job_id, group in groups.items() if job_id not in conflicting_jobs}


def _candidate(group: dict[str, dict[str, Any]]) -> tuple[str, str] | None:
    if set(group) != set(SCORE_NAMES):
        return None
    requested = _value(group["requested_mode"]["score"])
    delivered = _value(group["delivered_mode"]["score"])
    try:
        fit = float(_value(group["route_fit"]["score"]))
    except (TypeError, ValueError):
        return None
    kind = "control" if requested == delivered and fit >= 0.8 else "same" if requested == delivered and fit < 0.5 else "mismatch" if requested != delivered and fit < 0.7 else None
    return (group["requested_mode"]["observation_id"], kind, fit) if kind else None


def _is_hermes_turn(observation: dict[str, Any]) -> bool:
    if observation.get("type") != "CHAIN" or observation.get("name") != "Hermes turn":
        return False
    return _has_user_input(observation.get("input")) and _has_output(observation.get("output"))


def _has_content(value: Any) -> bool:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return bool(value.strip())
    if isinstance(value, dict) and "json" in value:
        return _has_content(value["json"])
    if isinstance(value, dict) and "data" in value and len(value) == 1:
        return _has_content(value["data"])
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_has_content(value.get(key)) for key in ("content", "text", "messages", "input", "output"))
    if isinstance(value, list):
        return any(_has_content(item) for item in value)
    return False


def _messages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        try:
            return _messages(json.loads(value))
        except json.JSONDecodeError:
            return []
    if isinstance(value, dict):
        if "json" in value:
            return _messages(value["json"])
        if isinstance(value.get("messages"), list):
            return [item for item in value["messages"] if isinstance(item, dict)]
        if "role" in value:
            return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _has_user_input(value: Any) -> bool:
    messages = _messages(value)
    return bool(messages) and all(message.get("role") == "user" and _has_content(message.get("content")) for message in messages)


def _has_output(value: Any) -> bool:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return bool(value.strip())
    if isinstance(value, dict) and "json" in value:
        return _has_output(value["json"])
    return isinstance(value, dict) and _has_content(value.get("content"))


def refill(client: LangfuseClient, queue_name: str = "CA routing review", config: ReviewConfig | None = None, dry_run: bool = False) -> list[str]:
    config = config or ReviewConfig()
    scores: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        page = client.scores(cursor, config.page_size)
        scores.extend(page.get("data", []))
        cursor = page.get("meta", {}).get("cursor")
        if not cursor:
            break
    queues = {queue.get("name"): queue for queue in client.queues()}
    queue = queues.get(queue_name)
    if not queue or not queue.get("id"):
        raise LangfuseError(f"Annotation queue not found: {queue_name}")
    queue_id = queue["id"]
    prior_items = client.queue_items(queue_id)
    known = {item.get("objectId") for item in prior_items}
    pending = sum(1 for item in prior_items if item.get("status") == "PENDING")
    room = min(config.per_run, max(0, config.pending_cap - pending))
    selected: list[str] = []
    candidates = [_candidate(group) for group in group_scores(scores).values()]
    # Lowest-fit misses are most informative; controls are only a trailing reserve.
    valid = [item for item in candidates if item and item[0] not in known]
    misses = sorted((item for item in valid if item[1] != "control"), key=lambda item: item[2])
    controls = sorted((item for item in valid if item[1] == "control"), key=lambda item: item[2])
    control_slots = 1 if room >= 2 and controls else 0
    ordered = misses[: max(0, room - control_slots)] + controls[:control_slots]
    if not ordered and controls:
        ordered = controls[:room]
    for observation_id, _kind, _fit in ordered:
        if len(selected) >= room or observation_id in known:
            continue
        if not _is_hermes_turn(client.observation(observation_id)):
            continue
        if not dry_run:
            client.add_item(queue_id, observation_id)
        selected.append(observation_id)
        known.add(observation_id)
    # Read back after writes so a successful HTTP response is not mistaken for queue state.
    if dry_run:
        return selected
    verified = client.queue_items(queue_id)
    verified_ids = {item.get("objectId") for item in verified}
    missing = set(selected) - verified_ids
    if missing:
        raise LangfuseError(f"Queue readback missing newly added observations: {sorted(missing)}")
    return selected


def run(dry_run: bool = False) -> int:
    public = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret = os.environ.get("LANGFUSE_SECRET_KEY")
    if not public or not secret:
        raise SystemExit("LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are required")
    config = ReviewConfig.from_env()
    selected = refill(LangfuseClient(public, secret, config.url), config=config, dry_run=dry_run)
    print(f"Dry-run candidates: {len(selected)} observation(s)" if dry_run else f"Queued {len(selected)} observation(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Refill the Langfuse CA routing review queue.")
    parser.add_argument("--dry-run", action="store_true", help="Report candidates without creating queue items.")
    return run(dry_run=parser.parse_args().dry_run)


__all__ = ["LangfuseClient", "LangfuseError", "ReviewConfig", "group_scores", "refill", "run"]


if __name__ == "__main__":
    raise SystemExit(main())
