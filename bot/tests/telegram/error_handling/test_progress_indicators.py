"""
Тесты системы прогресс-индикаторов для Telegram слоя.
Проверяет корректность отслеживания прогресса операций с изображениями.
"""

import pytest
from bot.handlers.common.image.progress_indicators import (
    ProgressStatus, ProgressType, ProgressStep, ProgressInfo,
    ProgressCallback, LoggingProgressCallback, TelegramProgressCallback
)


class TestTelegramProgressStatus:
    """Тесты статусов прогресса для Telegram."""
    
    def test_progress_status_values_for_telegram(self):
        """Тестирует значения статусов прогресса для Telegram операций."""
        # Операция не началась
        assert ProgressStatus.NOT_STARTED.value == "not_started"
        
        # Операция в процессе (например, загрузка изображения)
        assert ProgressStatus.IN_PROGRESS.value == "in_progress"
        
        # Операция завершена успешно
        assert ProgressStatus.COMPLETED.value == "completed"
        
        # Операция завершилась с ошибкой
        assert ProgressStatus.FAILED.value == "failed"
        
        # Операция была отменена пользователем
        assert ProgressStatus.CANCELLED.value == "cancelled"
    
    def test_progress_status_enumeration_for_telegram(self):
        """Тестирует, что все статусы прогресса уникальны для Telegram."""
        values = [status.value for status in ProgressStatus]
        assert len(values) == len(set(values))
        assert len(ProgressStatus) == 5


class TestTelegramProgressType:
    """Тесты типов прогресса для Telegram."""
    
    def test_progress_type_values_for_telegram(self):
        """Тестирует значения типов прогресса для Telegram операций."""
        # Определенное количество шагов (например, загрузка изображения)
        assert ProgressType.DETERMINATE.value == "determinate"
        
        # Неопределенное количество шагов (например, обработка)
        assert ProgressType.INDETERMINATE.value == "indeterminate"
        
        # Спиннер с анимацией (например, ожидание ответа)
        assert ProgressType.SPINNER.value == "spinner"
    
    def test_progress_type_enumeration_for_telegram(self):
        """Тестирует, что все типы прогресса уникальны для Telegram."""
        values = [ptype.value for ptype in ProgressType]
        assert len(values) == len(set(values))
        assert len(ProgressType) == 3


class TestTelegramProgressStep:
    """Тесты шагов прогресса для Telegram."""
    
    def test_progress_step_creation_for_telegram(self):
        """Тестирует создание шага прогресса для Telegram операции."""
        step = ProgressStep(
            id="telegram_image_download_step_1",
            name="Validate Image URL",
            description="Checking if the image URL is valid and accessible"
        )
        
        assert step.id == "telegram_image_download_step_1"
        assert step.name == "Validate Image URL"
        assert step.description == "Checking if the image URL is valid and accessible"
        assert step.status == ProgressStatus.NOT_STARTED
        assert step.start_time is None
        assert step.end_time is None
        assert step.error is None
        assert step.metadata == {}
    
    def test_progress_step_with_telegram_metadata(self):
        """Тестирует создание шага прогресса с Telegram метаданными."""
        step = ProgressStep(
            id="telegram_image_download_step_2",
            name="Download Image",
            description="Downloading image from URL",
            status=ProgressStatus.COMPLETED,
            start_time=1000.0,
            end_time=1100.0,
            error=None,
            metadata={
                "chat_id": 12345,
                "message_id": 67890,
                "url": "https://example.com/image.jpg",
                "file_size": 1024000
            }
        )
        
        assert step.id == "telegram_image_download_step_2"
        assert step.name == "Download Image"
        assert step.description == "Downloading image from URL"
        assert step.status == ProgressStatus.COMPLETED
        assert step.start_time == 1000.0
        assert step.end_time == 1100.0
        assert step.error is None
        assert step.metadata["chat_id"] == 12345
        assert step.metadata["message_id"] == 67890
        assert step.metadata["url"] == "https://example.com/image.jpg"
        assert step.metadata["file_size"] == 1024000


