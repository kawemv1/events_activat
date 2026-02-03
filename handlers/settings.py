from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy.orm import Session
from database.engine import SessionLocal
from database.models import User
from handlers.callback_data import SettingsCallback
from handlers.start import get_industries_keyboard, get_cities_keyboard
from datetime import datetime

router = Router()


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Обработчик команды /settings"""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

        if not user:
            await message.answer(
                "Ты еще не зарегистрирован. Используй /start для начала."
            )
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Изменить индустрии",
                    callback_data=SettingsCallback(action="edit_industries").pack()
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Изменить города",
                    callback_data=SettingsCallback(action="edit_cities").pack()
                )
            ],
        ])

        industries_text = ", ".join(user.industries) if user.industries else "Не выбраны"
        cities_text = ", ".join(user.cities) if user.cities else "Не выбраны"

        await message.answer(
            "⚙️ Настройки\n\n"
            f"📊 Индустрии: {industries_text}\n"
            f"🏙️ Города: {cities_text}\n\n"
            "Выбери, что хочешь изменить:",
            reply_markup=keyboard
        )
    finally:
        db.close()


@router.callback_query(SettingsCallback.filter(F.action == "edit_industries"))
async def edit_industries(callback: CallbackQuery, callback_data: SettingsCallback):
    """Редактирование индустрий"""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()

        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return

        keyboard = get_industries_keyboard(user.industries)
        # Добавляем кнопку "Назад"
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="← Назад",
                callback_data=SettingsCallback(action="back").pack()
            )
        ])

        await callback.message.edit_text(
            "Выбери интересующие тебя индустрии:",
            reply_markup=keyboard
        )
        await callback.answer()
    finally:
        db.close()


@router.callback_query(SettingsCallback.filter(F.action == "edit_cities"))
async def edit_cities(callback: CallbackQuery, callback_data: SettingsCallback):
    """Редактирование городов"""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()

        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return

        keyboard = get_cities_keyboard(user.cities)
        # Добавляем кнопку "Назад"
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="← Назад",
                callback_data=SettingsCallback(action="back").pack()
            )
        ])

        await callback.message.edit_text(
            "Выбери интересующие тебя города:",
            reply_markup=keyboard
        )
        await callback.answer()
    finally:
        db.close()


@router.callback_query(SettingsCallback.filter(F.action == "back"))
async def back_to_settings(callback: CallbackQuery, callback_data: SettingsCallback):
    """Возврат к настройкам"""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()

        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Изменить индустрии",
                    callback_data=SettingsCallback(action="edit_industries").pack()
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Изменить города",
                    callback_data=SettingsCallback(action="edit_cities").pack()
                )
            ],
        ])

        industries_text = ", ".join(user.industries) if user.industries else "Не выбраны"
        cities_text = ", ".join(user.cities) if user.cities else "Не выбраны"

        await callback.message.edit_text(
            "⚙️ Настройки\n\n"
            f"📊 Индустрии: {industries_text}\n"
            f"🏙️ Города: {cities_text}\n\n"
            "Выбери, что хочешь изменить:",
            reply_markup=keyboard
        )
        await callback.answer()
    finally:
        db.close()
