from sqlalchemy import Column, Integer, String, DateTime, Text, func
from sqlalchemy.orm import relationship
from database import Base


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    azure_pr_id = Column(Integer, nullable=False, index=True)
    repo = Column(String(100), nullable=False, index=True)
    title = Column(Text)
    description = Column(Text)
    author = Column(String(200))
    author_email = Column(String(200))
    source_branch = Column(String(500))
    target_branch = Column(String(500))
    status = Column(String(50), default="active")  # active, completed, abandoned
    is_reviewer_required = Column(String(10))  # yes, no
    reviewers_json = Column(Text)  # JSON array of all reviewers
    url = Column(Text)
    created_at = Column(DateTime(timezone=True))
    azure_created_at = Column(DateTime(timezone=True))
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())

    reviews = relationship("Review", back_populates="pull_request", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PR #{self.azure_pr_id} [{self.repo}] {self.title}>"
