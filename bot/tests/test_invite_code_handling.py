"""
Тесты для обработки инвайт-кодов
"""

import pytest
from unittest.mock import AsyncMock, patch
from bot.handlers.onboarding import handle_invite_code_input
from bot.tests.utils.mock_data import (
    VALID_INVITE_CODES,
    INVALID_INVITE_CODES,
    TEST_SCENARIOS
)

@pytest.mark.asyncio
async def test_successful_activation():
    """Тест успешной активации инвайт-кода"""
    message = AsyncMock()
    message.text = TEST_SCENARIOS["successful_activation"]["code"]
    
    with patch('bot.handlers.onboarding.BlockchainService') as mock_service:
        mock_service.return_value.validate_invite_code.return_value = TEST_SCENARIOS["successful_activation"]["expected_response"]
        
        await handle_invite_code_input(message)
        
        # Проверяем, что отправлено сообщение об успехе
        message.answer.assert_called_once()
        assert "успешно активирован" in message.answer.call_args[0][0]

@pytest.mark.asyncio
async def test_invalid_format():
    """Тест обработки неверного формата кода"""
    message = AsyncMock()
    message.text = TEST_SCENARIOS["invalid_format"]["code"]
    
    await handle_invite_code_input(message)
    
    # Проверяем, что отправлено сообщение об ошибке
    message.answer.assert_called_once()
    assert "Неверный формат" in message.answer.call_args[0][0]

@pytest.mark.asyncio
async def test_already_used_code():
    """Тест обработки уже использованного кода"""
    message = AsyncMock()
    message.text = TEST_SCENARIOS["already_used"]["code"]
    
    with patch('bot.handlers.onboarding.BlockchainService') as mock_service:
        mock_service.return_value.validate_invite_code.return_value = TEST_SCENARIOS["already_used"]["expected_response"]
        
        await handle_invite_code_input(message)
        
        # Проверяем, что отправлено сообщение об ошибке
        message.answer.assert_called_once()
        assert "уже использован" in message.answer.call_args[0][0]

@pytest.mark.asyncio
async def test_not_found_code():
    """Тест обработки несуществующего кода"""
    message = AsyncMock()
    message.text = TEST_SCENARIOS["not_found"]["code"]
    
    with patch('bot.handlers.onboarding.BlockchainService') as mock_service:
        mock_service.return_value.validate_invite_code.return_value = TEST_SCENARIOS["not_found"]["expected_response"]
        
        await handle_invite_code_input(message)
        
        # Проверяем, что отправлено сообщение об ошибке
        message.answer.assert_called_once()
        assert "не найден" in message.answer.call_args[0][0]

@pytest.mark.asyncio
async def test_navigation_buttons():
    """Тест наличия кнопок навигации"""
    message = AsyncMock()
    message.text = TEST_SCENARIOS["successful_activation"]["code"]
    
    with patch('bot.handlers.onboarding.BlockchainService') as mock_service:
        mock_service.return_value.validate_invite_code.return_value = TEST_SCENARIOS["successful_activation"]["expected_response"]
        
        await handle_invite_code_input(message)
        
        # Проверяем, что отправлено сообщение с кнопками
        message.answer.assert_called_once()
        assert message.answer.call_args[1].get('reply_markup') is not None 