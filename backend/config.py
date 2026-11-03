from pydantic_settings import BaseSettings
from typing import List, Literal
from pydantic import Field


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://admin:fern@localhost:5432/pr_review"
    AZURE_DEVOPS_PAT: str = ""
    AZURE_ORG: str = "AXONS-FIT-Business-and-CPTG"
    AZURE_PROJECT: str = "AgriTech"
    REVIEWER_NAME: str = "FERN"
    POLL_INTERVAL_MINUTES: int = 10
    REPOS: str = "purchase,usermgt,coop,backoffice"

    LLM_BACKEND: Literal["legacy", "hermes"] = "legacy"
    HERMES_BASE_URL: str = "http://host.docker.internal:8642/p/pr-review/v1"
    HERMES_API_KEY: str = ""
    HERMES_MODEL: str = "pr-review"
    HERMES_TIMEOUT_SECONDS: int = Field(default=450, ge=1, le=600)
    HERMES_TOOLS_KEY: str = ""
    HERMES_REQUIRE_TOOLS: bool = True
    HERMES_BATCH_WORKFLOW: bool = False

    @property
    def repos_list(self) -> List[str]:
        return [r.strip() for r in self.REPOS.split(",") if r.strip()]

    @property
    def azure_base_url(self) -> str:
        return f"https://dev.azure.com/{self.AZURE_ORG}/{self.AZURE_PROJECT}"

    class Config:
        env_file = ".env"


settings = Settings()
