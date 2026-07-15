"""PR Poller — checks for new PRs and triggers reviews."""

import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import PullRequest, PollState, Review, Finding
from services.azure_client import AzureDevOpsClient
from services.security_scanner import run_security_scan
from config import settings

logger = logging.getLogger(__name__)


async def get_or_create_poll_state(db: AsyncSession, repo: str) -> PollState:
    result = await db.execute(select(PollState).where(PollState.repo == repo))
    state = result.scalar_one_or_none()
    if not state:
        state = PollState(repo=repo, last_seen_pr_ids="[]")
        db.add(state)
        await db.flush()
    return state


async def poll_and_review(db: AsyncSession) -> Dict[str, Any]:
    """
    Main polling function:
    1. Fetch active PRs where REVIEWER_NAME is assigned
    2. Compare with DB — find new PRs only
    3. For each new PR: fetch files, security scan, create review record
    4. Return summary of what was found
    """
    client = AzureDevOpsClient()
    reviewer = settings.REVIEWER_NAME
    summary = {"repos_polled": 0, "new_prs": 0, "reviews_created": 0, "errors": []}

    for repo in settings.repos_list:
        try:
            # Ensure clean session state for each repo
            await db.rollback()
            # Get PRs where reviewer is assigned
            prs = await client.get_prs_for_reviewer(repo, reviewer)
            summary["repos_polled"] += 1

            if not prs:
                # Update poll state even if no PRs
                state = await get_or_create_poll_state(db, repo)
                state.last_poll_at = datetime.now(timezone.utc)
                continue

            # Get previously seen PR IDs
            state = await get_or_create_poll_state(db, repo)
            seen_ids = set(json.loads(state.last_seen_pr_ids or "[]"))
            current_ids = {pr["azure_pr_id"] for pr in prs}

            # First-run mode: only if NO poll_state existed before AND no PR records exist
            # This prevents duplicate creation on container restart
            existing_count = await db.execute(
                select(func.count(PullRequest.id)).where(PullRequest.repo == repo)
            )
            has_existing_prs = (existing_count.scalar() or 0) > 0

            is_first_run = not seen_ids and state.last_poll_at is None and not has_existing_prs
            if is_first_run:
                state.last_poll_at = datetime.now(timezone.utc)
                state.last_seen_pr_ids = json.dumps(list(current_ids))

                # Create PR records so they show up in dashboard (no review)
                for pr_data in prs:
                    existing = await db.execute(
                        select(PullRequest).where(
                            PullRequest.azure_pr_id == pr_data["azure_pr_id"],
                            PullRequest.repo == repo,
                        )
                    )
                    if not existing.scalar_one_or_none():
                        pr = PullRequest(
                            azure_pr_id=pr_data["azure_pr_id"],
                            repo=repo,
                            title=pr_data["title"],
                            description=pr_data.get("description", ""),
                            author=pr_data["author"],
                            author_email=pr_data.get("author_email", ""),
                            source_branch=pr_data["source_branch"],
                            target_branch=pr_data["target_branch"],
                            status=pr_data.get("status", "active"),
                            is_reviewer_required=pr_data.get("is_reviewer_required", "no"),
                            reviewers_json=pr_data.get("reviewers_json", "[]"),
                            url=pr_data["url"],
                            azure_created_at=_parse_date(pr_data.get("azure_created_at")),
                        )
                        db.add(pr)

                await db.commit()
                logger.info(
                    f"[{repo}] First run — recorded {len(current_ids)} existing PRs "
                    f"(skipping reviews, will only review new PRs going forward)"
                )
                summary["new_prs"] += 0
                continue

            # Ensure poll_state is always updated (even when first-run is skipped)
            if state.last_poll_at is None:
                state.last_poll_at = datetime.now(timezone.utc)
                state.last_seen_pr_ids = json.dumps(list(current_ids))
                logger.info(f"[{repo}] Synced poll_state with {len(current_ids)} existing PRs")

            # Filter to new PRs only
            new_prs = [pr for pr in prs if pr["azure_pr_id"] not in seen_ids]

            if not new_prs:
                # No new PRs — just update poll time
                state.last_poll_at = datetime.now(timezone.utc)
                state.last_seen_pr_ids = json.dumps(list(current_ids))
                logger.info(f"[{repo}] No new PRs for reviewer {reviewer}")
                continue

            summary["new_prs"] += len(new_prs)
            logger.info(f"[{repo}] Found {len(new_prs)} new PR(s) for {reviewer}")

            # Process each new PR
            for pr_data in new_prs:
                try:
                    await _process_new_pr(db, client, repo, pr_data)
                    summary["reviews_created"] += 1
                except Exception as e:
                    error_msg = f"Error processing PR #{pr_data['azure_pr_id']} in {repo}: {e}"
                    logger.error(error_msg)
                    summary["errors"].append(error_msg)

            # Update state with all current PR IDs (including old ones still active)
            state.last_poll_at = datetime.now(timezone.utc)
            state.last_seen_pr_ids = json.dumps(list(current_ids))

        except Exception as e:
            error_msg = f"Error polling {repo}: {e}"
            logger.error(error_msg)
            summary["errors"].append(error_msg)

    await db.commit()
    return summary


