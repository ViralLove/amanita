import hashlib
import uuid
from typing import Optional

def generate_invite_code(prefix: Optional[str] = None) -> str:
    """
    Генерирует уникальный инвайт-код.
    
    Args:
        prefix: Опциональный префикс для кода
        
    Returns:
        str: Уникальный инвайт-код
    """
    # Генерируем UUID
    unique_id = str(uuid.uuid4())
    
    # Создаем хеш
    hash_obj = hashlib.sha256(unique_id.encode())
    hash_hex = hash_obj.hexdigest()
    
    # Берем первые 8 символов хеша
    code = hash_hex[:8]
    
    # Добавляем префикс если указан
    if prefix:
        code = f"{prefix}-{code}"
        
    return code

def validate_invite_code(code: str) -> bool:
    """
    Проверяет формат инвайт-кода.
    
    Args:
        code: Инвайт-код для проверки
        
    Returns:
        bool: True если код валидный
    """
    # Проверяем длину (8 символов или 8 + длина префикса + 1)
    if len(code) != 8 and not (len(code) > 8 and code.count('-') == 1):
        return False
        
    # Проверяем что код состоит из hex-символов
    hex_chars = set('0123456789abcdef')
    code_parts = code.split('-')
    
    return all(c in hex_chars for c in code_parts[-1]) 