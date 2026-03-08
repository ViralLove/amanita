"""
PushSender: абстракция отправки запроса на подпись в приложение пользователя (Wallet).

Реальная реализация — FCM/APNs; в тестах и wallet-mock runner используется StubPushSender.
"""

from typing import Literal, Protocol

SignRequestType = Literal["sign_arweave", "sign_contract"]


class PushSender(Protocol):
    """Протокол отправки запроса на подпись в Wallet."""

    def send_sign_request(
        self,
        user_id: str,
        request_type: SignRequestType,
        request_id: str,
    ) -> None:
        """Отправить запрос на подпись пользователю (или записать событие в stub)."""
        ...
