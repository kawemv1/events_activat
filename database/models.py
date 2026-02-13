from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    industries = Column(JSON, default=list)
    cities = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    # Автотюнинг: исключения на основе feedback
    feedback_metadata = Column(JSON, default=dict)  # excluded_industries, excluded_sources, prefer_large_only
    created_at = Column(DateTime, default=datetime.utcnow)
    
    feedbacks = relationship("Feedback", back_populates="user")
    sent_events = relationship("UserEvent", back_populates="user")

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    city = Column(String, nullable=True, index=True)
    place = Column(String, nullable=True)       # Место проведения (Exhibition Center и т.д.)
    image_url = Column(String, nullable=True)   # Ссылка на картинку
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    url = Column(String, nullable=False, unique=True) # Unique чтобы не дублировать
    source = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    feedbacks = relationship("Feedback", back_populates="event")
    sent_to_users = relationship("UserEvent", back_populates="event")

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