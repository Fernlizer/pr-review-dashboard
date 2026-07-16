"""API endpoints for PRs, reviews, findings, and stats."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import logging

from database import get_db
from models import PullRequest, Review, Finding, PollState, AppConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


# --- PRs ---

@router.get("/prs")
async def list_prs(
    repo: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = select(PullRequest).options(selectinload(PullRequest.reviews))
    if repo:
        query = query.where(PullRequest.repo == repo)
    if status:
        query = query.where(PullRequest.status == status)
    query = query.order_by(desc(PullRequest.discovered_at)).limit(limit).offset(offset)

    result = await db.execute(query)
    prs = result.scalars().all()

    # Count total
    count_query = select(func.count(PullRequest.id))
    if repo:
        count_query = count_query.where(PullRequest.repo == repo)
    if status:
        count_query = count_query.where(PullRequest.status == status)
    total = (await db.execute(count_query)).scalar()

    return {
        "total": total,
        "prs": [
            {
                "id": pr.id,
                "azure_pr_id": pr.azure_pr_id,
                "repo": pr.repo,
                "title": pr.title,
                "author": pr.author,
                "source_branch": pr.source_branch,
                "target_branch": pr.target_branch,
                "status": pr.status,
                "is_reviewer_required": pr.is_reviewer_required,
                "url": pr.url,
                "discovered_at": pr.discovered_at.isoformat() if pr.discovered_at else None,
                "azure_created_at": pr.azure_created_at.isoformat() if pr.azure_created_at else None,
                "latest_review": _review_summary(pr.reviews[0]) if pr.reviews else None,
            }
            for pr in prs
        ],
    }


@router.get("/prs/{pr_id}")
async def get_pr(pr_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PullRequest)
        .options(selectinload(PullRequest.reviews).selectinload(Review.findings))
        .where(PullRequest.id == pr_id)
    )
    pr = result.scalar_one_or_none()
    if not pr:
        raise HTTPException(404, "PR not found")

    return {
        "id": pr.id,
        "azure_pr_id": pr.azure_pr_id,
        "repo": pr.repo,
        "title": pr.title,
        "description": pr.description,
        "author": pr.author,
        "author_email": pr.author_email,
        "source_branch": pr.source_branch,
        "target_branch": pr.target_branch,
        "status": pr.status,
        "is_reviewer_required": pr.is_reviewer_required,
        "reviewers_json": pr.reviewers_json,
        "url": pr.url,
        "discovered_at": pr.discovered_at.isoformat() if pr.discovered_at else None,
        "azure_created_at": pr.azure_created_at.isoformat() if pr.azure_created_at else None,
        "reviews": [
            {
                "id": rv.id,
                "status": rv.status,
                "score_logic": rv.score_logic,
                "score_security": rv.score_security,
                "score_tests": rv.score_tests,
                "score_style": rv.score_style,
                "score_architecture": rv.score_architecture,
                "summary": rv.summary,
                "recommendation": rv.recommendation,
                "started_at": rv.started_at.isoformat() if rv.started_at else None,
                "completed_at": rv.completed_at.isoformat() if rv.completed_at else None,
                "duration_seconds": rv.duration_seconds,
                "findings": [
                    {
                        "id": f.id,
                        "severity": f.severity,
                        "category": f.category,
                        "owasp_tag": f.owasp_tag,
                        "file_path": f.file_path,
                        "line_number": f.line_number,
                        "function_name": f.function_name,
                        "description": f.description,
                        "code_snippet": f.code_snippet,
                        "fix_suggestion": f.fix_suggestion,
                        "is_automated": f.is_automated,
                    }
                    for f in rv.findings
                ],
            }
            for rv in pr.reviews
        ],
    }


# --- Reviews ---

@router.get("/reviews")
async def list_reviews(
    status: Optional[str] = None,
    recommendation: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = select(Review).options(selectinload(Review.findings), selectinload(Review.pull_request))
    if status:
        query = query.where(Review.status == status)
    if recommendation:
        query = query.where(Review.recommendation == recommendation)
    query = query.order_by(desc(Review.created_at)).limit(limit).offset(offset)

    result = await db.execute(query)
    reviews = result.scalars().all()

    return {
        "reviews": [
            {
                "id": rv.id,
                "pr_id": rv.pr_id,
                "status": rv.status,
                "recommendation": rv.recommendation,
                "summary": rv.summary,
                "score_security": rv.score_security,
                "high_count": sum(1 for f in rv.findings if f.severity == "HIGH"),
                "medium_count": sum(1 for f in rv.findings if f.severity == "MEDIUM"),
                "low_count": sum(1 for f in rv.findings if f.severity == "LOW"),
                "duration_seconds": rv.duration_seconds,
                "created_at": rv.created_at.isoformat() if rv.created_at else None,
                "pr_title": rv.pull_request.title if rv.pull_request else None,
                "pr_repo": rv.pull_request.repo if rv.pull_request else None,
            }
            for rv in reviews
        ],
    }


@router.get("/reviews/{review_id}")
async def get_review(review_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.findings), selectinload(Review.pull_request))
        .where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(404, "Review not found")

    return {
        "id": review.id,
        "pr_id": review.pr_id,
        "status": review.status,
        "score_logic": review.score_logic,
        "score_security": review.score_security,
        "score_tests": review.score_tests,
        "score_style": review.score_style,
        "score_architecture": review.score_architecture,
        "summary": review.summary,
        "recommendation": review.recommendation,
        "raw_diff": review.raw_diff,
        "security_scan_json": review.security_scan_json,
        "started_at": review.started_at.isoformat() if review.started_at else None,
        "completed_at": review.completed_at.isoformat() if review.completed_at else None,
        "duration_seconds": review.duration_seconds,
        "findings": [
            {
                "id": f.id,
                "severity": f.severity,
                "category": f.category,
                "owasp_tag": f.owasp_tag,
                "file_path": f.file_path,
                "line_number": f.line_number,
                "function_name": f.function_name,
                "description": f.description,
                "code_snippet": f.code_snippet,
                "fix_suggestion": f.fix_suggestion,
                "is_automated": f.is_automated,
            }
            for f in review.findings
        ],
        "pr": {
            "id": review.pull_request.id,
            "azure_pr_id": review.pull_request.azure_pr_id,
            "repo": review.pull_request.repo,
            "title": review.pull_request.title,
            "author": review.pull_request.author,
            "url": review.pull_request.url,
        } if review.pull_request else None,
    }


@router.post("/prs/{pr_id}/review")
async def trigger_review(pr_id: int, db: AsyncSession = Depends(get_db)):
    """Manually trigger a review for a specific PR."""
    from services.pr_poller import _process_new_pr
    from services.azure_client import AzureDevOpsClient

    # Get PR from DB
    result = await db.execute(select(PullRequest).where(PullRequest.id == pr_id))
    pr = result.scalar_one_or_none()
    if not pr:
        raise HTTPException(404, "PR not found")

    client = AzureDevOpsClient()
    pr_data = {
        "azure_pr_id": pr.azure_pr_id,
        "title": pr.title,
        "description": pr.description or "",
        "author": pr.author or "",
        "author_email": pr.author_email or "",
        "source_branch": pr.source_branch or "",
        "target_branch": pr.target_branch or "",
        "status": pr.status or "active",
        "is_reviewer_required": pr.is_reviewer_required or "no",
        "reviewers_json": pr.reviewers_json or "[]",
        "url": pr.url or "",
    }

    try:
        await _process_new_pr(db, client, pr.repo, pr_data, existing_pr=pr)
        return {"status": "completed", "message": f"Review completed for PR #{pr.azure_pr_id}"}
    except Exception as e:
        raise HTTPException(500, f"Review failed: {str(e)}")


# --- Stats ---

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total_prs = (await db.execute(select(func.count(PullRequest.id)))).scalar()
    total_reviews = (await db.execute(select(func.count(Review.id)))).scalar()
    total_findings = (await db.execute(select(func.count(Finding.id)))).scalar()

    # Findings by severity
    severity_counts = {}
    for sev in ["HIGH", "MEDIUM", "LOW"]:
        count = (await db.execute(
            select(func.count(Finding.id)).where(Finding.severity == sev)
        )).scalar()
        severity_counts[sev] = count

    # Recommendations breakdown
    rec_counts = {}
    for rec in ["approve", "request_changes", "comment"]:
        count = (await db.execute(
            select(func.count(Review.id)).where(Review.recommendation == rec)
        )).scalar()
        rec_counts[rec] = count

    # Poll state
    poll_states = (await db.execute(select(PollState))).scalars().all()

    return {
        "total_prs": total_prs,
        "total_reviews": total_reviews,
        "total_findings": total_findings,
        "findings_by_severity": severity_counts,
        "recommendations": rec_counts,
        "poll_states": [
            {
                "repo": ps.repo,
                "last_poll_at": ps.last_poll_at.isoformat() if ps.last_poll_at else None,
            }
            for ps in poll_states
        ],
    }


# --- Manual Trigger ---

@router.post("/poll")
async def trigger_poll(db: AsyncSession = Depends(get_db)):
    """Manually trigger a poll cycle."""
    from services.pr_poller import poll_and_review
    result = await poll_and_review(db)
    return result


# --- Scheduler Control ---

@router.get("/scheduler/status")
async def scheduler_status(request: Request):
    """Get real scheduler status — reads from APScheduler, not a flag."""
    sched = request.app.state.scheduler
    job = sched.get_job("pr_poller")

    is_running = False
    next_run_time = None
    interval_minutes = getattr(request.app.state, "poll_interval", 10)

    if job:
        is_running = job.next_run_time is not None
        if job.next_run_time:
            next_run_time = job.next_run_time.isoformat()

    return {
        "enabled": is_running,
        "interval_minutes": interval_minutes,
        "next_run": next_run_time,
        "job_exists": job is not None,
        "scheduler_running": sched.running,
    }


class SchedulerIntervalUpdate(BaseModel):
    minutes: int = Field(ge=1, le=1440, description="Poll interval in minutes (1-1440)")


@router.put("/scheduler/interval")
async def update_interval(body: SchedulerIntervalUpdate, request: Request):
    """Update poll interval — reschedules the job with new interval."""
    sched = request.app.state.scheduler
    job = sched.get_job("pr_poller")

    if not job:
        raise HTTPException(404, "Poller job not found")

    sched.reschedule_job(
        "pr_poller",
        trigger="interval",
        minutes=body.minutes,
    )
    request.app.state.poll_interval = body.minutes

    logger.info(f"Poll interval updated to {body.minutes} minutes")

    return {
        "status": "updated",
        "interval_minutes": body.minutes,
        "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
    }


@router.post("/scheduler/enable")
async def enable_scheduler(request: Request):
    """Enable the poller — resumes the paused job."""
    sched = request.app.state.scheduler
    job = sched.get_job("pr_poller")

    if not job:
        raise HTTPException(404, "Poller job not found")

    if job.next_run_time is not None:
        return {"status": "already_enabled", "message": "Poller is already running"}

    sched.resume_job("pr_poller")
    request.app.state.poller_enabled = True

    # Re-read job state after resume
    job = sched.get_job("pr_poller")
    logger.info("Poller enabled")

    return {
        "status": "enabled",
        "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None,
    }


@router.post("/scheduler/disable")
async def disable_scheduler(request: Request):
    """Disable the poller — pauses the job (does NOT remove it)."""
    sched = request.app.state.scheduler
    job = sched.get_job("pr_poller")

    if not job:
        raise HTTPException(404, "Poller job not found")

    if job.next_run_time is None:
        return {"status": "already_disabled", "message": "Poller is already paused"}

    sched.pause_job("pr_poller")
    request.app.state.poller_enabled = False

    logger.info("Poller disabled")

    return {
        "status": "disabled",
        "message": "Poller paused. No automatic polling until re-enabled.",
    }


# --- Auto-Comment Settings ---

async def _get_config_value(db: AsyncSession, key: str, default: str = "") -> str:
    """Get config value from DB."""
    result = await db.execute(select(AppConfig).where(AppConfig.key == key))
    config = result.scalar_one_or_none()
    return config.value if config else default


async def _set_config_value(db: AsyncSession, key: str, value: str):
    """Set config value in DB (upsert)."""
    result = await db.execute(select(AppConfig).where(AppConfig.key == key))
    config = result.scalar_one_or_none()
    if config:
        config.value = value
    else:
        config = AppConfig(key=key, value=value)
        db.add(config)
    await db.commit()


@router.get("/settings/auto-comment")
async def get_auto_comment_setting(db: AsyncSession = Depends(get_db)):
    """Get auto-comment enabled status."""
    value = await _get_config_value(db, "auto_comment_enabled", "false")
    return {"enabled": value.lower() == "true"}


@router.post("/settings/auto-comment/enable")
async def enable_auto_comment(db: AsyncSession = Depends(get_db)):
    """Enable auto-comment on PRs after review."""
    await _set_config_value(db, "auto_comment_enabled", "true")
    logger.info("Auto-comment enabled")
    return {"status": "enabled", "message": "Auto-comment is now ON. Reviews will post comments to PRs."}


@router.post("/settings/auto-comment/disable")
async def disable_auto_comment(db: AsyncSession = Depends(get_db)):
    """Disable auto-comment on PRs after review."""
    await _set_config_value(db, "auto_comment_enabled", "false")
    logger.info("Auto-comment disabled")
    return {"status": "disabled", "message": "Auto-comment is now OFF. Reviews will not post comments."}


# --- Submit PR URL for Review ---

class SubmitPRUrlRequest(BaseModel):
    url: str = Field(description="Azure DevOps PR URL", examples=[
        "https://dev.azure.com/AXONS-FIT-Business-and-CPTG/AgriTech/_git/purchase/pullrequest/33762"
    ])


@router.post("/prs/submit-url", response_model=dict)
async def submit_pr_url(
    body: SubmitPRUrlRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Submit a PR URL for review — even if user is not assigned as reviewer."""
    import re

    url = body.url.strip()

    # Parse Azure DevOps PR URL
    # Pattern: https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{pr_id}
    pattern = r"https://dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/]+)/pullrequest/(\d+)"
    match = re.match(pattern, url)

    if not match:
        raise HTTPException(400, "Invalid Azure DevOps PR URL. Expected: https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{id}")

    org, project, repo, pr_id = match.groups()
    azure_pr_id = int(pr_id)

    # Check if already exists
    existing = await db.execute(
        select(PullRequest).where(
            PullRequest.azure_pr_id == azure_pr_id,
            PullRequest.repo == repo,
        )
    )
    existing_pr = existing.scalar_one_or_none()

    if existing_pr:
        # Already tracked — run review on latest
        background_tasks.add_task(run_single_review, existing_pr.id)
        return {
            "status": "existing",
            "pr_id": existing_pr.id,
            "message": f"PR #{azure_pr_id} already tracked. Running review...",
            "url": url,
        }

    # Fetch PR details from Azure DevOps
    from services.azure_client import AzureDevOpsClient
    client = AzureDevOpsClient()

    try:
        # Get PR details
        pr_url = f"{client.base_url}/_apis/git/repositories/{repo}/pullrequests/{azure_pr_id}?api-version=7.1"
        pr_data = await client._get(pr_url)
    except Exception as e:
        raise HTTPException(404, f"Could not fetch PR #{azure_pr_id} from repo '{repo}': {e}")

    if not pr_data:
        raise HTTPException(404, f"PR #{azure_pr_id} not found in repo '{repo}'")

    # Create PR record
    pr = PullRequest(
        azure_pr_id=azure_pr_id,
        repo=repo,
        title=pr_data.get("title", ""),
        author=pr_data.get("createdBy", {}).get("displayName", ""),
        source_branch=pr_data.get("sourceRefName", "").replace("refs/heads/", ""),
        target_branch=pr_data.get("targetRefName", "").replace("refs/heads/", ""),
        status=pr_data.get("status", "active").lower(),
        is_reviewer_required=False,
        azure_created_at=_parse_date(pr_data.get("creationDate", "")),
        url=url,
    )
    db.add(pr)
    await db.commit()
    await db.refresh(pr)

    # Run review in background
    background_tasks.add_task(run_single_review, pr.id)

    return {
        "status": "added",
        "pr_id": pr.id,
        "message": f"PR #{azure_pr_id} added to system. Running review...",
        "url": url,
        "title": pr.title,
        "author": pr.author,
        "repo": repo,
    }


