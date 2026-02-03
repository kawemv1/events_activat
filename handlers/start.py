from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy.orm import Session
from database.engine import SessionLocal
from database.models import User
from handlers.callback_data import (
    IndustryCallback,
    CityCallback,
    SelectAllCallback,
    ConfirmCallback,
)
from config import INDUSTRIES, CITIES
from datetime import datetime

router = Router()


def get_industries_keyboard(selected_industries: list = None) -> InlineKeyboardMarkup:
    """Создать клавиатуру для выбора индустрий"""
    if selected_industries is None:
        selected_industries = []

    keyboard = []
    # Разбиваем на колонки по 2
    for i in range(0, len(INDUSTRIES), 2):
        row = []
        for j in range(2):
            if i + j < len(INDUSTRIES):
                industry = INDUSTRIES[i + j]
                is_selected = industry in selected_industries
                prefix = "✅ " if is_selected else ""
                row.append(
                    InlineKeyboardButton(
                        text=f"{prefix}{industry}",
                        callback_data=IndustryCallback(industry=industry).pack()
                    )
                )
        keyboard.append(row)

    # Кнопка "Выбрать все"
    keyboard.append([
        InlineKeyboardButton(
            text="✅ Выбрать все" if len(selected_industries) == len(INDUSTRIES) else "Выбрать все",
            callback_data=SelectAllCallback(type="industry").pack()
        )
    ])

    # Кнопка "Далее"
    if selected_industries:
        keyboard.append([
            InlineKeyboardButton(
                text="Далее →",
                callback_data=ConfirmCallback(action="next_industries").pack()
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_cities_keyboard(selected_cities: list = None) -> InlineKeyboardMarkup:
    """Создать клавиатуру для выбора городов"""
    if selected_cities is None:
        selected_cities = []

    keyboard = []
    # Разбиваем на колонки по 2
    for i in range(0, len(CITIES), 2):
        row = []
        for j in range(2):
            if i + j < len(CITIES):
                city = CITIES[i + j]
                is_selected = city in selected_cities
                prefix = "✅ " if is_selected else ""
                row.append(
                    InlineKeyboardButton(
                        text=f"{prefix}{city}",
                        callback_data=CityCallback(city=city).pack()
                    )
                )
        keyboard.append(row)

    # Кнопка "Выбрать все"
    keyboard.append([
        InlineKeyboardButton(
            text="✅ Выбрать все" if len(selected_cities) == len(CITIES) else "Выбрать все",
            callback_data=SelectAllCallback(type="city").pack()
        )
    ])

    # Кнопка "Завершить"
    if selected_cities:
        keyboard.append([
            InlineKeyboardButton(
                text="✅ Завершить настройку",
                callback_data=ConfirmCallback(action="save").pack()
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    db: Session = SessionLocal()
    try:
        # Проверяем, есть ли пользователь в БД
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

        if user:
            # Пользователь уже зарегистрирован
            industries_text = ", ".join(user.industries) if user.industries else "Не выбраны"
            cities_text = ", ".join(user.cities) if user.cities else "Не выбраны"
            
            await message.answer(
                f"Привет, {message.from_user.first_name or 'пользователь'}! 👋\n\n"
                f"Ты уже зарегистрирован в системе.\n\n"
                f"📊 Твои настройки:\n"
                f"• Индустрии: {industries_text}\n"
                f"• Города: {cities_text}\n\n"
                f"💡 Бот автоматически присылает новые события каждые 60 минут.\n"
                f"💡 Используй /parse для немедленного поиска событий.\n"
                f"💡 Используй /settings для изменения настроек.\n"
                f"💡 Используй /help для списка всех команд."
            )
        else:
            # Новый пользователь - начинаем онбординг
            await message.answer(
                "👋 Добро пожаловать в бота мониторинга выставок!\n\n"
                "Я буду присылать тебе информацию о B2B выставках и форумах в Казахстане.\n\n"
                "Для начала выбери интересующие тебя индустрии:",
                reply_markup=get_industries_keyboard()
            )
    finally:
        db.close()


@router.callback_query(IndustryCallback.filter())
async def process_industry_selection(callback: CallbackQuery, callback_data: IndustryCallback):
    """Обработка выбора индустрии"""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()

        if not user:
            # Создаем нового пользователя
            user = User(
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
                last_name=callback.from_user.last_name,
                industries=[],
                cities=[],
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Переключаем выбор индустрии
        if callback_data.industry in user.industries:
            user.industries.remove(callback_data.industry)
        else:
            user.industries.append(callback_data.industry)

        user.updated_at = datetime.utcnow()
        db.commit()

        # Обновляем клавиатуру (проверяем, есть ли кнопка "Назад" - значит это редактирование из настроек)
        keyboard = get_industries_keyboard(user.industries)
        # Если в сообщении есть кнопка "Назад", добавляем её обратно
        if callback.message.reply_markup:
            for row in callback.message.reply_markup.inline_keyboard:
                for button in row:
                    if button.text == "← Назад":
                        keyboard.inline_keyboard.append([button])
                        break

        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(SelectAllCallback.filter(F.type == "industry"))
async def select_all_industries(callback: CallbackQuery, callback_data: SelectAllCallback):
    """Выбрать все индустрии"""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()

        if not user:
            user = User(
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
                last_name=callback.from_user.last_name,
                industries=[],
                cities=[],
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        if len(user.industries) == len(INDUSTRIES):
            # Снимаем все
            user.industries = []
        else:
            # Выбираем все
            user.industries = INDUSTRIES.copy()

        user.updated_at = datetime.utcnow()
        db.commit()

        keyboard = get_industries_keyboard(user.industries)
        # Если в сообщении есть кнопка "Назад", добавляем её обратно
        if callback.message.reply_markup:
            for row in callback.message.reply_markup.inline_keyboard:
                for button in row:
                    if button.text == "← Назад":
                        keyboard.inline_keyboard.append([button])
                        break

        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(ConfirmCallback.filter(F.action == "next_industries"))
async def next_to_cities(callback: CallbackQuery, callback_data: ConfirmCallback):
    """Переход к выбору городов"""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user or not user.industries:
            await callback.answer("Сначала выбери хотя бы одну индустрию!", show_alert=True)
            return

        await callback.message.edit_text(
            "Отлично! Теперь выбери интересующие тебя города:",
            reply_markup=get_cities_keyboard(user.cities)
        )
        await callback.answer()
    finally:
        db.close()


@router.callback_query(CityCallback.filter())
async def process_city_selection(callback: CallbackQuery, callback_data: CityCallback):
    """Обработка выбора города"""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()

        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return

        # Переключаем выбор города
        if callback_data.city in user.cities:
            user.cities.remove(callback_data.city)
        else:
            user.cities.append(callback_data.city)

        user.updated_at = datetime.utcnow()
        db.commit()

        # Обновляем клавиатуру (проверяем, есть ли кнопка "Назад" - значит это редактирование из настроек)
        keyboard = get_cities_keyboard(user.cities)
        # Если в сообщении есть кнопка "Назад", добавляем её обратно
        if callback.message.reply_markup:
            for row in callback.message.reply_markup.inline_keyboard:
                for button in row:
                    if button.text == "← Назад":
                        keyboard.inline_keyboard.append([button])
                        break

        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(SelectAllCallback.filter(F.type == "city"))
async def select_all_cities(callback: CallbackQuery, callback_data: SelectAllCallback):
    """Выбрать все города"""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()

        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return

        if len(user.cities) == len(CITIES):
            # Снимаем все
            user.cities = []
        else:
            # Выбираем все
            user.cities = CITIES.copy()

        user.updated_at = datetime.utcnow()
        db.commit()

        keyboard = get_cities_keyboard(user.cities)
        # Если в сообщении есть кнопка "Назад", добавляем её обратно
        if callback.message.reply_markup:
            for row in callback.message.reply_markup.inline_keyboard:
                for button in row:
                    if button.text == "← Назад":
                        keyboard.inline_keyboard.append([button])
                        break

        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(ConfirmCallback.filter(F.action == "save"))
async def save_settings(callback: CallbackQuery, callback_data: ConfirmCallback):
    """Сохранение настроек пользователя"""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()

        if not user:
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return

        if not user.industries or not user.cities:
            await callback.answer("Выбери хотя бы одну индустрию и один город!", show_alert=True)
            return

        user.is_active = True
        user.updated_at = datetime.utcnow()
        db.commit()

        # Проверяем, редактируем ли из настроек (есть ли кнопка "Назад")
        is_from_settings = False
        if callback.message.reply_markup:
            for row in callback.message.reply_markup.inline_keyboard:
                for button in row:
                    if button.text == "← Назад":
                        is_from_settings = True
                        break

        if is_from_settings:
            # Возвращаемся к настройкам
            from handlers.callback_data import SettingsCallback
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
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
                "✅ Настройки сохранены!\n\n"
                f"📊 Индустрии: {industries_text}\n"
                f"🏙️ Города: {cities_text}\n\n"
                "Выбери, что хочешь изменить:",
                reply_markup=keyboard
            )
            await callback.answer("Настройки сохранены!")
        else:
            # Первичная настройка
            await callback.message.edit_text(
                "✅ Настройки сохранены!\n\n"
                f"Выбранные индустрии: {', '.join(user.industries)}\n"
                f"Выбранные города: {', '.join(user.cities)}\n\n"
                "Теперь я буду присылать тебе подходящие события. Используй /settings для изменения настроек."
            )
            await callback.answer("Настройки сохранены!")
    finally:
        db.close()
