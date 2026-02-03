import re
import httpx
from bs4 import BeautifulSoup
from typing import List, Optional, Dict
from datetime import datetime
from config import STOP_WORDS, B2B_KEYWORDS, PARSING_SOURCES
import logging

logger = logging.getLogger(__name__)


class EventParser:
    """Парсер для извлечения информации о выставках с различных сайтов"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def is_b2b_event(self, text: str) -> bool:
        """Проверка, является ли событие B2B"""
        text_lower = text.lower()

        # Проверяем наличие стоп-слов
        for stop_word in STOP_WORDS:
            if stop_word.lower() in text_lower:
                return False

        # Проверяем наличие B2B ключевых слов
        for keyword in B2B_KEYWORDS:
            if keyword.lower() in text_lower:
                return True

        return False

    def extract_date(self, text: str) -> Optional[datetime]:
        """Извлечение даты из текста"""
        # Паттерны для дат
        patterns = [
            r'(\d{1,2})[./-](\d{1,2})[./-](\d{4})',  # DD.MM.YYYY
            r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})',  # YYYY.MM.DD
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if len(match.group(1)) == 4:  # YYYY.MM.DD
                        year, month, day = match.groups()
                    else:  # DD.MM.YYYY
                        day, month, year = match.groups()
                    return datetime(int(year), int(month), int(day))
                except (ValueError, IndexError):
                    continue

        return None

    def extract_city(self, text: str) -> Optional[str]:
        """Извлечение города из текста"""
        from config import CITIES

        text_lower = text.lower()
        for city in CITIES:
            if city.lower() in text_lower:
                return city
        return None

    async def parse_iteca_events(self) -> List[Dict]:
        """Парсинг iteca.events"""
        events = []
        try:
            url = "https://iteca.events"
            response = await self.client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            # Ищем карточки событий (структура может отличаться)
            event_cards = soup.find_all(['article', 'div'], class_=re.compile(r'event|exhibition|card', re.I))

            for card in event_cards[:10]:  # Ограничиваем количество
                title_elem = card.find(['h1', 'h2', 'h3', 'a'], class_=re.compile(r'title|name', re.I))
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                if not self.is_b2b_event(title):
                    continue

                # Извлекаем описание
                desc_elem = card.find(['p', 'div'], class_=re.compile(r'description|text|content', re.I))
                description = desc_elem.get_text(strip=True) if desc_elem else ""

                # Извлекаем ссылку
                link_elem = card.find('a', href=True)
                url_event = link_elem['href'] if link_elem else url
                if not url_event.startswith('http'):
                    url_event = f"https://iteca.events{url_event}"

                # Извлекаем дату
                date_text = card.get_text()
                start_date = self.extract_date(date_text)

                # Извлекаем город
                city = self.extract_city(date_text + " " + description)

                events.append({
                    'title': title,
                    'description': description[:300] if description else "",
                    'city': city,
                    'start_date': start_date,
                    'end_date': None,
                    'url': url_event,
                    'source': 'iteca.events',
                })
        except Exception as e:
            logger.error(f"Ошибка парсинга iteca.events: {e}")

        return events

    async def parse_generic_site(self, url: str) -> List[Dict]:
        """Универсальный парсер для сайтов с похожей структурой"""
        events = []
        try:
            response = await self.client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Ищем все ссылки и заголовки, которые могут быть событиями
            links = soup.find_all('a', href=True)
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])

            seen_titles = set()

            for elem in links + headings:
                text = elem.get_text(strip=True)
                if not text or len(text) < 10:
                    continue

                if not self.is_b2b_event(text):
                    continue

                if text.lower() in seen_titles:
                    continue
                seen_titles.add(text.lower())

                # Извлекаем ссылку
                if elem.name == 'a':
                    url_event = elem['href']
                else:
                    parent_link = elem.find_parent('a', href=True)
                    url_event = parent_link['href'] if parent_link else url
                    if not url_event.startswith('http'):
                        url_event = f"{url}{url_event}"

                # Ищем описание рядом
                parent = elem.find_parent(['div', 'article', 'section'])
                description = ""
                if parent:
                    desc_elem = parent.find(['p', 'div'], class_=re.compile(r'description|text|content', re.I))
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)[:300]

                # Извлекаем дату и город
                context_text = parent.get_text() if parent else text
                start_date = self.extract_date(context_text)
                city = self.extract_city(context_text)

                events.append({
                    'title': text,
                    'description': description,
                    'city': city,
                    'start_date': start_date,
                    'end_date': None,
                    'url': url_event,
                    'source': url,
                })

                if len(events) >= 10:  # Ограничиваем количество
                    break

        except Exception as e:
            logger.error(f"Ошибка парсинга {url}: {e}")

        return events

    async def parse_all_sources(self) -> List[Dict]:
        """Парсинг всех источников"""
        all_events = []

        # Специальный парсер для iteca.events
        if "iteca.events" in PARSING_SOURCES[0]:
            events = await self.parse_iteca_events()
            all_events.extend(events)

        # Универсальный парсер для остальных
        for source in PARSING_SOURCES[1:]:
            if "google.com" in source:
                # Пропускаем Google поиск, так как это не прямой источник
                continue
            events = await self.parse_generic_site(source)
            all_events.extend(events)

        # Удаляем дубликаты по URL
        seen_urls = set()
        unique_events = []
        for event in all_events:
            if event['url'] not in seen_urls:
                seen_urls.add(event['url'])
                unique_events.append(event)

        return unique_events

    async def close(self):
        """Закрыть клиент"""
        await self.client.aclose()
