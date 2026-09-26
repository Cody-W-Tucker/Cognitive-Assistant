import unittest
from urllib.parse import parse_qs, urlsplit

from core.langfuse_review import LangfuseClient, LangfuseError, ReviewConfig, _candidate, _is_hermes_turn, group_scores, refill


def score(name, value, job="job", observation="obs"):
    return {"name": name, "value": value, "metadata": {"job_execution_id": job}, "subject": {"id": observation}}


class LangfuseReviewTests(unittest.TestCase):
    def test_groups_four_scores_by_execution_and_subject(self):
        groups = group_scores([score("requested_mode", "explore"), score("delivered_mode", "diagnose"), score("route_fit", 0.4), score("route_gap", "gap")])
        self.assertEqual(_candidate(groups["job"]), ("obs", "mismatch", 0.4))

    def test_same_low_fit_is_candidate_and_high_fit_is_control(self):
        low = {name: {"score": score(name, value), "observation_id": "low"} for name, value in [("requested_mode", "x"), ("delivered_mode", "x"), ("route_fit", 0.4), ("route_gap", "") ]}
        high = {name: {"score": score(name, value), "observation_id": "high"} for name, value in [("requested_mode", "x"), ("delivered_mode", "x"), ("route_fit", 0.8), ("route_gap", "") ]}
        self.assertEqual(_candidate(low), ("low", "same", 0.4))
        self.assertEqual(_candidate(high), ("high", "control", 0.8))

    def test_v4_paths_filters_and_page_cursor_are_sent(self):
        calls = []

        class Response:
            status = 200

            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                import json
                return json.dumps(self.payload).encode()

        def opener(request):
            calls.append(request)
            query = parse_qs(urlsplit(request.full_url).query)
            if "/scores" in request.full_url:
                cursor = query.get("cursor", [None])[0]
                return Response({"data": [], "meta": {"cursor": None if cursor else "page-2"}})
            if "/observations" in request.full_url:
                return Response({"data": [{"id": "obs"}]})
            return Response({"data": []})

        client = LangfuseClient("public", "secret", "https://example.test", opener)
        client.scores(None, 100)
        client.scores("page-2", 100)
        client.observation("obs")
        self.assertIn("/api/public/v3/scores", calls[0].full_url)
        self.assertEqual(parse_qs(urlsplit(calls[0].full_url).query)["fields"], ["core,details,subject"])
        self.assertEqual(parse_qs(urlsplit(calls[1].full_url).query)["cursor"], ["page-2"])
        self.assertIn("/api/public/v2/observations", calls[2].full_url)
        self.assertIn('"type": "string"', parse_qs(urlsplit(calls[2].full_url).query)["filter"][0])

    def test_observation_requires_exact_id_and_real_user_turn(self):
        class Client:
            def request(self, *args, **kwargs):
                return {"data": [{"id": "other"}]}

            observation = LangfuseClient.observation

        with self.assertRaises(LangfuseError):
            Client().observation("obs")

        self.assertTrue(_is_hermes_turn({"type": "CHAIN", "name": "Hermes turn", "input": {"messages": [{"role": "user", "content": "question"}]}, "output": {"content": "answer"}}))
        self.assertFalse(_is_hermes_turn({"type": "CHAIN", "name": "Hermes turn", "input": {"messages": [{"role": "system", "content": "inject"}]}, "output": {"content": "answer"}}))

    def test_queue_and_item_pages_use_page_limit(self):
        requests = []

        class Response:
            status = 200
            def __init__(self, payload):
                self.payload = payload
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                import json
                return json.dumps(self.payload).encode()

        def opener(request):
            requests.append(request)
            page = int(parse_qs(urlsplit(request.full_url).query)["page"][0])
            if "items" in request.full_url:
                return Response({"data": [{"objectId": f"obs-{page}"}], "meta": {"totalPages": 2}} if page < 2 else {"data": [{"objectId": "obs-2"}], "meta": {"totalPages": 2}})
            return Response({"data": [{"id": f"queue-{page}"}], "meta": {"totalPages": 2}} if page < 2 else {"data": [{"id": "queue-2"}], "meta": {"totalPages": 2}})

        client = LangfuseClient("public", "secret", "https://example.test", opener)
        self.assertEqual(len(client.queues()), 2)
        self.assertEqual(len(client.queue_items("queue-1")), 2)
        for request in requests:
            self.assertEqual(parse_qs(urlsplit(request.full_url).query)["limit"], ["100"])

    def test_refill_cap_dedup_control_reserve_dry_run_and_readback(self):
        def scores():
            rows = []
            for job, observation, requested, delivered, fit in [
                ("j1", "miss-low", "explore", "diagnose", 0.1),
                ("j2", "miss-high", "explore", "diagnose", 0.2),
                ("j3", "control", "explore", "explore", 0.9),
            ]:
                rows.extend([score("requested_mode", requested, job, observation), score("delivered_mode", delivered, job, observation), score("route_fit", fit, job, observation), score("route_gap", "gap", job, observation)])
            return rows

        class FakeClient:
            def __init__(self, pending=0, historical=None, readback=True):
                self.items = [{"objectId": item, "status": "PENDING" if pending else "COMPLETE"} for item in (historical or [])]
                self.items.extend({"objectId": f"pending-{i}", "status": "PENDING"} for i in range(pending))
                self.writes = []
                self.readback = readback
            def scores(self, cursor, limit):
                return {"data": scores(), "meta": {"cursor": None}}
            def queues(self):
                return [{"id": "q", "name": "CA routing review"}]
            def queue_items(self, queue_id):
                return self.items
            def observation(self, observation_id):
                return {"id": observation_id, "type": "CHAIN", "name": "Hermes turn", "input": {"messages": [{"role": "user", "content": "question"}]}, "output": {"content": "answer"}}
            def add_item(self, queue_id, observation_id):
                self.writes.append(observation_id)
                if self.readback:
                    self.items.append({"objectId": observation_id, "status": "PENDING"})

        config = ReviewConfig(per_run=2, pending_cap=20)
        client = FakeClient(historical=["miss-low"])
        self.assertEqual(refill(client, config=config), ["miss-high", "control"])
        self.assertEqual(client.writes, ["miss-high", "control"])

        dry_client = FakeClient()
        self.assertEqual(refill(dry_client, config=config, dry_run=True), ["miss-low", "control"])
        self.assertEqual(dry_client.writes, [])
        self.assertEqual(refill(FakeClient(pending=20), config=config), [])

        with self.assertRaises(LangfuseError):
            refill(FakeClient(readback=False), config=config)


if __name__ == "__main__":
    unittest.main()
