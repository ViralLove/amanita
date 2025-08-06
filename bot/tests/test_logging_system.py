import os
import json
import logging
import tempfile
import shutil
import pytest
from unittest import mock
from bot.utils.logging_setup import setup_logging
from bot.utils.sentry_init import init_sentry

@pytest.fixture
def temp_log_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)

@pytest.fixture
def temp_log_file(temp_log_dir):
    return os.path.join(temp_log_dir, "test_api.log")


def test_logging_writes_json_to_file(temp_log_file):
    logger = setup_logging(log_level="INFO", log_file=temp_log_file, max_size=100000, backup_count=2)
    logger.info("Test log message", extra={"test": True, "endpoint": "/test"})
    logger.handlers[0].flush()
    with open(temp_log_file, "r", encoding="utf-8") as f:
        line = f.readline()
        log_entry = json.loads(line)
    assert log_entry["level"] == "INFO"
    assert log_entry["logger"] == "amanita_api"
    assert log_entry["message"] == "Test log message"
    assert log_entry["test"] is True
    assert log_entry["endpoint"] == "/test"


def test_logging_rotation(temp_log_file):
    logger = setup_logging(log_level="INFO", log_file=temp_log_file, max_size=200, backup_count=2)
    # Запишем много сообщений, чтобы вызвать ротацию
    for i in range(100):
        logger.info(f"msg {i}")
    logger.handlers[0].flush()
    # Проверяем, что хотя бы один файл ротации создан
    rotated_files = [f for f in os.listdir(os.path.dirname(temp_log_file)) if f.startswith("test_api.log")]
    assert len(rotated_files) > 1


def test_sentry_not_initialized_in_dev(monkeypatch):
    monkeypatch.setenv("AMANITA_API_ENVIRONMENT", "development")
    monkeypatch.setenv("SENTRY_ENABLED", "false")
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    with mock.patch("sentry_sdk.init") as sentry_init:
        init_sentry()
        sentry_init.assert_not_called()


def test_sentry_initialized_in_prod(monkeypatch):
    monkeypatch.setenv("AMANITA_API_ENVIRONMENT", "production")
    monkeypatch.setenv("SENTRY_ENABLED", "true")
    monkeypatch.setenv("SENTRY_DSN", "dummy_dsn")
    with mock.patch("sentry_sdk.init") as sentry_init:
        init_sentry()
        sentry_init.assert_called_once()


def test_log_format_fields(temp_log_file):
    logger = setup_logging(log_level="INFO", log_file=temp_log_file, max_size=100000, backup_count=2)
    logger.info("Test format fields", extra={"custom_field": 123})
    logger.handlers[0].flush()
    with open(temp_log_file, "r", encoding="utf-8") as f:
        log_entry = json.loads(f.readline())
    # Проверяем наличие ключевых полей
    for field in ["timestamp", "level", "logger", "message", "module", "function", "line"]:
        assert field in log_entry
    assert log_entry["custom_field"] == 123 