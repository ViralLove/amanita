"""
Валидация переходов состояний для Activities API.

Draft → SentToReview → Approved → Published; Published → Draft (unpublish).
"""

from __future__ import annotations

ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "Draft": ["SentToReview"],
    "SentToReview": ["Approved", "Draft"],
    "Approved": ["Published"],
    "Published": ["Draft"],
}


def validate_state_transition(current_status: str, new_status: str) -> bool:
    """
    Проверяет допустимость перехода current_status → new_status.

    Returns:
        True если переход разрешён, False если запрещён.
    """
    allowed = ALLOWED_TRANSITIONS.get(current_status, [])
    return new_status in allowed


def get_state_transition_error_message(current_status: str, new_status: str) -> str:
    """Сообщение об ошибке для запрещённого перехода (используется в storage, error responses)."""
    return f"Cannot transition from {current_status} to {new_status}"
