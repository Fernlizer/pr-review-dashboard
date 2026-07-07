from sqlalchemy import Column, Integer, String, DateTime, func
from database import Base


class AppConfig(Base):
    """Application configuration stored in DB."""
    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(500), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
