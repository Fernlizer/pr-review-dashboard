"""Auto-comment service — post review findings back to Azure DevOps PRs with dedup.

Follows Azure DevOps REST API 7.1 spec for pull request threads.
https://learn.microsoft.com/en-us/rest/api/azure/devops/git/pull-request-threads/create
"""

import base64
import json
import logging
from typing import List, Dict, Any, Optional, Set

import httpx
from config import settings

logger = logging.getLogger(__name__)

BOT_MARKER = "Auto-detected by PR Review Dashboard"


class AzureDevOpsCommentClient:
    """Post comments to Azure DevOps PRs following the official API spec."""

    def __init__(self):
        self.pat = settings.AZURE_DEVOPS_PAT
        self.base_url = f"{settings.azure_base_url}/_apis/git/repositories"
        self.auth_header = f"Basic {base64.b64encode(f':{self.pat}'.encode()).decode()}"
        self.headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def get_latest_iteration(self, repo: str, pr_id: int) -> Optional[int]:
        """Get the latest iteration ID for a PR."""
        url = f"{self.base_url}/{repo}/pullrequests/{pr_id}/iterations?api-version=7.1"
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    text = resp.text
                    if text.startswith("\ufeff"):
                        text = text[1:]
                    iterations = json.loads(text).get("value", [])
                    if iterations:
                        return iterations[-1]["id"]
            except Exception as e:
                logger.error(f"Failed to fetch iterations: {e}")
        return None

    async def get_existing_threads(self, repo: str, pr_id: int) -> List[dict]:
        """Fetch all existing comment threads on a PR."""
        url = f"{self.base_url}/{repo}/pullrequests/{pr_id}/threads?api-version=7.1"
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    text = resp.text
                    if text.startswith("\ufeff"):
                        text = text[1:]
                    return json.loads(text).get("value", [])
            except Exception as e:
                logger.error(f"Failed to fetch threads: {e}")
        return []

    async def post_general_comment(self, repo: str, pr_id: int, message: str) -> Optional[dict]:
        """Post a general (non-inline) comment on a PR thread."""
        url = f"{self.base_url}/{repo}/pullrequests/{pr_id}/threads?api-version=7.1"
        body = {
            "comments": [
                {
                    "parentCommentId": 0,
                    "content": message,
                    "commentType": 1,
                }
            ],
            "status": 1,
        }
        return await self._post_comment(url, body, f"general on PR #{pr_id}")

    async def post_inline_comment(
        self,
        repo: str,
        pr_id: int,
        file_path: str,
        line_number: int,
        message: str,
        iteration_id: int = 1,
    ) -> Optional[dict]:
        """
        Post an inline comment on a specific line in a PR.
        Follows the official Azure DevOps API spec with pullRequestThreadContext.
        """
        # Azure DevOps requires leading / in filePath
        if not file_path.startswith("/"):
            file_path = "/" + file_path

        url = f"{self.base_url}/{repo}/pullrequests/{pr_id}/threads?api-version=7.1"

        # Follow the official spec exactly
        body = {
            "comments": [
                {
                    "parentCommentId": 0,
                    "content": message,
                    "commentType": 1,
                }
            ],
            "status": 1,
            "threadContext": {
                "filePath": file_path,
                "rightFileStart": {
                    "line": line_number,
                    "offset": 1,
                },
                "rightFileEnd": {
                    "line": line_number,
                    "offset": 1,
                },
                "leftFileStart": None,
                "leftFileEnd": None,
            },
            "pullRequestThreadContext": {
                "changeTrackingId": 1,
                "iterationContext": {
                    "firstComparingIteration": iteration_id,
                    "secondComparingIteration": iteration_id,
                },
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
                    logger.error(f"Comment failed ({desc}): {resp.status_code} {resp.text[:300]}")
                    return None
            except Exception as e:
                logger.error(f"Comment error ({desc}): {e}")
                return None


def _build_existing_comment_keys(threads: List[dict]) -> Set[str]:
    """Build dedup keys from existing bot comments."""
    keys = set()
    for thread in threads:
        comments = thread.get("comments", [])
        if not comments:
            continue

        content = comments[0].get("content", "") or ""
        if BOT_MARKER not in content:
            continue

        ctx = thread.get("threadContext") or {}
        if ctx.get("filePath"):
            file_path = ctx.get("filePath", "")
            line = ctx.get("rightFileStart", {}).get("line", 0)
            keys.add(f"inline:{file_path}:{line}")
        else:
            keys.add("summary")

    return keys


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
    rec_badges = {
        "approve": "✅ **Approved**",
        "request_changes": "🚫 **Request Changes**",
        "comment": "💬 **Comment**",
    }
    rec_text = rec_badges.get(recommendation, recommendation)

    parts = []
    if high_count > 0:
        parts.append(f"🔴 {high_count} HIGH")
    if medium_count > 0:
        parts.append(f"🟡 {medium_count} MEDIUM")
    if low_count > 0:
        parts.append(f"🔵 {low_count} LOW")
    severity_text = " | ".join(parts) if parts else "🟢 No issues found"

    score_lines = []
    for label, score in scores.items():
        bar = "█" * score + "░" * (10 - score)
        score_lines.append(f"| {label} | {bar} | **{score}/10** |")
    score_table = "\n".join(score_lines)

    return f"""## 🔍 PR Auto-Review Summary

**Recommendation:** {rec_text}
**Findings:** {severity_text}
**Duration:** {duration_seconds}s

### Scores

| Category | Score | Value |
|----------|-------|-------|
{score_table}

---

> 🤖 {BOT_MARKER}
"""


def format_inline_comment(
    severity: str,
    category: str,
    owasp_tag: Optional[str],
    description: Optional[str],
    code_snippet: Optional[str],
    fix_suggestion: Optional[str],
) -> str:
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

    lines.append(f"\n---\n🤖 *{BOT_MARKER}*")

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
    """Post all comments for a completed review (with dedup)."""
    client = AzureDevOpsCommentClient()
    stats = {"summary_posted": False, "inline_posted": 0, "skipped": 0, "errors": []}

    high_count = sum(1 for f in findings if f.get("severity") == "HIGH")
    medium_count = sum(1 for f in findings if f.get("severity") == "MEDIUM")
    low_count = sum(1 for f in findings if f.get("severity") == "LOW")

    # Fetch existing threads for dedup
    existing_threads = await client.get_existing_threads(repo, pr_id)
    existing_keys = _build_existing_comment_keys(existing_threads)
    logger.info(f"Found {len(existing_keys)} existing bot comments on PR #{pr_id}")

    # Get latest iteration ID for inline comments
    iteration_id = await client.get_latest_iteration(repo, pr_id) or 1

    # Post summary comment (skip if already exists)
    if "summary" in existing_keys:
        logger.info(f"Summary comment already exists on PR #{pr_id}, skipping")
        stats["skipped"] += 1
    else:
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

    # Post inline comments for HIGH and MEDIUM findings
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

        if not file_path or not line_number or line_number < 1:
            continue

        normalized_path = file_path if file_path.startswith("/") else f"/{file_path}"
        dedup_key = f"inline:{normalized_path}:{line_number}"

        if dedup_key in existing_keys:
            logger.info(f"Inline comment already exists at {normalized_path}:{line_number}, skipping")
            stats["skipped"] += 1
            continue

        comment_text = format_inline_comment(
            severity=severity,
            category=finding.get("category", "Issue"),
            owasp_tag=finding.get("owasp_tag"),
            description=finding.get("description"),
            code_snippet=finding.get("code_snippet"),
            fix_suggestion=finding.get("fix_suggestion"),
        )

        import asyncio
        await asyncio.sleep(0.5)

        result = await client.post_inline_comment(
            repo, pr_id, file_path, line_number, comment_text,
            iteration_id=iteration_id,
        )
        if result:
            stats["inline_posted"] += 1
        else:
            stats["errors"].append(f"Failed to comment on {normalized_path}:{line_number}")

    return stats
