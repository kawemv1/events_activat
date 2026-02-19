from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import os

Base = declarative_base()

# Use JSONB on PostgreSQL, plain JSON on SQLite
_is_pg = not os.getenv("DATABASE_URL", "sqlite").startswith("sqlite")
JsonType = JSONB if _is_pg else JSON


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    countries = Column(JsonType, default=list)
    industries = Column(JsonType, default=list)
    cities = Column(JsonType, default=list)
    is_active = Column(Boolean, default=True)
    feedback_metadata = Column(JsonType, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    feedbacks = relationship("Feedback", back_populates="user")
    sent_events = relationship("UserEvent", back_populates="user")


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    city = Column(String, nullable=True, index=True)
    place = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    start_date = Column(DateTime, nullable=True, index=True)
    end_date = Column(DateTime, nullable=True)
    url = Column(String, nullable=False, unique=True)
    source = Column(String, nullable=True)
    country = Column(String, nullable=True, index=True)
    industry = Column(String, nullable=True, index=True)
    event_hash = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    feedbacks = relationship("Feedback", back_populates="event")
    sent_to_users = relationship("UserEvent", back_populates="event")

    __table_args__ = (
        Index("ix_events_country_start_date", "country", "start_date"),
    )


class Feedback(Base):
    __tablename__ = "feedbacks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    is_positive = Column(Boolean, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="feedbacks")
    event = relationship("Event", back_populates="feedbacks")


class UserEvent(Base):
    __tablename__ = "user_events"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="sent_events")
    event = relationship("Event", back_populates="sent_to_users")
