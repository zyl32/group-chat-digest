from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.models.db import Base


class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(String, ForeignKey("uploads.id"), nullable=False, index=True)
    who = Column(String, nullable=True)
    what = Column(String, nullable=False)
    due_at = Column(DateTime, nullable=True)
    source_msg_id = Column(Integer, nullable=True)
    state = Column(String, default="pending")  # pending|done|ignored|snoozed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
