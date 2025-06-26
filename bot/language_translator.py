import os
import json
import requests
from dotenv import load_dotenv
from typing import Dict, Set, Tuple
import logging
from requests.exceptions import RequestException
import html

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка ключа из bot/.env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', 'bot', '.env'))
DEEPL_API_KEY = os.getenv("DEEP_L_API_KEY")
DEEPL_URL = "https://api.deepl.com/v2/translate"

# Соответствие кода файла и языка DeepL
LANG_MAP = {
    "en": "EN",
    # "es": "ES", "fr": "FR", "de": "DE", "pt": "PT", "nl": "NL",
    # "pl": "PL", "lt": "LT", "lv": "LV", "et": "ET", "fi": "FI", "sv": "SV",
    # "da": "DA", "no": "NB", "ru": "RU"
}

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')

class TranslationError(Exception):
    """Базовый класс для ошибок перевода"""
    pass

class DeepLError(TranslationError):
    """Ошибка при работе с DeepL API"""
    pass

class FileOperationError(TranslationError):
    """Ошибка при работе с файлами"""
    pass

def extract_marker_and_text(text: str) -> (str, str):
    """Если строка начинается с changed_, возвращает (маркер без ведущих подчёркиваний, основной текст)"""
    if text.startswith("changed_"):
        i = 7
        while i < len(text) and (text[i].isdigit() or text[i] == '_'):
            i += 1
        marker = text[7:i].lstrip('_')  # убираем ведущие подчёркивания
        main_text = text[i:]
        return marker, main_text
    return '', text

def sanitize_text(text: str) -> str:
    """Очистка текста от специальных символов и HTML-сущностей, не удаляет маркер"""
    text = html.unescape(text)
    text = ''.join(char for char in text if char.isprintable() or char == '\n')
    return text.strip()

def translate_text(text: str, target_lang: str) -> str:
    """Перевод текста через DeepL API с обработкой ошибок и переносом только маркера"""
    if not text.strip():
        return text
    marker, main_text = extract_marker_and_text(text)
    try:
        data = {
            "auth_key": DEEPL_API_KEY,
            "text": sanitize_text(main_text if marker else text),
            "target_lang": target_lang
        }
        response = requests.post(DEEPL_URL, data=data)
        response.raise_for_status()
        translated = response.json()["translations"][0]["text"]
        return marker + translated if marker else translated
    except RequestException as e:
        logger.error(f"DeepL API error: {str(e)}")
        raise DeepLError(f"Failed to translate text: {str(e)}")
    except (KeyError, IndexError) as e:
        logger.error(f"Invalid DeepL API response: {str(e)}")
        raise DeepLError(f"Invalid API response: {str(e)}")

