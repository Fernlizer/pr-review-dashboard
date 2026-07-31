"""Safely continue newly-created Azure DevOps review conversations.

The service is intentionally advisory: it never updates a pull-request vote,
never approves a PR, and never changes an Azure DevOps thread status. A human
reviewer makes those decisions in Azure DevOps.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings
from models import Finding, PullRequest, Review
from services.auto_comment import AzureDevOpsCommentClient
from services.azure_client import AzureDevOpsClient
from services.llm_reviewer import _call_llm

logger = logging.getLogger(__name__)

_ACTIVE_DISCUSSION_STATUSES = {
    "awaiting_author",
    "still_open",
    "needs_human_review",
    "ready_for_human_review",
}
_VALID_DECISIONS = _ACTIVE_DISCUSSION_STATUSES


def _is_bot_comment(comment: dict) -> bool:
    author = comment.get("author") or {}
    identity = " ".join(
        str(author.get(key, "")) for key in ("displayName", "uniqueName", "id")
    ).lower()
    return settings.REVIEWER_NAME.lower() in identity


def _comment_id(comment: dict) -> int:
    return int(comment.get("id", 0) or 0)


def _is_eligible_pr(pr_data: Optional[dict]) -> bool:
    """Only an active, unapproved PR assigned to the human reviewer is eligible."""
    return bool(pr_data) and int(pr_data.get("reviewer_vote", 0) or 0) <= 0


def _thread_snapshot(thread: dict) -> list[dict]:
    comments = sorted(thread.get("comments") or [], key=_comment_id)
    return [
        {
            "id": _comment_id(comment),
            "author": (comment.get("author") or {}).get("displayName", "Unknown"),
            "content": comment.get("content", ""),
            "published_date": comment.get("publishedDate"),
            "is_bot": _is_bot_comment(comment),
        }
        for comment in comments
    ]


def _discussion_prompt(finding: Finding, transcript: list[dict]) -> str:
    return f"""คุณช่วยเป็นผู้ช่วย code reviewer ในการสนทนา Azure DevOps thread เท่านั้น

ข้อห้ามเด็ดขาด:
- ห้าม approve PR, ห้ามบอกว่า PR approved, ห้ามเปลี่ยน reviewer vote, ห้ามปิด Azure thread
- มนุษย์จะเป็นผู้ตัดสินใจและกด Approve เองเสมอ
- หากหลักฐานไม่พอหรือมีความเสี่ยง HIGH ให้เลือก needs_human_review หรือ still_open

Finding เดิม:
- severity: {finding.severity}
- category: {finding.category}
- location: {finding.file_path}:{finding.line_number}
- description: {finding.description or ''}
- suggested fix: {finding.fix_suggestion or ''}

บทสนทนา (เรียงตามเวลา):
{json.dumps(transcript, ensure_ascii=False)}

เลือก decision ได้เพียง: awaiting_author, still_open, ready_for_human_review, needs_human_review
- awaiting_author: ต้องขอข้อมูลเพิ่ม
- still_open: คำตอบ/หลักฐานยังไม่แก้ประเด็น
- ready_for_human_review: มีเหตุผลหรือหลักฐานเพียงพอให้มนุษย์ตรวจและตัดสินต่อ แต่ไม่ใช่ approval
- needs_human_review: มีความเสี่ยงสูง, นโยบาย, หรือไม่แน่ใจ