async def run_single_review(pr_id: int):
    """Run review for a single PR in background."""
    from services.pr_poller import _process_new_pr
    from services.azure_client import AzureDevOpsClient
    from database import async_session

    async with async_session() as db:
        try:
            result = await db.execute(
                select(PullRequest).where(PullRequest.id == pr_id)
            )
            pr = result.scalar_one_or_none()
            if not pr:
                return

            client = AzureDevOpsClient()
            pr_data = {
                "azure_pr_id": pr.azure_pr_id,
                "title": pr.title,
                "description": pr.description or "",
                "author": pr.author or "",
                "author_email": pr.author_email or "",
                "source_branch": pr.source_branch or "",
                "target_branch": pr.target_branch or "",
                "status": pr.status or "active",
                "is_reviewer_required": "no",
                "reviewers_json": "[]",
            }
            await _process_new_pr(db, client, str(pr.repo), pr_data)
            logger.info(f"Background review completed for PR#{pr_id}")
        except Exception as e:
            logger.error(f"Background review failed for PR#{pr_id}: {e}")


# --- Comment Selected Findings ---

class CommentSelectedRequest(BaseModel):
    finding_ids: List[int] = Field(description="List of finding IDs to comment on")


class CommentSelectedResponse(BaseModel):
    posted: int
    skipped: int
    errors: List[str]


