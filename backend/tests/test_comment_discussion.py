import unittest
from unittest.mock import patch

from models import Finding
from services.comment_discussion import _is_eligible_pr, _parse_assessment, _thread_snapshot


class CommentDiscussionTests(unittest.TestCase):
    def test_parse_assessment_only_allows_human_review_decisions(self):
        assessment = _parse_assessment(
            '{"decision":"ready_for_human_review","reason":"มีหลักฐาน","reply":"โปรดให้ reviewer ตรวจอีกครั้ง","confidence":0.9}'
        )

        self.assertEqual(assessment["decision"], "ready_for_human_review")
        self.assertIsNone(
            _parse_assessment(
                '{"decision":"approve","reason":"ok","reply":"approved","confidence":1}'
            )
        )

    def test_thread_snapshot_marks_configured_reviewer_as_bot(self):
        with patch("services.comment_discussion.settings.REVIEWER_NAME", "FERN"):
            snapshot = _thread_snapshot(
                {
                    "comments": [
                        {"id": 2, "author": {"displayName": "PR owner"}, "content": "I fixed it"},
                        {"id": 1, "author": {"uniqueName": "fern@axons.co.th"}, "content": "Please fix"},
                    ]
                }
            )

        self.assertEqual([comment["id"] for comment in snapshot], [1, 2])
        self.assertTrue(snapshot[0]["is_bot"])
        self.assertFalse(snapshot[1]["is_bot"])

    def test_new_discussion_fields_default_to_untracked(self):
        finding = Finding(severity="HIGH", category="Security")

        self.assertIsNone(finding.azure_thread_id)
        self.assertIsNone(finding.discussion_status)

    def test_positive_human_reviewer_vote_is_never_eligible_for_sync(self):
        self.assertTrue(_is_eligible_pr({"reviewer_vote": 0}))
        self.assertFalse(_is_eligible_pr({"reviewer_vote": 5}))
        self.assertFalse(_is_eligible_pr({"reviewer_vote": 10}))
        self.assertFalse(_is_eligible_pr(None))
