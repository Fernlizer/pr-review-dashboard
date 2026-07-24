from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from database import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pr_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=False, index=True)
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    score_logic = Column(Integer)
    score_security = Column(Integer)
    score_tests = Column(Integer)
    score_style = Column(Integer)
    score_architecture = Column(Integer)
    summary = Column(Text)
    recommendation = Column(String(50))  # approve, request_changes, comment
    raw_diff = Column(Text)  # full diff text
    security_scan_json = Column(Text)  # semgrep + grep results JSON
    azure_iteration_id = Column(Integer)  # Azure DevOps iteration reviewed
    source_commit_id = Column(String(64))
    target_commit_id = Column(String(64))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pull_request = relationship("PullRequest", back_populates="reviews")
    findings = relationship("Finding", back_populates="review", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Review #{self.id} PR#{self.pr_id} [{self.status}]>"