@router.post("/reviews/{review_id}/comment-selected", response_model=CommentSelectedResponse)
async def comment_selected_findings(
    review_id: int,
    body: CommentSelectedRequest,
    db: AsyncSession = Depends(get_db),
):
    """Post inline comments for selected findings on the PR."""
    from services.auto_comment import AzureDevOpsCommentClient, format_inline_comment

    # Get review with PR info
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.findings), selectinload(Review.pull_request))
        .where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(404, "Review not found")
    if not review.pull_request:
        raise HTTPException(404, "PR not found for this review")

    pr = review.pull_request
    client = AzureDevOpsCommentClient()

    # Get latest iteration for inline comments
    iteration_id = await client.get_latest_iteration(pr.repo, pr.azure_pr_id) or 1

    # Get existing threads for dedup
    existing_threads = await client.get_existing_threads(pr.repo, pr.azure_pr_id)
    from services.auto_comment import _build_existing_comment_keys
    existing_keys = _build_existing_comment_keys(existing_threads)

    # Filter to selected findings
    selected = [f for f in review.findings if f.id in body.finding_ids]
    if not selected:
        raise HTTPException(400, "No valid finding IDs provided")

    posted = 0
    skipped = 0
    errors = []

    for finding in selected:
        # Normalize path
        file_path = finding.file_path or ""
        if not file_path.startswith("/"):
            file_path = "/" + file_path

        # Dedup check
        dedup_key = f"inline:{file_path}:{finding.line_number}"
        if dedup_key in existing_keys:
            skipped += 1
            continue

        # Format comment
        comment_text = format_inline_comment(
            severity=finding.severity,
            category=finding.category,
            owasp_tag=finding.owasp_tag,
            description=finding.description,
            code_snippet=finding.code_snippet,
            fix_suggestion=finding.fix_suggestion,
        )

        # Post
        import asyncio
        await asyncio.sleep(0.5)

        result = await client.post_inline_comment(
            repo=pr.repo,
            pr_id=pr.azure_pr_id,
            file_path=finding.file_path,
            line_number=finding.line_number,
            message=comment_text,
            iteration_id=iteration_id,
        )
        if result:
            posted += 1
            existing_keys.add(dedup_key)
        else:
            errors.append(f"Failed: {file_path}:{finding.line_number}")

    return CommentSelectedResponse(posted=posted, skipped=skipped, errors=errors)


# --- Helpers ---

def _review_summary(review: Review) -> dict:
    return {
        "id": review.id,
        "status": review.status,
        "recommendation": review.recommendation,
        "score_security": review.score_security,
        "completed_at": review.completed_at.isoformat() if review.completed_at else None,
    }
