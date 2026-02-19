"""Export all events to a single CSV file."""
import csv
import logging
import re
from pathlib import Path
from sqlalchemy.orm import Session

from database.models import Event
from config import STOP_WORDS

logger = logging.getLogger(__name__)

CSV_PATH = Path("events.csv")
CSV_COLUMNS = [
    "name",
    "title",
    "short_description",
    "place",
    "date",
    "category",
    "url",
    "source",
    "country",
    "city",
    "image_url",
]


def export_events_to_csv(db: Session) -> str:
    """
    Export all events from DB to events.csv.
    Returns the absolute path to the created file.
    """
    events = db.query(Event).order_by(Event.id.desc()).all()

    def _contains_stop_word(text: str) -> bool:
        """Check if text contains any STOP_WORD variation (case-insensitive, handles hyphens/spaces)."""
        if not text:
            return False
        # Normalize text: lowercase, replace hyphens/spaces with single space
        normalized = re.sub(r'[-\s]+', ' ', text.lower())
        # Check each stop word (already lowercase in config)
        for stop_word in STOP_WORDS:
            # Normalize stop word too
            normalized_stop = re.sub(r'[-\s]+', ' ', stop_word.lower())
            # Check if stop word appears as whole word or part of word (for variations)
            if normalized_stop in normalized:
                return True
        return False

    rows = []
    for e in events:
        # Filter out events containing STOP_WORDS
        title = e.title or ""
        description = e.description or ""
        full_text = f"{title} {description}"
        
        if _contains_stop_word(full_text):
            logger.debug(f"Skipping event with STOP_WORDS in CSV export: {e.title[:50] if e.title else 'N/A'}")
            continue
        
        date_str = ""
        if e.start_date:
            date_str = e.start_date.strftime("%d.%m.%Y")
        rows.append({
            "name": (e.name or e.title or "")[:500],
            "title": (e.title or "")[:500],
            "short_description": (e.description or "")[:2000],
            "place": (e.place or "")[:300],
            "date": date_str,
            "category": (e.industry or "")[:200],
            "url": e.url or "",
            "source": e.source or "",
            "country": e.country or "",
            "city": e.city or "",
            "image_url": e.image_url or "",
        })

    filepath = Path(__file__).parent.parent / CSV_PATH
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Exported {len(rows)} events to {filepath}")
    return str(filepath.resolve())