async def _process_new_pr(
    db: AsyncSession, client: AzureDevOpsClient, repo: str, pr_data: Dict[str, Any],
    existing_pr: PullRequest = None,
):
    """Process a single new PR: create PR record, fetch files, scan, create review."""
    # Use existing PR record or create new one
    if existing_pr:
        pr = existing_pr
    else:
        pr = PullRequest(
        azure_pr_id=pr_data["azure_pr_id"],
        repo=repo,
        title=pr_data["title"],
        description=pr_data.get("description", ""),
        author=pr_data["author"],
        author_email=pr_data.get("author_email", ""),
        source_branch=pr_data["source_branch"],
        target_branch=pr_data["target_branch"],
        status=pr_data.get("status", "active"),
        is_reviewer_required=pr_data.get("is_reviewer_required", "no"),
        reviewers_json=pr_data.get("reviewers_json", "[]"),
        url=pr_data["url"],
        azure_created_at=_parse_date(pr_data.get("azure_created_at")),
    )
    db.add(pr)
    await db.flush()

    # Create review record (pending)
    review = Review(
        pr_id=pr.id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(review)
    await db.flush()

    # Fetch iterations and changes
    iter_id, source_sha, target_sha = await client.get_pr_iterations(repo, pr_data["azure_pr_id"])
    if not iter_id:
        review.status = "failed"
        review.summary = "No iterations found for this PR"
        await db.commit()
        return

    changes = await client.get_pr_changes(repo, pr_data["azure_pr_id"], iter_id)
    if not changes:
        review.status = "completed"
        review.summary = "No file changes found"
        review.recommendation = "comment"
        review.completed_at = datetime.now(timezone.utc)
        review.duration_seconds = 0
        await db.commit()
        return

    # Fetch all files in parallel
    source_branch = pr_data["source_branch"]
    target_branch = pr_data["target_branch"]
    fetched_files = await client.fetch_files_parallel(repo, changes, source_branch, target_branch)

    # Build diff text
    all_diffs = []
    files_content = {}
    for ff in fetched_files:
        if ff.src_content:
            all_diffs.append(f"\n{'='*60}\nFILE: {ff.path} ({ff.change_type})\n{'='*60}\n{ff.diff}")
            files_content[ff.path] = ff.src_content

    review.raw_diff = "\n".join(all_diffs)

    # Security scan (grep patterns + semgrep)
    security_findings = run_security_scan(files_content)
    review.security_scan_json = json.dumps([
        {
            "file": f.file,
            "line": f.line,
            "pattern": f.pattern,
            "severity": f.severity,
            "owasp": f.owasp,
            "code": f.code,
            "source": f.source,
        }
        for f in security_findings
    ])

    # LLM review (deep code analysis)
    llm_findings = []
    try:
        from services.llm_reviewer import review_pr_with_llm
        logger.info(f"Starting LLM review for PR #{pr_data['azure_pr_id']}...")
        llm_findings = await review_pr_with_llm(
            title=str(pr.title or ""),
            author=str(pr.author or ""),
            source_branch=str(pr_data["source_branch"]),
            target_branch=str(pr_data["target_branch"]),
            files=[
                {
                    "path": str(ff.path),
                    "change_type": str(ff.change_type),
                    "src_content": str(ff.src_content or ""),
                }
                for ff in fetched_files
                if ff.src_content
            ],
        )
        logger.info(f"LLM review found {len(llm_findings)} findings")
    except Exception as e:
        logger.error(f"LLM review failed (continuing with security scan only): {type(e).__name__}: {e}")
        llm_findings = []

    # Create Finding records — merge security scan + LLM findings
    high_count = 0
    medium_count = 0
    low_count = 0
    seen_keys = set()  # dedup security + LLM findings on same file:line

    # Security findings first
    for sf in security_findings:
        key = (sf.file, sf.line)
        seen_keys.add(key)
        finding = Finding(
            review_id=review.id,
            severity=sf.severity,
            category="Security",
            owasp_tag=sf.owasp,
            file_path=sf.file,
            line_number=sf.line,
            description=f"**{sf.pattern}** detected via {sf.source}\n\nCode: `{sf.code}`",
            code_snippet=sf.code,
            fix_suggestion=_get_fix_suggestion(sf.pattern),
            is_automated=True,
        )
        db.add(finding)
        if sf.severity == "HIGH":
            high_count += 1
        elif sf.severity == "MEDIUM":
            medium_count += 1
        else:
            low_count += 1

    # LLM findings (skip if same file:line already covered by security scan)
    for lf in llm_findings:
        key = (lf.file_path, lf.line_number)
        if key in seen_keys:
            continue  # security scan already found something here
        seen_keys.add(key)

        finding = Finding(
            review_id=review.id,
            severity=lf.severity,
            category=lf.category,
            owasp_tag=lf.owasp_tag,
            file_path=lf.file_path,
            line_number=lf.line_number,
            function_name=lf.function_name,
            description=lf.description,
            code_snippet=lf.code_snippet,
            fix_suggestion=lf.fix_suggestion,
            is_automated=True,
        )
        db.add(finding)
        if lf.severity == "HIGH":
            high_count += 1
        elif lf.severity == "MEDIUM":
            medium_count += 1
        else:
            low_count += 1

    # Set review scores based on all findings
    review.score_security = max(10 - high_count * 3 - medium_count, 1) if (high_count + medium_count) > 0 else 10
    # LLM findings refine logic/test/arch scores
    logic_issues = sum(1 for f in llm_findings if f.category in ("BUG", "Issue"))
    test_issues = sum(1 for f in llm_findings if f.category == "Test")
    arch_issues = sum(1 for f in llm_findings if f.category == "Architecture")
    review.score_logic = max(10 - logic_issues * 2, 1) if logic_issues > 0 else 9
    review.score_tests = max(10 - test_issues * 2, 1) if test_issues > 0 else 7
    review.score_style = 7
    review.score_architecture = max(10 - arch_issues * 2, 1) if arch_issues > 0 else 8

    # Set recommendation
    if high_count > 0:
        review.recommendation = "request_changes"
        review.summary = f"🔴 Found {high_count} HIGH, {medium_count} MEDIUM, {low_count} LOW issues ({len(security_findings)} security + {len(llm_findings)} LLM)."
    elif medium_count > 0:
        review.recommendation = "comment"
        review.summary = f"🟡 Security scan found {medium_count} MEDIUM, {low_count} LOW issues."
    else:
        review.recommendation = "approve"
        review.summary = f"🟢 Security scan clean. {low_count} LOW issues found."

    review.status = "completed"
    review.completed_at = datetime.now(timezone.utc)
    review.duration_seconds = int((review.completed_at - review.started_at).total_seconds())

    await db.commit()
    logger.info(
        f"Review completed for PR #{pr_data['azure_pr_id']} in {repo}: "
        f"HIGH={high_count}, MEDIUM={medium_count}, LOW={low_count}"
    )

    # Auto-comment if enabled
    await _maybe_auto_comment(db, repo, pr, review, security_findings)


async def _maybe_auto_comment(
    db: AsyncSession, repo: str, pr: PullRequest, review: Review,
    security_findings: list,
):
    """Post comments to Azure DevOps PR if auto-comment is enabled."""
    from models import AppConfig
    from services.auto_comment import auto_comment_on_review
    from sqlalchemy.orm import selectinload

    # Check if auto-comment is enabled
    result = await db.execute(
        select(AppConfig).where(AppConfig.key == "auto_comment_enabled")
    )
    config = result.scalar_one_or_none()
    if not config or config.value.lower() != "true":
        return

    # Re-fetch review with findings eagerly loaded (lazy load fails after commit)
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.findings))
        .where(Review.id == review.id)
    )
    review_with_findings = result.scalar_one_or_none()
    if not review_with_findings:
        return

    # Build findings data for comment
    findings_data = [
        {
            "severity": f.severity,
            "category": f.category,
            "owasp_tag": f.owasp_tag,
            "file_path": f.file_path,
            "line_number": f.line_number,
            "description": f.description,
            "code_snippet": f.code_snippet,
            "fix_suggestion": f.fix_suggestion,
        }
        for f in review_with_findings.findings
    ]

    scores = {
        "Logic": review_with_findings.score_logic or 0,
        "Security": review_with_findings.score_security or 0,
        "Tests": review_with_findings.score_tests or 0,
        "Style": review_with_findings.score_style or 0,
        "Architecture": review_with_findings.score_architecture or 0,
    }

    logger.info(f"Auto-commenting on PR #{pr.azure_pr_id} in {repo}...")
    stats = await auto_comment_on_review(
        repo=repo,
        pr_id=pr.azure_pr_id,
        title=pr.title or "",
        recommendation=review.recommendation or "comment",
        findings=findings_data,
        scores=scores,
        duration_seconds=review.duration_seconds or 0,
    )

    if stats["summary_posted"]:
        logger.info(f"  ✅ Summary comment posted on PR #{pr.azure_pr_id}")
    if stats["inline_posted"] > 0:
        logger.info(f"  ✅ {stats['inline_posted']} inline comments posted on PR #{pr.azure_pr_id}")
    if stats["errors"]:
        for err in stats["errors"]:
            logger.error(f"  ❌ {err}")


