import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from services import pr_poller


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar(self):
        return self.value


class _RowsResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class PollerTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_repositories_commit_each_poll_state(self):
        db = MagicMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        states = {repo: SimpleNamespace(last_poll_at=None, last_seen_pr_ids="[]") for repo in ("a", "b", "c")}
        client = MagicMock()
        client.get_prs_for_reviewer = AsyncMock(return_value=[])

        with patch.object(pr_poller.settings, "REPOS", "a,b,c"), patch(
            "services.pr_poller.AzureDevOpsClient", return_value=client
        ), patch("services.pr_poller.get_or_create_poll_state", side_effect=lambda _db, repo: states[repo]):
            result = await pr_poller._poll_and_review(db)

        self.assertEqual(result["repos_polled"], 3)
        self.assertEqual(db.commit.await_count, 3)
        self.assertEqual(db.rollback.await_count, 0)
        self.assertTrue(all(state.last_poll_at is not None for state in states.values()))

    async def test_recovery_state_does_not_reprocess_existing_prs(self):
        db = MagicMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        db.execute = AsyncMock(return_value=_ScalarResult(1))
        state = SimpleNamespace(last_poll_at=None, last_seen_pr_ids="[]")
        client = MagicMock()
        client.get_prs_for_reviewer = AsyncMock(return_value=[{"azure_pr_id": 99}])

        with patch.object(pr_poller.settings, "REPOS", "purchase"), patch(
            "services.pr_poller.AzureDevOpsClient", return_value=client
        ), patch("services.pr_poller.get_or_create_poll_state", return_value=state), patch(
            "services.pr_poller._process_new_pr", new=AsyncMock()
        ) as process:
            await pr_poller._poll_and_review(db)

        process.assert_not_awaited()
        self.assertEqual(json.loads(state.last_seen_pr_ids), [99])

    async def test_failed_review_remains_unseen_for_retry(self):
        db = MagicMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        db.execute = AsyncMock(side_effect=[_ScalarResult(1), _RowsResult([])])
        state = SimpleNamespace(last_poll_at=object(), last_seen_pr_ids="[]")
        client = MagicMock()
        client.get_prs_for_reviewer = AsyncMock(return_value=[{"azure_pr_id": 99}])

        with patch.object(pr_poller.settings, "REPOS", "purchase"), patch(
            "services.pr_poller.AzureDevOpsClient", return_value=client
        ), patch("services.pr_poller.get_or_create_poll_state", return_value=state), patch(
            "services.pr_poller._process_new_pr", new=AsyncMock(side_effect=RuntimeError("Azure unavailable"))
        ):
            result = await pr_poller._poll_and_review(db)

        self.assertEqual(json.loads(state.last_seen_pr_ids), [])
        self.assertEqual(db.rollback.await_count, 1)
        self.assertEqual(len(result["errors"]), 1)
