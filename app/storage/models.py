from sqlalchemy import Column, DateTime, Integer, String, Text

from app.storage.db import Base


class EventRecord(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(128), index=True, nullable=False)
    event_type = Column(String(64), index=True, nullable=False)
    event_timestamp = Column(DateTime(timezone=True), index=True, nullable=False)
    raw_payload = Column(Text, nullable=False)


class MessageRecord(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(128), index=True, nullable=False)
    template_name = Column(String(128), index=True, nullable=False)
    channel = Column(String(64), nullable=False)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(32), index=True, nullable=False)
    suppression_reason = Column(Text, nullable=True)
