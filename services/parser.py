import re
import json
import logging
import asyncio
import httpx
import hashlib
import os
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, unquote, urlparse, parse_qs
from html import unescape as html_unescape
from difflib import SequenceMatcher
from config import (
    STOP_WORDS,
    B2B_KEYWORDS,
    CITY_VARIANTS,
    INDUSTRIES,
    COUNTRIES,
    COUNTRY_SOURCES,
    EXPOSALE_ALL_URL,
    VYSTAVKI_MAIN_URL,
)

logger = logging.getLogger(__name__)

# Маппинг ключевых слов -> индустрия для автоопределения
INDUSTRY_KEYWORDS = {
    "IT/Digital": ["it", "digital", "цифр", "технолог", "software", "стартап", "ai", "artificial intelligence", "блокчейн", "blockchain", "кибербезопасност", "cybersecurity"],
    "Агросектор": ["агро", "сельск", "ферм", "food", "агропром", "агрокультура", "животноводств", "растениеводств", "irrigation", "watering"],
    "Медицина": ["медицин", "здоровь", "клиник", "kihe", "pharma", "фарм", "стоматолог", "dent", "ветеринар", "hospital", "surgery"],
    "Строительство": ["строительств", "build", "интерьер", "недвижим", "architect", "design", "ремонт", "отделк", "construction"],
    "Энергетика": ["энерг", "power", "electric", "renewable", "solar", "wind", "атом", "nuclear", "электростанц"],
    "Ритейл/FMCG": ["ритейл", "fmcg", "розниц", "retail", "товар", "потребитель", "consumer", "упаковк", "packaging", "продукт", "food processing"],
    "Нефть и Газ": ["нефть", "газ", "oil", "gas", "недропольз", "petrochemical", "нефтехим", "бурени", "drilling", "refinery"],
    "Транспорт": ["транспорт", "логистик", "авто", "transport", "logistic", "shipping", "aviation", "авиа", "railway", "жд"],
    "Mining": ["mining", "горн", "металл", "amm", "kioge", "металлург", "steel", "aluminum", "цветн", "precious metal"],
    "Туризм": ["туризм", "travel", "tourism", "hotel", "отель", "гостиниц", "hospitality", "курорт"],
    "Финансы": ["финанс", "finance", "bank", "банк", "инвест", "invest", "страхов", "insurance", "fintech"],
    "Образование": ["образовани", "education", "школ", "университет", "student", "учебн", "pedagog"],
    "Экология": ["эколог", "ecology", "environment", "recycling", "переработк", "waste", "green", "устойчив"],
}

# Все ключевые слова: B2B + все категории
ALL_RELEVANT_KEYWORDS = B2B_KEYWORDS + [
    kw for keywords in INDUSTRY_KEYWORDS.values() for kw in keywords
]

# Месяцы на разных языках для парсинга дат (включая склонения)
MONTHS = {
    'янв': 1, 'январ': 1, 'января': 1, 'jan': 1, 'january': 1,
    'фев': 2, 'феврал': 2, 'февраля': 2, 'feb': 2, 'february': 2,
    'мар': 3, 'март': 3, 'марта': 3, 'mar': 3, 'march': 3,
    'апр': 4, 'апрел': 4, 'апреля': 4, 'apr': 4, 'april': 4,
    'май': 5, 'мая': 5, 'may': 5,
    'июн': 6, 'июня': 6, 'jun': 6, 'june': 6,
    'июл': 7, 'июля': 7, 'jul': 7, 'july': 7,
    'авг': 8, 'август': 8, 'августа': 8, 'aug': 8, 'august': 8,
    'сен': 9, 'сентябр': 9, 'сентября': 9, 'sep': 9, 'september': 9,
    'окт': 10, 'октябр': 10, 'октября': 10, 'oct': 10, 'october': 10,
    'ноя': 11, 'ноябр': 11, 'ноября': 11, 'nov': 11, 'november': 11,
    'дек': 12, 'декабр': 12, 'декабря': 12, 'dec': 12, 'december': 12,
}


