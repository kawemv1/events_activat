from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy.orm.attributes import flag_modified
from database.engine import SessionLocal
from database.models import User
from handlers.callback_data import CountryCallback, IndustryCallback, CityCallback, SelectAllCallback, ConfirmCallback, MainMenuCallback
from config import COUNTRIES, INDUSTRIES, get_cities_for_countries

router = Router()

def get_countries_keyboard(selected_countries, for_settings=False):
    """Клавиатура выбора стран (для /start и настроек)."""
    return get_keyboard(COUNTRIES, selected_countries or [], "country", for_settings=for_settings)

def get_industries_keyboard(selected_industries, for_settings=False):
    """Клавиатура выбора индустрий (для /start и настроек)."""
    return get_keyboard(INDUSTRIES, selected_industries or [], "ind", for_settings=for_settings)

def get_cities_keyboard(selected_cities, countries=None, for_settings=False):
    """Клавиатура выбора городов (города зависят от выбранных стран)."""
    cities = get_cities_for_countries(countries or ["Казахстан"])
    return get_keyboard(cities, selected_cities or [], "city", for_settings=for_settings)

def get_keyboard(items, selected_items, type_, for_settings=False):
    kb = []
    for i in range(0, len(items), 2):
        row = []
        for item in items[i:i+2]:
            mark = "✅ " if item in selected_items else ""
            if type_ == "country":
                cb = CountryCallback(country=item, from_settings=for_settings).pack()
            elif type_ == "ind":
                cb = IndustryCallback(industry=item, from_settings=for_settings).pack()
            else:
                cb = CityCallback(city=item, from_settings=for_settings).pack()
            row.append(InlineKeyboardButton(text=f"{mark}{item}", callback_data=cb))
        kb.append(row)

    kb.append([InlineKeyboardButton(text="Выбрать все", callback_data=SelectAllCallback(type=type_, from_settings=for_settings).pack())])

    if for_settings:
        from handlers.callback_data import SettingsCallback
        kb.append([InlineKeyboardButton(text="← Назад", callback_data=SettingsCallback(action="back").pack())])
    elif type_ == "country":
        action, step, text = "next_step", "country", "Далее ➡️"
        kb.append([InlineKeyboardButton(text=text, callback_data=ConfirmCallback(action=action, step=step).pack())])
    elif type_ == "ind":
        action, step, text = "next_step", "ind", "Далее ➡️"
        kb.append([InlineKeyboardButton(text=text, callback_data=ConfirmCallback(action=action, step=step).pack())])
    else:
        action, step, text = "finish", "city", "Завершить ✅"
        kb.append([InlineKeyboardButton(text=text, callback_data=ConfirmCallback(action=action, step=step).pack())])

    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню: Моя подборка, Настройки, Помощь."""
    from handlers.callback_data import MainMenuCallback
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Моя подборка", callback_data=MainMenuCallback(action="events").pack())],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data=MainMenuCallback(action="settings").pack())],
        [InlineKeyboardButton(text="❓ Помощь", callback_data=MainMenuCallback(action="help").pack())],
    ])


def _has_preferences(user: User) -> bool:
    """User has completed onboarding: countries + (industries or cities)."""
    has_countries = user.countries and len(user.countries) > 0
    has_rest = (user.industries and len(user.industries) > 0) or (user.cities and len(user.cities) > 0)
    return has_countries and has_rest

@router.message(Command("start"))
async def cmd_start(message: Message):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=message.from_user.id).first()
    if not user:
        user = User(
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            countries=[], industries=[], cities=[]
        )
        db.add(user)
        db.commit()
    else:
        # Backfill: existing users get Kazakhstan if countries empty
        if not getattr(user, 'countries', None) or user.countries is None:
            user.countries = ["Казахстан"]
            flag_modified(user, "countries")
            db.commit()

    has_preferences = _has_preferences(user)
    db.close()

    if has_preferences:
        country_text = ", ".join(user.countries[:4]) if user.countries else "не выбраны"
        ind_text = ", ".join(user.industries[:4]) if user.industries else "не выбраны"
        city_text = ", ".join(user.cities[:4]) if user.cities else "не выбраны"
        if user.countries and len(user.countries) > 4:
            country_text += " …"
        if user.cities and len(user.cities) > 4:
            city_text += " …"
        if user.industries and len(user.industries) > 4:
            ind_text += " …"
        await message.answer(
            "👋 С возвращением! Твои интересы сохранены.\n\n"
            f"🌍 Страны: {country_text}\n"
            f"📊 Индустрии: {ind_text}\n"
            f"🏙️ Города: {city_text}\n\n"
            "Выбери действие:",
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Onboarding: countries first (if not yet selected)
    if not (user.countries and len(user.countries) > 0):
        await message.answer(
            "👋 Привет! Я бот для поиска B2B выставок в странах СНГ.\n"
            "Давай настроим твои интересы (их можно изменить в настройках).\n\n"
            "Выбери страны:",
            reply_markup=get_countries_keyboard(user.countries or [])
        )
        return

    # Countries done, industries next
    if not (user.industries and len(user.industries) > 0):
        await message.answer("Выбери индустрии:", reply_markup=get_keyboard(INDUSTRIES, user.industries, "ind"))
        return

    # Industries done, cities last
    cities = get_cities_for_countries(user.countries or ["Казахстан"])
    await message.answer("Выбери города:", reply_markup=get_keyboard(cities, user.cities, "city"))

@router.callback_query(CountryCallback.filter())
async def country_click(clb: CallbackQuery, callback_data: CountryCallback):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=clb.from_user.id).first()
    country = callback_data.country
    countries = user.countries if user.countries is not None else []
    if country in countries:
        user.countries = [c for c in countries if c != country]
    else:
        user.countries = countries + [country]
    flag_modified(user, "countries")
    db.commit()
    from_settings = getattr(callback_data, "from_settings", False)
    await clb.message.edit_reply_markup(reply_markup=get_countries_keyboard(user.countries, for_settings=from_settings))
    db.close()

@router.callback_query(IndustryCallback.filter())
async def industry_click(clb: CallbackQuery, callback_data: IndustryCallback):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=clb.from_user.id).first()
    ind = callback_data.industry
    if ind in user.industries:
        user.industries = [i for i in user.industries if i != ind]
    else:
        user.industries = user.industries + [ind]
    flag_modified(user, "industries")
    db.commit()
    from_settings = getattr(callback_data, "from_settings", False)
    await clb.message.edit_reply_markup(reply_markup=get_keyboard(INDUSTRIES, user.industries, "ind", for_settings=from_settings))
    db.close()

@router.callback_query(ConfirmCallback.filter(F.action == "next_step"))
async def next_step(clb: CallbackQuery, callback_data: ConfirmCallback):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=clb.from_user.id).first()
    step = getattr(callback_data, "step", None) or "ind"
    db.close()
    if step == "country":
        await clb.message.edit_text("Выбери индустрии:", reply_markup=get_keyboard(INDUSTRIES, user.industries, "ind"))
    else:
        cities = get_cities_for_countries(user.countries or ["Казахстан"])
        await clb.message.edit_text("Выбери города:", reply_markup=get_keyboard(cities, user.cities, "city"))

@router.callback_query(CityCallback.filter())
async def city_click(clb: CallbackQuery, callback_data: CityCallback):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=clb.from_user.id).first()
    city = callback_data.city
    if city in user.cities:
        user.cities = [c for c in user.cities if c != city]
    else:
        user.cities = user.cities + [city]
    flag_modified(user, "cities")
    db.commit()
    from_settings = getattr(callback_data, "from_settings", False)
    cities = get_cities_for_countries(user.countries or ["Казахстан"])
    await clb.message.edit_reply_markup(reply_markup=get_keyboard(cities, user.cities, "city", for_settings=from_settings))
    db.close()

@router.callback_query(ConfirmCallback.filter(F.action == "finish"))
async def finish(clb: CallbackQuery, callback_data: ConfirmCallback):
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
    from_settings = getattr(callback_data, "from_settings", False)
    if t == "country":
        user.countries = list(COUNTRIES)
        flag_modified(user, "countries")
        db.commit()
        await clb.message.edit_reply_markup(reply_markup=get_countries_keyboard(user.countries, for_settings=from_settings))
    elif t == "ind":
        user.industries = list(INDUSTRIES)
        flag_modified(user, "industries")
        db.commit()
        await clb.message.edit_reply_markup(reply_markup=get_keyboard(INDUSTRIES, user.industries, "ind", for_settings=from_settings))
    else:
        cities = get_cities_for_countries(user.countries or ["Казахстан"])
        user.cities = list(cities)
        flag_modified(user, "cities")
        db.commit()
        await clb.message.edit_reply_markup(reply_markup=get_keyboard(cities, user.cities, "city", for_settings=from_settings))
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
            "Я помогаю находить B2B выставки и форумы в странах СНГ (Казахстан, Узбекистан, Азербайджан и др.).\n\n"
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
        country_text = ", ".join((user.countries or [])[:4]) or "не выбраны"
        ind_text = ", ".join(user.industries[:4]) if user.industries else "не выбраны"
        city_text = ", ".join(user.cities[:4]) if user.cities else "не выбраны"
        if (user.countries or []) and len(user.countries) > 4:
            country_text += " …"
        if user.cities and len(user.cities) > 4:
            city_text += " …"
        if user.industries and len(user.industries) > 4:
            ind_text += " …"
        await clb.message.edit_text(
            "👋 Главное меню\n\n"
            f"🌍 Страны: {country_text}\n"
            f"📊 Индустрии: {ind_text}\n"
            f"🏙️ Города: {city_text}\n\n"
            "Выбери действие:",
            reply_markup=get_main_menu_keyboard()
        )
    await clb.answer()