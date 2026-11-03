import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from config import settings
from models import PullRequest
from services import llm_reviewer as reviewer, pr_poller
from services.azure_client import FetchedFile


class HermesReviewerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = patch.multiple(settings, LLM_BACKEND="hermes",
            HERMES_BASE_URL="http://hermes.test/p/pr-review/v1/",
            HERMES_API_KEY="test-key", HERMES_MODEL="pr-review")
        self.config.start()
        self.addCleanup(self.config.stop)

    async def test_calls_hermes_profile_without_legacy_fallback(self):
        response = httpx.Response(200, json={"choices": [{"message": {"content": "[]"}}]},
                                  request=httpx.Request("POST", "http://hermes.test"))
        client = AsyncMock()
        client.post.return_value = response
        client.__aenter__.return_value = client
        with patch.object(reviewer.httpx, "AsyncClient", return_value=client), patch.object(
            reviewer, "_try_provider", new=AsyncMock()
        ) as legacy:
            self.assertEqual(await reviewer._call_llm("code", "review rules"), "[]")
        legacy.assert_not_awaited()
        args = client.post.call_args
        self.assertEqual(args.args[0], "http://hermes.test/p/pr-review/v1/chat/completions")
        self.assertEqual(args.kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(args.kwargs["json"]["model"], "pr-review")
        self.assertEqual(args.kwargs["json"]["messages"][1]["content"], "code")
        self.assertIn("untrusted data", args.kwargs["json"]["messages"][0]["content"])

    async def test_timeout_does_not_fall_back(self):
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.side_effect = httpx.ReadTimeout("timeout")
        with patch.object(reviewer.httpx, "AsyncClient", return_value=client), patch.object(
            reviewer, "_try_provider", new=AsyncMock()
        ) as legacy:
            self.assertIsNone(await reviewer._call_llm("code"))
        legacy.assert_not_awaited()

    async def test_auth_failure_and_malformed_envelope_are_unavailable(self):
        for status, body in [(401, {}), (200, {}), (200, {"choices": []})]:
            with self.subTest(status=status, body=body):
                client = AsyncMock()
                client.__aenter__.return_value = client
                client.post.return_value = httpx.Response(status, json=body,
                    request=httpx.Request("POST", "http://hermes.test"))
                with patch.object(reviewer.httpx, "AsyncClient", return_value=client):
                    self.assertIsNone(await reviewer._call_llm("code"))

    async def test_missing_key_makes_no_network_request(self):
        with patch.object(settings, "HERMES_API_KEY", ""), patch.object(reviewer.httpx, "AsyncClient") as client:
            self.assertIsNone(await reviewer._call_llm("code"))
        client.assert_not_called()

    async def test_review_rejects_unavailable_or_invalid_response(self):
        for raw in [None, "unavailable", "{}", '[{"severity":"HIGH"}]']:
            with self.subTest(raw=raw), patch.object(reviewer, "_call_llm", new=AsyncMock(return_value=raw)):
                with self.assertRaises(RuntimeError):
                    await reviewer.review_pr_with_llm("test", "author", "feature", "main", [], {})

    async def test_findings_remain_limited_to_changed_lines(self):
        items = [{"severity": "medium", "file_path": "/example.ts", "line_number": line,
                  "description": "empty input crashes"} for line in [2, 8]]
        with patch.object(reviewer, "_call_llm", new=AsyncMock(return_value=json.dumps(items))):
            findings = await reviewer.review_pr_with_llm("test", "author", "feature", "main", [], {"/example.ts": {2}})
        self.assertEqual([f.line_number for f in findings], [2])
        self.assertEqual(findings[0].severity, "MEDIUM")

    async def test_valid_empty_review_is_clean(self):
        with patch.object(reviewer, "_call_llm", new=AsyncMock(return_value="[]")):
            self.assertEqual(await reviewer.review_pr_with_llm("test", "author", "feature", "main", [], {}), [])

    async def test_failed_hermes_review_is_recorded_failed_without_comment(self):
        db = MagicMock(commit=AsyncMock(), flush=AsyncMock())
        client = MagicMock()
        client.get_pr_iterations = AsyncMock(return_value=(1, "source", "target"))
        client.get_pr_changes = AsyncMock(return_value=[{"path": "/example.ts"}])
        client.fetch_files_parallel = AsyncMock(return_value=[FetchedFile(
            path="/example.ts", change_type="add", src_content="return users[0].name;"
        )])
        pr = PullRequest(id=7, azure_pr_id=99, repo="example")
        data = {"azure_pr_id": 99, "source_branch": "feature", "target_branch": "main"}
        with patch.object(pr_poller, "run_security_scan", return_value=[]), patch.object(
            reviewer, "review_pr_with_llm", new=AsyncMock(side_effect=RuntimeError("Hermes unavailable"))
        ), patch.object(pr_poller, "_maybe_auto_comment", new=AsyncMock()) as comment:
            with self.assertRaises(RuntimeError):
                await pr_poller._process_new_pr_unlocked(db, client, "example", data, existing_pr=pr)
        review = db.add.call_args.args[0]
        self.assertEqual(review.status, "failed")
        self.assertIsNone(review.recommendation)
        comment.assert_not_awaited()

    async def test_legacy_backend_remains_explicitly_available(self):
        with patch.object(settings, "LLM_BACKEND", "legacy"), patch.object(
            reviewer, "_try_provider", new=AsyncMock(return_value="[]")
        ) as legacy, patch.object(reviewer, "_call_hermes", new=AsyncMock()) as hermes:
            self.assertEqual(await reviewer._call_llm("code"), "[]")
        legacy.assert_awaited_once()
        hermes.assert_not_awaited()