class EventParser:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers=self.headers,
            verify=False,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
        self.images_dir = Path("parsed_images")
        self.images_dir.mkdir(exist_ok=True)
        
        # Кэш изображений для избежания повторных загрузок
        self._image_cache = set()

    async def close(self):
        await self.client.aclose()

    def _extract_all_image_urls_from_element(self, element, base_url: str) -> List[str]:
        """Извлечь ВСЕ возможные URL изображений из элемента."""
        image_urls = []
        if not element:
            return image_urls

        # 1. Img tag - все возможные атрибуты
        img = element.find('img') if hasattr(element, 'find') else None
        if img:
            for attr in ['src', 'data-src', 'data-lazy-src', 'data-original', 'data-srcset', 'data-thumb', 'original-src']:
                val = img.get(attr)
                if val and not val.startswith('data:'):
                    # Для srcset берём первое изображение
                    if attr == 'data-srcset' or attr == 'srcset':
                        val = val.split(',')[0].split()[0]
                    full_url = urljoin(base_url, val.strip())
                    image_urls.append(full_url)
            
            # Проверить вложенные picture > source
            picture = element.find('picture')
            if picture:
                for source in picture.find_all('source'):
                    srcset = source.get('srcset')
                    if srcset:
                        img_url = srcset.split(',')[0].split()[0]
                        image_urls.append(urljoin(base_url, img_url.strip()))

        # 2. Background-image в style
        if hasattr(element, 'get'):
            style = element.get('style', '')
            if style:
                # Разные форматы background-image
                bg_patterns = [
                    r'background-image:\s*url\(["\']?([^"\')\s]+)["\']?\)',
                    r'background:\s*[^;]*url\(["\']?([^"\')\s]+)["\']?\)',
                ]
                for pattern in bg_patterns:
                    matches = re.findall(pattern, style, re.IGNORECASE)
                    for match in matches:
                        image_urls.append(urljoin(base_url, match.strip()))

        # 3. Поиск по классам (.img, .image, .thumbnail, .photo)
        if hasattr(element, 'find_all'):
            for img_class in ['img', 'image', 'thumbnail', 'photo', 'picture', 'media']:
                for img_elem in element.find_all(class_=re.compile(img_class, re.I)):
                    # Проверить как img tag, так и background
                    img_tag = img_elem.find('img')
                    if img_tag and img_tag.get('src'):
                        image_urls.append(urljoin(base_url, img_tag['src']))
                    elif img_elem.get('style'):
                        style = img_elem.get('style')
                        bg_match = re.search(r'url\(["\']?([^"\')\s]+)["\']?\)', style)
                        if bg_match:
                            image_urls.append(urljoin(base_url, bg_match.group(1)))

        # 4. Соседние элементы с изображениями
        if hasattr(element, 'find_next_sibling'):
            for sibling in [element.find_next_sibling(), element.find_previous_sibling()]:
                if sibling:
                    sibling_imgs = sibling.find_all('img')
                    for img_tag in sibling_imgs:
                        if img_tag.get('src'):
                            image_urls.append(urljoin(base_url, img_tag['src']))

        # Удалить дубликаты и невалидные URL
        unique_urls = []
        seen = set()
        for url in image_urls:
            if url and url not in seen and url.startswith(('http://', 'https://')):
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls

    async def _download_and_save_image(self, image_url: str, event_url: str) -> Optional[str]:
        """Скачать изображение и сохранить в parsed_images. Возвращает локальный путь или None."""
        if not image_url:
            return None
        
        # Проверить кэш
        cache_key = f"{image_url}:{event_url}"
        if cache_key in self._image_cache:
            logger.debug(f"Image already cached: {image_url}")
            # Вернуть существующий файл если есть
            url_hash = hashlib.md5(event_url.encode('utf-8')).hexdigest()[:12]
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                filepath = self.images_dir / f"{url_hash}{ext}"
                if filepath.exists():
                    return str(filepath)

        if not image_url.startswith(('http://', 'https://')):
            return None

        try:
            url_hash = hashlib.md5(event_url.encode('utf-8')).hexdigest()[:12]
            parsed_url = urlparse(image_url)
            ext = os.path.splitext(parsed_url.path)[1].lower()
            
            # Если расширение неясно, попробовать определить по content-type
            if not ext or ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                ext = '.jpg'  # default

            filename = f"{url_hash}{ext}"
            filepath = self.images_dir / filename

            if filepath.exists():
                logger.debug(f"Image already exists: {filename}")
                self._image_cache.add(cache_key)
                return str(filepath)

            # Скачать изображение
            response = await self.client.get(image_url)
            response.raise_for_status()

            content_type = response.headers.get('content-type', '').lower()
            
            # Проверить что это изображение
            if not content_type.startswith('image/'):
                # Попробовать определить по содержимому (JPEG magic bytes)
                content = response.content[:10]
                is_image = (
                    content[:2] == b'\xff\xd8' or  # JPEG
                    content[:8] == b'\x89PNG\r\n\x1a\n' or  # PNG
                    content[:6] == b'GIF87a' or content[:6] == b'GIF89a' or  # GIF
                    content[:4] == b'RIFF' and content[8:12] == b'WEBP'  # WEBP
                )
                if not is_image:
                    logger.warning(f"Not an image: {image_url} (content-type: {content_type})")
                    return None
                # Определить правильное расширение
                if content[:2] == b'\xff\xd8':
                    ext = '.jpg'
                elif content[:8] == b'\x89PNG\r\n\x1a\n':
                    ext = '.png'
                elif content[:6] in [b'GIF87a', b'GIF89a']:
                    ext = '.gif'
                elif content[:4] == b'RIFF':
                    ext = '.webp'
                filepath = self.images_dir / f"{url_hash}{ext}"

            # Сохранить
            with open(filepath, 'wb') as f:
                f.write(response.content)

            logger.info(f"Downloaded image: {filename} ({len(response.content)} bytes)")
            self._image_cache.add(cache_key)
            return str(filepath)

        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error downloading {image_url}: {e.response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.warning(f"Request error downloading {image_url}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to download image from {image_url}: {e}")
            return None

    async def _extract_og_image(self, html_content: str, base_url: str) -> Optional[str]:
        """Извлечь og:image из meta tags HTML."""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Попробовать разные meta tags
            for prop in ['og:image', 'og:image:url', 'twitter:image', 'twitter:image:src']:
                meta = soup.find('meta', property=prop) or soup.find('meta', attrs={'name': prop})
                if meta and meta.get('content'):
                    return urljoin(base_url, meta['content'])
            
            # Поиск всех img и возврат первого большого (вероятно основного)
            for img in soup.find_all('img', src=True):
                src = img['src']
                if src and not src.startswith('data:'):
                    # Проверить размеры через class/id (большие изображения обычно главные)
                    img_class = img.get('class', [])
                    img_id = img.get('id', '')
                    if any('hero' in str(c).lower() or 'main' in str(c).lower() or 'large' in str(c).lower() 
                           for c in img_class) or 'hero' in img_id.lower() or 'main' in img_id.lower():
                        return urljoin(base_url, src)
            
            return None
        except Exception as e:
            logger.debug(f"Error extracting og:image: {e}")
            return None

    def _clean_text(self, text: str) -> str:
        """Очистить текст от лишнего whitespace и управляющих символов."""
        if not text:
            return ""
        # Удалить лишние пробелы, табы, новые строки
        text = re.sub(r'[\t\n\r\f]+', ' ', text)
        # Удалить лишние пробелы
        text = re.sub(r'\s+', ' ', text)
        # Удалить специальные символы в начале/конце
        text = text.strip(' \t\n\r\x0b\x0c\u200b')
        return text

    # Известные SEO-хвосты сайтов
    _SEO_TAILS = [
        'iteca', 'exposale', 'vystavki', 'worldexpo', 'atakent', 'qazexpo',
        'astanahub', 'expo-centralasia', 'bakuexpo', 'exhibitions', 'выставки',
        'все выставки', 'каталог выставок', 'главная', 'home',
    ]

    def _clean_title(self, title: str) -> str:
        """Очистить заголовок от мусора, SEO-текста, лишних символов."""
        if not title:
            return ""

        # Удалить SEO-хвосты только если они содержат известные паттерны
        for _ in range(2):
            m = re.search(r'\s*[-|–—]\s*([^-|–—]+)$', title)
            if m:
                tail = m.group(1).strip().lower()
                if any(seo in tail for seo in self._SEO_TAILS):
                    title = title[:m.start()]

        # Удалить лишние кавычки
        title = title.strip('"\'"')

        return self._clean_text(title)

    def _clean_description(self, description: str, full_html: str = "") -> str:
        """Очистить описание от мусора, навигации, рекламы."""
        if not description:
            return ""

        # Декодировать HTML entities
        description = html_unescape(description)
        # Удалить &nbsp; и прочие оставшиеся entities
        description = re.sub(r'&\w+;', ' ', description)

        # Удалить типичный мусор (только хвосты, не начала)
        tail_patterns = [
            r'Читать далее.*$',
            r'Подробнее\s*\.{0,3}\s*$',
            r'Learn more.*$',
            r'Купить билет.*$',
            r'Book now.*$',
            r'Поделиться.*$',
            r'Share on.*$',
            r'←.*$',
            r'→.*$',
            r'Home\s*>\s*.*$',
            r'Главная\s*>\s*.*$',
        ]

        for pattern in tail_patterns:
            description = re.sub(pattern, '', description, flags=re.IGNORECASE | re.MULTILINE)

        # Удалить пустые строки в начале
        desc_lines = description.split('\n')
        while desc_lines and not desc_lines[0].strip():
            desc_lines.pop(0)

        description = '\n'.join(desc_lines)
        return self._clean_text(description)

    def _clean_url(self, url: str) -> str:
        """Очистить URL от мусора."""
        if not url:
            return ""
        
        # Удалить tg://msg_url?url=
        if url.startswith("tg://msg_url?url="):
            url = url.replace("tg://msg_url?url=", "")
            try:
                url = unquote(url)
            except:
                pass
        
        # Игнорировать javascript:void(0)
        if url.lower() in ["javascript:void(0)", "javascript:void(0);", "#"]:
            return ""
        
        # Удалить якоря
        url = url.split('#')[0]
        
        # Удалить UTM метки (опционально, можно оставить для аналитики)
        # parsed = urlparse(url)
        # query_params = parse_qs(parsed.query)
        # clean_params = {k: v for k, v in query_params.items() if not k.lower().startswith('utm_')}
        # url = urlunparse(parsed._replace(query='&'.join(f'{k}={v[0]}' for k, v in clean_params.items())))
        
        return url.strip()

    def _normalize_text_for_comparison(self, text: str) -> str:
        """Нормализовать текст для сравнения."""
        if not text:
            return ""
        normalized = re.sub(r'[^\w\s]', ' ', text.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Рассчитать схожесть текстов (0.0 to 1.0)."""
        if not text1 or not text2:
            return 0.0
        norm1 = self._normalize_text_for_comparison(text1)
        norm2 = self._normalize_text_for_comparison(text2)
        if not norm1 or not norm2:
            return 0.0
        return SequenceMatcher(None, norm1, norm2).ratio()

    def _contains_stop_word(self, text: str) -> bool:
        """Проверить наличие стоп-слова."""
        if not text:
            return False
        normalized = re.sub(r'[-\s]+', ' ', text.lower())
        for stop_word in STOP_WORDS:
            normalized_stop = re.sub(r'[-\s]+', ' ', stop_word.lower())
            if normalized_stop in normalized:
                return True
        return False

    def _is_relevant(self, title: str, description: str) -> bool:
        """Проверить релевантность события (B2B, не стоп-слова)."""
        full_text = (title + " " + (description or "")).lower()
        if self._contains_stop_word(full_text):
            return False
        # B2B keywords или industry keywords
        if any(w in full_text for w in ALL_RELEVANT_KEYWORDS):
            return True
        # Паттерны типичных названий выставок: "Something 2026", "Something EXPO", год в названии
        title_lower = title.lower()
        if re.search(r'\b20[2-5]\d\b', title_lower):
            return True
        # Названия с типичными суффиксами выставок
        if re.search(r'\b(show|fair|week|summit|congress|symposium)\b', title_lower, re.I):
            return True
        return False

    def _extract_city(self, text: str) -> Optional[str]:
        """Извлечь город из текста."""
        if not text:
            return None
        text_lower = text.lower()
        for city, variants in CITY_VARIANTS.items():
            if any(v in text_lower for v in variants):
                return city
        return None

    def _extract_country_from_city(self, city: str) -> Optional[str]:
        """Определить страну по городу."""
        if not city:
            return None
        
        city_lower = city.lower()
        country_city_map = {
            "Казахстан": ["алматы", "астана", "шымкент", "атырау", "актау", "караганда", "актобе", "тараз", "павлодар", "уральск", "семей", "костанай", "кызылорда", "петропавловск", "туркестан", "кокшетау", "талдыкорган", "оскемен", "усть-каменогорск"],
            "Узбекистан": ["ташкент", "самарканд", "наманган", "андижан", "бухара", "хива", "карши", "термез"],
            "Азербайджан": ["баку", "гянджа", "сумгаит", "ленкорань", "шеки"],
            "Грузия": ["тбилиси", "батуми", "кутаиси", "рузтави"],
            "Армения": ["ереван", "гюмри", "ванадзор"],
            "Кыргызстан": ["бишкек", "ош", "джалал-абад", "каракол"],
            "Таджикистан": ["душанбе", "худжанд", "куляб"],
            "Туркменистан": ["ашхабад", "туркменабат", "мары", "дашогуз"],
        }
        
        for country, cities in country_city_map.items():
            if any(c in city_lower for c in cities):
                return country
        
        return None

    def _infer_country_from_text(self, text: str) -> Optional[str]:
        """Определить страну из текста."""
        if not text:
            return None
        t = text.lower()
        country_map = [
            ("казахстан", "Казахстан"), ("алматы", "Казахстан"), ("астана", "Казахстан"), ("шымкент", "Казахстан"), ("атырау", "Казахстан"),
            ("узбекистан", "Узбекистан"), ("ташкент", "Узбекистан"), ("самарканд", "Узбекистан"),
            ("азербайджан", "Азербайджан"), ("баку", "Азербайджан"),
            ("грузия", "Грузия"), ("тбилиси", "Грузия"), ("батуми", "Грузия"),
            ("армения", "Армения"), ("ереван", "Армения"),
            ("кыргызстан", "Кыргызстан"), ("киргиз", "Кыргызстан"), ("бишкек", "Кыргызстан"), ("ош", "Кыргызстан"),
            ("таджикистан", "Таджикистан"), ("душанбе", "Таджикистан"), ("худжанд", "Таджикистан"),
            ("туркменистан", "Туркменистан"), ("ашхабад", "Туркменистан"), ("мары", "Туркменистан"),
            # Нецелевые страны — определяем чтобы потом отфильтровать
            ("россия", "Россия"), ("москва", "Россия"), ("санкт-петербург", "Россия"), ("краснодар", "Россия"),
            ("новосибирск", "Россия"), ("екатеринбург", "Россия"), ("казань", "Россия"), ("нижний новгород", "Россия"),
            ("russia", "Россия"), ("moscow", "Россия"), ("st. petersburg", "Россия"),
            ("китай", "Китай"), ("china", "Китай"), ("пекин", "Китай"), ("шанхай", "Китай"),
            ("гуанчжоу", "Китай"), ("шэньчжэнь", "Китай"), ("beijing", "Китай"), ("shanghai", "Китай"),
            ("guangzhou", "Китай"), ("shenzhen", "Китай"), ("hong kong", "Китай"), ("гонконг", "Китай"),
            ("турция", "Турция"), ("turkey", "Турция"), ("стамбул", "Турция"), ("istanbul", "Турция"), ("анкара", "Турция"),
            ("иран", "Иран"), ("iran", "Иран"), ("тегеран", "Иран"),
            ("индия", "Индия"), ("india", "Индия"), ("дели", "Индия"), ("мумбаи", "Индия"),
            ("германия", "Германия"), ("germany", "Германия"), ("берлин", "Германия"), ("мюнхен", "Германия"),
            ("оаэ", "ОАЭ"), ("uae", "ОАЭ"), ("дубай", "ОАЭ"), ("dubai", "ОАЭ"), ("абу-даби", "ОАЭ"),
            ("беларус", "Беларусь"), ("belarus", "Беларусь"), ("минск", "Беларусь"), ("minsk", "Беларусь"),
            ("украин", "Украина"), ("ukraine", "Украина"), ("киев", "Украина"), ("kyiv", "Украина"), ("kiev", "Украина"),
            ("молдов", "Молдова"), ("moldova", "Молдова"), ("кишинёв", "Молдова"), ("кишинев", "Молдова"),
            ("польш", "Польша"), ("poland", "Польша"), ("варшав", "Польша"), ("warsaw", "Польша"),
            ("латви", "Латвия"), ("latvia", "Латвия"), ("рига", "Латвия"),
            ("литв", "Литва"), ("lithuania", "Литва"), ("вильнюс", "Литва"),
            ("эстони", "Эстония"), ("estonia", "Эстония"), ("таллин", "Эстония"),
        ]
        for kw, country in country_map:
            if kw in t:
                return country
        return None

    def _infer_industry(self, title: str, description: str) -> Optional[str]:
        """Определить индустрию по ключевым словам."""
        full = (title + " " + (description or "")).lower()
        
        # Считать совпадения по каждой индустрии
        industry_scores = {}
        for industry, keywords in INDUSTRY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in full)
            if score > 0:
                industry_scores[industry] = score
        
        if not industry_scores:
            return "Другое"
        
        # Вернуть индустрию с наибольшим количеством совпадений
        return max(industry_scores.items(), key=lambda x: x[1])[0]

    def _month_to_num(self, month_name: str) -> Optional[int]:
        """Преобразовать название месяца в число."""
        if not month_name:
            return None
        month_lower = month_name.lower().strip()
        # Сначала ищем точное вхождение (или вхождение ключа в название)
        best_match = None
        best_len = 0
        for m_name, m_num in MONTHS.items():
            if m_name in month_lower or month_lower.startswith(m_name):
                if len(m_name) > best_len:
                    best_len = len(m_name)
                    best_match = m_num
        return best_match

    def _extract_dates_from_text(self, text: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Извлечь даты начала и окончания из текста. Поддерживает множество форматов."""
        if not text:
            return None, None

        text_lower = text.lower().strip()
        current_year = datetime.now().year

        # Формат 1: "с DD.MM.YYYY по DD.MM.YYYY" / "DD.MM.YYYY — DD.MM.YYYY"
        m = re.search(r'(?:с\s+)?(\d{1,2})\.(\d{1,2})\.(20[2-5]\d)\s*(?:по|[-—–])\s*(\d{1,2})\.(\d{1,2})\.(20[2-5]\d)', text_lower)
        if m:
            try:
                return (
                    datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))),
                    datetime(int(m.group(6)), int(m.group(5)), int(m.group(4)))
                )
            except ValueError:
                pass

        # Формат 2: "DD.MM — DD.MM.YYYY" (год только у второй даты)
        m = re.search(r'(\d{1,2})\.(\d{1,2})\s*[-—–]\s*(\d{1,2})\.(\d{1,2})\.(20[2-5]\d)', text_lower)
        if m:
            try:
                year = int(m.group(5))
                return (
                    datetime(year, int(m.group(2)), int(m.group(1))),
                    datetime(year, int(m.group(4)), int(m.group(3)))
                )
            except ValueError:
                pass

        # Формат 3: "с DD месяц по DD месяц YYYY" (межмесячные диапазоны)
        m = re.search(
            r'(?:с\s+)?(\d{1,2})\s+([а-яё]+)\s+(?:по|[-—–])\s*(\d{1,2})\s+([а-яё]+)\s*(20[2-5]\d)?',
            text_lower
        )
        if m:
            day1, month1_name, day2, month2_name, year_str = m.groups()
            month1 = self._month_to_num(month1_name)
            month2 = self._month_to_num(month2_name)
            if month1 and month2:
                year = int(year_str) if year_str else current_year
                try:
                    return (
                        datetime(year, month1, int(day1)),
                        datetime(year, month2, int(day2))
                    )
                except ValueError:
                    pass

        # Формат 4: "DD-DD месяц YYYY" / "DD — DD месяц YYYY"
        m = re.search(r'(\d{1,2})\s*[-—–]\s*(\d{1,2})\s+([а-яёa-z]+)\s*(20[2-5]\d)?', text_lower)
        if m:
            day1, day2, month_name, year_str = m.groups()
            month_num = self._month_to_num(month_name)
            if month_num:
                year = int(year_str) if year_str else current_year
                try:
                    return (
                        datetime(year, month_num, int(day1)),
                        datetime(year, month_num, int(day2))
                    )
                except ValueError:
                    pass

        # Формат 5: "March 15-17, 2024" (английский)
        m = re.search(r'([a-z]+)\s+(\d{1,2})\s*[-—–]\s*(\d{1,2}),?\s*(20[2-5]\d)?', text_lower)
        if m:
            month_name, day1, day2, year_str = m.groups()
            month_num = self._month_to_num(month_name)
            if month_num:
                year = int(year_str) if year_str else current_year
                try:
                    return (
                        datetime(year, month_num, int(day1)),
                        datetime(year, month_num, int(day2))
                    )
                except ValueError:
                    pass

        # Формат 6: Одиночная дата "DD месяц YYYY"
        m = re.search(r'(\d{1,2})\s+([а-яёa-z]+)\s+(20[2-5]\d)', text_lower)
        if m:
            day, month_name, year_str = m.groups()
            month_num = self._month_to_num(month_name)
            if month_num:
                try:
                    return datetime(int(year_str), month_num, int(day)), None
                except ValueError:
                    pass

        # Формат 7: "DD месяц" без года
        m = re.search(r'(\d{1,2})\s+([а-яёa-z]{3,})', text_lower)
        if m:
            day, month_name = m.groups()
            month_num = self._month_to_num(month_name)
            if month_num:
                try:
                    return datetime(current_year, month_num, int(day)), None
                except ValueError:
                    pass

        # Формат 8: числовые "YYYY-MM-DD" или "DD.MM.YYYY"
        m = re.search(r'(20[2-5]\d)[-\./](\d{1,2})[-\./](\d{1,2})', text)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))), None
            except ValueError:
                pass

        m = re.search(r'(\d{1,2})[-\./](\d{1,2})[-\./](20[2-5]\d)', text)
        if m:
            first, second, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            day, month = (first, second) if first > 12 else (first, second)
            if second > 12:
                month, day = first, second
            try:
                return datetime(year, month, day), None
            except ValueError:
                pass

        return None, None

    def _extract_from_json_ld(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Извлечь события из JSON-LD structured data."""
        events = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '')
                # Может быть один объект или список
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    item_type = item.get('@type', '')
                    if item_type not in ('Event', 'ExhibitionEvent', 'BusinessEvent', 'Exhibition'):
                        continue
                    name = item.get('name', '')
                    if not name or len(name) < 5:
                        continue
                    start_str = item.get('startDate', '')
                    end_str = item.get('endDate', '')
                    start_date = end_date = None
                    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M'):
                        if start_str and not start_date:
                            try:
                                start_date = datetime.strptime(start_str[:19], fmt[:len(fmt)])
                            except (ValueError, IndexError):
                                pass
                        if end_str and not end_date:
                            try:
                                end_date = datetime.strptime(end_str[:19], fmt[:len(fmt)])
                            except (ValueError, IndexError):
                                pass

                    location = item.get('location', {})
                    if isinstance(location, dict):
                        place_name = location.get('name', '')
                        address = location.get('address', {})
                        if isinstance(address, dict):
                            city = address.get('addressLocality', '')
                            country = address.get('addressCountry', '')
                        elif isinstance(address, str):
                            city = address
                            country = ''
                        else:
                            city = ''
                            country = ''
                    else:
                        place_name = str(location) if location else ''
                        city = ''
                        country = ''

                    event_url = item.get('url', '') or base_url
                    if event_url and not event_url.startswith('http'):
                        event_url = urljoin(base_url, event_url)

                    image = item.get('image', '')
                    if isinstance(image, list):
                        image = image[0] if image else ''
                    if isinstance(image, dict):
                        image = image.get('url', '')

                    events.append({
                        'title': self._clean_title(name),
                        'name': name,
                        'description': self._clean_description(item.get('description', ''))[:800],
                        'city': self._extract_city(city or place_name) or city,
                        'place': place_name or None,
                        'start_date': start_date,
                        'end_date': end_date,
                        'url': self._clean_url(event_url),
                        'image_url': image or None,
                        'country': self._infer_country_from_text(f"{city} {country} {place_name}"),
                    })
            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        return events

    async def _fetch_page_content(self, url: str) -> Tuple[Optional[str], Optional[BeautifulSoup]]:
        """Скачать страницу и вернуть HTML + BeautifulSoup."""
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, 'lxml')
            return html, soup
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None, None

    async def _parse_event_detail_page(self, event_url: str, base_event: Dict) -> Dict:
        """Загрузить страницу события и извлечь детальную информацию."""
        try:
            html, soup = await self._fetch_page_content(event_url)
            if not html or not soup:
                return base_event
            
            # Извлечь og:image
            og_image = await self._extract_og_image(html, event_url)
            if og_image and not base_event.get('image_url'):
                local_path = await self._download_and_save_image(og_image, event_url)
                if local_path:
                    base_event['image_url'] = local_path
            
            # Извлечь title из h1
            h1 = soup.find('h1')
            if h1:
                h1_text = self._clean_title(h1.get_text())
                if len(h1_text) > len(base_event.get('title', '')):
                    base_event['title'] = h1_text
                    base_event['name'] = h1_text
            
            # Извлечь описание
            # Искать блоки с описанием
            desc_selectors = [
                'meta[name="description"]',
                '.description', '.content', '.about', '.event-description',
                '.details', '.info', 'article', '[itemprop="description"]',
            ]
            
            for selector in desc_selectors:
                if '>' in selector:
                    elem = soup.select_one(selector)
                else:
                    elem = soup.find(class_=re.compile(selector.strip('.#[]'), re.I))
                    if not elem:
                        elem = soup.find(selector.split('[')[0].strip('.'))
                
                if elem:
                    desc_text = self._clean_description(elem.get_text())
                    if len(desc_text) > len(base_event.get('description', '')):
                        base_event['description'] = desc_text
                    break
            
            # Извлечь дату
            date_selectors = [
                '.date', '.event-date', '.datetime', '[itemprop="startDate"]',
                '.schedule', '.when', '.time',
            ]
            
            for selector in date_selectors:
                elem = soup.find(class_=re.compile(selector.strip('.#[]'), re.I))
                if elem:
                    date_text = elem.get_text()
                    start, end = self._extract_dates_from_text(date_text)
                    if start:
                        base_event['start_date'] = start
                    if end:
                        base_event['end_date'] = end
                    break
            
            # Извлечь место
            place_selectors = [
                '.place', '.location', '.venue', '.address', '[itemprop="location"]',
                '.where', '.event-location',
            ]
            
            for selector in place_selectors:
                elem = soup.find(class_=re.compile(selector.strip('.#[]'), re.I))
                if elem:
                    place_text = self._clean_text(elem.get_text())
                    if place_text and len(place_text) > 5:
                        base_event['place'] = place_text
                        # Также извлечь город из места
                        city = self._extract_city(place_text)
                        if city and not base_event.get('city'):
                            base_event['city'] = city
                    break
            
        except Exception as e:
            logger.debug(f"Error parsing detail page {event_url}: {e}")
        
        return base_event

    # --- Парсеры для каждого источника ---

    async def parse_iteca(self) -> List[Dict]:
        """https://iteca.events/ru/exhibitions — Next.js RSC site with embedded JSON."""
        events = []
        base_url = "https://iteca.events"
        try:
            url = "https://iteca.events/ru/exhibitions"
            resp = await self.client.get(url)
            html = resp.text

            exhibitions = []

            # RSC payload: данные внутри __next_f.push() с экранированием \\"
            # Ищем \\"exhibitions\\":[{...}] в HTML
            esc_marker = '\\"exhibitions\\":[{'
            esc_idx = html.find(esc_marker)
            if esc_idx >= 0:
                chunk = html[esc_idx:esc_idx+100000]
                unescaped = chunk.replace('\\"', '"').replace('\\u0026', '&')
                m = re.search(r'"exhibitions":\[(.+?)\](?:,"|\})', unescaped)
                if m:
                    try:
                        exhibitions = json.loads('[' + m.group(1) + ']')
                    except json.JSONDecodeError:
                        pass

            # Fallback: __NEXT_DATA__ (старая версия сайта)
            if not exhibitions:
                soup = BeautifulSoup(html, 'lxml')
                nds = soup.find('script', id='__NEXT_DATA__')
                if nds and nds.string:
                    try:
                        nd = json.loads(nds.string)
                        exhibitions = nd.get('props', {}).get('pageProps', {}).get('exhibitions', [])
                    except (json.JSONDecodeError, KeyError):
                        pass

            seen_urls = set()
            for exh in exhibitions:
                if not isinstance(exh, dict):
                    continue
                try:
                    title = (exh.get('title', '') or exh.get('project', '') or '').strip()
                    if not title or len(title) < 5:
                        continue

                    description = exh.get('description', '') or ''
                    begin_date = exh.get('beginDate', '') or ''
                    end_date_str = exh.get('endDate', '') or ''
                    city_label = exh.get('city_label', '') or exh.get('city', '') or ''
                    location = exh.get('location', '') or exh.get('address', '') or ''
                    logo = exh.get('logo', '') or exh.get('logo_svg', '') or exh.get('image_profile', '') or ''
                    website = exh.get('website', '') or ''

                    # Даты
                    start_date = end_date = None
                    for ds, target in [(begin_date, 'start'), (end_date_str, 'end')]:
                        if ds:
                            for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%d.%m.%Y'):
                                try:
                                    parsed = datetime.strptime(str(ds)[:19], fmt)
                                    if target == 'start':
                                        start_date = parsed
                                    else:
                                        end_date = parsed
                                    break
                                except ValueError:
                                    pass
                    if not start_date:
                        date_text = exh.get('formattedDateRange', '') or f"{title} {description}"
                        start_date, end_date = self._extract_dates_from_text(date_text)

                    event_url = website if website.startswith('http') else url
                    if event_url in seen_urls:
                        continue
                    seen_urls.add(event_url)

                    # Изображение
                    local_image_path = None
                    if logo:
                        logo_url = logo if logo.startswith('http') else urljoin(base_url, logo)
                        local_image_path = await self._download_and_save_image(logo_url, event_url)

                    city = self._extract_city(city_label) or self._extract_city(location) or self._extract_city(title)

                    cleaned_url = self._clean_url(event_url)
                    if not cleaned_url:
                        continue

                    events.append({
                        'title': self._clean_title(title),
                        'name': description or title,
                        'description': self._clean_description(description)[:800],
                        'city': city,
                        'place': self._clean_text(location) or None,
                        'start_date': start_date,
                        'end_date': end_date,
                        'url': cleaned_url,
                        'image_url': local_image_path,
                        'source': 'iteca.events',
                        'country': self._extract_country_from_city(city) or 'Казахстан',
                        'industry': (lambda v: v if v and v != '$undefined' else None)(exh.get('industryTitle')) or self._infer_industry(title, description),
                    })
                except Exception as e:
                    logger.debug(f"Iteca item error: {e}")

        except Exception as e:
            logger.error(f"Iteca error: {e}")

        logger.info(f"parse_iteca: found {len(events)} events")
        return events

    async def parse_atakent(self) -> List[Dict]:
        """https://atakent-expo.kz/ — с дедупликацией внутри источника."""
        events = []
        seen_urls = set()
        try:
            url = "https://atakent-expo.kz/"
            html, soup = await self._fetch_page_content(url)
            if not soup:
                return events

            # JSON-LD
            json_ld_events = self._extract_from_json_ld(soup, url)
            for ev in json_ld_events:
                if ev.get('url') and ev['url'] not in seen_urls:
                    ev['source'] = 'atakent-expo.kz'
                    ev['industry'] = self._infer_industry(ev.get('title', ''), ev.get('description', ''))
                    ev['country'] = 'Казахстан'
                    if not ev.get('city'):
                        ev['city'] = 'Алматы'
                    if not ev.get('place'):
                        ev['place'] = 'Атакент'
                    if self._is_relevant(ev.get('title', ''), ev.get('description', '')):
                        events.append(ev)
                        seen_urls.add(ev['url'])

            # CSS selectors — с приоритетом более специфичных
            selectors = ['.event-item', '.exhibition-item', 'a[href*="event"]', 'article', '.card']
            items = []
            for sel in selectors:
                items.extend(soup.select(sel))

            for item in items:
                try:
                    title_tag = item.find(['h2', 'h3', 'h4']) or item
                    title = self._clean_title(title_tag.get_text())
                    if len(title) < 5:
                        continue

                    link = item.find('a', href=True) or (item if item.name == 'a' and item.get('href') else None)
                    event_url = urljoin(url, link['href']) if link and link.get('href') else url
                    if event_url in seen_urls:
                        continue

                    desc = item.find('p')
                    description = self._clean_description(desc.get_text()) if desc else ""

                    image_urls = self._extract_all_image_urls_from_element(item, url)
                    local_image_path = None
                    for img_url in image_urls:
                        local_image_path = await self._download_and_save_image(img_url, event_url)
                        if local_image_path:
                            break

                    full_text = title + " " + description
                    start_date, end_date = self._extract_dates_from_text(full_text)

                    if self._is_relevant(title, description):
                        cleaned_url = self._clean_url(event_url)
                        if not cleaned_url:
                            continue
                        seen_urls.add(event_url)

                        events.append({
                            'title': title,
                            'name': title,
                            'description': description[:800],
                            'city': self._extract_city(title) or "Алматы",
                            'place': "Атакент",
                            'start_date': start_date,
                            'end_date': end_date,
                            'url': cleaned_url,
                            'image_url': local_image_path,
                            'source': 'atakent-expo.kz',
                            'country': 'Казахстан',
                            'industry': self._infer_industry(title, description)
                        })
                except Exception as e:
                    logger.debug(f"Atakent item error: {e}")
        except Exception as e:
            logger.error(f"Atakent error: {e}")

        logger.info(f"parse_atakent: found {len(events)} events")
        return events

    async def parse_qazexpo(self) -> List[Dict]:
        """http://www.qazexpo.kz/"""
        events = []
        try:
            url = "http://www.qazexpo.kz/"
            html, soup = await self._fetch_page_content(url)
            if not soup:
                return events
            
            items = soup.find_all(['a', 'div', 'article'], class_=re.compile(r'event|exhibition|card|news', re.I))
            
            for item in items:
                try:
                    title = self._clean_title(item.get_text())
                    if len(title) < 10:
                        continue
                    
                    link = item if item.name == 'a' and item.get('href') else item.find('a', href=True)
                    event_url = urljoin(url, link['href']) if link and link.get('href') else url
                    
                    # Изображения
                    image_urls = self._extract_all_image_urls_from_element(item, url)
                    local_image_path = None
                    for img_url in image_urls:
                        local_image_path = await self._download_and_save_image(img_url, event_url)
                        if local_image_path:
                            break
                    
                    # Дата
                    start_date, end_date = self._extract_dates_from_text(title)
                    
                    if self._is_relevant(title, ""):
                        cleaned_url = self._clean_url(event_url)
                        if not cleaned_url:
                            continue

                        events.append({
                            'title': title[:200],
                            'name': title[:200],
                            'description': "",
                            'city': self._extract_city(title) or "Астана",
                            'place': "QazExpo",
                            'start_date': start_date,
                            'end_date': end_date,
                            'url': cleaned_url,
                            'image_url': local_image_path,
                            'source': 'qazexpo.kz',
                            'country': 'Казахстан',
                            'industry': self._infer_industry(title, "")
                        })
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"QazExpo error: {e}")
        
        logger.info(f"parse_qazexpo: found {len(events)} events")
        return events

    async def parse_expo_centralasia(self) -> List[Dict]:
        """https://expo-centralasia.com/"""
        events = []
        try:
            url = "https://expo-centralasia.com/"
            html, soup = await self._fetch_page_content(url)
            if not soup:
                return events
            
            items = soup.find_all(['a', 'article', 'div'], class_=re.compile(r'event|expo|card|news', re.I))
            
            for item in items:
                try:
                    title_tag = item.find(['h2', 'h3', 'h4']) or item
                    title = self._clean_title(title_tag.get_text())
                    if len(title) < 5:
                        continue
                    
                    link = item.find('a', href=True) or (item if item.name == 'a' else None)
                    event_url = urljoin(url, link['href']) if link and link.get('href') else url
                    
                    desc = item.find('p')
                    description = self._clean_description(desc.get_text()) if desc else ""
                    
                    # Изображения
                    image_urls = self._extract_all_image_urls_from_element(item, url)
                    local_image_path = None
                    for img_url in image_urls:
                        local_image_path = await self._download_and_save_image(img_url, event_url)
                        if local_image_path:
                            break
                    
                    # Дата
                    full_text = title + " " + description
                    start_date, end_date = self._extract_dates_from_text(full_text)
                    
                    if self._is_relevant(title, description):
                        cleaned_url = self._clean_url(event_url)
                        if not cleaned_url:
                            continue

                        events.append({
                            'title': title,
                            'name': title,
                            'description': description[:800],
                            'city': self._extract_city(full_text),
                            'place': None,
                            'start_date': start_date,
                            'end_date': end_date,
                            'url': cleaned_url,
                            'image_url': local_image_path,
                            'source': 'expo-centralasia.com',
                            'country': 'Казахстан',
                            'industry': self._infer_industry(title, description)
                        })
                except Exception as e:
                    logger.debug(f"Expo CentralAsia item error: {e}")
        except Exception as e:
            logger.error(f"Expo CentralAsia error: {e}")
        
        logger.info(f"parse_expo_centralasia: found {len(events)} events")
        return events

    async def parse_astanahub(self) -> List[Dict]:
        """https://astanahub.com/ru/event/ — card-based: <a> wraps div.event-card."""
        events = []
        base_url = "https://astanahub.com"
        try:
            url = "https://astanahub.com/ru/event/"
            html, soup = await self._fetch_page_content(url)
            if not soup:
                return events

            cards = soup.find_all('div', class_='event-card')
            seen_urls = set()

            for card in cards:
                try:
                    # Title from h5 (or h4/h3)
                    title_tag = card.find(['h5', 'h4', 'h3'])
                    if not title_tag:
                        continue
                    title = self._clean_title(title_tag.get_text())
                    if len(title) < 5:
                        continue

                    # URL from parent <a> tag wrapping the card
                    parent_a = card.find_parent('a', href=True)
                    event_url = urljoin(base_url, parent_a['href']) if parent_a else url
                    if event_url in seen_urls:
                        continue
                    seen_urls.add(event_url)

                    # Description
                    desc = card.find('p')
                    description = self._clean_description(desc.get_text()) if desc else ""

                    # Image: /media/ thumbnail inside div.event-thumb
                    thumb_div = card.find('div', class_='event-thumb')
                    img_tag = thumb_div.find('img', src=lambda s: s and '/media/' in s) if thumb_div else None
                    local_image_path = None
                    if img_tag:
                        img_url = urljoin(base_url, img_tag['src'])
                        local_image_path = await self._download_and_save_image(img_url, event_url)

                    # Date from span inside div.event-card-date
                    date_div = card.find('div', class_='event-card-date')
                    date_text = ""
                    if date_div:
                        span = date_div.find('span')
                        date_text = span.get_text().strip() if span else ""
                    full_text = title + " " + description + " " + date_text
                    start_date, end_date = self._extract_dates_from_text(full_text)

                    if self._is_relevant(title, description):
                        cleaned_url = self._clean_url(event_url)
                        if not cleaned_url:
                            continue

                        events.append({
                            'title': title,
                            'name': title,
                            'description': description[:800],
                            'city': self._extract_city(title) or "Астана",
                            'place': None,
                            'start_date': start_date,
                            'end_date': end_date,
                            'url': cleaned_url,
                            'image_url': local_image_path,
                            'source': 'astanahub.com',
                            'country': 'Казахстан',
                            'industry': self._infer_industry(title, description)
                        })
                except Exception as e:
                    logger.debug(f"AstanaHub item error: {e}")
        except Exception as e:
            logger.error(f"AstanaHub error: {e}")

        logger.info(f"parse_astanahub: found {len(events)} events")
        return events

    async def parse_worldexpo(self) -> List[Dict]:
        """https://worldexpo.pro/vystavki/kazahstan — с retry на 403."""
        events = []
        try:
            url = "https://worldexpo.pro/vystavki/kazahstan"
            # Попробовать с Referer header для обхода 403
            headers_variants = [
                {**self.headers, 'Referer': 'https://worldexpo.pro/'},
                {**self.headers, 'Referer': 'https://www.google.com/'},
                self.headers,
            ]
            html = None
            soup = None
            for hdrs in headers_variants:
                try:
                    resp = await self.client.get(url, headers=hdrs)
                    if resp.status_code == 200:
                        html = resp.text
                        soup = BeautifulSoup(html, 'lxml')
                        break
                    elif resp.status_code == 403:
                        logger.debug(f"WorldExpo 403, trying different headers")
                        continue
                    else:
                        resp.raise_for_status()
                except httpx.HTTPStatusError:
                    continue

            if not soup:
                logger.warning("WorldExpo: all header variants returned non-200")
                return events

            items = soup.find_all('div', class_='item-content')
            if not items:
                items = soup.select('.exhibition, .event-item, .news-item')
            if not items:
                items = soup.find_all('a', href=re.compile(r'/vystavk|/exhibition'))

            for item in items:
                try:
                    title_tag = item.find(['h4', 'h3', 'h2'])
                    if title_tag:
                        link = title_tag.find('a')
                        title = self._clean_title((link or title_tag).get_text())
                        event_url = urljoin(url, link['href']) if link and link.get('href') else url
                    else:
                        title = self._clean_title(item.get_text())
                        link = item.find('a', href=True)
                        event_url = urljoin(url, link['href']) if link else url

                    if len(title) < 5:
                        continue

                    date_span = item.find('span', class_=re.compile(r'date|item-content-date'))
                    loc_span = item.find('span', class_=re.compile(r'location|search-location'))
                    desc = item.find('p')
                    description = self._clean_description(desc.get_text()) if desc else ""

                    # Изображения
                    image_urls = self._extract_all_image_urls_from_element(item, url)
                    local_image_path = None
                    for img_url in image_urls:
                        local_image_path = await self._download_and_save_image(img_url, event_url)
                        if local_image_path:
                            break

                    # Дата — теперь извлекаем start И end
                    raw_date = date_span.get_text() if date_span else title
                    start_date, end_date = self._extract_dates_from_text(raw_date)

                    loc_text = loc_span.get_text() if loc_span else ""
                    city = self._extract_city(loc_text or title)
                    country = self._infer_country_from_text(loc_text) or 'Казахстан'

                    if self._is_relevant(title, description):
                        cleaned_url = self._clean_url(event_url)
                        if not cleaned_url:
                            continue

                        events.append({
                            'title': title,
                            'name': title,
                            'description': description[:800],
                            'city': city,
                            'place': self._clean_text(loc_text) or None,
                            'start_date': start_date,
                            'end_date': end_date,
                            'url': cleaned_url,
                            'image_url': local_image_path,
                            'source': 'worldexpo.pro',
                            'country': country,
                            'industry': self._infer_industry(title, description)
                        })
                except Exception as e:
                    logger.debug(f"WorldExpo item error: {e}")
        except Exception as e:
            logger.error(f"WorldExpo error: {e}")

        logger.info(f"parse_worldexpo: found {len(events)} events")
        return events


    async def parse_exposale_all(self) -> List[Dict]:
        """https://exposale.net/ru/exhibitions/all/... — JSON-LD + card-based parsing."""
        events = []
        base = "https://exposale.net"
        seen_urls = set()
        try:
            resp = await self.client.get(EXPOSALE_ALL_URL)
            soup = BeautifulSoup(resp.text, 'lxml')

            # Способ 1: JSON-LD structured data
            json_ld_events = self._extract_from_json_ld(soup, base)
            for ev in json_ld_events:
                if ev.get('url') and ev['url'] not in seen_urls:
                    ev['source'] = 'exposale.net'
                    ev['industry'] = self._infer_industry(ev.get('title', ''), ev.get('description', ''))
                    if not ev.get('country'):
                        ev['country'] = self._infer_country_from_text(
                            f"{ev.get('city', '')} {ev.get('place', '')}"
                        ) or 'Казахстан'
                    # exposale.net — все записи являются выставками, не фильтруем по relevance
                    if not self._contains_stop_word(ev.get('title', '') + ' ' + ev.get('description', '')):
                        events.append(ev)
                        seen_urls.add(ev['url'])

            # Способ 2: Карточки выставок — ищем ссылки на /ru/exhibition/
            for link in soup.find_all('a', href=re.compile(r'/ru/exhibition/')):
                try:
                    href = link.get('href', '')
                    event_url = urljoin(base, href)
                    if event_url in seen_urls:
                        continue

                    title = self._clean_title(link.get_text())
                    if len(title) < 5:
                        continue

                    # Подняться к карточке-контейнеру
                    card = link.find_parent(['div', 'article', 'li', 'tr', 'td'])
                    card_text = card.get_text() if card else title

                    country = self._infer_country_from_text(card_text) or "Казахстан"
                    city = self._extract_city(card_text)

                    # Описание
                    desc_elem = card.find('p') if card else None
                    description = self._clean_description(desc_elem.get_text()) if desc_elem else ""

                    # Изображения
                    image_urls = self._extract_all_image_urls_from_element(card, base) if card else []
                    local_image_path = None
                    for img_url in image_urls:
                        local_image_path = await self._download_and_save_image(img_url, event_url)
                        if local_image_path:
                            break

                    # Дата — из текста карточки (формат "с DD.MM.YYYY по DD.MM.YYYY")
                    start_date, end_date = self._extract_dates_from_text(card_text)

                    if self._contains_stop_word(title + ' ' + description):
                        continue
                    cleaned_url = self._clean_url(event_url)
                    if not cleaned_url:
                        continue
                    seen_urls.add(event_url)

                    events.append({
                        'title': title[:200],
                        'name': title[:200],
                        'description': description[:800] or self._clean_text(card_text)[:800],
                        'city': city,
                        'place': None,
                        'start_date': start_date,
                        'end_date': end_date,
                        'url': cleaned_url,
                        'image_url': local_image_path,
                        'source': 'exposale.net',
                        'country': country,
                        'industry': self._infer_industry(title, description)
                    })
                except Exception as e:
                    logger.debug(f"Exposale item error: {e}")
        except Exception as e:
            logger.error(f"Exposale all error: {e}")

        logger.info(f"parse_exposale_all: found {len(events)} events")
        return events

    def _parse_vystavki_title(self, raw_title: str) -> Dict:
        """Разобрать заголовок vystavki.su формата 'НАЗВАНИЕ YYYY Город, Страна DD — DD Месяц YYYY'."""
        result = {'title': raw_title, 'city': None, 'country': None, 'start_date': None, 'end_date': None}

        # Попробовать выделить дату из конца строки
        start_date, end_date = self._extract_dates_from_text(raw_title)
        if start_date:
            result['start_date'] = start_date
            result['end_date'] = end_date

        # Попробовать выделить город и страну
        city = self._extract_city(raw_title)
        if city:
            result['city'] = city
            result['country'] = self._extract_country_from_city(city)

        country = self._infer_country_from_text(raw_title)
        if country and not result['country']:
            result['country'] = country

        # Очистить заголовок: убрать дату и город/страну из конца
        clean = raw_title
        # Убрать дату (числа + месяц + год в конце)
        clean = re.sub(r'\s*\d{1,2}\s*[-—–]\s*\d{1,2}\s+[а-яёa-z]+\s*\d{4}\s*$', '', clean, flags=re.I)
        clean = re.sub(r'\s*\d{1,2}\s+[а-яёa-z]+\s*[-—–]\s*\d{1,2}\s+[а-яёa-z]+\s*\d{4}\s*$', '', clean, flags=re.I)
        # Убрать "Город, Страна" из конца
        clean = re.sub(r'\s*,?\s*(Казахстан|Узбекистан|Азербайджан|Грузия|Армения|Кыргызстан|Таджикистан|Туркменистан)\s*$', '', clean, flags=re.I)
        # Убрать год из конца
        clean = re.sub(r'\s+20[2-5]\d\s*$', '', clean)
        # Убрать город из конца если он отдельный
        if city:
            clean = re.sub(r'\s*,?\s*' + re.escape(city) + r'\s*$', '', clean, flags=re.I)

        result['title'] = self._clean_title(clean.strip()) or self._clean_title(raw_title)
        return result

    async def parse_vystavki_main(self) -> List[Dict]:
        """https://vystavki.su/ — WordPress, ссылки с img + текстом."""
        events = []
        seen_urls = set()
        try:
            url = VYSTAVKI_MAIN_URL
            html, soup = await self._fetch_page_content(url)
            if not soup:
                return events

            # Способ 1: JSON-LD
            json_ld_events = self._extract_from_json_ld(soup, url)
            for ev in json_ld_events:
                if ev.get('url') and ev['url'] not in seen_urls:
                    ev['source'] = 'vystavki.su'
                    ev['industry'] = self._infer_industry(ev.get('title', ''), ev.get('description', ''))
                    if not ev.get('country'):
                        ev['country'] = 'Казахстан'
                    if self._is_relevant(ev.get('title', ''), ev.get('description', '')):
                        events.append(ev)
                        seen_urls.add(ev['url'])

            # Способ 2: Ссылки с изображениями (основной контент vystavki.su)
            for link in soup.find_all('a', href=True):
                try:
                    href = link.get('href', '')
                    if not href or href == '/' or href == '#':
                        continue
                    event_url = urljoin(url, href)
                    if event_url in seen_urls:
                        continue
                    # Пропускать nav-ссылки, соцсети, и т.д.
                    if any(skip in event_url for skip in ['#', 'javascript:', 'mailto:', 'tel:', 'facebook', 'twitter', 'vk.com', 'instagram', 'youtube', 'telegram']):
                        continue
                    # Ссылка должна содержать img или значимый текст
                    has_img = link.find('img') is not None
                    link_text = self._clean_text(link.get_text())
                    if not has_img and len(link_text) < 10:
                        continue
                    if len(link_text) > 500:
                        continue

                    raw_title = link_text
                    parsed = self._parse_vystavki_title(raw_title)
                    title = parsed['title']
                    if len(title) < 5:
                        continue

                    city = parsed['city']
                    country = parsed['country'] or self._infer_country_from_text(raw_title) or 'Казахстан'
                    start_date = parsed['start_date']
                    end_date = parsed['end_date']

                    # Описание из родителя
                    parent = link.find_parent(['article', 'div', 'li', 'section'])
                    description = ""
                    if parent:
                        desc_tag = parent.find('p')
                        if desc_tag:
                            description = self._clean_description(desc_tag.get_text())

                    # Изображения
                    image_urls = self._extract_all_image_urls_from_element(link, url)
                    if not image_urls and parent:
                        image_urls = self._extract_all_image_urls_from_element(parent, url)
                    local_image_path = None
                    for img_url in image_urls:
                        local_image_path = await self._download_and_save_image(img_url, event_url)
                        if local_image_path:
                            break

                    if self._is_relevant(title, description or raw_title):
                        cleaned_url = self._clean_url(event_url)
                        if not cleaned_url:
                            continue
                        seen_urls.add(event_url)

                        events.append({
                            'title': title[:200],
                            'name': title[:200],
                            'description': description[:800],
                            'city': city,
                            'place': None,
                            'start_date': start_date,
                            'end_date': end_date,
                            'url': cleaned_url,
                            'image_url': local_image_path,
                            'source': 'vystavki.su',
                            'country': country,
                            'industry': self._infer_industry(title, description)
                        })
                except Exception as e:
                    logger.debug(f"Vystavki item error: {e}")

            # Способ 3: Fallback — article/post containers
            if not events:
                for item in soup.select('article, .post, .entry'):
                    try:
                        title_tag = item.find(['h2', 'h3', 'h4'])
                        if not title_tag:
                            continue
                        raw_title = title_tag.get_text()
                        parsed = self._parse_vystavki_title(raw_title)
                        title = parsed['title']
                        if len(title) < 5:
                            continue

                        link = item.find('a', href=True)
                        event_url = urljoin(url, link['href']) if link else url
                        if event_url in seen_urls:
                            continue

                        desc = item.find('p')
                        description = self._clean_description(desc.get_text()) if desc else ""

                        image_urls = self._extract_all_image_urls_from_element(item, url)
                        local_image_path = None
                        for img_url in image_urls:
                            local_image_path = await self._download_and_save_image(img_url, event_url)
                            if local_image_path:
                                break

                        if self._is_relevant(title, description or raw_title):
                            cleaned_url = self._clean_url(event_url)
                            if not cleaned_url:
                                continue
                            seen_urls.add(event_url)
                            events.append({
                                'title': title[:200],
                                'name': title[:200],
                                'description': description[:800],
                                'city': parsed['city'],
                                'place': None,
                                'start_date': parsed['start_date'],
                                'end_date': parsed['end_date'],
                                'url': cleaned_url,
                                'image_url': local_image_path,
                                'source': 'vystavki.su',
                                'country': parsed['country'] or 'Казахстан',
                                'industry': self._infer_industry(title, description)
                            })
                    except Exception as e:
                        logger.debug(f"Vystavki fallback item error: {e}")

        except Exception as e:
            logger.error(f"Vystavki.su error: {e}")

        logger.info(f"parse_vystavki_main: found {len(events)} events")
        return events

    async def parse_generic(self, url: str, source_name: str, country: str = "Казахстан") -> List[Dict]:
        """Универсальный парсер для любого сайта."""
        events = []
        try:
            html, soup = await self._fetch_page_content(url)
            if not soup:
                return events
            
            # Пробовать разные селекторы
            selectors = [
                '.exhibition', '.event', '.item', 'article', '[class*="expo"]',
                '.news', '.card', '.post', '.entry', '[class*="event-"]', '[class*="news-"]'
            ]
            items = []
            for sel in selectors:
                items.extend(soup.select(sel))
            
            # Если не нашли, взять все ссылки
            if not items:
                items = soup.find_all('a', href=True)[:80]
            
            for item in items:
                try:
                    if hasattr(item, 'find') and item.find(['h2', 'h3', 'h4']):
                        title_tag = item.find(['h2', 'h3', 'h4']) or item.find('a')
                        title = self._clean_title((title_tag or item).get_text())
                        link = item.find('a', href=True) or (item if item.name == 'a' and item.get('href') else None)
                    else:
                        if item.name != 'a' or not item.get('href'):
                            continue
                        title = self._clean_title(item.get_text())
                        link = item
                    
                    if len(title) < 5:
                        continue
                    
                    event_url = urljoin(url, link['href']) if link and link.get('href') else url
                    desc = item.find('p') if hasattr(item, 'find') else None
                    description = self._clean_description(desc.get_text()) if desc else ""
                    
                    # Изображения
                    image_urls = self._extract_all_image_urls_from_element(item, url)
                    local_image_path = None
                    for img_url in image_urls:
                        local_image_path = await self._download_and_save_image(img_url, event_url)
                        if local_image_path:
                            break
                    
                    # Дата
                    full_text = title + " " + description
                    start_date, end_date = self._extract_dates_from_text(full_text)
                    
                    if self._is_relevant(title, description):
                        cleaned_url = self._clean_url(event_url)
                        if not cleaned_url:
                            continue

                        events.append({
                            'title': title[:200],
                            'name': title[:200],
                            'description': description[:800] or "",
                            'city': self._extract_city(full_text),
                            'place': None,
                            'start_date': start_date,
                            'end_date': end_date,
                            'url': cleaned_url,
                            'image_url': local_image_path,
                            'source': source_name,
                            'country': country,
                            'industry': self._infer_industry(title, description)
                        })
                except Exception as e:
                    logger.debug(f"Generic item error: {e}")
        except Exception as e:
            logger.error(f"Generic {source_name} error: {e}")
        
        logger.info(f"parse_generic {source_name}: found {len(events)} events")
        return events

    async def parse_uzexpocentre(self) -> List[Dict]:
        return await self.parse_generic("https://uzexpocentre.uz/", "uzexpocentre.uz", "Узбекистан")

    async def parse_iteca_uz(self) -> List[Dict]:
        """https://iteca.uz/ru/kalendarx-sobtij — календарь событий ITECA Uzbekistan."""
        events = []
        base_url = "https://iteca.uz"
        try:
            url = "https://iteca.uz/ru/kalendarx-sobtij"
            html, soup = await self._fetch_page_content(url)
            if not soup:
                return events

            # Каждое событие — <a href="..."> с вложенными img, time, h4, h3, p
            seen_urls = set()
            for link in soup.find_all('a', href=True):
                try:
                    # Карточка должна содержать h3 или h4 (название выставки)
                    h4 = link.find('h4')
                    h3 = link.find('h3')
                    if not h4 and not h3:
                        continue

                    title_short = self._clean_text(h4.get_text()) if h4 else ""
                    title_full = self._clean_text(h3.get_text()) if h3 else ""
                    title = title_full or title_short
                    if len(title) < 5:
                        continue

                    # URL события
                    href = link.get('href', '')
                    if not href or href.startswith('#') or href.startswith('javascript'):
                        continue
                    event_url = href if href.startswith('http') else urljoin(base_url, href)
                    if event_url in seen_urls:
                        continue
                    seen_urls.add(event_url)

                    # Дата из <time> тега
                    time_tag = link.find('time')
                    date_text = self._clean_text(time_tag.get_text()) if time_tag else ""
                    start_date, end_date = self._extract_dates_from_text(date_text)
                    if not start_date:
                        start_date, end_date = self._extract_dates_from_text(title)

                    # Место проведения из <p>
                    place_text = ""
                    city = None
                    p_tag = link.find('p')
                    if p_tag:
                        raw_place = self._clean_text(p_tag.get_text())
                        # "Место проведения: НВК "Узэкспоцентр" / Ташкент, Узбекистан"
                        place_text = re.sub(r'^Место проведения:\s*', '', raw_place, flags=re.IGNORECASE)
                        city = self._extract_city(place_text)

                    if not city:
                        city = self._extract_city(title) or "Ташкент"

                    # Описание — собрать из полного названия + место
                    description = ""
                    if title_full and title_short:
                        description = title_full
                    if place_text:
                        description = (description + ". " + place_text).strip('. ')

                    # Изображение
                    local_image_path = None
                    img_tag = link.find('img')
                    if img_tag:
                        img_src = img_tag.get('src') or img_tag.get('data-src') or ''
                        if img_src and not img_src.startswith('data:'):
                            img_url = img_src if img_src.startswith('http') else urljoin(base_url, img_src)
                            local_image_path = await self._download_and_save_image(img_url, event_url)

                    cleaned_url = self._clean_url(event_url)
                    if not cleaned_url:
                        continue

                    events.append({
                        'title': self._clean_title(title_short or title),
                        'name': title_full or title_short or title,
                        'description': self._clean_description(description)[:800],
                        'city': city,
                        'place': place_text or None,
                        'start_date': start_date,
                        'end_date': end_date,
                        'url': cleaned_url,
                        'image_url': local_image_path,
                        'source': 'iteca.uz',
                        'country': 'Узбекистан',
                        'industry': self._infer_industry(title, description),
                    })
                except Exception as e:
                    logger.debug(f"Iteca UZ item error: {e}")

        except Exception as e:
            logger.error(f"Iteca UZ error: {e}")

        logger.info(f"parse_iteca_uz: found {len(events)} events")
        return events

    async def parse_bakuexpo(self) -> List[Dict]:
        return await self.parse_generic("https://bakuexpo.center/", "bakuexpo.center", "Азербайджан")

    async def parse_iteca_az(self) -> List[Dict]:
        """https://iteca.az/ru/events — ITECA Caspian (Azerbaijan) exhibitions."""
        events = []
        base_url = "https://iteca.az"
        try:
            url = "https://iteca.az/ru/events"
            html, soup = await self._fetch_page_content(url)
            if not soup:
                return events

            seen_urls = set()
            # Карточки: div.event-item содержит <a title="...">, дату, ссылку на сайт
            for item in soup.find_all('div', class_='event-item'):
                try:
                    # Название из <a title="..."> внутри div.event-logo
                    title_link = item.find('a', title=True)
                    if not title_link:
                        continue
                    title = self._clean_text(title_link.get('title', ''))
                    if len(title) < 5:
                        continue

                    # URL — первая внешняя ссылка (сайт выставки)
                    event_url = ''
                    for a in item.find_all('a', href=True):
                        href = a.get('href', '')
                        if href.startswith('http') and 'get-the-ticket' not in href and 'reservation' not in href:
                            event_url = href
                            break
                    if not event_url or event_url in seen_urls:
                        continue
                    seen_urls.add(event_url)

                    # Дата из текста карточки
                    item_text = item.get_text()
                    start_date, end_date = self._extract_dates_from_text(item_text)

                    # Изображение
                    local_image_path = None
                    img = item.find('img')
                    if img:
                        img_src = img.get('src', '')
                        if img_src and not img_src.startswith('data:'):
                            img_url = img_src if img_src.startswith('http') else urljoin(base_url, img_src)
                            local_image_path = await self._download_and_save_image(img_url, event_url)

                    cleaned_url = self._clean_url(event_url)
                    if not cleaned_url:
                        continue

                    events.append({
                        'title': self._clean_title(title),
                        'name': title,
                        'description': self._clean_description(title)[:800],
                        'city': 'Баку',
                        'place': None,
                        'start_date': start_date,
                        'end_date': end_date,
                        'url': cleaned_url,
                        'image_url': local_image_path,
                        'source': 'iteca.az',
                        'country': 'Азербайджан',
                        'industry': self._infer_industry(title, ''),
                    })
                except Exception as e:
                    logger.debug(f"Iteca AZ item error: {e}")

        except Exception as e:
            logger.error(f"Iteca AZ error: {e}")

        logger.info(f"parse_iteca_az: found {len(events)} events")
        return events

    async def parse_expomap(self) -> List[Dict]:
        """https://expomap.ru/expo/country/{country}/ — JSON-LD structured data for CIS countries."""
        events = []
        base = "https://expomap.ru"
        seen_urls = set()
        country_slugs = {
            "Казахстан": "kazakhstan",
            "Узбекистан": "uzbekistan",
            "Азербайджан": "azerbaijan",
            "Грузия": "georgia",
            "Армения": "armenia",
            "Кыргызстан": "kyrgyzstan",
            "Таджикистан": "tajikistan",
            "Туркменистан": "turkmenistan",
        }
        for country_name, slug in country_slugs.items():
            try:
                url = f"{base}/expo/country/{slug}/"
                resp = await self.client.get(url)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, 'lxml')
                json_ld_events = self._extract_from_json_ld(soup, base)
                for ev in json_ld_events:
                    if ev.get('url') and ev['url'] not in seen_urls:
                        ev['source'] = 'expomap.ru'
                        ev['industry'] = self._infer_industry(ev.get('title', ''), ev.get('description', ''))
                        if not ev.get('country') or ev['country'] == '':
                            ev['country'] = country_name
                        if not self._contains_stop_word(ev.get('title', '') + ' ' + ev.get('description', '')):
                            events.append(ev)
                            seen_urls.add(ev['url'])
            except Exception as e:
                logger.debug(f"Expomap {slug} error: {e}")

        logger.info(f"parse_expomap: found {len(events)} events")
        return events

    async def parse_exposale_country(self, url: str, country: str) -> List[Dict]:
        return await self.parse_generic(url, url.split('/')[2] if '//' in url else 'exposale.net', country)

    async def parse_vystavki_country(self, url: str, country: str) -> List[Dict]:
        return await self.parse_generic(url, "vystavki.su", country)

    async def _safe_parse(self, coro, name: str) -> List[Dict]:
        """Безопасно выполнить парсер, возвращая пустой список при ошибке."""
        try:
            return await coro
        except Exception as e:
            logger.error(f"{name} failed: {e}")
            return []

    def _normalize_title_for_dedup(self, title: str) -> str:
        """Нормализовать заголовок для дедупликации."""
        if not title:
            return ""
        t = re.sub(r'[^\w\s]', '', title.lower())
        t = re.sub(r'\s+', ' ', t).strip()
        # Убрать год
        t = re.sub(r'\b20[2-5]\d\b', '', t).strip()
        return t

    async def parse_all(self) -> List[Dict]:
        all_events = []

        # Этап 1: Основные парсеры — параллельно через asyncio.gather
        # Удалены мёртвые сайты: qazexpo.kz (DNS), expo-centralasia.com (DNS),
        # bakuexpo.center (DNS), atakent-expo.kz (SSL expired), worldexpo.pro (403)
        main_tasks = [
            self._safe_parse(self.parse_iteca(), "parse_iteca"),
            self._safe_parse(self.parse_astanahub(), "parse_astanahub"),
            self._safe_parse(self.parse_exposale_all(), "parse_exposale_all"),
            self._safe_parse(self.parse_vystavki_main(), "parse_vystavki_main"),
            self._safe_parse(self.parse_expomap(), "parse_expomap"),
        ]

        results = await asyncio.gather(*main_tasks)
        for result in results:
            all_events.extend(result)

        # Этап 2: CIS парсеры — параллельно
        cis_tasks = [
            self._safe_parse(self.parse_uzexpocentre(), "parse_uzexpocentre"),
            self._safe_parse(self.parse_iteca_uz(), "parse_iteca_uz"),
            self._safe_parse(self.parse_iteca_az(), "parse_iteca_az"),
        ]

        # Дополнительные country-specific парсеры
        for country in ("Узбекистан", "Азербайджан"):
            for url in COUNTRY_SOURCES.get(country, []):
                if any(skip in url for skip in ["uzexpocentre.uz", "iteca.uz", "bakuexpo.center", "iteca.az"]):
                    continue
                if "exposale" in url:
                    cis_tasks.append(self._safe_parse(self.parse_exposale_country(url, country), f"exposale_{country}"))
                elif "vystavki.su" in url:
                    cis_tasks.append(self._safe_parse(self.parse_vystavki_country(url, country), f"vystavki_{country}"))
                else:
                    source_name = url.split('/')[2] if '//' in url else url
                    cis_tasks.append(self._safe_parse(self.parse_generic(url, source_name, country), f"generic_{source_name}"))

        # Другие страны CIS
        other_countries = ["Таджикистан", "Туркменистан", "Грузия", "Армения", "Кыргызстан"]
        for country in other_countries:
            for url in COUNTRY_SOURCES.get(country, []):
                if "exposale" in url:
                    cis_tasks.append(self._safe_parse(self.parse_exposale_country(url, country), f"exposale_{country}"))
                elif "vystavki.su" in url:
                    cis_tasks.append(self._safe_parse(self.parse_vystavki_country(url, country), f"vystavki_{country}"))
                else:
                    source_name = url.split('/')[2] if '//' in url else url
                    cis_tasks.append(self._safe_parse(self.parse_generic(url, source_name, country), f"generic_{source_name}"))

        cis_results = await asyncio.gather(*cis_tasks)
        for result in cis_results:
            all_events.extend(result)

        # Дедупликация 1: по URL
        unique_by_url = {}
        for e in all_events:
            url = e.get('url', '')
            if url and url not in unique_by_url:
                unique_by_url[url] = e

        # Дедупликация 2: по заголовку + дате (нормализованные)
        unique_by_title_date = {}
        for event in unique_by_url.values():
            title_norm = self._normalize_title_for_dedup(event.get('title', ''))
            date_key = ''
            if event.get('start_date'):
                date_key = event['start_date'].strftime('%Y-%m')
            dedup_key = f"{title_norm}|{date_key}"
            if dedup_key not in unique_by_title_date:
                unique_by_title_date[dedup_key] = event
            else:
                # Предпочесть событие с более полными данными
                existing = unique_by_title_date[dedup_key]
                if (event.get('description', '') and len(event.get('description', '')) > len(existing.get('description', ''))):
                    unique_by_title_date[dedup_key] = event

        # Дедупликация 3: по схожести описания (>=75%)
        filtered_events = []
        for event in unique_by_title_date.values():
            event_description = event.get('description', '')
            if not event_description or len(event_description.strip()) < 20:
                filtered_events.append(event)
                continue

            is_duplicate = False
            for existing_event in filtered_events:
                existing_description = existing_event.get('description', '')
                if existing_description and len(existing_description.strip()) >= 20:
                    similarity = self._calculate_text_similarity(event_description, existing_description)
                    if similarity >= 0.75:
                        logger.debug(
                            f"Parser: Skipping duplicate (similarity {similarity:.2%}): "
                            f"'{event.get('title', '')[:50]}' vs '{existing_event.get('title', '')[:50]}'"
                        )
                        is_duplicate = True
                        break

            if not is_duplicate:
                filtered_events.append(event)

        logger.info(f"Parser: Filtered {len(all_events)} -> {len(filtered_events)} unique events (removed {len(all_events) - len(filtered_events)} duplicates)")

        # Фильтрация мусорных записей — навигационные ссылки, новостные статьи и т.д.
        JUNK_PATTERNS = [
            r'^\d+\s+exhibitions?$',                    # "20 exhibitions"
            r'^Международные выставки\b',               # navigation links
            r'^Календарь\b',                             # "Календарь выставок"
            r'^Мероприятия$',                            # generic "Events" page title
            r'^\d{1,2}\s+\w+\s+20\d{2}\s+',            # news articles starting with date "26 September 2025 ..."
        ]
        junk_re = re.compile('|'.join(JUNK_PATTERNS), re.IGNORECASE)
        pre_junk = len(filtered_events)
        filtered_events = [e for e in filtered_events if not junk_re.search(e.get('title', ''))]
        if pre_junk != len(filtered_events):
            logger.info(f"Parser: Junk filter {pre_junk} -> {len(filtered_events)} (removed {pre_junk - len(filtered_events)} junk entries)")

        # Фильтрация по странам — оставляем только целевые (из config.COUNTRIES)
        allowed_countries = set(COUNTRIES)
        country_filtered = []
        for event in filtered_events:
            country = event.get('country', '')
            # Перепроверить страну по тексту title/description (часто country='Казахстан' а title='... Москва, Россия')
            full_text = f"{event.get('title', '')} {event.get('description', '')} {event.get('city', '')}"
            inferred = self._infer_country_from_text(full_text)
            if inferred:
                event['country'] = inferred
                country = inferred

            if country in allowed_countries:
                country_filtered.append(event)
            else:
                logger.debug(f"Parser: Skipping event from '{country}': {event.get('title', '')[:60]}")

        logger.info(f"Parser: Country filter {len(filtered_events)} -> {len(country_filtered)} (removed {len(filtered_events) - len(country_filtered)} from non-target countries)")

        # NOTE: AI enrichment (Groq Llama) happens in scheduler.py run_parsing_cycle(),
        # not here, to avoid double API calls.

        # Set "NO IMAGE" for events without images
        for event in country_filtered:
            if not event.get('image_url') or str(event.get('image_url', '')).strip() == '':
                event['image_url'] = 'NO IMAGE'

        return country_filtered
