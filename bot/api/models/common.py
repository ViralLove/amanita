"""
Общие типы и утилиты для API моделей
"""
import re
from typing import Optional, Union, Any, Annotated
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic_core import core_schema
import secrets
import string


class EthereumAddress(str):
    """Валидатор для Ethereum адресов"""
    
    def __new__(cls, value):
        """Создание с валидацией"""
        validated = cls.validate_ethereum_address(value)
        return super().__new__(cls, validated)
    
    @classmethod
    def validate_ethereum_address(cls, v, *args, **kwargs) -> str:
        if isinstance(v, str):
            # Проверяем формат Ethereum адреса (0x + 40 hex символов)
            if re.match(r'^0x[a-fA-F0-9]{40}$', v):
                return v.lower()  # Нормализуем к нижнему регистру
        raise ValueError('Invalid Ethereum address format')
    
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler) -> dict:
        """Схема для Pydantic v2"""
        return core_schema.with_info_after_validator_function(
            cls.validate_ethereum_address,
            core_schema.str_schema(),
            serialization=core_schema.str_schema(),
        )
    
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        """JSON схема для OpenAPI"""
        json_schema = handler(core_schema)
        json_schema.update(
            type="string",
            pattern=r"^0x[a-fA-F0-9]{40}$",
            description="Ethereum address in hex format (0x + 40 characters)",
            example="0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6"
        )
        return json_schema


class ApiKey(str):
    """Валидатор для API ключей"""
    
    def __new__(cls, value):
        """Создание с валидацией"""
        validated = cls.validate_api_key(value)
        return super().__new__(cls, validated)
    
    @classmethod
    @field_validator('*', mode='before')
    def validate_api_key(cls, v: Any) -> str:
        if isinstance(v, str):
            # Поддерживаем разные форматы API ключей:
            # 1. 64 символа hex (традиционный формат)
            # 2. ak_ + 16 символов (формат Amanita)
            # 3. sk_ + 64 символа hex (секретный ключ)
            if (re.match(r'^[a-fA-F0-9]{64}$', v) or  # 64 hex символа
                re.match(r'^ak_[a-zA-Z0-9]{16}$', v) or  # ak_ + 16 символов
                re.match(r'^sk_[a-fA-F0-9]{64}$', v)):   # sk_ + 64 hex символа
                return v.lower()
        raise ValueError('Invalid API key format')
    
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        """JSON схема для OpenAPI"""
        json_schema = handler(core_schema)
        json_schema.update(
            type="string",
            pattern=r"^([a-fA-F0-9]{64}|ak_[a-zA-Z0-9]{16}|sk_[a-fA-F0-9]{64})$",
            description="API key in supported formats: 64 hex chars, ak_ + 16 chars, or sk_ + 64 hex chars",
            example="ak_22bc74537e53698e"
        )
        return json_schema


class Nonce(int):
    """Валидатор для nonce значений"""
    
    def __new__(cls, value):
        """Создание с валидацией"""
        validated = cls.validate_nonce(value)
        return super().__new__(cls, validated)
    
    @classmethod
    @field_validator('*', mode='before')
    def validate_nonce(cls, v: Any) -> int:
        if isinstance(v, (int, str)):
            try:
                nonce = int(v)
                if nonce >= 0:
                    return nonce
            except (ValueError, TypeError):
                pass
        raise ValueError('Nonce must be a non-negative integer')


class Timestamp(int):
    """Валидатор для timestamp значений"""
    
    def __new__(cls, value):
        """Создание с валидацией"""
        validated = cls.validate_timestamp(value)
        return super().__new__(cls, validated)
    
    @classmethod
    @field_validator('*', mode='before')
    def validate_timestamp(cls, v: Any) -> int:
        if isinstance(v, (int, str)):
            try:
                timestamp = int(v)
                if timestamp > 0:
                    return timestamp
            except (ValueError, TypeError):
                pass
        raise ValueError('Timestamp must be a positive integer')
    
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        """JSON схема для OpenAPI"""
        json_schema = handler(core_schema)
        json_schema.update(
            type="integer",
            description="Unix timestamp (seconds since epoch)",
            example=1640995200
        )
        return json_schema


class RequestId(str):
    """Валидатор для ID запросов"""
    
    def __new__(cls, value):
        """Создание с валидацией"""
        validated = cls.validate_request_id(value)
        return super().__new__(cls, validated)
    
    @classmethod
    @field_validator('*', mode='before')
    def validate_request_id(cls, v: Any) -> str:
        if isinstance(v, str):
            # Request ID должен быть UUID или похожим идентификатором
            if re.match(r'^[a-zA-Z0-9\-_]{8,64}$', v):
                return v
        raise ValueError('Invalid request ID format')
    
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        """JSON схема для OpenAPI"""
        json_schema = handler(core_schema)
        json_schema.update(
            type="string",
            pattern=r"^[a-zA-Z0-9\-_]{8,64}$",
            description="Unique request identifier",
            example="req_1234567890abcdef"
        )
        return json_schema


class Signature(str):
    """Валидатор для подписей"""
    
    @classmethod
    @field_validator('*', mode='before')
    def validate_signature(cls, v: Any) -> str:
        if isinstance(v, str):
            # Подпись должна быть в hex формате
            if re.match(r'^[a-fA-F0-9]{128,132}$', v):
                return v.lower()
        raise ValueError('Invalid signature format')


class HexString(str):
    """Валидатор для hex строк"""
    
    @classmethod
    @field_validator('*', mode='before')
    def validate_hex_string(cls, v: Any) -> str:
        if isinstance(v, str):
            # Убираем префикс 0x если есть
            if v.startswith('0x'):
                v = v[2:]
            # Проверяем что это hex строка
            if re.match(r'^[a-fA-F0-9]+$', v):
                return v.lower()
        raise ValueError('Invalid hex string format')


def generate_request_id() -> str:
    """Генерирует уникальный ID для запроса"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))


def get_current_timestamp() -> int:
    """Возвращает текущий timestamp в секундах"""
    return int(datetime.now().timestamp())


class PaginationParams(BaseModel):
    """Параметры пагинации"""
    page: int = Field(default=1, ge=1, description="Номер страницы")
    size: int = Field(default=20, ge=1, le=100, description="Размер страницы")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class SortParams(BaseModel):
    """Параметры сортировки"""
    sort_by: Optional[str] = Field(default=None, description="Поле для сортировки")
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$", description="Порядок сортировки")
    
    model_config = ConfigDict(arbitrary_types_allowed=True) 