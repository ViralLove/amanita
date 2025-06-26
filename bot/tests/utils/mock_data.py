"""
Мок-данные для тестирования онбординга
"""

# Валидные инвайт-коды для тестирования
VALID_INVITE_CODES = [
    "TEST12345678",  # Для теста успешной активации
    "USED12345678",  # Для теста уже использованного кода
    "FAKE12345678",  # Для теста несуществующего кода
]

# Невалидные инвайт-коды для тестирования
INVALID_INVITE_CODES = [
    "123",           # Слишком короткий
    "1234567890123", # Слишком длинный
    "12345678901!",  # Содержит спецсимволы
    "12345678901 ",  # Содержит пробел
]

# Мок-ответы от смарт-контракта
MOCK_CONTRACT_RESPONSES = {
    "TEST12345678": {
        "success": True,
        "message": "Инвайт-код успешно активирован",
        "data": {
            "token_id": 1,
            "owner": "0x123...",
            "created_at": 1234567890,
            "expiry": 0
        }
    },
    "USED12345678": {
        "success": False,
        "message": "Инвайт-код уже использован",
        "error": "already_used"
    },
    "FAKE12345678": {
        "success": False,
        "message": "Инвайт-код не найден",
        "error": "not_found"
    }
}

# Тестовые сценарии
TEST_SCENARIOS = {
    "successful_activation": {
        "code": "TEST12345678",
        "expected_response": MOCK_CONTRACT_RESPONSES["TEST12345678"],
        "description": "Успешная активация валидного кода"
    },
    "invalid_format": {
        "code": "123",
        "expected_response": {
            "success": False,
            "message": "Неверный формат кода",
            "error": "invalid_format"
        },
        "description": "Попытка активации кода неверного формата"
    },
    "already_used": {
        "code": "USED12345678",
        "expected_response": MOCK_CONTRACT_RESPONSES["USED12345678"],
        "description": "Попытка активации уже использованного кода"
    },
    "not_found": {
        "code": "FAKE12345678",
        "expected_response": MOCK_CONTRACT_RESPONSES["FAKE12345678"],
        "description": "Попытка активации несуществующего кода"
    }
} 