def _parse_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        # Azure DevOps format: 2024-01-15T10:30:00.000Z
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _get_fix_suggestion(pattern: str) -> str:
    fixes = {
        "hardcoded_password": "Move password to environment variable: `process.env.PASSWORD`",
        "hardcoded_api_key": "Move API key to environment variable or secrets manager",
        "hardcoded_token": "Move token to environment variable or secrets manager",
        "hardcoded_jwt": "Remove JWT from code. Use environment variable.",
        "aws_key": "Remove AWS key from code. Use IAM roles or env vars.",
        "private_key": "Remove private key from code. Use secrets manager.",
        "sql_concat": "Use parameterized queries: `.query('SELECT * FROM t WHERE id = $1', [id])`",
        "sql_string_format": "Use parameterized queries instead of string formatting",
        "command_injection": "Use array form: `spawn('cmd', [arg1, arg2])` instead of string concat",
        "eval_usage": "Remove eval(). Use safe alternatives like JSON.parse() or proper abstractions.",
        "dangerous_deserialize": "Use safe deserialization. Validate input before parsing.",
        "xxe_parser": "Disable external entity processing in XML parser",
        "ssrf_user_url": "Validate URL hostname against allowlist before making request",
        "ssrf_url_construct": "Validate URL hostname against allowlist before making request",
        "path_traversal": "Validate and sanitize file paths. Use path.resolve() and check prefix.",
        "path_user_input": "Validate file paths against allowed directory. Don't use user input directly.",
        "password_in_log": "Remove sensitive data from log statements",
        "password_in_response": "Exclude password fields from API responses",
        "cors_wildcard": "Use specific allowed origins instead of wildcard",
        "ssl_verify_false": "Enable SSL verification. Never disable in production.",
        "debug_enabled": "Disable debug mode in production",
        "mass_assign": "Use DTOs with explicit field definitions instead of passing req.body directly",
        "unvalidated_body": "Validate input with DTO/schema before passing to service",
        "weak_hash": "Use bcrypt or argon2 for password hashing",
        "weak_random": "Use crypto.randomBytes() for security-sensitive random values",
        "http_not_https": "Use HTTPS instead of HTTP",
    }
    return fixes.get(pattern, "Review this pattern and apply appropriate fix.")
