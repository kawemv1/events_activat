import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy.orm import Session
from database.engine import SessionLocal
from database.models import User, Event
from handlers.callback_data import EventsListCallback
from services.notification import get_filtered_events_for_user

router = Router()
PER_PAGE = 1  # Одна карточка на страницу
DESCRIPTION_MAX_LEN = 300  # 2-3 предложения


def _format_event_card(e: Event, page: int, total: int) -> str:
    """Формат карточки: Заголовок, Дата и Город, Описание (2-3 предложения)."""
    title_safe = html.escape((e.title or "").strip())
    date_str = e.start_date.strftime("%d.%m.%Y") if e.start_date else "Дата уточняется"
    city_str = e.city or "Город не указан"
    place_str = f" ({e.place})" if e.place else ""
    desc = (e.description or "").strip()
    if len(desc) > DESCRIPTION_MAX_LEN:
        desc = desc[:DESCRIPTION_MAX_LEN].rsplit(" ", 1)[0] + "…"
    desc = html.escape(desc) if desc else "Описание отсутствует."
    return (
        f"🎯 <b>{title_safe}</b>\n\n"
        f"📅 <b>Дата:</b> {date_str}\n"
        f"🏙 <b>Город:</b> {city_str}{place_str}\n\n"
        f"📝 {desc}\n\n"
        f"<i>Карточка {page} из {total}</i>"
    )


def _events_keyboard(page: int, total_events: int, current_event: Event) -> InlineKeyboardMarkup:
    from handlers.callback_data import EventFeedbackCallback
    total_pages = max(1, total_events)
    row = []
    if page > 1:
        row.append(InlineKeyboardButton(text="◀ Назад", callback_data=EventsListCallback(page=page - 1).pack()))
    if page < total_pages:
        row.append(InlineKeyboardButton(text="Вперёд ▶", callback_data=EventsListCallback(page=page + 1).pack()))
    fb_row = [
        InlineKeyboardButton(text="👍 Релевантно", callback_data=EventFeedbackCallback(event_id=current_event.id, action="like", page=page).pack()),
        InlineKeyboardButton(text="👎 Не подходит", callback_data=EventFeedbackCallback(event_id=current_event.id, action="dislike", page=page).pack())
    ]
    link_row = [InlineKeyboardButton(text="🔗 На сайт / Для экспонентов", url=current_event.url)]
    return InlineKeyboardMarkup(inline_keyboard=[row, fb_row, link_row] if row else [fb_row, link_row])


async def _send_events_page(target, event: Event, page: int, total: int, is_edit: bool):
    text = _format_event_card(event, page, total)
    kb = _events_keyboard(page, total, event)
    if is_edit:
        await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


async def show_events_page(clb_or_msg, page: int = 1, is_edit: bool = False):
    """Показать карточку события (одно на страницу)."""
    db = SessionLocal()
    try:
        user_id = clb_or_msg.from_user.id
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            text = "Сначала пройди настройку: /start"
            if is_edit:
                await clb_or_msg.message.edit_text(text)
            else:
                await clb_or_msg.answer(text)
            return
        events = get_filtered_events_for_user(user, db)
        total = len(events)
        if not events:
            text = "📭 Пока нет подходящих выставок. Зайди позже или обнови список командой /parse."
            if is_edit:
                await clb_or_msg.message.edit_text(text)
            else:
                await clb_or_msg.answer(text)
            return
        page = max(1, min(page, total))
        event = events[page - 1]
        await _send_events_page(clb_or_msg, event, page, total, is_edit)
    finally:
        db.close()


@router.message(Command("events"))
async def cmd_events(message: Message):
    await show_events_page(message, page=1, is_edit=False)


@router.callback_query(EventsListCallback.filter())
async def events_list_page(clb: CallbackQuery, callback_data: EventsListCallback):
    await show_events_page(clb, page=callback_data.page, is_edit=True)
    await clb.answer()
