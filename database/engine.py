from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL
from database.models import Base

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    # Добавляем колонки, если их не было (миграция для существующих БД)
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(events)"))
        columns = [row[1] for row in result.fetchall()]
        if "place" not in columns:
            conn.execute(text("ALTER TABLE events ADD COLUMN place VARCHAR"))
            conn.commit()
        if "image_url" not in columns:
            conn.execute(text("ALTER TABLE events ADD COLUMN image_url VARCHAR"))
            conn.commit()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()