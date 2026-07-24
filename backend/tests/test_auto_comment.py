import unittest
from unittest import mock
from unittest.mock import AsyncMock, patch

from services.auto_comment import AzureDevOpsCommentClient, auto_comment_on_review


class InlineCommentTests(unittest.IsolatedAsyncioTestCase):
    async def test_post_inline_comment_uses_base_and_reviewed_iterations(self):
        client = AzureDevOpsCommentClient()
        client._post_comment = AsyncMock(return_value={"id": 1})

        await client.post_inline_comment(
            repo="purchase",
            pr_id=123,
            file_path="/src/example.ts",
            line_number=42,
            message="test",
            iteration_id=6,
            change_tracking_id=7,
        )

        body = client._post_comment.await_args.args[1]
        context = body["pullRequestThreadContext"]
        self.assertEqual(context["changeTrackingId"], 7)
        self.assertEqual(
            context["iterationContext"],
            {"firstComparingIteration": 1, "secondComparingIteration": 6},
        )

    async def test_auto_comment_skips_unknown_file_instead_of_falling_back_to_one(self):
        client = mock.MagicMock()
        client.get_existing_threads = AsyncMock(return_value=[])
        client.get_change_tracking_ids = AsyncMock(return_value={"/src/known.ts": 9})
        client.post_general_comment = AsyncMock(return_value={"id": 1})
        client.post_inline_comment = AsyncMock(return_value={"id": 2})

        findings = [
            {"severity": "HIGH", "file_path": "/src/known.ts", "line_number": 10},
            {"severity": "HIGH", "file_path": "/src/missing.ts", "line_number": 20},
        ]
        with patch("services.auto_comment.AzureDevOpsCommentClient", return_value=client), patch(
            "asyncio.sleep", new=AsyncMock()
        ):
            result = await auto_comment_on_review(
                repo="purchase",
                pr_id=123,
                title="test",
                recommendation="comment",
                findings=findings,
                scores={},
                duration_seconds=1,
                iteration_id=6,
            )

        self.assertEqual(result["inline_posted"], 1)
        self.assertEqual(client.post_inline_comment.await_count, 1)
        self.assertEqual(client.post_inline_comment.await_args.kwargs["change_tracking_id"], 9)
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("missing.ts", result["errors"][0])
