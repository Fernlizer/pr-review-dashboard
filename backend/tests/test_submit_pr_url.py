import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import BackgroundTasks
from sqlalchemy.exc import IntegrityError

from models import PullRequest
from routers import api


class _ScalarsFirstResult:
    def __init__(self, value):
        self.value = value

    def scalars(self):
        return self

    def first(self):
        return self.value


class SubmitPrUrlTests(unittest.IsolatedAsyncioTestCase):
    async def test_submit_recovers_when_poll_inserted_same_pr_first(self):
        existing_pr = PullRequest(
            id=1220,
            azure_pr_id=34459,
            repo="purchase",
            title="old",
            url="old",
        )
        db = MagicMock()
        db.execute = AsyncMock(side_effect=[
            _ScalarsFirstResult(None),
            _ScalarsFirstResult(existing_pr),
        ])
        db.commit = AsyncMock(side_effect=[
            IntegrityError("insert", {}, Exception("duplicate")),
            None,
        ])
        db.rollback = AsyncMock()
        db.refresh = AsyncMock()

        azure_client = MagicMock()
        azure_client.base_url = "https://dev.azure.com/AXONS-FIT-Business-and-CPTG/AgriTech"
        azure_client._get = AsyncMock(return_value={
            "pullRequestId": 34459,
            "title": "refactor: extract helper methods",
            "description": "test",
            "status": "active",
            "sourceRefName": "refs/heads/test/pr-refector-function",
            "targetRefName": "refs/heads/main",
            "creationDate": "2026-07-24T04:12:55.263007Z",
            "createdBy": {
                "displayName": "Sasharat Katbuakaw",
                "uniqueName": "sasharat@example.com",
            },
            "reviewers": [
                {"displayName": "Sasharat Katbuakaw", "isRequired": None},
            ],
        })
        tasks = BackgroundTasks()

        with patch("services.azure_client.AzureDevOpsClient", return_value=azure_client):
            response = await api.submit_pr_url(
                api.SubmitPRUrlRequest(
                    url="https://dev.azure.com/AXONS-FIT-Business-and-CPTG/AgriTech/_git/purchase/pullrequest/34459"
                ),
                tasks,
                db,
            )

        self.assertEqual(response["status"], "existing")
        self.assertEqual(response["repo"], "purchase")
        self.assertEqual(response["azure_pr_id"], 34459)
        self.assertEqual(existing_pr.title, "refactor: extract helper methods")
        self.assertEqual(existing_pr.source_branch, "test/pr-refector-function")
        self.assertEqual(db.rollback.await_count, 1)
        self.assertEqual(len(tasks.tasks), 1)


if __name__ == "__main__":
    unittest.main()
