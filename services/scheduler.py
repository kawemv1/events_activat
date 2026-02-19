import logging
import re
import hashlib
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from database.engine import SessionLocal
from database.models import Event, UserEvent, Feedback
from services.parser import EventParser
from services.ai_service import extract_event_structured
from services.notification import notify_users, notify_no_new_events
from services.csv_export import export_events_to_csv
from config import DAILY_PARSING_HOUR, DAILY_PARSING_MINUTE, SCHEDULER_TIMEZONE, STOP_WORDS

EXPIRED_AFTER_DAYS = 7
IMAGES_DIR = Path("parsed_images")

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone=SCHEDULER_TIMEZONE)


def _parse_date_str(s: str) -> Optional[datetime]:
    """Try DD.MM.YYYY or similar."""
    if not s or not isinstance(s, str):
        return None
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s.strip())
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except (ValueError, IndexError):
            pass
    return None


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
        # This catches "bootcamp", "online-bootcamp", "bootcamp-2024", etc.
        if normalized_stop in normalized:
            return True
    return False


def _normalize_text_for_comparison(text: str) -> str:
    """Normalize text for comparison: lowercase, remove extra spaces, punctuation."""
    if not text:
        return ""
    # Lowercase, remove extra whitespace, remove common punctuation
    normalized = re.sub(r'[^\w\s]', ' ', text.lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def _calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two texts (0.0 to 1.0)."""
    if not text1 or not text2:
        return 0.0
    norm1 = _normalize_text_for_comparison(text1)
    norm2 = _normalize_text_for_comparison(text2)
    if not norm1 or not norm2:
        return 0.0
    return SequenceMatcher(None, norm1, norm2).ratio()


def _compute_event_hash(title: str, description: str, start_date: Optional[datetime]) -> str:
    """Compute hash for event based on title, description, and start_date."""
    # Normalize text for hashing
    title_norm = (title or "").lower().strip()
    desc_norm = (description or "").lower().strip()
    date_str = start_date.strftime("%Y-%m-%d") if start_date else ""
    
    # Create hash from normalized content
    content = f"{title_norm}|{desc_norm}|{date_str}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def _cleanup_expired_events(db) -> int:
    """Delete events whose start_date is more than 7 days in the past.
    Also removes associated local images and related records."""
    cutoff = datetime.utcnow() - timedelta(days=EXPIRED_AFTER_DAYS)
    expired = db.query(Event).filter(Event.start_date < cutoff).all()

    if not expired:
        return 0

    deleted_images = 0
    for event in expired:
        # Delete local image if it exists
        if event.image_url and not event.image_url.startswith("http"):
            image_path = Path(event.image_url)
            if not image_path.is_absolute():
                image_path = IMAGES_DIR.parent / event.image_url
            if image_path.exists():
                try:
                    image_path.unlink()
                    deleted_images += 1
                except OSError as e:
                    logger.warning(f"Failed to delete image {image_path}: {e}")

        # Delete related records first (foreign keys)
        db.query(UserEvent).filter(UserEvent.event_id == event.id).delete()
        db.query(Feedback).filter(Feedback.event_id == event.id).delete()
        db.delete(event)

    db.commit()
    logger.info(
        f"Cleanup: deleted {len(expired)} expired events "
        f"(older than {cutoff.strftime('%Y-%m-%d')}), "
        f"removed {deleted_images} local images"
    )
    return len(expired)


async def run_parsing_cycle(bot: Bot):
    logger.info("Starting parsing cycle...")
    parser = EventParser()
    db = SessionLocal()
    try:
        # Step 0: Clean up expired events (start_date > 7 days ago)
        _cleanup_expired_events(db)

        events_data = await parser.parse_all()
        new_events_objects = []

        for e_data in events_data:
            raw_title = e_data.get("title", "")
            raw_desc = e_data.get("description", "") or ""
            raw_url = e_data.get("url", "")

            # Keyword check (B2B or any industry category) + Gemini extraction
            extracted = await extract_event_structured(
                raw_title, raw_desc, raw_url
            )

            # Merge extracted fields into event data
            e_data["name"] = extracted.get("name") or raw_title
            e_data["title"] = extracted.get("title") or raw_title
            e_data["description"] = extracted.get("short_description") or raw_desc[:500]
            if extracted.get("place"):
                e_data["place"] = extracted["place"]
            if extracted.get("date"):
                parsed = _parse_date_str(extracted["date"])
                if parsed:
                    e_data["start_date"] = parsed

            # Final STOP_WORDS check after AI extraction
            final_title = e_data.get("title", "")
            final_description = e_data.get("description") or ""
            full_text = f"{final_title} {final_description}"
            
            # Use improved stop word checking that handles variations
            if _contains_stop_word(full_text):
                logger.debug(f"Skipping event with STOP_WORDS: {e_data.get('title', '')[:50]}")
                continue

            # Compute hash for duplicate detection
            event_hash = _compute_event_hash(
                e_data.get("title", ""),
                e_data.get("description", ""),
                e_data.get("start_date")
            )
            
            # Check for duplicates by hash (more reliable than URL alone)
            exists_by_hash = db.query(Event).filter(Event.event_hash == event_hash).first()
            if exists_by_hash:
                logger.debug(f"Skipping duplicate event (hash match): {e_data.get('title', '')[:50]}")
                continue
            
            # Also check by URL as fallback
            exists_by_url = db.query(Event).filter(Event.url == raw_url).first()
            if exists_by_url:
                logger.debug(f"Skipping duplicate event (URL match): {e_data.get('title', '')[:50]}")
                continue
            
            # Check for similar descriptions (>=75% similarity) even if names differ
            new_description = e_data.get("description", "")
            is_duplicate_by_description = False
            if new_description and len(new_description.strip()) > 20:  # Only check if description is meaningful
                existing_events = db.query(Event).filter(Event.description.isnot(None)).all()
                for existing_event in existing_events:
                    if existing_event.description and len(existing_event.description.strip()) > 20:
                        similarity = _calculate_text_similarity(new_description, existing_event.description)
                        if similarity >= 0.75:  # 75% similarity threshold
                            logger.debug(
                                f"Skipping duplicate event (description similarity {similarity:.2%}): "
                                f"'{e_data.get('title', '')[:50]}' similar to '{existing_event.title[:50] if existing_event.title else 'N/A'}'"
                            )
                            is_duplicate_by_description = True
                            break  # Found a duplicate, no need to check further
            
            if is_duplicate_by_description:
                continue

            # Add hash to event data
            e_data["event_hash"] = event_hash
            event = Event(**e_data)
            db.add(event)
            db.commit()
            db.refresh(event)
            new_events_objects.append(event)

        # Export ALL events to CSV
        csv_path = export_events_to_csv(db)
        logger.info(f"Events saved to {csv_path}")

        if new_events_objects:
            logger.info(f"Found {len(new_events_objects)} new events. Notifying users...")
            await notify_users(bot, new_events_objects, db)
        else:
            logger.info("No new events found. Telling users.")
            await notify_no_new_events(bot, db)

    except Exception as e:
        logger.error(f"Parsing cycle error: {e}", exc_info=True)
    finally:
        await parser.close()
        db.close()

def start_scheduler(bot: Bot):
    scheduler.add_job(
        run_parsing_cycle,
        CronTrigger(hour=DAILY_PARSING_HOUR, minute=DAILY_PARSING_MINUTE),
        args=[bot],
        id="daily_events_update",
    )
    logger.info(f"Daily events update at {DAILY_PARSING_HOUR:02d}:{DAILY_PARSING_MINUTE:02d} ({SCHEDULER_TIMEZONE})")
    scheduler.start()