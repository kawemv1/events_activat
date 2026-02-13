from aiogram.filters.callback_data import CallbackData
from typing import Optional

class IndustryCallback(CallbackData, prefix="ind"):
    industry: str

class CityCallback(CallbackData, prefix="city"):
    city: str

class SettingsCallback(CallbackData, prefix="set"):
    action: str
    value: Optional[str] = None

class SelectAllCallback(CallbackData, prefix="all"):
    type: str

class ConfirmCallback(CallbackData, prefix="conf"):
    action: str

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