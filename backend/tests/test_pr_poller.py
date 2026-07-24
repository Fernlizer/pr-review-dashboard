import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from models import PullRequest
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


class _ScalarsFirstResult:
    def __init__(self, value):
        self.value = value

    def scalars(self):
        return self

    def first(self):
        return self.value


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

    async def test_seen_pr_with_new_iteration_is_reviewed_again(self):
        db = MagicMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        existing_pr = PullRequest(id=7, azure_pr_id=99, repo="purchase")
        old_review = SimpleNamespace(
            id=3,
            azure_iteration_id=1,
            source_commit_id="old-source",
            target_commit_id="target",
        )
        db.execute = AsyncMock(
            side_effect=[
                _ScalarResult(1),
                _ScalarsFirstResult(existing_pr),
                _ScalarsFirstResult(old_review),
            ]
        )
        state = SimpleNamespace(last_poll_at=object(), last_seen_pr_ids="[99]")
        pr_data = {
            "azure_pr_id": 99,
            "title": "Update existing PR",
            "source_branch": "feature",
            "target_branch": "main",
        }
        client = MagicMock()
        client.get_prs_for_reviewer = AsyncMock(return_value=[pr_data])
        client.get_pr_iterations = AsyncMock(return_value=(2, "new-source", "target"))

        with patch.object(pr_poller.settings, "REPOS", "purchase"), patch(
            "services.pr_poller.AzureDevOpsClient", return_value=client
        ), patch("services.pr_poller.get_or_create_poll_state", return_value=state), patch(
            "services.pr_poller._process_new_pr", new=AsyncMock(return_value=True)
        ) as process:
            result = await pr_poller._poll_and_review(db)

        self.assertEqual(result["new_prs"], 0)
        self.assertEqual(result["updated_prs"], 1)
        self.assertEqual(result["reviews_created"], 1)
        process.assert_awaited_once()
        self.assertIs(process.await_args.kwargs["existing_pr"], existing_pr)
        self.assertEqual(pr_data["_review_iteration"]["iteration_id"], 2)
        self.assertEqual(json.loads(state.last_seen_pr_ids), [99])

    async def test_review_is_committed_running_before_long_work(self):
        db = MagicMock()
        db.commit = AsyncMock()
        db.flush = AsyncMock()
        db.add = MagicMock()
        client = MagicMock()
        client.get_pr_iterations = AsyncMock(side_effect=RuntimeError("Azure unavailable"))
        existing_pr = PullRequest(id=7, azure_pr_id=99, repo="purchase")
        pr_data = {
            "azure_pr_id": 99,
            "title": "New PR",
            "description": "",
            "author": "A",
            "author_email": "",
            "source_branch": "feature",
            "target_branch": "main",
            "status": "active",
            "is_reviewer_required": "no",
            "reviewers_json": "[]",
            "url": "https://example.test/pr/99",
        }

        with self.assertRaises(RuntimeError):
            await pr_poller._process_new_pr_unlocked(db, client, "purchase", pr_data, existing_pr=existing_pr)

        review = db.add.call_args.args[0]
        self.assertEqual(review.status, "failed")
        self.assertIn("Azure unavailable", review.summary)
        self.assertIsNotNone(review.completed_at)
        self.assertEqual(db.commit.await_count, 2)
