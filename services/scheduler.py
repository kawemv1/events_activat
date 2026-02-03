from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from database.engine import SessionLocal
from database.models import Event
from services.parser import EventParser
from services.notification import notify_users_about_events
from config import PARSING_INTERVAL_MINUTES
from aiogram import Bot
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def parse_and_save_events(bot: Bot):
    """Парсинг событий и сохранение в БД"""
    db: Session = SessionLocal()
    parser = None
    try:
        parser = EventParser()
        events_data = await parser.parse_all_sources()

        new_events = []

        for event_data in events_data:
            # Проверяем, есть ли уже такое событие в БД (по URL)
            existing = db.query(Event).filter(Event.url == event_data['url']).first()

            if not existing:
                # Создаем новое событие
                event = Event(
                    title=event_data['title'],
                    description=event_data['description'],
                    city=event_data['city'],
                    start_date=event_data['start_date'],
                    end_date=event_data['end_date'],
                    url=event_data['url'],
                    source=event_data['source'],
                    industry=event_data.get('industry'),
                )
                db.add(event)
                new_events.append(event)
            else:
                # Обновляем существующее событие
                existing.title = event_data['title']
                existing.description = event_data['description']
                existing.city = event_data['city']
                existing.start_date = event_data['start_date']
                existing.end_date = event_data['end_date']
                existing.updated_at = datetime.utcnow()

        db.flush()  # Получаем ID для новых событий
        db.commit()

        # Отправляем уведомления о новых событиях
        if new_events:
            await notify_users_about_events(bot, new_events)
            logger.info(f"Найдено {len(new_events)} новых событий")

    except Exception as e:
        logger.error(f"Ошибка при парсинге событий: {e}")
        db.rollback()
    finally:
        if parser:
            await parser.close()
        db.close()


def start_scheduler(bot: Bot, run_immediately: bool = False):
    """Запуск планировщика"""
    scheduler.add_job(
        parse_and_save_events,
        trigger=IntervalTrigger(minutes=PARSING_INTERVAL_MINUTES),
        args=[bot],
        id='parse_events',
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Планировщик запущен. Интервал: {PARSING_INTERVAL_MINUTES} минут")
    
    if run_immediately:
        # Запускаем парсинг сразу при старте (асинхронно, не блокируя запуск)
        import asyncio
        asyncio.create_task(parse_and_save_events(bot))


def stop_scheduler():
    """Остановка планировщика"""
    scheduler.shutdown()
    logger.info("Планировщик остановлен")
