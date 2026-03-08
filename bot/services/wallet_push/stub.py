"""
StubPushSender: in-memory реализация PushSender для тестов и wallet-mock runner.

События накапливаются в списке; runner читает их через get_pending_events().
Однопоточное использование (документировано); при необходимости — подмена на thread-safe реализацию.
"""

from __future__ import annotations

import time
from typing import Any

from services.wallet_push.interface import SignRequestType


def _event(
    user_id: str,
    request_type: SignRequestType,
    request_id: str,
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "request_type": request_type,
        "request_id": request_id,
        "timestamp": time.time(),
    }


class StubPushSender:
    """
    Заглушка PushSender: записывает события в in-memory список.

    Использование: тесты проверяют вызовы через get_pending_events();
    wallet-mock runner читает события и эмулирует «приложение получило пуш».
    Ограничение: однопоточное использование (один поток пишет, один читает в тестах/runner).
    """

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def send_sign_request(
        self,
        user_id: str,
        request_type: SignRequestType,
        request_id: str,
    ) -> None:
        self._events.append(_event(user_id, request_type, request_id))

    def get_pending_events(self) -> list[dict[str, Any]]:
        """Вернуть копию списка накопленных событий (не очищает список)."""
        return list(self._events)

    def clear_pending(self) -> None:
        """Очистить список событий (для runner между сценариями)."""
        self._events.clear()
