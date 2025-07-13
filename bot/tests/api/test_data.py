"""
Тестовые данные для API тестов
"""

# Валидные Ethereum адреса
VALID_ETHEREUM_ADDRESSES = [
    "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6",
    "0x1234567890123456789012345678901234567890",
    "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
]

# Невалидные Ethereum адреса
INVALID_ETHEREUM_ADDRESSES = [
    "invalid-address",
    "0x123",
    "not-an-address",
    "",
    None
]

# Валидные API ключи (реальные ключи из .env)
VALID_API_KEYS = [
    "ak_22bc74537e53698e",  # Реальный API ключ
    "95eab10dcae73aedba904d57ce91bc2593e24e92e799e4874bdd75eeb7627532",
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
]

# Невалидные API ключи
INVALID_API_KEYS = [
    "invalid-key",
    "short",
    "x" * 100,
    "",
    None
]

# Тестовые данные для запросов
TEST_REQUEST_DATA = {
    "valid_api_key_request": {
        "client_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6",
        "description": "Test API key"
    },
    "invalid_api_key_request": {
        "client_address": "invalid-address",
        "description": "x" * 300  # Слишком длинное описание
    },
    "empty_request": {},
    "partial_request": {
        "client_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6"
    }
}

# Тестовые заголовки
TEST_HEADERS = {
    "valid_content_type": {"Content-Type": "application/json"},
    "invalid_content_type": {"Content-Type": "text/plain"},
    "missing_content_type": {}
} 