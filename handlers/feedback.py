from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.engine import SessionLocal
from database.models import User, Feedback
from handlers.callback_data import EventFeedbackCallback, FeedbackReasonCallback, EventsListCallback
from config import FEEDBACK_REASONS

router = Router()

def get_event_keyboard(event_id, url):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍 Релевантно", callback_data=EventFeedbackCallback(event_id=event_id, action="like").pack()),
            InlineKeyboardButton(text="👎 Не подходит", callback_data=EventFeedbackCallback(event_id=event_id, action="dislike").pack())
        ],
        [InlineKeyboardButton(text="🔗 На сайт", url=url)]
    ])

def _return_to_events_keyboard(page: int = 1) -> InlineKeyboardMarkup:
    """Кнопка возврата к событиям."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Вернуться к событиям", callback_data=EventsListCallback(page=page).pack())]
    ])

@router.callback_query(EventFeedbackCallback.filter(F.action == "like"))
async def like(clb: CallbackQuery, callback_data: EventFeedbackCallback):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=clb.from_user.id).first()
    if user:
        fb = Feedback(user_id=user.id, event_id=callback_data.event_id, is_positive=True, reason=None)
        db.add(fb)
        db.commit()
    db.close()
    await clb.answer("Спасибо! 👍")
    page = callback_data.page
    try:
        await clb.message.edit_reply_markup(reply_markup=_return_to_events_keyboard(page))
    except Exception:
        pass


@router.callback_query(EventFeedbackCallback.filter(F.action == "dislike"))
async def dislike(clb: CallbackQuery, callback_data: EventFeedbackCallback):
    page = callback_data.page
    kb = []
    for idx, reason in enumerate(FEEDBACK_REASONS):
        kb.append([InlineKeyboardButton(text=reason, callback_data=FeedbackReasonCallback(event_id=callback_data.event_id, reason_idx=idx, page=page).pack())])
    kb.append([InlineKeyboardButton(text="📅 Вернуться к событиям", callback_data=EventsListCallback(page=page).pack())])
    await clb.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(FeedbackReasonCallback.filter())
async def reason_chosen(clb: CallbackQuery, callback_data: FeedbackReasonCallback):
    from sqlalchemy.orm import flag_modified
    from database.models import Event
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=clb.from_user.id).first()
    if not user:
        await clb.answer("Сначала пройди настройку: /start", show_alert=True)
        db.close()
        return
    event = db.query(Event).filter_by(id=callback_data.event_id).first()
    reason_idx = min(callback_data.reason_idx, len(FEEDBACK_REASONS) - 1)
    reason = FEEDBACK_REASONS[reason_idx]
    fb = Feedback(user_id=user.id, event_id=callback_data.event_id, is_positive=False, reason=reason)
    db.add(fb)
    # Автотюнинг: обновляем предпочтения пользователя
    meta = user.feedback_metadata or {}
    if "excluded_industries" not in meta:
        meta["excluded_industries"] = []
    if "excluded_sources" not in meta:
        meta["excluded_sources"] = []
    if "Не моя сфера" in reason and event and event.industry:
        if event.industry not in meta["excluded_industries"]:
            meta["excluded_industries"].append(event.industry)
    elif "Не B2B формат" in reason and event and event.source:
        if event.source not in meta["excluded_sources"]:
            meta["excluded_sources"].append(event.source)
    elif "Недостаточный масштаб" in reason:
        meta["prefer_large_only"] = True
    user.feedback_metadata = meta
    flag_modified(user, "feedback_metadata")
    db.commit()
    db.close()
    await clb.answer("Спасибо, мы учтём это!")
    page = callback_data.page
    thanks_text = "Спасибо за отзыв! ✅ Мы учтём это при подборе."
    try:
        if clb.message.photo:
            await clb.message.edit_caption(caption=thanks_text, reply_markup=_return_to_events_keyboard(page))
        else:
            prev = (clb.message.text or clb.message.caption or "") + "\n\n" + thanks_text
            await clb.message.edit_text(prev, reply_markup=_return_to_events_keyboard(page), parse_mode="HTML")
    except Exception:
        try:
            await clb.message.edit_reply_markup(reply_markup=_return_to_events_keyboard(page))
        except Exception:
            await clb.message.delete()