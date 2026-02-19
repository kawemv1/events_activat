"""Script to delete all records from the database."""
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.engine import SessionLocal
from database.models import Event, User, Feedback, UserEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clear_all_records():
    """Delete all records from all tables."""
    db = SessionLocal()
    try:
        # Delete in order to respect foreign key constraints
        deleted_user_events = db.query(UserEvent).delete()
        deleted_feedbacks = db.query(Feedback).delete()
        deleted_events = db.query(Event).delete()
        deleted_users = db.query(User).delete()
        
        db.commit()
        
        logger.info(f"Deleted {deleted_user_events} user_events records")
        logger.info(f"Deleted {deleted_feedbacks} feedbacks records")
        logger.info(f"Deleted {deleted_events} events records")
        logger.info(f"Deleted {deleted_users} users records")
        logger.info("✅ All records deleted successfully!")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting records: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    clear_all_records()
