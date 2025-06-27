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
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        file_path = os.path.join(project_root, "bot", "templates", f"{lang}.json")
        print(f"[LOCALIZATION] file_path={file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
            
        # Рекурсивный поиск по вложенным ключам
        def find_nested(d: Dict[str, Any], k: str) -> str:
            if k in d:
                return d[k]
            for v in d.values():
                if isinstance(v, dict):
                    result = find_nested(v, k)
                    if result and result != k:
                        return result
            return k
        result = find_nested(translations, key)
        print(f"[LOCALIZATION] lang={lang}, key={key}, result={result}")
        return result
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[LOCALIZATION][ERROR] lang={lang}, key={key}, error={e}")
        return key 