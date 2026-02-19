"""Script to run full parsing cycle and export to CSV (no Bot/AI needed)."""
import asyncio
import hashlib
import logging
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.engine import init_db, SessionLocal
from database.models import Event
from services.parser import EventParser
from services.csv_export import export_events_to_csv
from config import STOP_WORDS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _contains_stop_word(text: str) -> bool:
    if not text:
        return False
    normalized = re.sub(r'[-\s]+', ' ', text.lower())
    for stop_word in STOP_WORDS:
        normalized_stop = re.sub(r'[-\s]+', ' ', stop_word.lower())
        if normalized_stop in normalized:
            return True
    return False


def _compute_event_hash(title: str, description: str, start_date: Optional[datetime]) -> str:
    title_norm = (title or "").lower().strip()
    desc_norm = (description or "").lower().strip()
    date_str = start_date.strftime("%Y-%m-%d") if start_date else ""
    content = f"{title_norm}|{desc_norm}|{date_str}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def _calculate_text_similarity(text1: str, text2: str) -> float:
    if not text1 or not text2:
        return 0.0
    norm1 = re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', text1.lower())).strip()
    norm2 = re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', text2.lower())).strip()
    if not norm1 or not norm2:
        return 0.0
    return SequenceMatcher(None, norm1, norm2).ratio()


async def main():
    logger.info("=" * 60)
    logger.info("Starting parse and export (standalone, no AI/Bot)")
    logger.info("=" * 60)

    # Initialize database
    init_db()

    # Step 1: Clear existing events
    db = SessionLocal()
    try:
        deleted = db.query(Event).delete()
        db.commit()
        logger.info(f"Cleared {deleted} existing events from DB")
    except Exception as e:
        db.rollback()
        logger.error(f"Error clearing events: {e}")
    finally:
        db.close()

    # Step 2: Parse all sources
    logger.info("\nParsing all sources...")
    parser = EventParser()
    try:
        events_data = await parser.parse_all()
        logger.info(f"Parser returned {len(events_data)} events")
    finally:
        await parser.close()

    # Step 3: Save to database with dedup + stop-word filtering
    db = SessionLocal()
    saved_count = 0
    skipped_stop = 0
    skipped_dup = 0
    try:
        for e_data in events_data:
            title = e_data.get("title", "")
            description = e_data.get("description", "") or ""
            full_text = f"{title} {description}"

            if _contains_stop_word(full_text):
                skipped_stop += 1
                continue

            # Compute hash
            event_hash = _compute_event_hash(title, description, e_data.get("start_date"))

            # Check duplicates by hash
            if db.query(Event).filter(Event.event_hash == event_hash).first():
                skipped_dup += 1
                continue

            # Check duplicates by URL
            raw_url = e_data.get("url", "")
            if raw_url and db.query(Event).filter(Event.url == raw_url).first():
                skipped_dup += 1
                continue

            # Check description similarity
            is_dup = False
            if description and len(description.strip()) > 20:
                existing = db.query(Event).filter(Event.description.isnot(None)).all()
                for ex in existing:
                    if ex.description and len(ex.description.strip()) > 20:
                        if _calculate_text_similarity(description, ex.description) >= 0.75:
                            is_dup = True
                            break
            if is_dup:
                skipped_dup += 1
                continue

            # Use title as name if not set
            if "name" not in e_data or not e_data["name"]:
                e_data["name"] = title

            e_data["event_hash"] = event_hash
            event = Event(**e_data)
            db.add(event)
            db.commit()
            db.refresh(event)
            saved_count += 1

        logger.info(f"\nSaved {saved_count} events to DB")
        logger.info(f"Skipped: {skipped_stop} (stop words), {skipped_dup} (duplicates)")

        # Step 4: Export to CSV
        csv_path = export_events_to_csv(db)
        logger.info(f"\nCSV exported to: {csv_path}")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        db.close()

    logger.info("=" * 60)
    logger.info("Done!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
