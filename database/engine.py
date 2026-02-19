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
        if "country" not in columns:
            conn.execute(text("ALTER TABLE events ADD COLUMN country VARCHAR"))
            conn.commit()
        if "name" not in columns:
            conn.execute(text("ALTER TABLE events ADD COLUMN name VARCHAR"))
            conn.commit()
        if "event_hash" not in columns:
            conn.execute(text("ALTER TABLE events ADD COLUMN event_hash VARCHAR"))
            conn.commit()
        users_cols = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        users_columns = [row[1] for row in users_cols] if users_cols else []
        if "feedback_metadata" not in users_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN feedback_metadata VARCHAR DEFAULT '{}'"))
            conn.commit()
        if "countries" not in users_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN countries VARCHAR DEFAULT '[]'"))
            conn.commit()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()