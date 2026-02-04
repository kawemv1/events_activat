import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from database.engine import SessionLocal
from database.models import Event
from services.parser import EventParser
from services.notification import notify_users, notify_no_new_events
from config import DAILY_PARSING_HOUR, DAILY_PARSING_MINUTE, SCHEDULER_TIMEZONE
import logging

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone=SCHEDULER_TIMEZONE)

async def run_parsing_cycle(bot: Bot):
    logger.info("Starting parsing cycle...")
    parser = EventParser()
    db = SessionLocal()
    try:
        events_data = await parser.parse_all()
        new_events_objects = []
        
        for e_data in events_data:
            exists = db.query(Event).filter(Event.url == e_data['url']).first()
            if not exists:
                event = Event(**e_data)
                db.add(event)
                db.commit()
                db.refresh(event)
                new_events_objects.append(event)
        
        if new_events_objects:
            logger.info(f"Found {len(new_events_objects)} new events. Notifying users...")
            await notify_users(bot, new_events_objects, db)
        else:
            logger.info("No new events found. Telling users.")
            await notify_no_new_events(bot, db)
            
    except Exception as e:
        logger.error(f"Parsing cycle error: {e}")
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
    logger.info(f"Daily events update scheduled at {DAILY_PARSING_HOUR:02d}:{DAILY_PARSING_MINUTE:02d} ({SCHEDULER_TIMEZONE})")
    scheduler.start()