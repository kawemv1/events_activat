from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from config import DATABASE_URL

# Создаем синхронный движок для SQLite
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

# Создаем сессию
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Получить сессию базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Инициализировать базу данных (создать таблицы)"""
    from database.models import Base
    Base.metadata.create_all(bind=engine)
