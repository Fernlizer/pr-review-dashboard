from sqlalchemy import Column, Integer, String, DateTime, Text, func
from database import Base


class PollState(Base):
    __tablename__ = "poll_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo = Column(String(100), unique=True, nullable=False)
    last_poll_at = Column(DateTime(timezone=True))
    last_seen_pr_ids = Column(Text, default="[]")  # JSON array of PR IDs
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
