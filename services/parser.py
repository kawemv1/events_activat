import re
import logging
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin
from config import STOP_WORDS, B2B_KEYWORDS, CITY_VARIANTS, INDUSTRIES

logger = logging.getLogger(__name__)

# Маппинг ключевых слов -> индустрия для автоопределения
INDUSTRY_KEYWORDS = {
    "IT/Digital": ["it", "digital", "цифр", "технолог", "software", "стартап"],
    "Агросектор": ["агро", "сельск", "ферм", "food", "агропром"],
    "Медицина": ["медицин", "здоровь", "клиник", "kihe", "pharma"],
    "Строительство": ["строительств", "build", "интерьер", "недвижим"],
    "Энергетика": ["энерг", "oil", "gas", "нефть", "уголь"],
    "Ритейл/FMCG": ["ритейл", "fmcg", "розниц", "retail", "товар"],
    "Нефть и Газ": ["нефть", "газ", "oil", "gas", "недропольз"],
    "Транспорт": ["транспорт", "логистик", "авто"],
    "Mining": ["mining", "горн", "металл", "amm", "kioge"],
}


class EventParser:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=self.headers)

    async def close(self):
        await self.client.aclose()

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip()

    def _is_relevant(self, title: str, description: str) -> bool:
        full_text = (title + " " + (description or "")).lower()
        if any(w in full_text for w in STOP_WORDS):
            return False
        if any(w in full_text for w in B2B_KEYWORDS):
            return True
        return False

    def _extract_city(self, text: str) -> Optional[str]:
        if not text:
            return None
        text_lower = text.lower()
        for city, variants in CITY_VARIANTS.items():
            if any(v in text_lower for v in variants):
                return city
        return None

    def _infer_industry(self, title: str, description: str) -> Optional[str]:
        full = (title + " " + (description or "")).lower()
        for industry, keywords in INDUSTRY_KEYWORDS.items():
            if any(kw in full for kw in keywords):
                return industry
        return None

    def _extract_date_ru(self, text: str) -> Optional[datetime]:
        months = {
            'январ': 1, 'феврал': 2, 'март': 3, 'апрел': 4, 'май': 5, 'июн': 6,
            'июл': 7, 'август': 8, 'сентябр': 9, 'октябр': 10, 'ноябр': 11, 'декабр': 12
        }
        if not text:
            return None
        text_lower = text.lower()
        year_match = re.search(r'20[2-5]\d', text_lower)
        year = int(year_match.group(0)) if year_match else datetime.now().year

        for m_name, m_num in months.items():
            if m_name in text_lower:
                day_match = re.search(r'(\d{1,2})\s*[—\-]?\s*\d{0,2}\s*' + m_name, text_lower)
                if day_match:
                    try:
                        day = int(day_match.group(1))
                        return datetime(year, m_num, day)
                    except (ValueError, IndexError):
                        pass
        return None

    # --- Парсеры для каждого источника ---

    async def parse_iteca(self) -> List[Dict]:
        """https://iteca.events/ru/"""
        events = []
        try:
            url = "https://iteca.events/ru/exhibitions"
            resp = await self.client.get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            cards = soup.find_all('div', class_=re.compile(r'p-5 flex flex-col|flex flex-col'))
            if not cards:
                cards = soup.find_all('article') or soup.select('a[href*="/ru/"]')
            for card in cards[:50]:
                try:
                    title_tag = card.find(['h3', 'h4', 'h2']) or card.find('a')
                    if not title_tag:
                        continue
                    title = self._clean_text(title_tag.get_text())
                    if len(title) < 5:
                        continue
                    link = card.find('a', href=True)
                    event_url = urljoin(url, link['href']) if link else url
                    desc_tag = card.find('p')
                    description = self._clean_text(desc_tag.get_text()) if desc_tag else ""
                    spans = card.find_all('span')
                    raw_date = spans[0].get_text() if spans else ""
                    raw_location = spans[1].get_text() if len(spans) > 1 else ""
                    city = self._extract_city(raw_location or title)
                    date = self._extract_date_ru(raw_date or title)
                    img = card.find('img') or (card.find_parent() and card.find_parent().find('img'))
                    image_url = urljoin(url, img['src']) if img and img.get('src') else None
                    if self._is_relevant(title, description):
                        events.append({
                            'title': title, 'description': description[:500], 'city': city,
                            'place': self._clean_text(raw_location) or None, 'start_date': date,
                            'url': event_url, 'image_url': image_url, 'source': 'iteca.events',
                            'industry': self._infer_industry(title, description)
                        })
                except Exception as e:
                    logger.debug(f"Iteca item error: {e}")
        except Exception as e:
            logger.error(f"Iteca error: {e}")
        return events

    async def parse_atakent(self) -> List[Dict]:
        """https://atakent-expo.kz/"""
        events = []
        try:
            url = "https://atakent-expo.kz/"
            resp = await self.client.get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            for item in soup.select('a[href*="event"], .event-item, .exhibition-item, article, .card'):
                try:
                    title_tag = item.find(['h2', 'h3', 'h4']) or item
                    title = self._clean_text(title_tag.get_text())
                    if len(title) < 5:
                        continue
                    link = item.find('a', href=True) or (item if item.name == 'a' and item.get('href') else None)
                    event_url = urljoin(url, link['href']) if link and link.get('href') else url
                    desc = item.find('p')
                    description = self._clean_text(desc.get_text()) if desc else ""
                    if self._is_relevant(title, description):
                        events.append({
                            'title': title, 'description': description[:500],
                            'city': self._extract_city(title) or "Алматы",
                            'place': "Атакент", 'start_date': self._extract_date_ru(title + " " + description),
                            'url': event_url, 'image_url': None, 'source': 'atakent-expo.kz',
                            'industry': self._infer_industry(title, description)
                        })
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Atakent error: {e}")
        return events

    async def parse_qazexpo(self) -> List[Dict]:
        """http://www.qazexpo.kz/"""
        events = []
        try:
            url = "http://www.qazexpo.kz/"
            resp = await self.client.get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            for item in soup.find_all(['a', 'div', 'article'], class_=re.compile(r'event|exhibition|card', re.I)):
                try:
                    title = self._clean_text(item.get_text())
                    if len(title) < 10:
                        continue
                    link = item if item.name == 'a' and item.get('href') else item.find('a', href=True)
                    event_url = urljoin(url, link['href']) if link and link.get('href') else url
                    if self._is_relevant(title, ""):
                        events.append({
                            'title': title[:200], 'description': "",
                            'city': self._extract_city(title) or "Астана",
                            'place': "QazExpo", 'start_date': self._extract_date_ru(title),
                            'url': event_url, 'image_url': None, 'source': 'qazexpo.kz',
                            'industry': self._infer_industry(title, "")
                        })
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"QazExpo error: {e}")
        return events

    async def parse_expo_centralasia(self) -> List[Dict]:
        """https://expo-centralasia.com/"""
        events = []
        try:
            url = "https://expo-centralasia.com/"
            resp = await self.client.get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            for item in soup.find_all(['a', 'article', 'div'], class_=re.compile(r'event|expo|card', re.I)):
                try:
                    title_tag = item.find(['h2', 'h3', 'h4']) or item
                    title = self._clean_text(title_tag.get_text())
                    if len(title) < 5:
                        continue
                    link = item.find('a', href=True) or (item if item.name == 'a' else None)
                    event_url = urljoin(url, link['href']) if link and link.get('href') else url
                    desc = item.find('p')
                    description = self._clean_text(desc.get_text()) if desc else ""
                    if self._is_relevant(title, description):
                        events.append({
                            'title': title, 'description': description[:500],
                            'city': self._extract_city(title + " " + description),
                            'place': None, 'start_date': self._extract_date_ru(title + " " + description),
                            'url': event_url, 'image_url': None, 'source': 'expo-centralasia.com',
                            'industry': self._infer_industry(title, description)
                        })
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Expo CentralAsia error: {e}")
        return events

    async def parse_astanahub(self) -> List[Dict]:
        """https://astanahub.com/ru/events"""
        events = []
        try:
            url = "https://astanahub.com/ru/events"
            resp = await self.client.get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            for item in soup.select('.event, .events-item, article, [class*="event"]'):
                try:
                    title_tag = item.find(['h2', 'h3', 'h4']) or item.find('a')
                    if not title_tag:
                        continue
                    title = self._clean_text(title_tag.get_text())
                    if len(title) < 5:
                        continue
                    link = item.find('a', href=True)
                    event_url = urljoin(url, link['href']) if link else url
                    desc = item.find('p')
                    description = self._clean_text(desc.get_text()) if desc else ""
                    if self._is_relevant(title, description):
                        events.append({
                            'title': title, 'description': description[:500],
                            'city': self._extract_city(title) or "Астана",
                            'place': None, 'start_date': self._extract_date_ru(title + " " + description),
                            'url': event_url, 'image_url': None, 'source': 'astanahub.com',
                            'industry': self._infer_industry(title, description)
                        })
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"AstanaHub error: {e}")
        return events

    async def parse_digitalbusiness(self) -> List[Dict]:
        """https://digitalbusiness.kz/"""
        events = []
        try:
            url = "https://digitalbusiness.kz/calendar/"
            resp = await self.client.get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            items = soup.select('ul.article-list li, .event-item, .calendar-item, article')
            if not items:
                items = soup.find_all('a', href=re.compile(r'/event|/calendar|/news'))
            for item in items:
                try:
                    title_tag = item.find(['h4', 'h3', 'h2']).find('a') if item.find(['h4', 'h3', 'h2']) else item.find('a')
                    if not title_tag:
                        title_tag = item
                    title = self._clean_text(title_tag.get_text())
                    if len(title) < 5:
                        continue
                    link = title_tag if title_tag.name == 'a' else title_tag.find('a', href=True)
                    event_url = urljoin(url, link['href']) if link and link.get('href') else url
                    desc = item.find('p')
                    description = self._clean_text(desc.get_text()) if desc else ""
                    date_tag = item.find('time')
                    date_str = date_tag.get_text() if date_tag else ""
                    if self._is_relevant(title, description):
                        events.append({
                            'title': title, 'description': description[:500],
                            'city': self._extract_city(title),
                            'place': None, 'start_date': self._extract_date_ru(date_str or title),
                            'url': event_url, 'image_url': None, 'source': 'digitalbusiness.kz',
                            'industry': 'IT/Digital'
                        })
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"DigitalBusiness error: {e}")
        return events

    async def parse_profit(self) -> List[Dict]:
        """https://profit.kz/events/"""
        events = []
        try:
            url = "https://profit.kz/events/"
            resp = await self.client.get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            for item in soup.select('.event, .events-list li, article, [class*="event"]'):
                try:
                    title_tag = item.find(['h2', 'h3', 'h4']) or item.find('a')
                    if not title_tag:
                        continue
                    title = self._clean_text(title_tag.get_text())
                    if len(title) < 5:
                        continue
                    link = item.find('a', href=True)
                    event_url = urljoin(url, link['href']) if link else url
                    desc = item.find('p')
                    description = self._clean_text(desc.get_text()) if desc else ""
                    if self._is_relevant(title, description):
                        events.append({
                            'title': title, 'description': description[:500],
                            'city': self._extract_city(title + " " + description),
                            'place': None, 'start_date': self._extract_date_ru(title + " " + description),
                            'url': event_url, 'image_url': None, 'source': 'profit.kz',
                            'industry': self._infer_industry(title, description)
                        })
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Profit error: {e}")
        return events

    async def parse_worldexpo(self) -> List[Dict]:
        """https://worldexpo.pro/vystavki/kazahstan"""
        events = []
        try:
            url = "https://worldexpo.pro/vystavki/kazahstan"
            resp = await self.client.get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            items = soup.find_all('div', class_='item-content') or soup.select('.exhibition, .event-item')
            if not items:
                items = soup.find_all('a', href=re.compile(r'/vystavk|/exhibition'))
            for item in items:
                try:
                    title_tag = item.find(['h4', 'h3', 'h2'])
                    if title_tag:
                        link = title_tag.find('a')
                        title = self._clean_text((link or title_tag).get_text())
                        event_url = urljoin(url, link['href']) if link and link.get('href') else url
                    else:
                        title = self._clean_text(item.get_text())
                        link = item.find('a', href=True)
                        event_url = urljoin(url, link['href']) if link else url
                    if len(title) < 5:
                        continue
                    date_span = item.find('span', class_=re.compile(r'date|item-content-date'))
                    loc_span = item.find('span', class_=re.compile(r'location|search-location'))
                    desc = item.find('p')
                    description = self._clean_text(desc.get_text()) if desc else ""
                    if self._is_relevant(title, description):
                        events.append({
                            'title': title, 'description': description[:500],
                            'city': self._extract_city(loc_span.get_text() if loc_span else title),
                            'place': self._clean_text(loc_span.get_text()) if loc_span else None,
                            'start_date': self._extract_date_ru(date_span.get_text() if date_span else title),
                            'url': event_url, 'image_url': None, 'source': 'worldexpo.pro',
                            'industry': self._infer_industry(title, description)
                        })
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"WorldExpo error: {e}")
        return events

    async def parse_exposale(self) -> List[Dict]:
        """https://exposale.net/ru/country/kazahstan"""
        events = []
        try:
            url = "https://exposale.net/ru/country/kazahstan"
            resp = await self.client.get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            for item in soup.select('.exhibition, .event, .item, article, [class*="expo"]'):
                try:
                    title_tag = item.find(['h2', 'h3', 'h4']) or item.find('a')
                    if not title_tag:
                        continue
                    title = self._clean_text(title_tag.get_text())
                    if len(title) < 5:
                        continue
                    link = item.find('a', href=True)
                    event_url = urljoin(url, link['href']) if link else url
                    desc = item.find('p')
                    description = self._clean_text(desc.get_text()) if desc else ""
                    if self._is_relevant(title, description):
                        events.append({
                            'title': title, 'description': description[:500],
                            'city': self._extract_city(title + " " + description),
                            'place': None, 'start_date': self._extract_date_ru(title + " " + description),
                            'url': event_url, 'image_url': None, 'source': 'exposale.net',
                            'industry': self._infer_industry(title, description)
                        })
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Exposale error: {e}")
        return events

    async def parse_vystavki_su(self) -> List[Dict]:
        """https://vystavki.su/kazakhstan/"""
        events = []
        try:
            url = "https://vystavki.su/kazakhstan/"
            resp = await self.client.get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            for item in soup.select('.event, .exhibition, .post, article, .entry'):
                try:
                    title_tag = item.find(['h2', 'h3', 'h4']) or item.find('a')
                    if not title_tag:
                        continue
                    title = self._clean_text(title_tag.get_text())
                    if len(title) < 5:
                        continue
                    link = item.find('a', href=True)
                    event_url = urljoin(url, link['href']) if link else url
                    desc = item.find('p')
                    description = self._clean_text(desc.get_text()) if desc else ""
                    if self._is_relevant(title, description):
                        events.append({
                            'title': title, 'description': description[:500],
                            'city': self._extract_city(title + " " + description),
                            'place': None, 'start_date': self._extract_date_ru(title + " " + description),
                            'url': event_url, 'image_url': None, 'source': 'vystavki.su',
                            'industry': self._infer_industry(title, description)
                        })
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Vystavki.su error: {e}")
        return events

    async def parse_generic(self, url: str, source_name: str) -> List[Dict]:
        """Универсальный fallback"""
        events = []
        try:
            resp = await self.client.get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            for a in soup.find_all('a', href=True):
                text = self._clean_text(a.get_text())
                if len(text) > 15 and self._is_relevant(text, ""):
                    event_url = urljoin(url, a['href'])
                    events.append({
                        'title': text[:200], 'description': "",
                        'city': self._extract_city(text),
                        'place': None, 'start_date': self._extract_date_ru(text),
                        'url': event_url, 'image_url': None, 'source': source_name,
                        'industry': self._infer_industry(text, "")
                    })
        except Exception as e:
            logger.error(f"Generic {source_name} error: {e}")
        return events

    async def parse_all(self) -> List[Dict]:
        all_events = []
        parsers = [
            self.parse_iteca,
            self.parse_atakent,
            self.parse_qazexpo,
            self.parse_expo_centralasia,
            self.parse_astanahub,
            self.parse_digitalbusiness,
            self.parse_profit,
            self.parse_worldexpo,
            self.parse_exposale,
            self.parse_vystavki_su,
        ]
        for parse_fn in parsers:
            try:
                events = await parse_fn()
                all_events.extend(events)
                logger.info(f"{parse_fn.__name__}: found {len(events)} events")
            except Exception as e:
                logger.error(f"{parse_fn.__name__} failed: {e}")
        unique = {e['url']: e for e in all_events}
        return list(unique.values())