class TestTelegramProgressInfo:
    """Тесты информации о прогрессе для Telegram."""
    
    def test_progress_info_creation_for_telegram(self):
        """Тестирует создание информации о прогрессе для Telegram операции."""
        info = ProgressInfo(
            operation_id="telegram_op_12345",
            operation_name="telegram_image_download",
            status=ProgressStatus.IN_PROGRESS,
            progress_type=ProgressType.DETERMINATE,
            current_step=2,
            total_steps=4,
            progress_percent=50.0,
            start_time=1000.0,
            elapsed_time=15.0
        )
        
        assert info.operation_id == "telegram_op_12345"
        assert info.operation_name == "telegram_image_download"
        assert info.status == ProgressStatus.IN_PROGRESS
        assert info.progress_type == ProgressType.DETERMINATE
        assert info.current_step == 2
        assert info.total_steps == 4
        assert info.progress_percent == 50.0
        assert info.start_time == 1000.0
        assert info.elapsed_time == 15.0
        assert info.estimated_remaining is None
        assert info.steps == []
        assert info.metadata == {}
    
    def test_progress_info_with_telegram_steps(self):
        """Тестирует информацию о прогрессе с шагами для Telegram."""
        step1 = ProgressStep("step1", "Validate URL", "Check image URL")
        step2 = ProgressStep("step2", "Download Image", "Download from URL")
        
        info = ProgressInfo(
            operation_id="telegram_op_12345",
            operation_name="telegram_image_download",
            status=ProgressStatus.IN_PROGRESS,
            progress_type=ProgressType.DETERMINATE,
            current_step=2,
            total_steps=4,
            progress_percent=50.0,
            start_time=1000.0,
            elapsed_time=20.0,
            estimated_remaining=20.0,
            steps=[step1, step2],
            metadata={"chat_id": 12345, "user_id": 11111}
        )
        
        assert info.estimated_remaining == 20.0
        assert len(info.steps) == 2
        assert info.steps[0] == step1
        assert info.steps[1] == step2
        assert info.metadata["chat_id"] == 12345
        assert info.metadata["user_id"] == 11111


class TestTelegramProgressCallback:
    """Тесты абстрактного ProgressCallback для Telegram."""
    
    def test_progress_callback_is_abstract_for_telegram(self):
        """Тестирует, что ProgressCallback является абстрактным для Telegram."""
        with pytest.raises(TypeError):
            ProgressCallback()


class TestTelegramLoggingProgressCallback:
    """Тесты LoggingProgressCallback для Telegram."""
    
    def test_logging_progress_callback_initialization_for_telegram(self):
        """Тестирует инициализацию LoggingProgressCallback для Telegram."""
        callback = LoggingProgressCallback()
        
        assert callback.logger is not None
    
    @pytest.mark.asyncio
    async def test_logging_progress_callback_methods_for_telegram(self):
        """Тестирует все методы LoggingProgressCallback для Telegram."""
        callback = LoggingProgressCallback()
        
        # Создаем тестовый ProgressInfo с Telegram контекстом
        progress_info = ProgressInfo(
            operation_id="telegram_op_12345",
            operation_name="telegram_image_download",
            status=ProgressStatus.IN_PROGRESS,
            progress_type=ProgressType.DETERMINATE,
            current_step=2,
            total_steps=4,
            progress_percent=50.0,
            start_time=1000.0,
            elapsed_time=20.0
        )
        
        step = ProgressStep("step2", "Download Image", "Downloading image from URL")
        error = Exception("Network timeout")
        
        # Все методы должны выполняться без ошибок
        await callback.on_progress_update(progress_info)
        await callback.on_step_complete(step)
        await callback.on_operation_complete(progress_info, "success")
        await callback.on_operation_failed(progress_info, error)


class TestTelegramTelegramProgressCallback:
    """Тесты TelegramProgressCallback для Telegram."""
    
    def test_telegram_progress_callback_initialization(self):
        """Тестирует инициализацию TelegramProgressCallback."""
        callback = TelegramProgressCallback()
        
        assert callback.logger is not None
    
    @pytest.mark.asyncio
    async def test_telegram_progress_callback_methods(self):
        """Тестирует все методы TelegramProgressCallback для Telegram."""
        callback = TelegramProgressCallback()
        
        # Создаем тестовый ProgressInfo с Telegram контекстом
        progress_info = ProgressInfo(
            operation_id="telegram_op_12345",
            operation_name="telegram_image_download",
            status=ProgressStatus.IN_PROGRESS,
            progress_type=ProgressType.DETERMINATE,
            current_step=2,
            total_steps=4,
            progress_percent=50.0,
            start_time=1000.0,
            elapsed_time=20.0
        )
        
        step = ProgressStep("step2", "Download Image", "Downloading image from URL")
        error = Exception("Network timeout")
        
        # Все методы должны выполняться без ошибок
        await callback.on_progress_update(progress_info)
        await callback.on_step_complete(step)
        await callback.on_operation_complete(progress_info, "success")
        await callback.on_operation_failed(progress_info, error)
