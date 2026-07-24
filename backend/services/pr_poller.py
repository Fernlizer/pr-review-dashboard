"""PR Poller — checks for new PRs and triggers reviews."""

import asyncio
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
_poll_lock = asyncio.Lock()
_review_locks: Dict[str, asyncio.Lock] = {}


async def get_or_create_poll_state(db: AsyncSession, repo: str) -> PollState:
    result = await db.execute(select(PollState).where(PollState.repo == repo))
    state = result.scalar_one_or_none()
    if not state:
        state = PollState(repo=repo, last_seen_pr_ids="[]")
        db.add(state)
        await db.flush()
    return state


async def poll_and_review(db: AsyncSession) -> Dict[str, Any]:
    """Run at most one poll cycle per application process at a time."""
    if _poll_lock.locked():
        logger.warning("Poll requested while another poll is still running; skipping duplicate run")
        return {
            "repos_polled": 0,
            "new_prs": 0,
            "reviews_created": 0,
            "errors": [],
            "status": "already_running",
        }

    async with _poll_lock:
        return await _poll_and_review(db)


async def _poll_and_review(db: AsyncSession) -> Dict[str, Any]:
    """
    Main polling function:
    1. Fetch active PRs where REVIEWER_NAME is assigned
    2. Compare with DB — find new PRs only
    3. For each new PR: fetch files, security scan, create review record
    4. Return summary of what was found
    """
    client = AzureDevOpsClient()
    reviewer = settings.REVIEWER_NAME
    summary = {
        "repos_polled": 0,
        "new_prs": 0,
        "updated_prs": 0,
        "reviews_created": 0,
        "errors": [],
    }

    for repo in settings.repos_list:
        try:
            # Get PRs where reviewer is assigned
            prs = await client.get_prs_for_reviewer(repo, reviewer)
            summary["repos_polled"] += 1

            if not prs:
                # Update poll state even if no PRs
                state = await get_or_create_poll_state(db, repo)
                state.last_poll_at = datetime.now(timezone.utc)
                await db.commit()  # Commit state immediately
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
                    if not existing.scalars().first():
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
                await db.commit()
                logger.info(f"[{repo}] Synced poll_state with {len(current_ids)} existing PRs")
                # This is a recovery/bootstrap path. Do not immediately classify
                # every already-open PR as new using the stale, empty seen_ids.
                continue

            # Filter to new PRs only, then separately detect PRs that were
            # already seen but moved to a newer Azure iteration/commit.
            new_prs = [pr for pr in prs if pr["azure_pr_id"] not in seen_ids]
            updated_prs = await _find_updated_prs(db, client, repo, prs, seen_ids)

            # Additional dedup: skip PRs that already have a completed review recently
            already_reviewed_ids = set()
            if new_prs:
                pr_ids_to_check = [pr["azure_pr_id"] for pr in new_prs]
                existing_reviews = await db.execute(
                    select(PullRequest.azure_pr_id)
                    .join(Review, Review.pr_id == PullRequest.id)
                    .where(
                        PullRequest.repo == repo,
                        PullRequest.azure_pr_id.in_(pr_ids_to_check),
                        Review.status == "completed",
                    )
                    .distinct()
                )
                already_reviewed_ids = {row[0] for row in existing_reviews.fetchall()}
                if already_reviewed_ids:
                    logger.info(
                        f"[{repo}] Skipping {len(already_reviewed_ids)} PRs already reviewed: "
                        f"{already_reviewed_ids}"
                    )
                new_prs = [pr for pr in new_prs if pr["azure_pr_id"] not in already_reviewed_ids]

            if not new_prs and not updated_prs:
                # No new PRs — just update poll time
                state.last_poll_at = datetime.now(timezone.utc)
                state.last_seen_pr_ids = json.dumps(list(current_ids))
                await db.commit()  # Commit state immediately
                logger.info(f"[{repo}] No new PRs for reviewer {reviewer}")
                continue

            summary["new_prs"] += len(new_prs)
            summary["updated_prs"] += len(updated_prs)
            logger.info(
                f"[{repo}] Found {len(new_prs)} new PR(s) and "
                f"{len(updated_prs)} updated PR(s) for {reviewer}"
            )

            completed_ids = set()

            # Process each new PR
            for pr_data in new_prs:
                try:
                    completed = await _process_new_pr(db, client, repo, pr_data)
                    if completed:
                        completed_ids.add(pr_data["azure_pr_id"])
                        summary["reviews_created"] += 1
                except Exception as e:
                    await db.rollback()
                    error_msg = f"Error processing PR #{pr_data['azure_pr_id']} in {repo}: {e}"
                    logger.error(error_msg)
                    summary["errors"].append(error_msg)

            # Process PRs that already existed but have newer code than the
            # latest completed review captured.
            for pr_data, existing_pr in updated_prs:
                try:
                    completed = await _process_new_pr(db, client, repo, pr_data, existing_pr=existing_pr)
                    if completed:
                        completed_ids.add(pr_data["azure_pr_id"])
                        summary["reviews_created"] += 1
                except Exception as e:
                    await db.rollback()
                    error_msg = f"Error processing updated PR #{pr_data['azure_pr_id']} in {repo}: {e}"
                    logger.error(error_msg)
                    summary["errors"].append(error_msg)

            # Only completed (or previously completed) PRs are marked seen. A
            # failed review stays eligible for a later retry instead of vanishing.
            # A failed review may have rolled back this session, so re-read the
            # persistent state before updating it.
            state = await get_or_create_poll_state(db, repo)
            state.last_poll_at = datetime.now(timezone.utc)
            seen_for_next_poll = (seen_ids & current_ids) | already_reviewed_ids | completed_ids
            state.last_seen_pr_ids = json.dumps(list(seen_for_next_poll))
            await db.commit()  # Commit state immediately after processing

        except Exception as e:
            await db.rollback()
            error_msg = f"Error polling {repo}: {e}"
            logger.error(error_msg)
            summary["errors"].append(error_msg)

    return summary


