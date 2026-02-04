from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.engine import SessionLocal
from database.models import User, Feedback
from handlers.callback_data import EventFeedbackCallback, FeedbackReasonCallback
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

@router.callback_query(EventFeedbackCallback.filter(F.action == "dislike"))
async def dislike(clb: CallbackQuery, callback_data: EventFeedbackCallback):
    kb = []
    for reason in FEEDBACK_REASONS:
        kb.append([InlineKeyboardButton(text=reason, callback_data=FeedbackReasonCallback(event_id=callback_data.event_id, reason=reason).pack())])
    await clb.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(FeedbackReasonCallback.filter())
async def reason_chosen(clb: CallbackQuery, callback_data: FeedbackReasonCallback):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=clb.from_user.id).first()
    fb = Feedback(user_id=user.id, event_id=callback_data.event_id, is_positive=False, reason=callback_data.reason)
    db.add(fb)
    db.commit()
    db.close()
    await clb.answer("Спасибо, мы учтем это!")
    await clb.message.delete()