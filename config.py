import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
DATABASE_URL = "sqlite:///./events_bot.db"

# Ежедневное обновление выставок в 10:00 (часовой пояс бота)
DAILY_PARSING_HOUR = 10
DAILY_PARSING_MINUTE = 0
SCHEDULER_TIMEZONE = "Asia/Almaty"

# Источники для парсинга (все 10 из ТЗ)
PARSING_SOURCES = [
    "https://iteca.events/ru/",
    "https://atakent-expo.kz/",
    "http://www.qazexpo.kz/",
    "https://expo-centralasia.com/",
    "https://astanahub.com/ru/events",
    "https://digitalbusiness.kz/",
    "https://profit.kz/events/",
    "https://worldexpo.pro/vystavki/kazahstan",
    "https://exposale.net/ru/country/kazahstan",
    "https://vystavki.su/kazakhstan/"
]

STOP_WORDS = [
    "мастер-класс", "обучение", "вебинар", "вакансия", "онлайн-курс",
    "курс", "тренинг", "стажировка", "онлайн-марафон", "meetup"
]

B2B_KEYWORDS = [
    "выставка", "форум", "стенд", "экспонент", "делегация", "b2b",
    "экспо", "expo", "exhibition", "конференция", "саммит",
    "networking", "нет воркинг", "business"
]

INDUSTRIES = [
    "IT/Digital", "Агросектор", "Медицина", "Строительство",
    "Энергетика", "Ритейл/FMCG", "Нефть и Газ", "Транспорт", "Mining", "Другое"
]

# Расширенный словарь городов для умного поиска
CITY_VARIANTS = {
    "Алматы": ["алматы", "алма-ата", "almaty", "алмате"],
    "Астана": ["астана", "астане", "astana", "нур-султан"],
    "Шымкент": ["шымкент", "shymkent"],
    "Атырау": ["атырау", "atyrau"],
    "Актау": ["актау", "aktau"],
    "Караганда": ["караганда", "karaganda"],
    "Актобе": ["актобе", "aktobe"],
    "Тараз": ["тараз", "taraz"],
    "Павлодар": ["павлодар", "pavlodar"],
    "Усть-Каменогорск": ["усть-каменогорск", "oskemen"],
    "Семей": ["семей", "semey"],
    "Костанай": ["костанай", "kostanay"],
    "Кызылорда": ["кызылорда", "kyzylorda"],
    "Уральск": ["уральск", "uralsk"],
    "Петропавловск": ["петропавловск", "petropavlovsk"],
    "Туркестан": ["туркестан", "turkestan"],
    "Кокшетау": ["кокшетау", "kokshetau"],
    "Талдыкорган": ["талдыкорган", "taldykorgan"]
}

CITIES = list(CITY_VARIANTS.keys()) + ["Все города"]

FEEDBACK_REASONS = [
    "Не моя сфера",
    "Не B2B формат (мероприятие не подходит для продаж/стендов)",
    "Недостаточный масштаб (слишком мелко)"
]