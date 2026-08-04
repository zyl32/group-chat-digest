from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from app.models.db import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("upload_id", "msg_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(String, ForeignKey("uploads.id"), nullable=False, index=True)
    sender = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    msg_id = Column(String, nullable=False)  # 来源平台去重