def load_language_file(file_path: str) -> Dict:
    """Загрузка языкового файла с обработкой ошибок"""
    try:
        with open(file_path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Language file not found: {file_path}")
        raise FileOperationError(f"Language file not found: {file_path}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {file_path}: {str(e)}")
        raise FileOperationError(f"Invalid JSON in file {file_path}: {str(e)}")
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {str(e)}")
        raise FileOperationError(f"Error loading file {file_path}: {str(e)}")

def save_language_file(file_path: str, data: Dict) -> None:
    """Сохранение языкового файла с обработкой ошибок"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving file {file_path}: {str(e)}")
        raise FileOperationError(f"Error saving file {file_path}: {str(e)}")

def get_clean_value(value: str) -> str:
    """Получение чистого значения без префикса changed_XXX (только для сравнения)"""
    if isinstance(value, str) and value.startswith("changed_"):
        i = 7
        while i < len(value) and (value[i].isdigit() or value[i] == '_'):
            i += 1
        return value[i:]
    return value

def find_changed_keys(base_dict: Dict, target_dict: Dict) -> Tuple[Set[str], Set[str], Set[str]]:
    """Поиск изменений в ключах между файлами"""
    base_keys = set(base_dict.keys())
    target_keys = set(target_dict.keys())
    
    new_keys = base_keys - target_keys
    removed_keys = target_keys - base_keys
    changed_keys = set()
    
    logger.info("Comparing keys:")
    for key in base_keys & target_keys:
        base_value = str(base_dict[key])
        target_value = str(target_dict[key])
        
        # Проверяем только те ключи, которые имеют префикс changed_ в русском файле
        if base_value.startswith("changed_"):
            logger.info(f"Key: {key}")
            logger.info(f"  Base value: {base_value}")
            logger.info(f"  Target value: {target_value}")
            logger.info(f"  -> Changed!")
            changed_keys.add(key)
    
    return new_keys, changed_keys, removed_keys

def translate_dict(d: Dict, target_lang: str) -> Dict:
    """Рекурсивный перевод вложенного словаря"""
    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = translate_dict(v, target_lang)
        elif isinstance(v, str):
            result[k] = translate_text(v, target_lang)
        else:
            result[k] = v
    return result

def update_translations(base_file: str, target_file: str, target_lang: str) -> None:
    """Обновление переводов с подробным логированием и удалением changed_ из ru.json после перевода"""
    try:
        logger.info(f"Loading base file: {base_file}")
        base_data = load_language_file(base_file)
        
        logger.info(f"Loading target file: {target_file}")
        target_data = load_language_file(target_file)
        
        # Обновляем секцию onboarding
        if "onboarding" in base_data and "onboarding" in target_data:
            logger.info("Base onboarding keys:")
            for k, v in base_data["onboarding"].items():
                logger.info(f"  {k}: {v}")
            
            logger.info("Target onboarding keys:")
            for k, v in target_data["onboarding"].items():
                logger.info(f"  {k}: {v}")
            
            new_keys, changed_keys, removed_keys = find_changed_keys(
                base_data["onboarding"], 
                target_data["onboarding"]
            )
            
            logger.info(f"Found in onboarding: {len(new_keys)} new keys, {len(changed_keys)} changed keys, {len(removed_keys)} removed keys")
            if changed_keys:
                logger.info("Changed keys:")
                for key in changed_keys:
                    logger.info(f"  {key}")
            
            # Добавляем новые ключи
            for key in new_keys:
                target_data["onboarding"][key] = translate_text(str(base_data["onboarding"][key]), target_lang)
            
            # Обновляем изменённые ключи
            for key in changed_keys:
                target_data["onboarding"][key] = translate_text(str(base_data["onboarding"][key]), target_lang)
            
            # Удаляем устаревшие ключи
            for key in removed_keys:
                if key in target_data["onboarding"]:
                    del target_data["onboarding"][key]
        
        logger.info(f"Saving updated translations to: {target_file}")
        save_language_file(target_file, target_data)
        
        # Если это был русский файл, убираем префиксы changed_XXX
        if target_file.endswith('ru.json'):
            logger.info("Cleaning up changed_ prefixes from Russian file")
            if "onboarding" in base_data:
                for key in base_data["onboarding"]:
                    value = base_data["onboarding"][key]
                    if isinstance(value, str) and value.startswith("changed_"):
                        marker, main_text = extract_marker_and_text(value)
                        base_data["onboarding"][key] = marker + main_text
            save_language_file(base_file, base_data)
        
    except TranslationError as e:
        logger.error(f"Translation error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise

def main():
    """Основная функция с обработкой ошибок"""
    if not DEEPL_API_KEY:
        logger.error("DEEPL_API_KEY not found in environment variables")
        return

    logger.info("Starting translation update process")
    base_file = os.path.join(TEMPLATES_DIR, 'ru.json')
    
    try:
        for code, deepl_code in LANG_MAP.items():
            if code == "ru":
                continue
            target_file = os.path.join(TEMPLATES_DIR, f"{code}.json")
            logger.info(f"Processing language: {code} ({deepl_code})")
            update_translations(base_file, target_file, deepl_code)
            logger.info(f"Successfully updated: {target_file}")
            
        # После всех переводов очищаем ru.json
        update_translations(base_file, base_file, "RU")
        
    except Exception as e:
        logger.error(f"Failed to complete translation update: {str(e)}")
        raise

if __name__ == "__main__":
    main()