async def _find_updated_prs(
    db: AsyncSession,
    client: AzureDevOpsClient,
    repo: str,
    prs: List[Dict[str, Any]],
    seen_ids: set,
) -> List[tuple[Dict[str, Any], PullRequest]]:
    """Return seen PRs whose latest Azure iteration is newer than the last review."""
    updated = []
    seen_prs = [pr for pr in prs if pr["azure_pr_id"] in seen_ids]

    for pr_data in seen_prs:
        existing = await _get_existing_pr(db, repo, pr_data["azure_pr_id"])
        if not existing:
            continue

        latest_review = await _get_latest_completed_review(db, existing.id)
        if not latest_review:
            continue

        iter_id, source_sha, target_sha = await client.get_pr_iterations(repo, pr_data["azure_pr_id"])
        if not iter_id:
            continue

        if _review_matches_iteration(latest_review, iter_id, source_sha, target_sha):
            continue

        logger.info(
            "[%s] PR #%s changed since review #%s: iteration %s -> %s",
            repo,
            pr_data["azure_pr_id"],
            latest_review.id,
            latest_review.azure_iteration_id,
            iter_id,
        )
        pr_data["_review_iteration"] = {
            "iteration_id": iter_id,
            "source_sha": source_sha,
            "target_sha": target_sha,
        }
        updated.append((pr_data, existing))

    return updated


async def _get_existing_pr(db: AsyncSession, repo: str, azure_pr_id: int) -> Optional[PullRequest]:
    result = await db.execute(
        select(PullRequest).where(
            PullRequest.azure_pr_id == azure_pr_id,
            PullRequest.repo == repo,
        )
    )
    return result.scalars().first()


async def _get_latest_completed_review(db: AsyncSession, pr_id: int) -> Optional[Review]:
    result = await db.execute(
        select(Review)
        .where(Review.pr_id == pr_id, Review.status == "completed")
        .order_by(Review.id.desc())
        .limit(1)
    )
    return result.scalars().first()


def _review_matches_iteration(
    review: Review,
    iteration_id: int,
    source_sha: Optional[str],
    target_sha: Optional[str],
) -> bool:
    if review.azure_iteration_id != iteration_id:
        return False
    if source_sha and review.source_commit_id != source_sha:
        return False
    if target_sha and review.target_commit_id != target_sha:
        return False
    return True


async def _process_new_pr(
    db: AsyncSession, client: AzureDevOpsClient, repo: str, pr_data: Dict[str, Any],
    existing_pr: PullRequest = None,
):
    """Serialize review creation for one Azure DevOps PR in this process."""
    key = f"{repo}:{pr_data['azure_pr_id']}"
    lock = _review_locks.setdefault(key, asyncio.Lock())
    if lock.locked():
        logger.warning("Review already running for %s; skipping duplicate request", key)
        return False

    async with lock:
        return await _process_new_pr_unlocked(db, client, repo, pr_data, existing_pr)


