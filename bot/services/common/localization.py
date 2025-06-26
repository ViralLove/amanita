# Сервис для загрузки и выбора языков (локализация) 
import json
import os
import logging
import traceback

# Создаем логгер для модуля локализации
logger = logging.getLogger(__name__)

class Localization:
    def __init__(self, lang='ru'):
        self.lang = lang
        logger.debug(f"[LOCALIZATION] Инициализация Localization с языком: {lang}")
        self.labels = self.load_labels(lang)
        
        # Сразу проверим критически важные ключи
        self._verify_critical_keys()

    def load_labels(self, lang):
        path = os.path.join(os.path.dirname(__file__), '..', 'templates', f'{lang}.json')
        logger.debug(f"[LOCALIZATION] Загрузка языкового файла: {path}")
        logger.debug(f"[LOCALIZATION] Файл существует: {os.path.exists(path)}")
        
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"[LOCALIZATION] Файл загружен, количество корневых ключей: {len(data)}")
                # Выведем первый уровень ключей для отладки
                logger.debug(f"[LOCALIZATION] Корневые ключи: {list(data.keys())}")
                # Проверим наличие onboarding в корневых ключах
                if 'onboarding' in data:
                    onboarding_keys = list(data['onboarding'].keys())
                    logger.debug(f"[LOCALIZATION] Ключи внутри 'onboarding': {onboarding_keys}")
                    # Проверим наличие success в ключах onboarding
                    if 'success' in data['onboarding']:
                        logger.debug(f"[LOCALIZATION] Значение 'onboarding.success': {data['onboarding']['success'][:30]}...")
                    else:
                        logger.error(f"[LOCALIZATION] Ключ 'success' отсутствует в 'onboarding'")
                        # Список всех ключей для отладки
                        logger.error(f"[LOCALIZATION] Доступные ключи: {onboarding_keys}")
                else:
                    logger.error(f"[LOCALIZATION] Ключ 'onboarding' отсутствует в корневых ключах")
                
                # Проверка на наличие ключей invite_prompt и success
                self._check_for_invite_and_success_keys(data)
                
                return data
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(f"[LOCALIZATION] Ошибка при загрузке файла {path}: {str(e)}")
            logger.error(f"[LOCALIZATION] Traceback: {stack_trace}")
            return {}
    
    def _check_for_invite_and_success_keys(self, data):
        """Проверяет наличие критических ключей для отладки"""
        if 'onboarding' not in data:
            logger.error("[LOCALIZATION] Отсутствует секция 'onboarding' в файле локализации")
            return
        
        # Проверяем invite_prompt
        if 'invite_prompt' not in data['onboarding']:
            logger.error("[LOCALIZATION] Отсутствует ключ 'invite_prompt' в секции 'onboarding'")
        else:
            logger.debug(f"[LOCALIZATION] Ключ 'invite_prompt' найден: {data['onboarding']['invite_prompt'][:50]}...")
        
        # Проверяем success
        if 'success' not in data['onboarding']:
            logger.error("[LOCALIZATION] Отсутствует ключ 'success' в секции 'onboarding'")
        else:
            logger.debug(f"[LOCALIZATION] Ключ 'success' найден: {data['onboarding']['success'][:50]}...")
    
    def _verify_critical_keys(self):
        """Проверяет наличие критических ключей в загруженных данных"""
        try:
            invite_prompt = self.t("onboarding.invite_prompt")
            logger.debug(f"[LOCALIZATION] Проверка ключа 'onboarding.invite_prompt': {invite_prompt[:30]}...")
            
            success = self.t("onboarding.success")
            logger.debug(f"[LOCALIZATION] Проверка ключа 'onboarding.success': {success[:30]}...")
        except Exception as e:
            logger.error(f"[LOCALIZATION] Ошибка при проверке критических ключей: {str(e)}")

    def t(self, key):
        # Пример: key = 'onboarding.welcome'
        logger.debug(f"[LOCALIZATION] Запрошен перевод для ключа: '{key}', язык: {self.lang}")
        parts = key.split('.')
        logger.debug(f"[LOCALIZATION] Ключ разбит на части: {parts}")
        
        value = self.labels
        
        # Печатаем состояние labels перед началом поиска
        logger.debug(f"[LOCALIZATION] Состояние labels: {type(value)}, корневые ключи: {list(value.keys()) if isinstance(value, dict) else 'не словарь'}")
        
        for i, part in enumerate(parts):
            logger.debug(f"[LOCALIZATION] Поиск части [{i}]: '{part}'")
            
            if not isinstance(value, dict):
                logger.error(f"[LOCALIZATION] Значение не является словарем на этапе поиска '{part}'")
                return key
                
            if part not in value:
                logger.error(f"[LOCALIZATION] Часть '{part}' не найдена. Доступные ключи: {list(value.keys())}")
                # Проверка на возможное различие в имени ключа (с подчеркиванием вместо точки)
                if part == 'success' and 'onboarding_success' in value:
                    logger.warning(f"[LOCALIZATION] Найден похожий ключ 'onboarding_success' вместо 'success'")
                return key
                
            value = value.get(part)
            logger.debug(f"[LOCALIZATION] Результат после поиска '{part}': {value if isinstance(value, (str, int, bool)) else type(value)}")
            
            if value is None:
                logger.error(f"[LOCALIZATION] Значение для части '{part}' равно None")
                return key
                
        logger.debug(f"[LOCALIZATION] Итоговый результат для ключа '{key}': {value if isinstance(value, (str, int, bool)) else type(value)}")
        return value 