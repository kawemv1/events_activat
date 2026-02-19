"""
AI-powered event extraction using Google Gemini Pro.
Extracts structured fields: name, title, short_description (100 words), place, date.
"""
import asyncio
import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

MAX_DESC_WORDS = 100
FALLBACK_DESC_LEN = 500  # chars if Gemini fails


def _has_relevant_keyword(text: str, keywords: list) -> bool:
    """Check if text contains at least one keyword from B2B or any industry category."""
    if not text:
        return False
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


async def extract_event_structured(
    raw_title: str,
    raw_desc: str,
    raw_url: str = "",
    relevant_keywords: Optional[list] = None,
) -> dict:
    """
    Lightweight, local extraction WITHOUT calling Gemini.

    - Keeps original title as both name/title (trimmed)
    - Truncates description to MAX_DESC_WORDS (by words)
    - Leaves place/date empty (to avoid any external API calls)

    This respects the user's requirement to **not use Gemini API for now**,
    while keeping the same return shape so other parts of the code continue
    to work without changes.
    """
    # Base fallback result (no external API)
    desc = (raw_desc or "")[:FALLBACK_DESC_LEN]
    words = desc.split()[:MAX_DESC_WORDS]
    short_desc = " ".join(words)

    result = {
        "name": (raw_title or "")[:200],
        "title": (raw_title or "")[:200],
        "short_description": short_desc,
        "place": "",
        "date": "",
    }

    # NOTE: we deliberately DO NOT:
    # - import or call google.generativeai
    # - read GEMINI_API_KEY
    # - make any network requests
    #
    # If in future you decide to re-enable Gemini,
    # you can restore the previous implementation here.

    return result


# Kept for backward compatibility
async def summarize_event(title: str, raw_desc: str) -> str:
    """Legacy: returns short_description from extract_event_structured."""
    r = await extract_event_structured(title, raw_desc)
    return r.get("short_description", (raw_desc or "")[:300])
