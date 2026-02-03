from typing import List, Dict
from sqlalchemy.orm import Session
from database.engine import SessionLocal
from database.models import User, Event, UserEvent, Feedback
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from handlers.feedback import get_event_keyboard
import logging

logger = logging.getLogger(__name__)


def format_event_message(event: Event) -> str:
    """Форматирование сообщения об ивенте"""
    message = f"🎯 <b>{event.title}</b>\n\n"

    if event.start_date:
        date_str = event.start_date.strftime("%d.%m.%Y")
        if event.end_date:
            date_str += f" - {event.end_date.strftime('%d.%m.%Y')}"
        message += f"📅 <b>Даты:</b> {date_str}\n"

    if event.city:
        message += f"🏙️ <b>Город:</b> {event.city}\n"

    if event.description:
        message += f"\n{event.description}\n"

    if event.source:
        message += f"\n📌 Источник: {event.source}"

    return message


async def send_event_to_user(bot: Bot, user: User, event: Event, db: Session):
    """Отправить событие пользователю"""
    try:
        # Проверяем, не отправляли ли уже это событие пользователю
        existing = db.query(UserEvent).filter(
            UserEvent.user_id == user.id,
            UserEvent.event_id == event.id
        ).first()

        if existing:
            return False

        # Проверяем фидбек пользователя на это событие
        feedback = db.query(Feedback).filter(
            Feedback.user_id == user.id,
            Feedback.event_id == event.id,
            Feedback.is_positive == False
        ).first()

        if feedback:
            # Пользователь уже отклонил это событие
            return False

        # Формируем сообщение
        message = format_event_message(event)
        keyboard = get_event_keyboard(event.id)

        # Добавляем кнопку со ссылкой
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="🔗 Открыть сайт", url=event.url)
        ])

        # Отправляем сообщение
        await bot.send_message(
            chat_id=user.telegram_id,
            text=message,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        # Сохраняем факт отправки
        user_event = UserEvent(
            user_id=user.id,
            event_id=event.id
        )
        db.add(user_event)
        db.commit()

        return True
    except Exception as e:
        logger.error(f"Ошибка отправки события пользователю {user.telegram_id}: {e}")
        return False


async def notify_users_about_events(bot: Bot, events: List[Event]):
    """Уведомить пользователей о новых событиях"""
    db: Session = SessionLocal()
    try:
        # Получаем всех активных пользователей
        users = db.query(User).filter(User.is_active == True).all()

        for event in events:
            for user in users:
                # Проверяем соответствие фильтрам пользователя
                if not user.industries or not user.cities:
                    continue

                # Проверяем город
                if event.city and event.city not in user.cities:
                    if "Все города" not in user.cities:
                        continue

                # Проверяем индустрию (если указана)
                if event.industry and event.industry not in user.industries:
                    continue

                # Отправляем событие
                await send_event_to_user(bot, user, event, db)

    finally:
        db.close()
