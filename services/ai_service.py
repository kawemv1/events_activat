"""
AI-powered event extraction using Groq API with Llama-3.1-8b-instant.
Extracts structured fields: name, title, short_description (100 words), place, date.
"""
import json
import logging
import os
from typing import Optional

from groq import AsyncGroq

logger = logging.getLogger(__name__)

MAX_DESC_WORDS = 100
FALLBACK_DESC_LEN = 500

GROQ_MODEL = "llama-3.1-8b-instant"

_client: Optional[AsyncGroq] = None


def _get_client() -> Optional[AsyncGroq]:
    """Lazy-init Groq client. Returns None if API key is missing."""
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not set — AI enrichment disabled, using fallback")
        return None
    _client = AsyncGroq(api_key=api_key)
    return _client


SYSTEM_PROMPT = """\
Ты — профессиональный редактор B2B мероприятий и аналитик данных. \
Твоя задача — обработать сырые данные о бизнес-мероприятии (выставка, форум, конференция) \
и вернуть структурированный результат.

СТРОГИЕ ПРАВИЛА:
1. Ответ — ТОЛЬКО валидный JSON-объект. Никакого текста до или после JSON.
2. Не выдумывай факты. Если данных нет в тексте — оставь поле пустой строкой "".
3. Если исходный текст на английском или другом языке — переведи short_description на русский.

ФОРМАТ JSON:
{
  "title": "Краткий кликабельный заголовок (максимум 10 слов). Профессиональный тон, без кликбейта.",
  "short_description": "Выжимка на русском языке, до 100 слов. Фокус: суть мероприятия, ключевые темы, B2B ценность (нетворкинг, экспоненты, деловая программа). Упомяни спикеров или организаторов, если указаны.",
  "place": "Точное место проведения (название выставочного центра, адрес), если явно указано. Иначе пустая строка.",
  "date": "Дата или период проведения, если явно указаны. Формат: '15-17 марта 2026'. Иначе пустая строка."
}"""


def _build_fallback(raw_title: str, raw_desc: str) -> dict:
    """Build a fallback result from raw data without AI."""
    desc = (raw_desc or "")[:FALLBACK_DESC_LEN]
    words = desc.split()[:MAX_DESC_WORDS]
    short_desc = " ".join(words)
    return {
        "name": (raw_title or "")[:200],
        "title": (raw_title or "")[:200],
        "short_description": short_desc,
        "place": "",
        "date": "",
    }


async def extract_event_structured(
    raw_title: str,
    raw_desc: str,
    raw_url: str = "",
    relevant_keywords: Optional[list] = None,
) -> dict:
    """
    Extract structured event data using Groq Llama-3.1-8b-instant.

    Falls back to local truncation if:
    - GROQ_API_KEY is not set
    - API returns an error (rate limit, network, etc.)
    - Response is not valid JSON
    """
    fallback = _build_fallback(raw_title, raw_desc)

    client = _get_client()
    if client is None:
        return fallback

    user_message = (
        f"Заголовок: {raw_title or '(нет)'}\n\n"
        f"Описание:\n{(raw_desc or '(нет)')[:3000]}"
    )

    try:
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=512,
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        # Validate and merge with fallback
        result = {
            "name": fallback["name"],
            "title": (data.get("title") or fallback["title"])[:200],
            "short_description": data.get("short_description") or fallback["short_description"],
            "place": (data.get("place") or "")[:300],
            "date": (data.get("date") or "")[:100],
        }

        # Enforce word limit on short_description
        words = result["short_description"].split()
        if len(words) > MAX_DESC_WORDS:
            result["short_description"] = " ".join(words[:MAX_DESC_WORDS])

        logger.debug(f"AI enriched: '{raw_title[:50]}' -> '{result['title'][:50]}'")
        return result

    except json.JSONDecodeError as e:
        logger.warning(f"Groq returned invalid JSON for '{raw_title[:50]}': {e}")
        return fallback
    except Exception as e:
        logger.warning(f"Groq API error for '{raw_title[:50]}': {e}")
        return fallback


# Kept for backward compatibility
async def summarize_event(title: str, raw_desc: str) -> str:
    """Legacy: returns short_description from extract_event_structured."""
    r = await extract_event_structured(title, raw_desc)
    return r.get("short_description", (raw_desc or "")[:300])
