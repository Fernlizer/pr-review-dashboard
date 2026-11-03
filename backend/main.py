"""PR Review Dashboard — FastAPI backend with APScheduler polling."""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db, async_session
from routers.api import router as api_router
from services.pr_poller import poll_and_review
from services.comment_discussion import sync_comment_discussions
from services.hermes_mcp import mcp, mcp_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def scheduled_poll():
    """Poll Azure DevOps for new PRs (called by scheduler)."""
    logger.info("Polling Azure DevOps for new PRs...")
    async with async_session() as db:
        try:
            result = await poll_and_review(db)
            logger.info(
                f"Poll complete: {result['repos_polled']} repos, "
                f"{result['new_prs']} new PRs, "
                f"{result.get('updated_prs', 0)} updated PRs, "
                f"{result['reviews_created']} reviews created"
            )
            if result["errors"]:
                for err in result["errors"]:
                    logger.error(f"  - {err}")
        except Exception as e:
            logger.error(f"Poll failed: {e}")


async def scheduled_discussion_sync():
    """Safely sync new replies without altering the established review poller."""
    async with async_session() as db:
        try:
            result = await sync_comment_discussions(db)
            logger.info("Discussion sync: %(tracked)s tracked, %(replies)s replied, %(skipped_approved)s approved skipped", result)
        except Exception:
            logger.exception("Discussion sync failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    await init_db()

    logger.info(f"Starting poller (interval: {settings.POLL_INTERVAL_MINUTES} min)")
    scheduler.add_job(
        scheduled_poll,
        "interval",
        minutes=settings.POLL_INTERVAL_MINUTES,
        id="pr_poller",
        replace_existing=True,
    )
    scheduler.add_job(
        scheduled_discussion_sync,
        "interval",
        minutes=settings.POLL_INTERVAL_MINUTES,
        id="discussion_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        scheduled_poll,
        "date",
        id="initial_pr_poll",
        replace_existing=True,
    )
    scheduler.start()

    # Expose scheduler to API routes
    app.state.scheduler = scheduler
    app.state.poll_interval = settings.POLL_INTERVAL_MINUTES
    app.state.poller_enabled = True

    # Do not make API readiness depend on Azure DevOps or LLM latency. The
    # one-shot scheduler job above runs the initial poll as soon as the event
    # loop is available, independently from the FastAPI lifespan handshake.
    logger.info("Initial poll scheduled in background")

    async with mcp.session_manager.run():
        yield

    # Shutdown
    scheduler.shutdown()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="PR Review Dashboard",
    description="Automated Azure DevOps PR review with security scanning",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.mount("/hermes-tools", mcp_app)


@app.get("/health")
async def health():
    return {"status": "ok", "reviewer": settings.REVIEWER_NAME, "repos": settings.repos_list}
