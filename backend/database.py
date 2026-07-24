import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # create_all does not evolve an existing table. Keep these small,
        # idempotent compatibility migrations close to the model until a full
        # migration framework is introduced.
        await conn.execute(text(
            "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS azure_iteration_id INTEGER"
        ))
        await conn.execute(text(
            "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS source_commit_id VARCHAR(64)"
        ))
        await conn.execute(text(
            "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS target_commit_id VARCHAR(64)"
        ))

        duplicate_count = (await conn.execute(text(
            "SELECT COUNT(*) FROM ("
            "SELECT 1 FROM pull_requests GROUP BY repo, azure_pr_id HAVING COUNT(*) > 1"
            ") duplicate_prs"
        ))).scalar_one()
        if duplicate_count:
            logger.warning(
                "Cannot add the pull-request uniqueness index: %s duplicate Azure PR identities exist. "
                "Run the duplicate-data migration first.",
                duplicate_count,
            )
        else:
            await conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_pull_requests_repo_azure_pr_id "
                "ON pull_requests (repo, azure_pr_id)"
            ))
