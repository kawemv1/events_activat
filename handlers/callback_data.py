from aiogram.filters.callback_data import CallbackData


class IndustryCallback(CallbackData, prefix="industry"):
    """Callback для выбора индустрии"""
    industry: str


class CityCallback(CallbackData, prefix="city"):
    """Callback для выбора города"""
    city: str


class SelectAllCallback(CallbackData, prefix="select_all"):
    """Callback для выбора всех"""
    type: str  # "industry" или "city"


class ConfirmCallback(CallbackData, prefix="confirm"):
    """Callback для подтверждения выбора"""
    action: str  # "save" или "cancel"


class EventFeedbackCallback(CallbackData, prefix="event_feedback"):
    """Callback для фидбека по ивенту"""
    event_id: int
    action: str  # "like" или "dislike"


class FeedbackReasonCallback(CallbackData, prefix="feedback_reason"):
    """Callback для выбора причины отклонения"""
    event_id: int
    reason: str


class SettingsCallback(CallbackData, prefix="settings"):
    """Callback для настроек"""
    action: str  # "edit_industries", "edit_cities", "back"
