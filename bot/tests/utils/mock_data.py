"""
Мок-данные для тестирования онбординга
"""

# Валидные инвайт-коды для тестирования (формат: AMANITA-XXXX-XXXX)
VALID_INVITE_CODES = [
    "AMANITA-TEST-1234",  # Для теста успешной активации
    "AMANITA-USED-5678",  # Для теста уже использованного кода
    "AMANITA-FAKE-9012",  # Для теста несуществующего кода
]

# Невалидные инвайт-коды для тестирования
INVALID_INVITE_CODES = [
    "123",           # Слишком короткий
    "1234567890123", # Слишком длинный
    "12345678901!",  # Содержит спецсимволы
    "12345678901 ",  # Содержит пробел
]

# Мок-ответы от смарт-контракта (формат кодов: AMANITA-XXXX-XXXX)
MOCK_CONTRACT_RESPONSES = {
    "AMANITA-TEST-1234": {
        "success": True,
        "message": "Инвайт-код успешно активирован",
        "data": {
            "token_id": 1,
            "owner": "0x123...",
            "created_at": 1234567890,
            "expiry": 0
        }
    },
    "AMANITA-USED-5678": {
        "success": False,
        "message": "Инвайт-код уже использован",
        "error": "already_used"
    },
    "AMANITA-FAKE-9012": {
        "success": False,
        "message": "Инвайт-код не найден",
        "error": "not_found"
    }
}

# Тестовые сценарии (формат кодов: AMANITA-XXXX-XXXX для валидных)
TEST_SCENARIOS = {
    "successful_activation": {
        "code": "AMANITA-TEST-1234",
        "expected_response": MOCK_CONTRACT_RESPONSES["AMANITA-TEST-1234"],
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
        "code": "AMANITA-USED-5678",
        "expected_response": MOCK_CONTRACT_RESPONSES["AMANITA-USED-5678"],
        "description": "Попытка активации уже использованного кода"
    },
    "not_found": {
        "code": "AMANITA-FAKE-9012",
        "expected_response": MOCK_CONTRACT_RESPONSES["AMANITA-FAKE-9012"],
        "description": "Попытка активации несуществующего кода"
    }
} 