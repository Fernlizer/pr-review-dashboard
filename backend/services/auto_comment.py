"""Auto-comment service — post review findings back to Azure DevOps PRs with dedup.

Follows Azure DevOps REST API 7.1 spec for pull request threads.
https://learn.microsoft.com/en-us/rest/api/azure/devops/git/pull-request-threads/create
"""

import base64
import json
import logging
import re
from typing import List, Dict, Any, Optional, Set

import httpx
from config import settings

logger = logging.getLogger(__name__)

# Hidden dedup marker (invisible zero-width space sequence)
# Used internally to identify our comments without showing anything to users
_DEDUP_ID = "\u200b\u200b\u200b"  # triple zero-width space

_LANG_BY_EXTENSION = {
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "jsx",
    ".py": "python",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".cs": "csharp",
    ".sql": "sql",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sh": "bash",
}


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

    async def get_change_tracking_ids(
        self, repo: str, pr_id: int, iteration_id: int
    ) -> Dict[str, int]:
        """Get changeTrackingId per file path for a given iteration.

        Returns a dict mapping file_path -> changeTrackingId.
        Each file in a PR iteration has a unique changeTrackingId that MUST be
        used in pullRequestThreadContext when posting inline comments.
        Using the wrong changeTrackingId causes comments to render on wrong lines.
        """
        url = (
            f"{self.base_url}/{repo}/pullrequests/{pr_id}"
            f"/iterations/{iteration_id}/changes?api-version=7.1"
        )
        mapping: Dict[str, int] = {}
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    text = resp.text
                    if text.startswith("\ufeff"):
                        text = text[1:]
                    entries = json.loads(text).get("changeEntries", [])
                    for entry in entries:
                        path = entry.get("item", {}).get("path", "")
                        tracking_id = entry.get("changeTrackingId", 1)
                        if path:
                            mapping[path] = tracking_id
            except Exception as e:
                logger.error(f"Failed to fetch change tracking IDs: {e}")
        return mapping

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
        iteration_id: int,
        change_tracking_id: int,
    ) -> Optional[dict]:
        """Post an inline comment on a specific line in a PR.

        Args:
            iteration_id: PR iteration ID (from get_latest_iteration).
            change_tracking_id: Per-file tracking ID (from get_change_tracking_ids).
                Using the wrong value causes comments to render on wrong files/lines.
        """
        if not file_path or line_number < 1 or change_tracking_id < 1 or iteration_id < 1:
            logger.error("Refusing inline comment with incomplete Azure DevOps location context")
            return None

        if not file_path.startswith("/"):
            file_path = "/" + file_path

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
            "threadContext": {
                "filePath": file_path,
                "rightFileStart": {"line": line_number, "offset": 1},
                "rightFileEnd": {"line": line_number, "offset": 1},
                "leftFileStart": None,
                "leftFileEnd": None,
            },
            "pullRequestThreadContext": {
                "changeTrackingId": change_tracking_id,
                "iterationContext": {
                    # A matching first/second iteration means the common commit,
                    # not the PR diff. Comments on the current PR diff must refer
                    # to the base iteration and the reviewed iteration.
                    "firstComparingIteration": 1,
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
    """Build dedup keys from existing bot comments using hidden marker."""
    keys = set()
    for thread in threads:
        comments = thread.get("comments", [])
        if not comments:
            continue

        content = comments[0].get("content", "") or ""
        # Check for our hidden dedup marker
        if _DEDUP_ID not in content:
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

    return f"""## 🔍 PR Review Summary

**Recommendation:** {rec_text}
**Findings:** {severity_text}
**Duration:** {duration_seconds}s

### Scores

| Category | Score | Value |
|----------|-------|-------|
{score_table}
{_DEDUP_ID}"""


def _infer_markdown_language(file_path: Optional[str]) -> str:
    """Infer a Markdown fence language from a repository file path."""
    if not file_path:
        return ""

    path = file_path.lower()
    for ext, language in _LANG_BY_EXTENSION.items():
        if path.endswith(ext):
            return language
    return ""


def _clean_comment_text(value: Optional[str]) -> str:
    """Normalize LLM-provided text before embedding it in Azure DevOps Markdown."""
    if not value:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def _strip_outer_code_fence(value: str) -> str:
    """Remove one surrounding Markdown code fence when the whole value is fenced."""
    match = re.fullmatch(r"\s*```[a-zA-Z0-9_-]*\n(?P<code>.*?)\n```\s*", value, re.DOTALL)
    if match:
        return match.group("code").strip("\n")
    return value


def _fenced_code_block(code: str, language: str = "") -> str:
    code = _strip_outer_code_fence(_clean_comment_text(code))
    fence = f"```{language}" if language else "```"
    return f"{fence}\n{code}\n```"


def _looks_like_code_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith(("@", "//", "/*", "*", "*/", "{", "}", ")", "];", "});")):
        return True
    if re.match(
        r"^(async\s+)?(function|return|if|else|for|while|switch|try|catch|throw|const|let|var|class|interface|type|import|export|await|public|private|protected)\b",
        stripped,
    ):
        return True
    if re.match(r"^(async\s+)?[A-Za-z_$][\w$]*\s*\([^)]*$", stripped):
        return True
    return bool(re.search(r"[{};=]$", stripped) or re.search(r"\w+\([^)]*\)\s*[,{;]?$", stripped))


def _split_fix_suggestion(value: str) -> tuple[str, str]:
    """Split LLM fix text into human prose and code when it contains multiline code."""
    text = _clean_comment_text(value)
    text = re.sub(r"^(?:💡\s*)?(?:\*\*)?fix(?:\s*suggestion)?(?:\*\*)?\s*[:：-]\s*", "", text, flags=re.I)
    if not text:
        return "", ""

    if "```" in text:
        return text, ""

    lines = text.split("\n")
    if len(lines) == 1:
        return text, ""

    code_start = None
    for idx, line in enumerate(lines):
        remaining = [ln for ln in lines[idx:] if ln.strip()]
        code_like = sum(1 for ln in remaining if _looks_like_code_line(ln))
        if _looks_like_code_line(line) and code_like >= 2:
            code_start = idx
            break

    if code_start is None:
        return text, ""

    prose = "\n".join(lines[:code_start]).strip()
    code = "\n".join(lines[code_start:]).strip()
    return prose, code


def format_inline_comment(
    severity: str,
    category: str,
    owasp_tag: Optional[str],
    description: Optional[str],
    code_snippet: Optional[str],
    fix_suggestion: Optional[str],
    file_path: Optional[str] = None,
) -> str:
    severity_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🔵"}.get(severity, "⚪")
    language = _infer_markdown_language(file_path)

    lines = [f"{severity_emoji} **[{severity}] {category}**"]
    if owasp_tag:
        lines[0] += f" — `{owasp_tag}`"

    cleaned_description = _clean_comment_text(description)
    if cleaned_description:
        lines.append(f"\n{cleaned_description}")

    cleaned_snippet = _clean_comment_text(code_snippet)
    if cleaned_snippet:
        lines.append(f"\n**Problematic code**\n\n{_fenced_code_block(cleaned_snippet, language)}")

    cleaned_fix = _clean_comment_text(fix_suggestion)
    if cleaned_fix:
        prose, code = _split_fix_suggestion(cleaned_fix)
        if code:
            fix_body = []
            if prose:
                fix_body.append(prose)
            fix_body.append(_fenced_code_block(code, language))
            lines.append("\n💡 **Fix**\n\n" + "\n\n".join(fix_body))
        else:
            lines.append(f"\n💡 **Fix**\n\n{prose}")

    # Hidden dedup marker at end
    lines.append(f"\n{_DEDUP_ID}")

    return "\n".join(lines)


async def auto_comment_on_review(
    repo: str,
    pr_id: int,
    title: str,
    recommendation: str,
    findings: List[Dict[str, Any]],
    scores: Dict[str, int],
    duration_seconds: int,
    iteration_id: int,
) -> Dict[str, Any]:
    """Post all comments for a completed review (with dedup)."""
    client = AzureDevOpsCommentClient()
    stats = {"summary_posted": False, "inline_posted": 0, "skipped": 0, "errors": []}

    high_count = sum(1 for f in findings if f.get("severity") == "HIGH")
    medium_count = sum(1 for f in findings if f.get("severity") == "MEDIUM")
    low_count = sum(1 for f in findings if f.get("severity") == "LOW")

    existing_threads = await client.get_existing_threads(repo, pr_id)
    existing_keys = _build_existing_comment_keys(existing_threads)
    logger.info(f"Found {len(existing_keys)} existing bot comments on PR #{pr_id}")

    # Fetch changeTrackingId per file — each file has a unique ID
    change_tracking_map = await client.get_change_tracking_ids(repo, pr_id, iteration_id)
    logger.info(
        f"Change tracking map for PR #{pr_id} iter {iteration_id}: "
        f"{len(change_tracking_map)} files"
    )

    # Summary
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

    # Inline comments
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
            file_path=file_path,
        )

        import asyncio
        await asyncio.sleep(0.5)

        # Look up the correct changeTrackingId for this file
        normalized_for_lookup = file_path if file_path.startswith("/") else f"/{file_path}"
        ct_id = change_tracking_map.get(normalized_for_lookup)
        if not ct_id:
            error = (
                f"Skipped inline comment at {normalized_path}:{line_number}: "
                "file is not present in the reviewed Azure DevOps iteration"
            )
            logger.warning(error)
            stats["errors"].append(error)
            continue

        result = await client.post_inline_comment(
            repo, pr_id, file_path, line_number, comment_text,
            iteration_id=iteration_id,
            change_tracking_id=ct_id,
        )
        if result:
            stats["inline_posted"] += 1
        else:
            stats["errors"].append(f"Failed to comment on {normalized_path}:{line_number}")

    return stats
