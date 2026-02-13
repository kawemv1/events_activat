from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy.orm.attributes import flag_modified
from database.engine import SessionLocal
from database.models import User
from handlers.callback_data import IndustryCallback, CityCallback, SelectAllCallback, ConfirmCallback, MainMenuCallback
from config import INDUSTRIES, CITIES

router = Router()

def get_industries_keyboard(selected_industries):
    """Клавиатура выбора индустрий (для /start и настроек)."""
    return get_keyboard(INDUSTRIES, selected_industries or [], "ind")

def get_cities_keyboard(selected_cities):
    """Клавиатура выбора городов (для /start и настроек)."""
    return get_keyboard(CITIES, selected_cities or [], "city")

def get_keyboard(items, selected_items, type_):
    kb = []
    # Генерация кнопок сеткой по 2
    for i in range(0, len(items), 2):
        row = []
        for item in items[i:i+2]:
            mark = "✅ " if item in selected_items else ""
            if type_ == "ind":
                cb = IndustryCallback(industry=item).pack()
            else:
                cb = CityCallback(city=item).pack()
            row.append(InlineKeyboardButton(text=f"{mark}{item}", callback_data=cb))
        kb.append(row)
    
    kb.append([InlineKeyboardButton(text="Выбрать все", callback_data=SelectAllCallback(type=type_).pack())])
    
    action = "next_step" if type_ == 'ind' else "finish"
    text = "Далее ➡️" if type_ == 'ind' else "Завершить ✅"
    kb.append([InlineKeyboardButton(text=text, callback_data=ConfirmCallback(action=action).pack())])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню: Моя подборка, Настройки, Помощь."""
    from handlers.callback_data import MainMenuCallback
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Моя подборка", callback_data=MainMenuCallback(action="events").pack())],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data=MainMenuCallback(action="settings").pack())],
        [InlineKeyboardButton(text="❓ Помощь", callback_data=MainMenuCallback(action="help").pack())],
    ])


@router.message(Command("start"))
async def cmd_start(message: Message):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=message.from_user.id).first()
    if not user:
        user = User(
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            industries=[], cities=[]
        )
        db.add(user)
        db.commit()
    
    # Уже проходил настройку (интересы/города сохранены в БД) — показываем главное меню
    has_preferences = (user.industries and len(user.industries) > 0) or (user.cities and len(user.cities) > 0)
    db.close()
    
    if has_preferences:
        ind_text = ", ".join(user.industries[:5]) if user.industries else "не выбраны"
        city_text = ", ".join(user.cities[:5]) if user.cities else "не выбраны"
        if user.cities and len(user.cities) > 5:
            city_text += " …"
        if user.industries and len(user.industries) > 5:
            ind_text += " …"
        await message.answer(
            "👋 С возвращением! Твои интересы и города сохранены.\n\n"
            f"📊 Индустрии: {ind_text}\n"
            f"🏙️ Города: {city_text}\n\n"
            "Выбери действие:",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    await message.answer(
        "👋 Привет! Я бот для поиска B2B выставок.\nДавай настроим твои интересы (их можно будет изменить в настройках).\n\nВыбери индустрии:",
        reply_markup=get_keyboard(INDUSTRIES, user.industries, "ind")
    )

@router.callback_query(IndustryCallback.filter())
async def industry_click(clb: CallbackQuery, callback_data: IndustryCallback):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=clb.from_user.id).first()
    
    ind = callback_data.industry
    if ind in user.industries: user.industries = [i for i in user.industries if i != ind]
    else: user.industries = user.industries + [ind]
    
    # Force update JSON column
    flag_modified(user, "industries")
    
    db.commit()
    await clb.message.edit_reply_markup(reply_markup=get_keyboard(INDUSTRIES, user.industries, "ind"))
    db.close()

@router.callback_query(ConfirmCallback.filter(F.action == "next_step"))
async def next_step(clb: CallbackQuery):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=clb.from_user.id).first()
    db.close()
    await clb.message.edit_text("Теперь выбери города:", reply_markup=get_keyboard(CITIES, user.cities, "city"))

@router.callback_query(CityCallback.filter())
async def city_click(clb: CallbackQuery, callback_data: CityCallback):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=clb.from_user.id).first()
    
    city = callback_data.city
    if city in user.cities: user.cities = [c for c in user.cities if c != city]
    else: user.cities = user.cities + [city]
    
    flag_modified(user, "cities")
    db.commit()
    await clb.message.edit_reply_markup(reply_markup=get_keyboard(CITIES, user.cities, "city"))
    db.close()

@router.callback_query(ConfirmCallback.filter(F.action == "finish"))
async def finish(clb: CallbackQuery):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=clb.from_user.id).first()
    if user:
        flag_modified(user, "industries")
        flag_modified(user, "cities")
        db.commit()
    db.close()
    await clb.message.edit_text(
        "✅ Настройка завершена! Жди уведомлений о новых выставках.",
        reply_markup=get_main_menu_keyboard()
    )


@router.callback_query(SelectAllCallback.filter())
async def select_all_click(clb: CallbackQuery, callback_data: SelectAllCallback):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=clb.from_user.id).first()
    if not user:
        await clb.answer("Сначала /start")
        db.close()
        return
    t = callback_data.type
    if t == "ind":
        user.industries = list(INDUSTRIES)
        flag_modified(user, "industries")
        db.commit()
        await clb.message.edit_reply_markup(reply_markup=get_keyboard(INDUSTRIES, user.industries, "ind"))
    else:
        user.cities = list(CITIES)
        flag_modified(user, "cities")
        db.commit()
        await clb.message.edit_reply_markup(reply_markup=get_keyboard(CITIES, user.cities, "city"))
    db.close()
    await clb.answer("Выбрано всё")


@router.callback_query(MainMenuCallback.filter())
async def main_menu_click(clb: CallbackQuery, callback_data: MainMenuCallback):
    from handlers.events import show_events_page
    from handlers.settings import send_settings_menu
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=clb.from_user.id).first()
    db.close()
    if not user:
        await clb.answer("Сначала /start")
        return
    action = callback_data.action
    if action == "events":
        await show_events_page(clb, page=1, is_edit=True)
    elif action == "settings":
        await send_settings_menu(clb, user)
    elif action == "help":
        help_text = (
            "📖 <b>Помощь</b>\n\n"
            "Я помогаю находить B2B выставки и форумы в Казахстане.\n\n"
            "📅 <b>Моя подборка</b> — актуальные мероприятия по твоим индустриям и городам.\n"
            "⚙️ <b>Настройки</b> — изменить индустрии и города.\n\n"
            "Под каждой карточкой события есть кнопки 👍/👎 — "
            "нажимай, чтобы улучшить рекомендации.\n\n"
            "Новые события приходят автоматически при их появлении."
        )
        await clb.message.edit_text(help_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="← Назад", callback_data=MainMenuCallback(action="back").pack())]
        ]))
    elif action == "back":
        ind_text = ", ".join(user.industries[:5]) if user.industries else "не выбраны"
        city_text = ", ".join(user.cities[:5]) if user.cities else "не выбраны"
        if user.cities and len(user.cities) > 5:
            city_text += " …"
        if user.industries and len(user.industries) > 5:
            ind_text += " …"
        await clb.message.edit_text(
            "👋 Главное меню\n\n"
            f"📊 Индустрии: {ind_text}\n"
            f"🏙️ Города: {city_text}\n\n"
            "Выбери действие:",
            reply_markup=get_main_menu_keyboard()
        )
    await clb.answer()