async def _process_new_pr_unlocked(
    db: AsyncSession, client: AzureDevOpsClient, repo: str, pr_data: Dict[str, Any],
    existing_pr: PullRequest = None,
):
    """Process a single new PR: create PR record, fetch files, scan, create review."""
    # Use existing PR record or create new one (with dedup check)
    if existing_pr:
        pr = existing_pr
    else:
        # Check if PR record already exists to avoid duplicates
        result = await db.execute(
            select(PullRequest).where(
                PullRequest.azure_pr_id == pr_data["azure_pr_id"],
                PullRequest.repo == repo,
            )
        )
        # Legacy databases may already contain duplicate records. Prefer the
        # first one while the database unique migration is being rolled out.
        pr = result.scalars().first()
        if not pr:
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

    pr.title = pr_data.get("title", pr.title)
    pr.description = pr_data.get("description", pr.description or "")
    pr.author = pr_data.get("author", pr.author)
    pr.author_email = pr_data.get("author_email", pr.author_email or "")
    pr.source_branch = pr_data.get("source_branch", pr.source_branch)
    pr.target_branch = pr_data.get("target_branch", pr.target_branch)
    pr.status = pr_data.get("status", pr.status or "active")
    pr.is_reviewer_required = pr_data.get("is_reviewer_required", pr.is_reviewer_required)
    pr.reviewers_json = pr_data.get("reviewers_json", pr.reviewers_json or "[]")
    pr.url = pr_data.get("url", pr.url)

    # Create review record (pending)
    review = Review(
        pr_id=pr.id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(review)
    await db.flush()

    # Fetch iterations and changes
    iteration_hint = pr_data.get("_review_iteration") or {}
    if iteration_hint:
        iter_id = iteration_hint["iteration_id"]
        source_sha = iteration_hint.get("source_sha")
        target_sha = iteration_hint.get("target_sha")
    else:
        iter_id, source_sha, target_sha = await client.get_pr_iterations(repo, pr_data["azure_pr_id"])
    if not iter_id:
        review.status = "failed"
        review.summary = "No iterations found for this PR"
        await db.commit()
        return False

    review.azure_iteration_id = iter_id
    review.source_commit_id = source_sha
    review.target_commit_id = target_sha

    changes = await client.get_pr_changes(repo, pr_data["azure_pr_id"], iter_id)
    if not changes:
        review.status = "completed"
        review.summary = "No file changes found"
        review.recommendation = "comment"
        review.completed_at = datetime.now(timezone.utc)
        review.duration_seconds = 0
        await db.commit()
        return True

    # Fetch all files in parallel
    source_branch = pr_data["source_branch"]
    target_branch = pr_data["target_branch"]
    fetched_files = await client.fetch_files_parallel(repo, changes, source_branch, target_branch)

    # Build diff text + track changed lines
    all_diffs = []
    files_content = {}
    changed_lines = {}  # {file_path: set of changed line numbers in new file}

    for ff in fetched_files:
        if ff.src_content:
            all_diffs.append(f"\n{'='*60}\nFILE: {ff.path} ({ff.change_type})\n{'='*60}\n{ff.diff}")
            files_content[ff.path] = ff.src_content

            # Extract changed line numbers from diff
            if ff.change_type == "add":
                # New file — all lines are changed
                changed_lines[ff.path] = set(range(1, len(ff.src_content.splitlines()) + 1))
            elif ff.tgt_content:
                # Compute diff and find changed lines
                changed_lines[ff.path] = _extract_changed_lines(ff.tgt_content, ff.src_content)
            else:
                changed_lines[ff.path] = set()

    review.raw_diff = "\n".join(all_diffs)

    # Security scan (grep patterns + semgrep)
    raw_security_findings = run_security_scan(files_content)
    security_findings = [
        finding
        for finding in raw_security_findings
        if finding.line in changed_lines.get(finding.file, set())
    ]
    skipped_unchanged = len(raw_security_findings) - len(security_findings)
    if skipped_unchanged:
        logger.info(
            "Ignored %s security finding(s) outside changed lines for PR #%s",
            skipped_unchanged,
            pr_data["azure_pr_id"],
        )
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

    # LLM review (deep code analysis — diff only)
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
                    "tgt_content": str(ff.tgt_content or ""),
                }
                for ff in fetched_files
                if ff.src_content
            ],
            changed_lines=changed_lines,
        )
        logger.info(f"LLM review found {len(llm_findings)} findings (changed lines only)")
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
    await _maybe_auto_comment(db, repo, pr, review)
    return True


async def _maybe_auto_comment(
    db: AsyncSession, repo: str, pr: PullRequest, review: Review,
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
        iteration_id=review.azure_iteration_id or 0,
    )

    if stats["summary_posted"]:
        logger.info(f"  ✅ Summary comment posted on PR #{pr.azure_pr_id}")
    if stats["inline_posted"] > 0:
        logger.info(f"  ✅ {stats['inline_posted']} inline comments posted on PR #{pr.azure_pr_id}")
    if stats["errors"]:
        for err in stats["errors"]:
            logger.error(f"  ❌ {err}")


def _extract_changed_lines(old_content: str, new_content: str) -> set:
    """Extract line numbers that were changed (added/modified) in the new file."""
    import difflib
    changed = set()
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("insert", "replace"):
            # Lines j1 to j2 in the new file were changed
            for line_num in range(j1 + 1, j2 + 1):  # 1-indexed
                changed.add(line_num)

    return changed


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
