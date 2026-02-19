import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, URLInputFile
from sqlalchemy.orm import Session
from database.models import User, Event, UserEvent, Feedback
from handlers.feedback import get_event_keyboard

logger = logging.getLogger(__name__)

async def notify_users(bot: Bot, events: list, db: Session):
    users = db.query(User).filter(User.is_active == True).all()
    
    for event in events:
        for user in users:
            if not _check_filters(user, event):
                continue
            
            if _is_already_sent_or_rejected(user, event, db):
                continue

            try:
                text = (
                    f"🎯 <b>{event.title}</b>\n\n"
                    f"📅 <b>Когда:</b> {event.start_date.strftime('%d.%m.%Y') if event.start_date else 'Дата уточняется'}\n"
                    f"🌍 <b>Страна:</b> {event.country or '—'}\n"
                    f"🏙 <b>Город:</b> {event.city or 'Не указан'}{f' ({event.place})' if event.place else ''}\n\n"
                    f"{event.description[:300]}...\n\n"
                    f"🔗 <a href='{event.url}'>Подробнее на сайте</a>"
                )
                
                kb = get_event_keyboard(event.id, event.url)
                
                if event.image_url:
                    await bot.send_photo(
                        chat_id=user.telegram_id,
                        photo=event.image_url,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=kb
                    )
                else:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=text,
                        parse_mode="HTML",
                        reply_markup=kb,
                        disable_web_page_preview=False
                    )
                
                # Запись об отправке
                db.add(UserEvent(user_id=user.id, event_id=event.id))
                db.commit()
                
            except Exception as e:
                logger.error(f"Failed to send event {event.id} to user {user.id}: {e}")

def _check_filters(user: User, event: Event) -> bool:
    # Фильтр по стране
    user_countries = user.countries if user.countries is not None else []
    if user_countries and event.country:
        if event.country not in user_countries:
            return False
    elif user_countries and not event.country:
        # Event has no country (legacy) - treat as Kazakhstan for backward compat
        if "Казахстан" not in user_countries:
            return False
    # Фильтр по городу
    if user.cities and "Все города" not in user.cities:
        if not event.city or event.city not in user.cities:
            return False
    # Фильтр по индустрии (если пользователь выбрал)
    if user.industries and event.industry:
        if event.industry not in user.industries:
            return False
    # Автотюнинг: исключённые индустрии
    meta = user.feedback_metadata or {}
    excluded_ind = meta.get("excluded_industries") or []
    if event.industry and event.industry in excluded_ind:
        return False
    # Автотюнинг: исключённые источники
    excluded_src = meta.get("excluded_sources") or []
    if event.source and event.source in excluded_src:
        return False
    # Автотюнинг: только крупные (международные)
    if meta.get("prefer_large_only"):
        text = ((event.title or "") + " " + (event.description or "")).lower()
        if "международн" not in text and "international" not in text:
            return False
    return True

def get_filtered_events_for_user(user: User, db: Session, limit: int = 100):
    """Список выставок, подходящих пользователю по фильтрам (город, индустрия, автотюнинг)."""
    q = db.query(Event).order_by(Event.id.desc())
    events = q.limit(limit * 3).all()
    return [e for e in events if _check_filters(user, e)][:limit]

def _is_already_sent_or_rejected(user: User, event: Event, db: Session) -> bool:
    sent = db.query(UserEvent).filter_by(user_id=user.id, event_id=event.id).first()
    if sent: return True
    
    rejected = db.query(Feedback).filter_by(
        user_id=user.id, event_id=event.id, is_positive=False
    ).first()
    if rejected: return True
    
    return False


async def notify_no_new_events(bot: Bot, db: Session):
    """Сообщить пользователям, что проверка выполнена и новых выставок пока нет."""
    users = db.query(User).filter(User.is_active == True).all()
    # Только тем, у кого уже есть настройки (прошли онбординг)
    for user in users:
        if not ((user.countries and len(user.countries)) or user.cities or user.industries):
            continue
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=(
                    "🕐 Проверка выполнена.\n\n"
                    "Новых выставок по твоим фильтрам пока нет. "
                    "Загляни позже или нажми /events — там актуальный список."
                ),
            )
        except Exception as e:
            logger.debug(f"Could not send 'no new events' to user {user.id}: {e}")