ตอบ JSON object เท่านั้น:
{{"decision":"...","reason":"สรุปภาษาไทยสั้น ๆ","reply":"ข้อความตอบเจ้าของ PR ภาษาไทยสั้น ๆ","confidence":0.0}}
"""


def _parse_assessment(raw: Optional[str]) -> Optional[dict]:
    if not raw:
        return None
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        assessment = json.loads(match.group())
    except json.JSONDecodeError:
        return None
    if assessment.get("decision") not in _VALID_DECISIONS:
        return None
    if not isinstance(assessment.get("reason"), str) or not isinstance(assessment.get("reply"), str):
        return None
    return assessment


async def sync_comment_discussions(db: AsyncSession) -> dict[str, int]:
    """Read new author replies for newly tracked, still-active PR threads.

    Historical records are excluded by `azure_thread_id IS NOT NULL`. The
    Azure PR list is additionally filtered by configured reviewer's vote, so a
    PR with an approval vote is untouched.
    """
    result = await db.execute(
        select(Finding)
        .join(Review, Finding.review_id == Review.id)
        .join(PullRequest, Review.pr_id == PullRequest.id)
        .options(selectinload(Finding.review).selectinload(Review.pull_request))
        .where(
            Finding.azure_thread_id.is_not(None),
            Finding.discussion_status.in_(_ACTIVE_DISCUSSION_STATUSES),
            PullRequest.status == "active",
        )
    )
    findings = result.scalars().all()
    stats = {"tracked": len(findings), "replies": 0, "skipped_approved": 0, "errors": 0}
    if not findings:
        return stats

    azure = AzureDevOpsClient()
    comment_client = AzureDevOpsCommentClient()
    active_prs: dict[tuple[str, int], dict] = {}
    for repo in {finding.review.pull_request.repo for finding in findings}:
        try:
            for pr_data in await azure.get_prs_for_reviewer(repo, settings.REVIEWER_NAME):
                active_prs[(repo, pr_data["azure_pr_id"])] = pr_data
        except Exception:
            logger.exception("Could not list active PRs for discussion sync in %s", repo)
            stats["errors"] += 1

    threads_cache: dict[tuple[str, int], dict[int, dict]] = {}
    for finding in findings:
        pr = finding.review.pull_request
        pr_data = active_prs.get((pr.repo, pr.azure_pr_id))
        # A missing PR is inactive or no longer assigned to this human reviewer.
        # A positive vote is an approval and is strictly out of scope.
        if not _is_eligible_pr(pr_data):
            stats["skipped_approved"] += 1
            continue

        cache_key = (pr.repo, pr.azure_pr_id)
        if cache_key not in threads_cache:
            try:
                threads = await comment_client.get_existing_threads(pr.repo, pr.azure_pr_id)
                threads_cache[cache_key] = {int(thread.get("id")): thread for thread in threads if thread.get("id")}
            except Exception:
                logger.exception("Could not read threads for PR #%s", pr.azure_pr_id)
                stats["errors"] += 1
                continue

        thread = threads_cache[cache_key].get(finding.azure_thread_id)
        if not thread:
            logger.warning("Tracked Azure thread %s no longer exists", finding.azure_thread_id)
            stats["errors"] += 1
            continue

        transcript = _thread_snapshot(thread)
        latest_id = max((comment["id"] for comment in transcript), default=0)
        new_author_comments = [
            comment for comment in transcript
            if comment["id"] > (finding.last_synced_comment_id or 0) and not comment["is_bot"]
        ]
        if not new_author_comments:
            continue

        assessment = _parse_assessment(await _call_llm(
            _discussion_prompt(finding, transcript),
            system_message=(
                "ตอบ JSON object เท่านั้นสำหรับการสรุป Azure DevOps discussion "
                "ห้าม approve PR ห้ามเปลี่ยน reviewer vote และห้ามปิด Azure thread"
            ),
        ))
        if not assessment:
            logger.warning("Discussion assessment unavailable for finding %s; retrying later", finding.id)
            stats["errors"] += 1
            continue

        reply = "🤖 **AI discussion summary (human approval required)**\n\n" + assessment["reply"]
        posted = await comment_client.post_thread_reply(pr.repo, pr.azure_pr_id, finding.azure_thread_id, reply)
        if not posted:
            stats["errors"] += 1
            continue

        finding.discussion_status = assessment["decision"]
        finding.discussion_reason = assessment["reason"]
        finding.discussion_json = json.dumps(transcript, ensure_ascii=False)
        finding.last_synced_comment_id = max(latest_id, _comment_id(posted))
        finding.last_synced_at = datetime.now(timezone.utc)
        finding.last_bot_reply_at = datetime.now(timezone.utc)
        stats["replies"] += 1

    if stats["replies"]:
        await db.commit()
    return stats
