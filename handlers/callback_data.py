from aiogram.filters.callback_data import CallbackData
from typing import Optional

class CountryCallback(CallbackData, prefix="country"):
    country: str
    from_settings: bool = False

class IndustryCallback(CallbackData, prefix="ind"):
    industry: str
    from_settings: bool = False

class CityCallback(CallbackData, prefix="city"):
    city: str
    from_settings: bool = False

class SettingsCallback(CallbackData, prefix="set"):
    action: str
    value: Optional[str] = None

class SelectAllCallback(CallbackData, prefix="all"):
    type: str
    from_settings: bool = False

class ConfirmCallback(CallbackData, prefix="conf"):
    action: str
    step: Optional[str] = None  # "country" | "ind" | "city" for onboarding flow

class EventFeedbackCallback(CallbackData, prefix="fb"):
    event_id: int
    action: str
    page: int = 1  # Для кнопки "Вернуться к событиям"

class FeedbackReasonCallback(CallbackData, prefix="reason"):
    event_id: int
    reason_idx: int  # Индекс в FEEDBACK_REASONS (ограничение 64 байт callback_data)
    page: int = 1  # Для кнопки "Вернуться к событиям"

class EventsListCallback(CallbackData, prefix="evlist"):
    page: int


class MainMenuCallback(CallbackData, prefix="main"):
    action: str