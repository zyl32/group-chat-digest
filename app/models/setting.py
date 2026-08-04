from sqlalchemy import Column, String

from app.models.db import Base


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)
