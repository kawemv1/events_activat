import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
DATABASE_URL = "sqlite:///./events_bot.db"

# Ежедневное обновление выставок в 10:00 (часовой пояс бота)
DAILY_PARSING_HOUR = 10
DAILY_PARSING_MINUTE = 0
SCHEDULER_TIMEZONE = "Asia/Almaty"

# Источники для парсинга
PARSING_SOURCES = [
    "https://iteca.events/ru/exhibitions",
    "https://kazexpo.kz/exhibitions",
    "https://digitalbusiness.kz/calendar/",
    "https://profit.kz/events/",
    "https://worldexpo.pro/country/kazahstan",
    "https://vystavki.su/category/kazakhstan/",
    "https://exposale.net/ru/country/kazahstan"
]

STOP_WORDS = [
    "мастер-класс", "вебинар", "курс", "обучение", "тренинг", 
    "вакансия", "стажировка", "онлайн-марафон", "meetup"
]

B2B_KEYWORDS = [
    "выставка", "форум", "экспо", "expo", "exhibition", 
    "конференция", "саммит", "b2b", "стенд", "делегация", 
    "networking", "нет воркинг", "business"
]

INDUSTRIES = [
    "IT & Digital", "Нефть и Газ", "Строительство", "Медицина", 
    "Агропром", "Транспорт", "Энергетика", "Ритейл", "Mining", "Другое"
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
    "Не B2B формат",
    "Слишком мелко/Локально"
]