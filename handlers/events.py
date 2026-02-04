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
PER_PAGE = 5
DESCRIPTION_MAX_LEN = 180


def _format_events_page(events: list, page: int, total: int) -> str:
    if not events:
        return "📭 Пока нет подходящих выставок. Зайди позже или обнови список командой /parse."
    total_pages = (total + PER_PAGE - 1) // PER_PAGE if total else 1
    lines = [
        f"📅 <b>Выставки (страница {page} из {total_pages})</b>\n"
    ]
    for i, e in enumerate(events, start=1):
        date_str = e.start_date.strftime("%d.%m.%Y") if e.start_date else "Дата уточняется"
        city_str = f", {e.city}" if e.city else ""
        title_safe = html.escape((e.title or "").strip())
        desc = (e.description or "").strip()
        if len(desc) > DESCRIPTION_MAX_LEN:
            desc = desc[:DESCRIPTION_MAX_LEN].rsplit(" ", 1)[0] + "…"
        desc = html.escape(desc)
        desc_line = f"   {desc}\n" if desc else ""
        lines.append(
            f"{i}. <b>{title_safe}</b>\n"
            f"{desc_line}"
            f"   📅 {date_str}{city_str}\n"
            f"   🔗 <a href=\"{e.url}\">Подробнее</a>\n"
        )
    return "\n".join(lines)


def _events_keyboard(page: int, total_events: int) -> InlineKeyboardMarkup:
    total_pages = max(1, (total_events + PER_PAGE - 1) // PER_PAGE)
    row = []
    if page > 1:
        row.append(InlineKeyboardButton(text="◀ Назад", callback_data=EventsListCallback(page=page - 1).pack()))
    if page < total_pages:
        row.append(InlineKeyboardButton(text="Вперёд ▶", callback_data=EventsListCallback(page=page + 1).pack()))
    return InlineKeyboardMarkup(inline_keyboard=[row] if row else [])


async def _send_events_page(target, events_slice: list, page: int, total: int, is_edit: bool):
    text = _format_events_page(events_slice, page, total)
    kb = _events_keyboard(page, total)
    if is_edit:
        await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("events"))
async def cmd_events(message: Message):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not user:
            await message.answer("Сначала пройди настройку: /start")
            return
        events = get_filtered_events_for_user(user, db)
        total = len(events)
        page = 1
        start = (page - 1) * PER_PAGE
        slice_ = events[start : start + PER_PAGE]
        await _send_events_page(message, slice_, page, total, is_edit=False)
    finally:
        db.close()


@router.callback_query(EventsListCallback.filter())
async def events_list_page(clb: CallbackQuery, callback_data: EventsListCallback):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == clb.from_user.id).first()
        if not user:
            await clb.answer("Сначала /start")
            return
        events = get_filtered_events_for_user(user, db)
        total = len(events)
        page = max(1, min(callback_data.page, (total + PER_PAGE - 1) // PER_PAGE or 1))
        start = (page - 1) * PER_PAGE
        slice_ = events[start : start + PER_PAGE]
        await _send_events_page(clb, slice_, page, total, is_edit=True)
        await clb.answer()
    finally:
        db.close()


def get_view_events_button() -> InlineKeyboardMarkup:
    """Кнопка «Текущие выставки» для размещения после /start."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Текущие выставки", callback_data=EventsListCallback(page=1).pack())]
    ])
