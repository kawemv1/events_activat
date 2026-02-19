from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy.orm import Session
from database.engine import SessionLocal
from database.models import User
from handlers.callback_data import SettingsCallback
from handlers.start import get_countries_keyboard, get_industries_keyboard, get_cities_keyboard

router = Router()

def get_settings_main_keyboard():
    """Утилита для создания главного меню настроек"""
    from handlers.callback_data import MainMenuCallback
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✏️ Изменить страны",
                callback_data=SettingsCallback(action="edit_countries").pack()
            )
        ],
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
        [InlineKeyboardButton(text="← В главное меню", callback_data=MainMenuCallback(action="back").pack())],
    ])

async def send_settings_menu(message_or_query, user: User):
    """Общая функция для отрисовки меню настроек"""
    countries_text = ", ".join(user.countries or []) if (user.countries and len(user.countries)) else "Не выбраны"
    industries_text = ", ".join(user.industries) if user.industries else "Не выбраны"
    cities_text = ", ".join(user.cities) if user.cities else "Не выбраны"
    
    text = (
        "⚙️ <b>Настройки</b>\n\n"
        f"🌍 <b>Страны:</b> {countries_text}\n"
        f"📊 <b>Индустрии:</b> {industries_text}\n"
        f"🏙️ <b>Города:</b> {cities_text}\n\n"
        "Выбери, что хочешь изменить:"
    )
    kb = get_settings_main_keyboard()

    if isinstance(message_or_query, Message):
        await message_or_query.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message_or_query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not user:
            await message.answer("Ты еще не зарегистрирован. Используй /start.")
            return
        await send_settings_menu(message, user)
    finally:
        db.close()

@router.callback_query(SettingsCallback.filter(F.action == "edit_countries"))
async def edit_countries(callback: CallbackQuery):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        keyboard = get_countries_keyboard(user.countries or [], for_settings=True)
        await callback.message.edit_text("Выбери интересующие тебя страны:", reply_markup=keyboard)
        await callback.answer()
    finally:
        db.close()

@router.callback_query(SettingsCallback.filter(F.action == "edit_industries"))
async def edit_industries(callback: CallbackQuery):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        keyboard = get_industries_keyboard(user.industries, for_settings=True)
        await callback.message.edit_text("Выбери интересующие тебя индустрии:", reply_markup=keyboard)
        await callback.answer()
    finally:
        db.close()

@router.callback_query(SettingsCallback.filter(F.action == "edit_cities"))
async def edit_cities(callback: CallbackQuery):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        keyboard = get_cities_keyboard(user.cities, countries=user.countries, for_settings=True)
        await callback.message.edit_text("Выбери интересующие тебя города:", reply_markup=keyboard)
        await callback.answer()
    finally:
        db.close()

@router.callback_query(SettingsCallback.filter(F.action == "back"))
async def back_to_settings(callback: CallbackQuery):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        await send_settings_menu(callback, user)
        await callback.answer()
    finally:
        db.close()