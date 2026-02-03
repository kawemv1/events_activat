import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
API_KEY = os.getenv("API_KEY")

# Database
DATABASE_URL = "sqlite:///./events_bot.db"

# Парсинг настройки
PARSING_INTERVAL_MINUTES = 60  # Интервал парсинга в минутах

# Список сайтов для парсинга
PARSING_SOURCES = [
    "https://iteca.events/ru/exhibitions",
    "https://kazexpo.kz/",
    "https://expocentr.asia/news/",
    "https://astanahub.com/ru/event/",
    "https://digitalbusiness.kz",
    "https://profit.kz/calendar/",
    "https://worldexpo.pro/country/kazahstan",
    "https://exposale.net",
    "https://vystavki.su",
]

# Стоп-слова для фильтрации (игнорируем)
STOP_WORDS = [
    "мастер-класс",
    "мастер класс",
    "обучение",
    "вебинар",
    "тренинг",
    "курс",
    "семинар",
    "лекция",
    "конференция онлайн",
    "онлайн-конференция",
]

# Ключевые слова для B2B событий (должны присутствовать)
B2B_KEYWORDS = [
    "выставка",
    "форум",
    "стенд",
    "экспонент",
    "b2b",
    "экспозиция",
    "ярмарка",
    "expo",
    "exhibition",
    "trade show",
]

# Индустрии для выбора пользователем
INDUSTRIES = [
    "IT",
    "Агро",
    "Медицина",
    "Строительство",
    "Энергетика",
    "Транспорт",
    "Туризм",
    "Образование",
    "Финансы",
    "Производство",
    "Торговля",
    "Другое",
]

# Города Казахстана
CITIES = [
    "Алматы",
    "Астана",
    "Шымкент",
    "Актобе",
    "Караганда",
    "Тараз",
    "Усть-Каменогорск",
    "Павлодар",
    "Семей",
    "Уральск",
    "Костанай",
    "Кызылорда",
    "Петропавловск",
    "Атырау",
    "Актау",
    "Темиртау",
    "Туркестан",
    "Кокшетау",
    "Талдыкорган",
    "Экибастуз",
    "Рудный",
    "Жезказган",
    "Все города",
]

# Причины отклонения ивента
FEEDBACK_REASONS = [
    "Не моя сфера",
    "Не B2B",
    "Малый масштаб",
]
