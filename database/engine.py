from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from config import DATABASE_URL
from database.models import Base

is_sqlite = DATABASE_URL.startswith("sqlite")

engine_kwargs = {"echo": False}

if is_sqlite:
    # SQLite needs check_same_thread=False for multi-threaded use
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL (Supabase): disable SQLAlchemy pooling —
    # Supabase manages the connection pool on its side.
    engine_kwargs["poolclass"] = NullPool

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
