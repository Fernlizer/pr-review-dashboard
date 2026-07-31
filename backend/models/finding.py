from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from database import Base


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False, index=True)
    severity = Column(String(20), nullable=False)  # HIGH, MEDIUM, LOW
    category = Column(String(50), nullable=False)  # BUG, Security, Issue, Suggestion
    owasp_tag = Column(String(100))  # A01:Broken Access Control
    file_path = Column(Text)
    line_number = Column(Integer)
    function_name = Column(String(200))
    description = Column(Text)
    code_snippet = Column(Text)
    fix_suggestion = Column(Text)
    is_automated = Column(Boolean, default=False)  # from semgrep/grep vs LLM
    # Conversation fields are populated only for comments created after the
    # discussion feature is enabled. Existing findings deliberately remain
    # untracked so historical Azure DevOps threads are never processed.
    azure_thread_id = Column(Integer, index=True)
    azure_root_comment_id = Column(Integer)
    discussion_status = Column(String(50))  # awaiting_author, still_open, ready_for_human_review, needs_human_review
    discussion_reason = Column(Text)
    discussion_json = Column(Text)
    last_synced_comment_id = Column(Integer)
    last_synced_at = Column(DateTime(timezone=True))
    last_bot_reply_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    review = relationship("Review", back_populates="findings")

    def __repr__(self):
        return f"<Finding [{self.severity}] {self.category}: {self.file_path}:{self.line_number}>"
