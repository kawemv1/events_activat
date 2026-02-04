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

class FeedbackReasonCallback(CallbackData, prefix="reason"):
    event_id: int
    reason: str

class EventsListCallback(CallbackData, prefix="evlist"):
    page: int