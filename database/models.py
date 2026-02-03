from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    industries = Column(JSON, default=list)  # Список выбранных индустрий
    cities = Column(JSON, default=list)  # Список выбранных городов
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    feedbacks = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")
    sent_events = relationship("UserEvent", back_populates="user", cascade="all, delete-orphan")


class Event(Base):
    """Модель события/выставки"""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    city = Column(String, nullable=True, index=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    url = Column(String, nullable=False)
    source = Column(String, nullable=True)  # Источник парсинга
    industry = Column(String, nullable=True, index=True)  # Индустрия
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    feedbacks = relationship("Feedback", back_populates="event", cascade="all, delete-orphan")
    sent_to_users = relationship("UserEvent", back_populates="event", cascade="all, delete-orphan")


class Feedback(Base):
    """Модель обратной связи пользователя на событие"""
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    is_positive = Column(Boolean, nullable=False)  # True для 👍, False для 👎
    reason = Column(String, nullable=True)  # Причина отклонения (если is_positive=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    user = relationship("User", back_populates="feedbacks")
    event = relationship("Event", back_populates="feedbacks")


class UserEvent(Base):
    """Связь пользователя и отправленного ему события (для отслеживания уже отправленных)"""
    __tablename__ = "user_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    user = relationship("User", back_populates="sent_events")
    event = relationship("Event", back_populates="sent_to_users")
