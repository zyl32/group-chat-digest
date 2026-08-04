import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.models.db import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(String, primary_key=True, default=_new_uuid)  # uuid
    filename = Column(String, nullable=False)
    fmt = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="received")  # received|parsing|done|failed
    error_msg = Column(String, nullable=True)
