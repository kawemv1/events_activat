import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./events_bot.db")

# Ежедневное обновление выставок в 10:00 (часовой пояс бота)
DAILY_PARSING_HOUR = 10
DAILY_PARSING_MINUTE = 0
SCHEDULER_TIMEZONE = "Asia/Almaty"

# Multi-country support: CIS target countries
COUNTRIES = [
    "Казахстан",
    "Узбекистан",
    "Азербайджан",
    "Грузия",
    "Армения",
    "Кыргызстан",
    "Таджикистан",
    "Туркменистан",
]

# Exposale unified URL: all CIS except Tajikistan, Turkmenistan
# (10,25,22,60,6,1 = country IDs for KZ, UZ, AZ, GE, AM, KG)
EXPOSALE_ALL_URL = "https://exposale.net/ru/exhibitions/all/10,25,22,60,6,1/all"

# Vystavki.su main page - all events in different cities
VYSTAVKI_MAIN_URL = "https://vystavki.su/"

# Country-specific sources (exposale country pages & vystavki.su country pages all return 404 as of Feb 2026)
COUNTRY_SOURCES = {
    "Казахстан": [
        "https://iteca.events/ru/exhibitions",
        "https://astanahub.com/ru/event/",
    ],
    "Узбекистан": [
        "https://uzexpocentre.uz/",
        "https://iteca.uz/ru/kalendarx-sobtij",
    ],
    "Азербайджан": [
        "https://iteca.az/ru/events",
    ],
    "Грузия": [],
    "Армения": [],
    "Кыргызстан": [],
    "Таджикистан": [],
    "Туркменистан": [],
}

PARSING_SOURCES = [
    "https://iteca.events/ru/exhibitions",
    "https://astanahub.com/ru/event/",
    "https://exposale.net/ru/exhibitions/all/10,25,22,60,6,1/all",
    "https://vystavki.su/",
    "https://iteca.uz/ru/kalendarx-sobtij",
    "https://iteca.az/ru/events",
    "https://uzexpocentre.uz/",
]

STOP_WORDS = [
    # Обучение и курсы
    "мастер-класс", "мастер класс", "мастеркласс",
    "обучение", "обучени", "обучен",
    "вебинар", "вебинары", "вебинаров",
    "вакансия", "вакансии", "вакансий",
    "онлайн-курс", "онлайн курс", "онлайнкурс", "online course", "online-course",
    "курс", "курсы", "курсов", "course", "courses",
    "тренинг", "тренинги", "тренингов", "training", "trainings",
    "стажировка", "стажировки", "стажировок", "internship", "internships",
    "онлайн-марафон", "онлайн марафон", "онлайнмарафон", "online marathon",
    "интенсив", "интенсивы", "интенсивов", "intensive", "intensives",
    
    # Мероприятия
    "meetup", "meet-up", "meet ups",
    "хакатон", "хакатоны", "хакатонов", "hackathon", "hackathons", "hack-a-thon",
    "креатон", "креатоны", "креатонов", "creathon", "creathons",
    "воркшоп", "воркшопы", "воркшопов", "workshop", "workshops", "work-shop",
    "bootcamp", "boot-camp", "boot camp", "bootcamps", "буткемп", "буткемпы",
    "online-bootcamp", "online bootcamp", "онлайн-буткемп", "онлайн буткемп",
    
    # Другое
    "бронирование", "бронирование стенда", "бронирован",
    "ted talks", "ted talk", "ted-talks",
    "прямой эфир", "прямые эфиры",
    "it quiz", "it-quiz", "it квиз",
    "интеллектуальная игра", "интеллектуальные игры",
    "официальные газеты", "официальная газета",
    "стендисты", "стендист", "стендистка",
    "переводчики на выставку", "переводчик на выставку",
    "новый год", "новым годом", "new year", "happy new year",
    
    # Аккредитация и правила
    "аккредитация журналистов", "аккредитация журналиста", "accreditation of journalists",
    "аккредитация прессы", "аккредитация сми", "press accreditation",
    "реклама на выставках", "реклама на выставке", "advertising at exhibitions",
    "реклама выставок", "advertising exhibitions", "рекламные услуги",
    "правила посещения", "правила посещения выставки", "visiting rules",
    "правила участия", "условия посещения", "visiting conditions",
    "регламент посещения", "порядок посещения",
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
    "Талдыкорган": ["талдыкорган", "taldykorgan"],
    "Ташкент": ["ташкент", "tashkent"],
    "Баку": ["баку", "baku"],
    "Тбилиси": ["тбилиси", "tbilisi"],
    "Ереван": ["ереван", "yerevan"],
    "Бишкек": ["бишкек", "bishkek"],
    "Душанбе": ["душанбе", "dushanbe"],
    "Ашхабад": ["ашхабад", "ashgabat"],
    "Самарканд": ["самарканд", "samarkand"],
    "Наманган": ["наманган", "namangan"],
    "Гянджа": ["гянджа", "ganja"],
    "Батуми": ["батуми", "batumi"],
    "Кутаиси": ["кутаиси", "kutaisi"],
    "Ванадзор": ["ванадзор", "vanadzor"],
    "Ош": ["ош", "osh"],
    "Худжанд": ["худжанд", "khujand"],
    "Мары": ["мары", "mary"],
    "Туркменабат": ["туркменабат", "turkmenabat"],
}

# Cities by country (for city selection in onboarding)
COUNTRY_CITIES = {
    "Казахстан": [
        "Алматы", "Астана", "Шымкент", "Атырау", "Актау", "Караганда", "Актобе",
        "Тараз", "Павлодар", "Усть-Каменогорск", "Семей", "Костанай", "Кызылорда",
        "Уральск", "Петропавловск", "Туркестан", "Кокшетау", "Талдыкорган",
    ],
    "Узбекистан": ["Ташкент", "Самарканд", "Наманган"],
    "Азербайджан": ["Баку", "Гянджа"],
    "Грузия": ["Тбилиси", "Батуми", "Кутаиси"],
    "Армения": ["Ереван", "Ванадзор"],
    "Кыргызстан": ["Бишкек", "Ош"],
    "Таджикистан": ["Душанбе", "Худжанд"],
    "Туркменистан": ["Ашхабад", "Мары", "Туркменабат"],
}


def get_cities_for_countries(countries: list) -> list:
    """Return cities for selected countries + 'Все города'. If not Kazakhstan, include all cities from those countries."""
    if not countries:
        return list(CITY_VARIANTS.keys())[:20] + ["Все города"]
    cities = []
    for c in countries:
        cities.extend(COUNTRY_CITIES.get(c, []))
    return list(dict.fromkeys(cities)) + ["Все города"]


CITIES = get_cities_for_countries(["Казахстан"])  # default/legacy

FEEDBACK_REASONS = [
    "Не моя сфера",
    "Не B2B формат (мероприятие не подходит для продаж/стендов)",
    "Недостаточный масштаб (слишком мелко)"
]