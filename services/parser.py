import re
import logging
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin
from config import STOP_WORDS, B2B_KEYWORDS, CITY_VARIANTS

logger = logging.getLogger(__name__)

class EventParser:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=self.headers)

    async def close(self):
        await self.client.aclose()

    def _clean_text(self, text: str) -> str:
        if not text: return ""
        return re.sub(r'\s+', ' ', text).strip()

    def _is_relevant(self, title: str, description: str) -> bool:
        full_text = (title + " " + description).lower()
        if any(w in full_text for w in STOP_WORDS):
            return False
        if any(w in full_text for w in B2B_KEYWORDS):
            return True
        return False # По умолчанию False, если нет явных признаков B2B

    def _extract_city(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for city, variants in CITY_VARIANTS.items():
            if any(v in text_lower for v in variants):
                return city
        return None

    def _extract_date_ru(self, text: str) -> Optional[datetime]:
        months = {
            'январ': 1, 'феврал': 2, 'март': 3, 'апрел': 4, 'май': 5, 'июн': 6,
            'июл': 7, 'август': 8, 'сентябр': 9, 'октябр': 10, 'ноябр': 11, 'декабр': 12
        }
        text_lower = text.lower()
        
        # Паттерн: 10 - 12 апрель 2026
        # Ищем год
        year_match = re.search(r'202[4-9]', text_lower)
        year = int(year_match.group(0)) if year_match else datetime.now().year
        
        for m_name, m_num in months.items():
            if m_name in text_lower:
                # Ищем день перед месяцем
                day_match = re.search(r'(\d{1,2})\s*[—\-]?\s*\d{0,2}\s*' + m_name, text_lower)
                if day_match:
                    try:
                        day = int(day_match.group(1))
                        return datetime(year, m_num, day)
                    except: pass
        return None

    # --- Парсеры для конкретных сайтов ---

    async def parse_iteca(self) -> List[Dict]:
        """Парсинг Iteca.events (по структуре из ТЗ)"""
        events = []
        try:
            url = "https://iteca.events/ru/exhibitions"
            resp = await self.client.get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            
            # Селектор из ТЗ: class="p-5 flex flex-col"
            cards = soup.find_all('div', class_=re.compile(r'p-5 flex flex-col'))
            
            for card in cards:
                try:
                    title_tag = card.find('h4')
                    if not title_tag: continue
                    title = self._clean_text(title_tag.text)
                    
                    desc_tag = card.find('p')
                    description = self._clean_text(desc_tag.text) if desc_tag else ""
                    
                    # Дата и место обычно в span
                    spans = card.find_all('span')
                    raw_date = spans[0].text if len(spans) > 0 else ""
                    raw_location = spans[1].text if len(spans) > 1 else ""
                    
                    city = self._extract_city(raw_location)
                    date = self._extract_date_ru(raw_date)
                    
                    # Ссылка
                    link_parent = card.find_parent('a')
                    event_url = urljoin(url, link_parent['href']) if link_parent else url
                    
                    # Изображение
                    img_tag = card.find_parent('div').find('img') if card.find_parent('div') else None
                    image_url = urljoin(url, img_tag['src']) if img_tag else None

                    if self._is_relevant(title, description):
                        events.append({
                            'title': title, 'description': description, 'city': city,
                            'place': raw_location, 'start_date': date, 'url': event_url,
                            'image_url': image_url, 'source': 'iteca.events'
                        })
                except Exception as e:
                    logger.error(f"Error extracting iteca item: {e}")
        except Exception as e:
            logger.error(f"Iteca global error: {e}")
        return events

    async def parse_digitalbusiness(self) -> List[Dict]:
        """Парсинг DigitalBusiness.kz (структура из ТЗ: ul class='article-list')"""
        events = []
        try:
            url = "https://digitalbusiness.kz/calendar/"
            resp = await self.client.get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            
            items = soup.select('ul.article-list li div')
            
            for item in items:
                try:
                    title_tag = item.find('h4').find('a')
                    if not title_tag: continue
                    title = self._clean_text(title_tag.text)
                    event_url = urljoin(url, title_tag['href'])
                    
                    desc_tag = item.find('p')
                    description = self._clean_text(desc_tag.text) if desc_tag else ""
                    
                    date_tag = item.find('time')
                    date_str = date_tag.text if date_tag else ""
                    date = self._extract_date_ru(date_str)
                    
                    # Город часто в заголовке: "IT-беш. Астана"
                    city = self._extract_city(title)
                    
                    # Попытка найти картинку в родительском li
                    li = item.find_parent('li')
                    img_tag = li.find('img') if li else None
                    image_url = urljoin(url, img_tag['src']) if img_tag else None

                    if self._is_relevant(title, description):
                        events.append({
                            'title': title, 'description': description, 'city': city,
                            'place': None, 'start_date': date, 'url': event_url,
                            'image_url': image_url, 'source': 'digitalbusiness.kz'
                        })
                except Exception as e: continue
        except Exception as e:
            logger.error(f"DigitalBusiness error: {e}")
        return events

    async def parse_worldexpo(self) -> List[Dict]:
        """Парсинг WorldExpo.pro (структура из ТЗ: div class='item-content')"""
        events = []
        try:
            url = "https://worldexpo.pro/country/kazahstan"
            resp = await self.client.get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            
            items = soup.find_all('div', class_='item-content')
            for item in items:
                try:
                    title_tag = item.find('h4').find('a')
                    title = self._clean_text(title_tag.text)
                    event_url = urljoin(url, title_tag['href'])
                    
                    date_span = item.find('span', class_='item-content-date')
                    date = self._extract_date_ru(date_span.text) if date_span else None
                    
                    loc_span = item.find('span', class_='search-location')
                    city = self._extract_city(loc_span.text) if loc_span else None
                    
                    desc_p = item.find_all('p')[-1] # Обычно последнее p это описание
                    description = self._clean_text(desc_p.text) if desc_p else ""

                    if self._is_relevant(title, description):
                        events.append({
                            'title': title, 'description': description, 'city': city,
                            'place': loc_span.text if loc_span else None,
                            'start_date': date, 'url': event_url,
                            'image_url': None, 'source': 'worldexpo.pro'
                        })
                except Exception as e: continue
        except Exception as e:
             logger.error(f"WorldExpo error: {e}")
        return events

    async def parse_generic(self, url: str) -> List[Dict]:
        """Универсальный fallback парсер"""
        events = []
        try:
            resp = await self.client.get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            # Простой поиск ссылок с ключевыми словами в тексте
            for a in soup.find_all('a', href=True):
                text = self._clean_text(a.text)
                if len(text) > 10 and self._is_relevant(text, ""):
                    event_url = urljoin(url, a['href'])
                    events.append({
                        'title': text, 'description': "", 
                        'city': self._extract_city(text),
                        'place': None, 'start_date': self._extract_date_ru(text),
                        'url': event_url, 'image_url': None, 'source': url
                    })
        except Exception as e: pass
        return events

    async def parse_all(self) -> List[Dict]:
        all_events = []
        # Запуск специализированных парсеров
        all_events.extend(await self.parse_iteca())
        all_events.extend(await self.parse_digitalbusiness())
        all_events.extend(await self.parse_worldexpo())
        
        # Запуск дженерика для остальных (пример)
        # all_events.extend(await self.parse_generic("https://profit.kz/events/"))
        
        # Дедупликация по URL
        unique = {e['url']: e for e in all_events}.values()
        return list(unique)