"""
Migrate events from local SQLite DB (or events.csv) to Supabase PostgreSQL.

Usage:
    python scripts/migrate_to_supabase.py

Requires DATABASE_URL in .env pointing to Supabase PostgreSQL.
Optionally reads from local events_bot.db if it exists, otherwise from events.csv.
"""
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from database.models import Base, Event

SUPABASE_URL = os.getenv("DATABASE_URL")
LOCAL_DB_PATH = Path(__file__).parent.parent / "events_bot.db"
CSV_PATH = Path(__file__).parent.parent / "events.csv"


def parse_date(date_str: str):
    """Parse date string in DD.MM.YYYY format."""
    if not date_str or not date_str.strip():
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def migrate_from_sqlite(pg_session, sqlite_session):
    """Migrate events from local SQLite to PostgreSQL."""
    events = sqlite_session.query(Event).all()
    print(f"Found {len(events)} events in local SQLite DB")

    migrated = 0
    skipped = 0
    for e in events:
        # Check duplicate by URL
        exists = pg_session.query(Event).filter(Event.url == e.url).first()
        if exists:
            skipped += 1
            continue

        new_event = Event(
            name=e.name,
            title=e.title,
            description=e.description,
            city=e.city,
            place=e.place,
            image_url=e.image_url,
            start_date=e.start_date,
            end_date=e.end_date,
            url=e.url,
            source=e.source,
            country=e.country,
            industry=e.industry,
            event_hash=e.event_hash,
        )
        pg_session.add(new_event)
        migrated += 1

    pg_session.commit()
    print(f"Migrated {migrated} events, skipped {skipped} duplicates")


def migrate_from_csv(pg_session):
    """Migrate events from events.csv to PostgreSQL."""
    if not CSV_PATH.exists():
        print(f"CSV file not found: {CSV_PATH}")
        return

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Found {len(rows)} events in {CSV_PATH}")

    migrated = 0
    skipped = 0
    for row in rows:
        url = row.get("url", "").strip()
        if not url:
            skipped += 1
            continue

        # Check duplicate by URL
        exists = pg_session.query(Event).filter(Event.url == url).first()
        if exists:
            skipped += 1
            continue

        new_event = Event(
            name=row.get("name", "")[:500] or None,
            title=row.get("title", "")[:500] or "Untitled",
            description=row.get("short_description", "")[:2000] or None,
            city=row.get("city", "") or None,
            place=row.get("place", "") or None,
            image_url=row.get("image_url", "") or None,
            start_date=parse_date(row.get("date", "")),
            url=url,
            source=row.get("source", "") or None,
            country=row.get("country", "") or None,
            industry=row.get("category", "") or None,
        )
        pg_session.add(new_event)
        migrated += 1

    pg_session.commit()
    print(f"Migrated {migrated} events from CSV, skipped {skipped} duplicates")


def main():
    if not SUPABASE_URL or "supabase" not in SUPABASE_URL:
        print("ERROR: DATABASE_URL in .env must point to Supabase PostgreSQL")
        print(f"Current value: {SUPABASE_URL}")
        sys.exit(1)

    print(f"Connecting to Supabase: {SUPABASE_URL[:50]}...")
    pg_engine = create_engine(SUPABASE_URL, poolclass=NullPool, echo=False)
    PgSession = sessionmaker(bind=pg_engine)

    # Create tables in Supabase
    print("Creating tables...")
    Base.metadata.create_all(bind=pg_engine)
    print("Tables created successfully")

    pg_session = PgSession()

    try:
        # Prefer SQLite migration (has all fields), fallback to CSV
        if LOCAL_DB_PATH.exists():
            print(f"Migrating from local SQLite: {LOCAL_DB_PATH}")
            sqlite_engine = create_engine(
                f"sqlite:///{LOCAL_DB_PATH}",
                connect_args={"check_same_thread": False}
            )
            SqliteSession = sessionmaker(bind=sqlite_engine)
            sqlite_session = SqliteSession()
            migrate_from_sqlite(pg_session, sqlite_session)
            sqlite_session.close()
        elif CSV_PATH.exists():
            print(f"No local DB found, migrating from CSV: {CSV_PATH}")
            migrate_from_csv(pg_session)
        else:
            print("No local data found (no events_bot.db or events.csv)")
            print("Tables have been created in Supabase — ready for fresh data")

        # Verify
        count = pg_session.query(Event).count()
        print(f"\nTotal events in Supabase: {count}")
        print("Migration complete!")

    finally:
        pg_session.close()


if __name__ == "__main__":
    main()
