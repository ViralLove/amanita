"""
Тесты fallback стратегий для Telegram слоя.
Проверяет корректность восстановления после ошибок при работе с изображениями.
"""

import pytest
from bot.handlers.common.image.fallback_strategies import (
    DegradationLevel, FallbackResult, ProgressTracker, UserNotifier
)


class TestTelegramFallbackStrategies:
    """Тесты fallback стратегий для Telegram."""
    
    def test_degradation_levels_for_telegram(self):
        """Тестирует уровни деградации для Telegram сообщений."""
        # Полная функциональность - изображение + текст
        assert DegradationLevel.FULL_FUNCTIONALITY.value == "full"
        
        # Высокое качество - изображение с ограничениями
        assert DegradationLevel.HIGH_QUALITY.value == "high"
        
        # Среднее качество - базовое изображение
        assert DegradationLevel.MEDIUM_QUALITY.value == "medium"
        
        # Базовая функциональность - только текст
        assert DegradationLevel.BASIC_FUNCTIONALITY.value == "basic"
        
        # Только текст - без изображений
        assert DegradationLevel.TEXT_ONLY.value == "text_only"
        
        # Сообщение об ошибке - минимальная информация
        assert DegradationLevel.ERROR_MESSAGE.value == "error_message"
    
    def test_fallback_result_for_telegram_image_download(self):
        """Тестирует результат fallback для загрузки изображения в Telegram."""
        result = FallbackResult(
            success=True,
            data="https://example.com/placeholder.jpg",
            degradation_level=DegradationLevel.HIGH_QUALITY,
            message="Image downloaded with fallback strategy",
            fallback_strategy="placeholder_image_fallback",
            execution_time=1.2,
            retry_count=1
        )
        
        assert result.success is True
        assert result.data == "https://example.com/placeholder.jpg"
        assert result.degradation_level == DegradationLevel.HIGH_QUALITY
        assert result.message == "Image downloaded with fallback strategy"
        assert result.fallback_strategy == "placeholder_image_fallback"
        assert result.execution_time == 1.2
        assert result.retry_count == 1
    
    def test_fallback_result_for_telegram_text_only(self):
        """Тестирует результат fallback для текстового режима в Telegram."""
        result = FallbackResult(
            success=True,
            data="Product description without images",
            degradation_level=DegradationLevel.TEXT_ONLY,
            message="Fallback to text-only mode",
            fallback_strategy="text_fallback",
            execution_time=0.5,
            retry_count=2
        )
        
        assert result.success is True
        assert result.data == "Product description without images"
        assert result.degradation_level == DegradationLevel.TEXT_ONLY
        assert result.message == "Fallback to text-only mode"
        assert result.fallback_strategy == "text_fallback"
        assert result.execution_time == 0.5
        assert result.retry_count == 2


class TestTelegramProgressTracker:
    """Тесты отслеживания прогресса для Telegram."""
    
    def test_progress_tracker_for_telegram_image_operation(self):
        """Тестирует отслеживание прогресса для операции с изображением в Telegram."""
        tracker = ProgressTracker()
        tracker.start_operation(4, "telegram_image_download")
        
        assert tracker.start_time is not None
        assert tracker.current_step == 0
        assert tracker.total_steps == 4
        assert tracker.step_messages == []
        
        # Шаг 1: Проверка URL
        tracker.update_progress("Validating image URL", 1)
        assert tracker.current_step == 1
        assert len(tracker.step_messages) == 1
        assert tracker.step_messages[0] == "Validating image URL"
        
        # Шаг 2: Загрузка изображения
        tracker.update_progress("Downloading image", 2)
        assert tracker.current_step == 2
        assert len(tracker.step_messages) == 2
        assert tracker.step_messages[1] == "Downloading image"
        
        # Шаг 3: Валидация файла
        tracker.update_progress("Validating downloaded file", 3)
        assert tracker.current_step == 3
        assert len(tracker.step_messages) == 3
        assert tracker.step_messages[2] == "Validating downloaded file"
        
        # Шаг 4: Отправка в Telegram
        tracker.update_progress("Sending to Telegram", 4)
        assert tracker.current_step == 4
        assert len(tracker.step_messages) == 4
        assert tracker.step_messages[3] == "Sending to Telegram"
    
    def test_progress_info_for_telegram(self):
        """Тестирует информацию о прогрессе для Telegram."""
        tracker = ProgressTracker()
        tracker.start_operation(3, "telegram_product_send")
        tracker.update_progress("Preparing product data", 1)
        tracker.update_progress("Formatting message", 2)
        
        info = tracker.get_progress_info()
        
        assert info["status"] == "in_progress"
        assert info["current_step"] == 2
        assert info["total_steps"] == 3
        assert abs(info["progress_percent"] - 66.67) < 0.01
        assert info["elapsed_time"] > 0
        assert len(info["step_messages"]) == 2
        assert info["step_messages"][0] == "Preparing product data"
        assert info["step_messages"][1] == "Formatting message"


class TestTelegramUserNotifier:
    """Тесты уведомлений пользователя для Telegram."""
    
    def test_user_notifier_initialization_for_telegram(self):
        """Тестирует инициализацию уведомлений для Telegram."""
        notifier = UserNotifier()
        
        assert notifier.logger is not None
    
    @pytest.mark.asyncio
    async def test_user_notifier_progress_for_telegram(self):
        """Тестирует уведомления о прогрессе для Telegram."""
        notifier = UserNotifier()
        
        # Тест должен пройти без ошибок
        await notifier.notify_progress("Downloading image for Telegram", {
            "progress_percent": 75.0,
            "current_step": 3,
            "total_steps": 4,
            "chat_id": 12345
        })
    
    @pytest.mark.asyncio
    async def test_user_notifier_fallback_start_for_telegram(self):
        """Тестирует уведомления о начале fallback для Telegram."""
        notifier = UserNotifier()
        
        # Тест должен пройти без ошибок
        await notifier.notify_fallback_start("placeholder_image_fallback", "network_error")
