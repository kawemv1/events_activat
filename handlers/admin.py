from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram import Bot
from services.scheduler import parse_and_save_events
from sqlalchemy.orm import Session
from database.engine import SessionLocal
from database.models import User, Event
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("parse"))
async def cmd_parse(message: Message, bot: Bot):
    """Ручной запуск парсинга событий"""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        
        if not user:
            await message.answer("Сначала зарегистрируйся через /start")
            return

        await message.answer("🔍 Начинаю парсинг событий... Это может занять некоторое время.")
        
        # Запускаем парсинг
        await parse_and_save_events(bot)
        
        # Проверяем, сколько событий в БД
        events_count = db.query(Event).count()
        
        await message.answer(
            f"✅ Парсинг завершен!\n\n"
            f"📊 Всего событий в базе: {events_count}\n"
            f"🆕 Новые события будут отправлены тебе автоматически, если они соответствуют твоим фильтрам.\n\n"
            f"💡 Используй /stats для просмотра статистики."
        )
    except Exception as e:
        logger.error(f"Ошибка при ручном парсинге: {e}")
        await message.answer(f"❌ Ошибка при парсинге: {str(e)}")
    finally:
        db.close()


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика по событиям"""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        
        if not user:
            await message.answer("Сначала зарегистрируйся через /start")
            return

        total_events = db.query(Event).count()
        user_industries = ", ".join(user.industries) if user.industries else "Не выбраны"
        user_cities = ", ".join(user.cities) if user.cities else "Не выбраны"
        
        await message.answer(
            f"📊 Статистика\n\n"
            f"📅 Всего событий в базе: {total_events}\n\n"
            f"👤 Твои настройки:\n"
            f"📊 Индустрии: {user_industries}\n"
            f"🏙️ Города: {user_cities}\n\n"
            f"💡 Используй /parse для поиска новых событий"
        )
    finally:
        db.close()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по командам"""
    help_text = (
        "📖 Справка по командам:\n\n"
        "/start - Начать работу с ботом\n"
        "/settings - Изменить настройки (индустрии и города)\n"
        "/parse - Запустить поиск новых событий вручную\n"
        "/stats - Показать статистику\n"
        "/help - Показать эту справку\n\n"
        "💡 Бот автоматически присылает новые события каждые 60 минут.\n"
        "💡 Используй кнопки 👍/👎 под событиями для улучшения рекомендаций."
    )
    await message.answer(help_text)
