from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.orm import Session
from database.engine import SessionLocal
from database.models import User, Event, Feedback
from handlers.callback_data import EventFeedbackCallback, FeedbackReasonCallback
from config import FEEDBACK_REASONS
from datetime import datetime

router = Router()


def get_event_keyboard(event_id: int) -> InlineKeyboardMarkup:
    """Создать клавиатуру с кнопками 👍 и 👎 для ивента"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="👍",
                callback_data=EventFeedbackCallback(event_id=event_id, action="like").pack()
            ),
            InlineKeyboardButton(
                text="👎",
                callback_data=EventFeedbackCallback(event_id=event_id, action="dislike").pack()
            ),
        ]
    ])


def get_feedback_reasons_keyboard(event_id: int) -> InlineKeyboardMarkup:
    """Создать клавиатуру с причинами отклонения"""
    keyboard = []
    for reason in FEEDBACK_REASONS:
        keyboard.append([
            InlineKeyboardButton(
                text=reason,
                callback_data=FeedbackReasonCallback(event_id=event_id, reason=reason).pack()
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.callback_query(EventFeedbackCallback.filter(F.action == "like"))
async def process_like(callback: CallbackQuery, callback_data: EventFeedbackCallback):
    """Обработка лайка (👍)"""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        event = db.query(Event).filter(Event.id == callback_data.event_id).first()

        if not user or not event:
            await callback.answer("Ошибка: данные не найдены", show_alert=True)
            return

        # Проверяем, есть ли уже фидбек
        existing_feedback = db.query(Feedback).filter(
            Feedback.user_id == user.id,
            Feedback.event_id == event.id
        ).first()

        if existing_feedback:
            # Обновляем существующий фидбек
            existing_feedback.is_positive = True
            existing_feedback.reason = None
        else:
            # Создаем новый фидбек
            feedback = Feedback(
                user_id=user.id,
                event_id=event.id,
                is_positive=True,
                reason=None,
            )
            db.add(feedback)

        db.commit()
        await callback.answer("Спасибо за фидбек! 👍")
    finally:
        db.close()


@router.callback_query(EventFeedbackCallback.filter(F.action == "dislike"))
async def process_dislike(callback: CallbackQuery, callback_data: EventFeedbackCallback):
    """Обработка дизлайка (👎) - показываем меню причин"""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        event = db.query(Event).filter(Event.id == callback_data.event_id).first()

        if not user or not event:
            await callback.answer("Ошибка: данные не найдены", show_alert=True)
            return

        await callback.message.edit_reply_markup(
            reply_markup=get_feedback_reasons_keyboard(callback_data.event_id)
        )
        await callback.answer("Выбери причину:")
    finally:
        db.close()


@router.callback_query(FeedbackReasonCallback.filter())
async def process_feedback_reason(callback: CallbackQuery, callback_data: FeedbackReasonCallback):
    """Обработка выбора причины отклонения"""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        event = db.query(Event).filter(Event.id == callback_data.event_id).first()

        if not user or not event:
            await callback.answer("Ошибка: данные не найдены", show_alert=True)
            return

        # Проверяем, есть ли уже фидбек
        existing_feedback = db.query(Feedback).filter(
            Feedback.user_id == user.id,
            Feedback.event_id == event.id
        ).first()

        if existing_feedback:
            # Обновляем существующий фидбек
            existing_feedback.is_positive = False
            existing_feedback.reason = callback_data.reason
        else:
            # Создаем новый фидбек
            feedback = Feedback(
                user_id=user.id,
                event_id=event.id,
                is_positive=False,
                reason=callback_data.reason,
            )
            db.add(feedback)

        db.commit()

        # Возвращаем клавиатуру с кнопками 👍/👎
        await callback.message.edit_reply_markup(
            reply_markup=get_event_keyboard(callback_data.event_id)
        )
        await callback.answer(f"Спасибо! Причина: {callback_data.reason}")
    finally:
        db.close()
