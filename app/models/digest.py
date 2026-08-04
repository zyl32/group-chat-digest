from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String

from app.models.db import Base


class Digest(Base):
    __tablename__ = "digests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(String, ForeignKey("uploads.id"), nullable=False, unique=True)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    window = Column(String, nullable=False)
    summary_blocks = Column(JSON, nullable=False)  # [{topic, summary, msg_range}]
    created_at = Column(DateTime, default=datetime.utcnow)
    model_used = Column(String, nullable=False)
