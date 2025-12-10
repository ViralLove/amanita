"""
Тесты для обработки инвайт-кодов
"""

import pytest
from unittest.mock import AsyncMock, patch
from bot.handlers.onboarding_fsm import process_invite_code
from bot.tests.utils.mock_data import (
    VALID_INVITE_CODES,
    INVALID_INVITE_CODES,
    TEST_SCENARIOS
)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_successful_activation():
    """Тест успешной активации инвайт-кода"""
    message = AsyncMock()
    message.text = TEST_SCENARIOS["successful_activation"]["code"]
    
    # ✅ ИСПРАВЛЕНО: Мокаем state для успешной активации
    state = AsyncMock()
    state.set_data = AsyncMock()
    state.set_state = AsyncMock()
    
    with patch('bot.handlers.onboarding_fsm.blockchain') as mock_blockchain:
        mock_blockchain.validate_invite_code.return_value = TEST_SCENARIOS["successful_activation"]["expected_response"]
        
        await process_invite_code(message, state)
        
        # ✅ ИСПРАВЛЕНО: При успешной активации отправляется 1 сообщение
        assert message.answer.call_count == 1, f"Ожидалось 1 сообщение, получено {message.answer.call_count}"
        # Проверяем содержимое сообщения об успехе (реальное сообщение содержит "код в порядке" или "активируем")
        success_message = message.answer.call_args[0][0]
        assert ("код" in success_message.lower() or "активируем" in success_message.lower() or 
                "активация" in success_message.lower() or "validated" in success_message.lower()), \
            f"Сообщение об успехе должно содержать информацию о коде/активации: {success_message[:100]}"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalid_format():
    """Тест обработки неверного формата кода"""
    message = AsyncMock()
    message.text = TEST_SCENARIOS["invalid_format"]["code"]
    
    await process_invite_code(message, None)
    
    # ✅ ИСПРАВЛЕНО: При неверном формате отправляется 2 сообщения (invalid_invite + retry)
    assert message.answer.call_count == 2, f"Ожидалось 2 сообщения, получено {message.answer.call_count}"
    
    # Проверяем содержимое первого сообщения (invalid_invite)
    first_message = message.answer.call_args_list[0][0][0]
    assert "не так с кодом" in first_message.lower() or "invalid" in first_message.lower() or "ошибка" in first_message.lower()
    
    # Проверяем содержимое второго сообщения (retry)
    second_message = message.answer.call_args_list[1][0][0]
    assert "повторить" in second_message.lower() or "retry" in second_message.lower()

@pytest.mark.unit
@pytest.mark.asyncio
async def test_already_used_code():
    """Тест обработки уже использованного кода"""
    message = AsyncMock()
    message.text = TEST_SCENARIOS["already_used"]["code"]
    
    with patch('bot.handlers.onboarding_fsm.blockchain') as mock_blockchain:
        mock_blockchain.validate_invite_code.return_value = TEST_SCENARIOS["already_used"]["expected_response"]
        
        await process_invite_code(message, None)
        
        # ✅ ИСПРАВЛЕНО: При ошибке валидации отправляется 2 сообщения (invalid_invite + retry)
        assert message.answer.call_count == 2, f"Ожидалось 2 сообщения, получено {message.answer.call_count}"
        
        # Проверяем содержимое первого сообщения (invalid_invite)
        first_message = message.answer.call_args_list[0][0][0]
        assert "не так с кодом" in first_message.lower() or "invalid" in first_message.lower() or "ошибка" in first_message.lower()
        
        # Проверяем содержимое второго сообщения (retry)
        second_message = message.answer.call_args_list[1][0][0]
        assert "повторить" in second_message.lower() or "retry" in second_message.lower()

@pytest.mark.unit
@pytest.mark.asyncio
async def test_not_found_code():
    """Тест обработки несуществующего кода"""
    message = AsyncMock()
    message.text = TEST_SCENARIOS["not_found"]["code"]
    
    with patch('bot.handlers.onboarding_fsm.blockchain') as mock_blockchain:
        mock_blockchain.validate_invite_code.return_value = TEST_SCENARIOS["not_found"]["expected_response"]
        
        await process_invite_code(message, None)
        
        # ✅ ИСПРАВЛЕНО: При ошибке валидации отправляется 2 сообщения (invalid_invite + retry)
        assert message.answer.call_count == 2, f"Ожидалось 2 сообщения, получено {message.answer.call_count}"
        
        # Проверяем содержимое первого сообщения (invalid_invite)
        first_message = message.answer.call_args_list[0][0][0]
        assert "не так с кодом" in first_message.lower() or "invalid" in first_message.lower() or "ошибка" in first_message.lower()
        
        # Проверяем содержимое второго сообщения (retry)
        second_message = message.answer.call_args_list[1][0][0]
        assert "повторить" in second_message.lower() or "retry" in second_message.lower()

@pytest.mark.unit
@pytest.mark.asyncio
async def test_navigation_buttons():
    """Тест наличия кнопок навигации"""
    message = AsyncMock()
    message.text = TEST_SCENARIOS["successful_activation"]["code"]
    
    # ✅ ИСПРАВЛЕНО: Мокаем state для успешной активации
    state = AsyncMock()
    state.set_data = AsyncMock()
    state.set_state = AsyncMock()
    
    with patch('bot.handlers.onboarding_fsm.blockchain') as mock_blockchain:
        mock_blockchain.validate_invite_code.return_value = TEST_SCENARIOS["successful_activation"]["expected_response"]
        
        await process_invite_code(message, state)
        
        # ✅ ИСПРАВЛЕНО: При успешной активации отправляется 1 сообщение с кнопками
        assert message.answer.call_count == 1, f"Ожидалось 1 сообщение, получено {message.answer.call_count}"
        # Проверяем, что отправлено сообщение с кнопками
        assert message.answer.call_args[1].get('reply_markup') is not None, "Сообщение должно содержать reply_markup" 