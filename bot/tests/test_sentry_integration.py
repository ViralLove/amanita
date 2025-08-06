import os
import logging
import pytest
from unittest import mock
from dotenv import load_dotenv

SENTRY_MOCK_LOG = "logs/sentry_mock.log"

# Мок-объект для sentry_sdk
class SentryMock:
    def __init__(self, log_file=SENTRY_MOCK_LOG):
        self.log_file = log_file
        # Очищаем файл перед тестом
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

    def capture_exception(self, exc):
        with open(self.log_file, "a") as f:
            f.write(f"capture_exception: {repr(exc)}\n")

    def capture_message(self, msg):
        with open(self.log_file, "a") as f:
            f.write(f"capture_message: {msg}\n")

@pytest.fixture
def sentry_mock(monkeypatch):
    mock_sentry = SentryMock()
    monkeypatch.setattr("sentry_sdk.capture_exception", mock_sentry.capture_exception)
    monkeypatch.setattr("sentry_sdk.capture_message", mock_sentry.capture_message)
    yield mock_sentry
    # Очистка после теста
    if os.path.exists(SENTRY_MOCK_LOG):
        os.remove(SENTRY_MOCK_LOG)

def test_sentry_capture_exception_and_message(sentry_mock):
    import sentry_sdk
    # Проверяем capture_exception
    try:
        raise ValueError("Test Sentry Exception")
    except Exception as e:
        sentry_sdk.capture_exception(e)
    # Проверяем capture_message
    sentry_sdk.capture_message("Test Sentry Message")
    # Проверяем, что оба события записаны в файл
    with open(SENTRY_MOCK_LOG, "r") as f:
        content = f.read()
    assert "capture_exception: ValueError" in content
    assert "capture_message: Test Sentry Message" in content


def test_sentry_real_connection():
    """
    Проверяет реальное соединение с Sentry (отправляет тестовое сообщение).
    Для ручной проверки: событие должно появиться в проекте Sentry.
    Также выводит id(sentry_sdk) и id функции capture_message для проверки, что используется реальный SDK.
    """
    # Загружаем переменные окружения из .env
    load_dotenv()
    import sentry_sdk
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        pytest.skip("SENTRY_DSN не задан, пропускаем тест реального соединения с Sentry")
    sentry_sdk.init(dsn=dsn, traces_sample_rate=0.0)  # Без трейсинга, только события
    test_message = "[TEST] Sentry real connection check"
    # Выводим id SDK и функции capture_message
    print(f"sentry_sdk id: {id(sentry_sdk)}")
    print(f"sentry_sdk.capture_message id: {id(sentry_sdk.capture_message)}")
    sentry_sdk.capture_message(test_message)
    # Логируем для пользователя
    print(f"Тестовое сообщение отправлено в Sentry: {test_message}")
    # Проверка проходит всегда, результат — ручная проверка в Sentry UI
    assert True 