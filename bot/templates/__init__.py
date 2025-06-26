import json
import os
from typing import Dict, Any

def get_text(key: str, lang: str = 'en') -> str:
    """
    Получает текст по ключу из соответствующего языкового файла.
    
    Args:
        key (str): Ключ для поиска текста
        lang (str): Код языка (по умолчанию 'en')
        
    Returns:
        str: Найденный текст или ключ, если текст не найден
    """
    try:
        file_path = os.path.join(os.path.dirname(__file__), f'{lang}.json')
        with open(file_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
            
        # Рекурсивный поиск по вложенным ключам
        def find_nested(d: Dict[str, Any], k: str) -> str:
            if k in d:
                return d[k]
            for v in d.values():
                if isinstance(v, dict):
                    result = find_nested(v, k)
                    if result:
                        return result
            return k
            
        return find_nested(translations, key)
    except (FileNotFoundError, json.JSONDecodeError):
        return key 