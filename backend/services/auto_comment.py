"""Auto-comment service — post review findings back to Azure DevOps PRs."""

import base64
import json
import logging
import time
from typing import List, Dict, Any, Optional

import httpx
from config import settings

logger = logging.getLogger(__name__)


class AzureDevOpsCommentClient:
    """Post comments to Azure DevOps PRs."""

    def __init__(self):
        self.pat = settings.AZURE_DEVOPS_PAT
        self.base_url = f"{settings.azure_base_url}/_apis/git/repositories"
        self.auth_header = f"Basic {base64.b64encode(f':{self.pat}'.encode()).decode()}"
        self.headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def post_general_comment(self, repo: str, pr_id: int, message: str) -> Optional[dict]:
        """Post a general (non-inline) comment on a PR thread."""
        url = f"{self.base_url}/{repo}/pullrequests/{pr_id}/threads?api-version=7.1"
        body = {"comments": [{"content": message}]}
        return await self._post_comment(url, body, f"general on PR #{pr_id}")

    async def post_inline_comment(
        self, repo: str, pr_id: int, file_path: str, line_number: int, message: str
    ) -> Optional[dict]:
        """Post an inline comment on a specific line in a PR."""
        url = f"{self.base_url}/{repo}/pullrequests/{pr_id}/threads?api-version=7.1"
        body = {
            "comments": [{"content": message}],
            "threadContext": {
                "filePath": file_path,
                "rightFileStart": {"line": line_number},
            },
        }
        return await self._post_comment(
            url, body, f"inline {file_path}:{line_number} on PR #{pr_id}"
        )

    async def _post_comment(self, url: str, body: dict, desc: str) -> Optional[dict]:
        """POST comment to Azure DevOps. Returns response or None on error."""
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.post(url, headers=self.headers, json=body)
                if resp.status_code in (200, 201):
                    text = resp.text
                    if text.startswith("\ufeff"):
                        text = text[1:]
                    logger.info(f"Comment posted: {desc}")
                    return json.loads(text)
                else:
                    logger.error(f"Comment failed ({desc}): {resp.status_code} {resp.text[:200]}")
                    return None
            except Exception as e:
                logger.error(f"Comment error ({desc}): {e}")
                return None


def format_summary_comment(
    repo: str,
    pr_id: int,
    title: str,
    recommendation: str,
    high_count: int,
    medium_count: int,
    low_count: int,
    scores: Dict[str, int],
    duration_seconds: int,
) -> str:
    """Format a markdown summary comment for the PR."""

    # Recommendation badge
    rec_badges = {
        "approve": "✅ **Approved**",
        "request_changes": "🚫 **Request Changes**",
        "comment": "💬 **Comment**",
    }
    rec_text = rec_badges.get(recommendation, recommendation)

    # Severity emoji
    parts = []
    if high_count > 0:
        parts.append(f"🔴 {high_count} HIGH")
    if medium_count > 0:
        parts.append(f"🟡 {medium_count} MEDIUM")
    if low_count > 0:
        parts.append(f"🔵 {low_count} LOW")
    severity_text = " | ".join(parts) if parts else "🟢 No issues found"

    # Score table
    score_lines = []
    for label, score in scores.items():
        bar = "█" * score + "░" * (10 - score)
        score_lines.append(f"| {label} | {bar} | **{score}/10** |")
    score_table = "\n".join(score_lines)

    comment = f"""## 🔍 PR Auto-Review Summary

**Recommendation:** {rec_text}
**Findings:** {severity_text}
**Duration:** {duration_seconds}s

### Scores

| Category | Score | Value |
|----------|-------|-------|
{score_table}

---

> 🤖 Auto-reviewed by **PR Review Dashboard** | [Open Dashboard](http://localhost:9101/prs)
"""
    return comment


def format_inline_comment(
    severity: str,
    category: str,
    owasp_tag: Optional[str],
    file_path: str,
    line_number: int,
    description: Optional[str],
    code_snippet: Optional[str],
    fix_suggestion: Optional[str],
) -> str:
    """Format an inline comment for a specific finding."""

    severity_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🔵"}.get(severity, "⚪")

    lines = [f"{severity_emoji} **[{severity}] {category}**"]
    if owasp_tag:
        lines[0] += f" — `{owasp_tag}`"

    if description:
        lines.append(f"\n{description}")

    if code_snippet:
        lines.append(f"\n```\n{code_snippet}\n```")

    if fix_suggestion:
        lines.append(f"\n💡 **Fix:** {fix_suggestion}")

    lines.append(f"\n---\n🤖 *Auto-detected by PR Review Dashboard*")

    return "\n".join(lines)


async def auto_comment_on_review(
    repo: str,
    pr_id: int,
    title: str,
    recommendation: str,
    findings: List[Dict[str, Any]],
    scores: Dict[str, int],
    duration_seconds: int,
) -> Dict[str, Any]:
    """
    Post all comments for a completed review.
    1. Post summary comment (general thread)
    2. Post inline comments for HIGH/MEDIUM findings
    Returns stats: {summary_posted, inline_posted, errors}
    """
    client = AzureDevOpsCommentClient()
    stats = {"summary_posted": False, "inline_posted": 0, "errors": []}

    high_count = sum(1 for f in findings if f.get("severity") == "HIGH")
    medium_count = sum(1 for f in findings if f.get("severity") == "MEDIUM")
    low_count = sum(1 for f in findings if f.get("severity") == "LOW")

    # 1. Post summary comment
    summary_text = format_summary_comment(
        repo, pr_id, title, recommendation,
        high_count, medium_count, low_count,
        scores, duration_seconds,
    )
    result = await client.post_general_comment(repo, pr_id, summary_text)
    if result:
        stats["summary_posted"] = True
    else:
        stats["errors"].append("Failed to post summary comment")

    # 2. Post inline comments for HIGH and MEDIUM findings only
    # Group by file+line to avoid duplicate comments
    seen_lines = set()
    for finding in findings:
        severity = finding.get("severity", "LOW")
        if severity not in ("HIGH", "MEDIUM"):
            continue

        file_path = finding.get("file_path", "")
        line_number = finding.get("line_number", 0)
        key = (file_path, line_number)

        if key in seen_lines:
            continue
        seen_lines.add(key)

        comment_text = format_inline_comment(
            severity=severity,
            category=finding.get("category", "Issue"),
            owasp_tag=finding.get("owasp_tag"),
            file_path=file_path,
            line_number=line_number,
            description=finding.get("description"),
            code_snippet=finding.get("code_snippet"),
            fix_suggestion=finding.get("fix_suggestion"),
        )

        # Small delay to avoid rate limiting
        await _async_sleep(0.5)

        result = await client.post_inline_comment(
            repo, pr_id, file_path, line_number, comment_text
        )
        if result:
            stats["inline_posted"] += 1
        else:
            stats["errors"].append(f"Failed to comment on {file_path}:{line_number}")

    return stats


async def _async_sleep(seconds: float):
    """Async sleep wrapper."""
    import asyncio
    await asyncio.sleep(seconds)
