"""Azure DevOps REST API client with parallel file fetching."""

import asyncio
import base64
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import httpx
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class FetchedFile:
    path: str
    change_type: str
    src_content: Optional[str] = None
    tgt_content: Optional[str] = None
    diff: str = ""
    error: Optional[str] = None


class AzureDevOpsClient:
    def __init__(self):
        self.pat = settings.AZURE_DEVOPS_PAT
        self.base_url = settings.azure_base_url
        self.repo_base = f"{self.base_url}/_apis/git/repositories"
        self.auth_header = f"Basic {base64.b64encode(f':{self.pat}'.encode()).decode()}"
        self.headers = {
            "Authorization": self.auth_header,
            "Accept": "application/json",
        }

    async def _get(self, url: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            text = resp.text
            # Strip BOM
            if text.startswith("\ufeff"):
                text = text[1:]
            return json.loads(text)

    async def _get_raw(self, url: str) -> Optional[str]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            text = resp.text
            if text.startswith("\ufeff"):
                text = text[1:]
            return text

    async def get_prs_for_reviewer(self, repo: str, reviewer_name: str) -> List[Dict[str, Any]]:
        """Get active PRs where reviewer_name is a required or optional reviewer."""
        url = (
            f"{self.repo_base}/{repo}/pullrequests"
            f"?searchCriteria.status=active"
            f"&api-version=7.1"
        )
        data = await self._get(url)
        prs = data.get("value", [])

        matched = []
        for pr in prs:
            reviewers = pr.get("reviewers", [])
            is_reviewer = False
            is_required = False
            for r in reviewers:
                display = r.get("displayName", "")
                unique = r.get("uniqueName", "")
                if reviewer_name.lower() in display.lower() or reviewer_name.lower() in unique.lower():
                    is_reviewer = True
                    if r.get("isRequired", False):
                        is_required = True
                    break
            if is_reviewer:
                matched.append({
                    "azure_pr_id": pr["pullRequestId"],
                    "repo": repo,
                    "title": pr.get("title", ""),
                    "description": pr.get("description", ""),
                    "author": pr.get("createdBy", {}).get("displayName", ""),
                    "author_email": pr.get("createdBy", {}).get("uniqueName", ""),
                    "source_branch": pr.get("sourceRefName", "").replace("refs/heads/", ""),
                    "target_branch": pr.get("targetRefName", "").replace("refs/heads/", ""),
                    "status": pr.get("status", "active"),
                    "is_reviewer_required": "yes" if is_required else "no",
                    "reviewers_json": json.dumps([
                        {"name": r.get("displayName", ""), "required": r.get("isRequired", False)}
                        for r in reviewers
                    ]),
                    "url": f"https://dev.azure.com/{settings.AZURE_ORG}/{settings.AZURE_PROJECT}/_git/{repo}/pullrequest/{pr['pullRequestId']}",
                    "azure_created_at": pr.get("creationDate", ""),
                })

        return matched

    async def get_pr_iterations(self, repo: str, pr_id: int) -> tuple:
        """Get latest iteration ID and source/target commit SHAs."""
        url = f"{self.repo_base}/{repo}/pullrequests/{pr_id}/iterations?api-version=7.1"
        data = await self._get(url)
        iterations = data.get("value", [])
        if not iterations:
            return None, None, None
        latest = iterations[-1]
        iter_id = latest["id"]
        source_sha = latest.get("sourceRefCommit", {}).get("commitId")
        target_sha = latest.get("targetRefCommit", {}).get("commitId")
        return iter_id, source_sha, target_sha

    async def get_pr_changes(self, repo: str, pr_id: int, iteration_id: int) -> List[dict]:
        """Get list of changed files in a PR iteration."""
        url = (
            f"{self.repo_base}/{repo}/pullrequests/{pr_id}"
            f"/iterations/{iteration_id}/changes?api-version=7.1"
        )
        data = await self._get(url)
        return data.get("changeEntries", [])

    async def fetch_file_content(
        self, repo: str, path: str, branch: str
    ) -> Optional[str]:
        """Fetch file content from a specific branch."""
        url = (
            f"{self.repo_base}/{repo}/items"
            f"?path={path}"
            f"&versionDescriptor.version={branch}"
            f"&versionDescriptor.versionType=branch"
            f"&api-version=7.1-preview.1"
            f"&includeContent=true"
        )
        return await self._get_raw(url)

    async def fetch_files_parallel(
        self, repo: str, files: List[dict], source_branch: str, target_branch: str
    ) -> List[FetchedFile]:
        """Fetch all file contents in parallel using ThreadPoolExecutor."""
        import difflib

        results: List[FetchedFile] = []

        async def _fetch_one(item: dict) -> FetchedFile:
            path = item["item"]["path"]
            change_type = item["changeType"]
            ff = FetchedFile(path=path, change_type=change_type)

            try:
                # Source (feature branch) — always fetch
                src_task = self.fetch_file_content(repo, path, source_branch)

                if change_type == "add":
                    ff.src_content = await src_task
                    ff.tgt_content = None
                else:
                    # Fetch both in parallel
                    tgt_task = self.fetch_file_content(repo, path, target_branch)
                    ff.src_content, ff.tgt_content = await asyncio.gather(src_task, tgt_task)

                # Generate diff
                if ff.src_content and ff.tgt_content:
                    diff_lines = difflib.unified_diff(
                        ff.tgt_content.splitlines(keepends=True),
                        ff.src_content.splitlines(keepends=True),
                        fromfile=f"base/{path}",
                        tofile=f"head/{path}",
                        lineterm="",
                    )
                    ff.diff = "\n".join(diff_lines)
                elif ff.src_content:
                    ff.diff = ff.src_content  # new file
                else:
                    ff.error = "File not found"
                    ff.diff = ""

            except Exception as e:
                ff.error = str(e)
                logger.error(f"Error fetching {path}: {e}")

            return ff

        # Run all fetches concurrently (max 10 at a time)
        semaphore = asyncio.Semaphore(10)

        async def _bounded(item):
            async with semaphore:
                return await _fetch_one(item)

        tasks = [_bounded(item) for item in files]
        results = await asyncio.gather(*tasks)

        return results
