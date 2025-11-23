"""
FallbackLocalizationService - Каскадный fallback для локализации

Обеспечивает каскадную стратегию fallback:
1. Запрошенный язык - основной перевод
2. Русский язык - fallback по умолчанию  
3. Ключ перевода - если перевод не найден
4. Placeholder - последний fallback

Интегрируется с LocalizationService для обеспечения надёжности переводов.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class FallbackLevel(Enum):
    """Уровни fallback стратегии"""
    REQUESTED_LANGUAGE = "requested_language"
    DEFAULT_LANGUAGE = "default_language"  # Русский
    TRANSLATION_KEY = "translation_key"
    PLACEHOLDER = "placeholder"

@dataclass
class FallbackResult:
    """Результат fallback операции"""
    translation: str
    level: FallbackLevel
    source: str  # Откуда получен перевод
    confidence: float  # Уверенность в качестве (0.0-1.0)

class FallbackLocalizationService:
    """Сервис каскадного fallback для локализации"""
    
    def __init__(self, default_language: str = 'ru'):
        """
        Инициализация сервиса fallback
        
        Args:
            default_language: Язык по умолчанию для fallback
        """
        self.default_language = default_language
        self.logger = logging.getLogger(__name__)
        
        # Статистика fallback операций
        self.fallback_stats = {
            'total_requests': 0,
            'requested_language_hits': 0,
            'default_language_hits': 0,
            'translation_key_hits': 0,
            'placeholder_hits': 0,
            'errors': 0
        }
        
        # Конфигурация fallback стратегий
        self.fallback_config = {
            'enable_cascade': True,
            'enable_translation_key_fallback': True,
            'enable_placeholder_fallback': True,
            'confidence_threshold': 0.5
        }
        
        # Placeholder шаблоны для разных типов контента
        self.placeholder_templates = {
            'product': {
                'title': '[Название продукта]',
                'description': '[Описание продукта]',
                'ingredients': '[Состав продукта]',
                'dosage': '[Дозировка]',
                'contraindications': '[Противопоказания]'
            },
            'component': {
                'common_name': '[Название компонента]',
                'scientific_name': '[Научное название]',
                'description': '[Описание компонента]',
                'properties': '[Свойства компонента]',
                'safety': '[Безопасность]'
            },
            'interface': {
                'button': '[Кнопка]',
                'message': '[Сообщение]',
                'error': '[Ошибка]',
                'success': '[Успех]',
                'loading': '[Загрузка]'
            }
        }
        
        self.logger.info(f"[FallbackLocalizationService] Инициализирован с языком по умолчанию: {default_language}")
    
    def get_translation_with_fallback(self, 
                                    key: str, 
                                    requested_language: str,
                                    translation_sources: Dict[str, Any],
                                    default: Optional[str] = None,
                                    **kwargs) -> FallbackResult:
        """
        Получает перевод с каскадным fallback
        
        Args:
            key: Ключ перевода (например, 'product.business_id.title')
            requested_language: Запрошенный язык
            translation_sources: Источники переводов {language: {data}}
            default: Значение по умолчанию
            **kwargs: Параметры для форматирования
            
        Returns:
            FallbackResult: Результат с переводом и метаданными
        """
        self.fallback_stats['total_requests'] += 1
        
        try:
            # 1. Пытаемся получить перевод на запрошенном языке
            if requested_language in translation_sources:
                result = self._try_get_translation(key, requested_language, translation_sources[requested_language], **kwargs)
                if result:
                    self.fallback_stats['requested_language_hits'] += 1
                    return FallbackResult(
                        translation=result,
                        level=FallbackLevel.REQUESTED_LANGUAGE,
                        source=f"language_{requested_language}",
                        confidence=1.0
                    )
            
            # 2. Fallback на язык по умолчанию (русский)
            if self.default_language in translation_sources and requested_language != self.default_language:
                result = self._try_get_translation(key, self.default_language, translation_sources[self.default_language], **kwargs)
                if result:
                    self.fallback_stats['default_language_hits'] += 1
                    return FallbackResult(
                        translation=result,
                        level=FallbackLevel.DEFAULT_LANGUAGE,
                        source=f"language_{self.default_language}",
                        confidence=0.8
                    )
            
            # 3. Fallback на ключ перевода
            if self.fallback_config['enable_translation_key_fallback']:
                key_fallback = self._extract_key_fallback(key)
                if key_fallback:
                    self.fallback_stats['translation_key_hits'] += 1
                    return FallbackResult(
                        translation=key_fallback,
                        level=FallbackLevel.TRANSLATION_KEY,
                        source="translation_key",
                        confidence=0.3
                    )
            
            # 4. Fallback на placeholder
            if self.fallback_config['enable_placeholder_fallback']:
                placeholder = self._get_placeholder(key, default)
                self.fallback_stats['placeholder_hits'] += 1
                return FallbackResult(
                    translation=placeholder,
                    level=FallbackLevel.PLACEHOLDER,
                    source="placeholder",
                    confidence=0.1
                )
            
            # Если все fallback стратегии не сработали
            final_fallback = default or key
            self.fallback_stats['placeholder_hits'] += 1
            return FallbackResult(
                translation=final_fallback,
                level=FallbackLevel.PLACEHOLDER,
                source="final_fallback",
                confidence=0.0
            )
            
        except Exception as e:
            self.fallback_stats['errors'] += 1
            self.logger.error(f"[FallbackLocalizationService] Ошибка при получении перевода '{key}': {e}")
            
            # Возвращаем безопасный fallback при ошибке
            return FallbackResult(
                translation=default or key,
                level=FallbackLevel.PLACEHOLDER,
                source="error_fallback",
                confidence=0.0
            )
    
    def _try_get_translation(self, key: str, language: str, source_data: Dict[str, Any], **kwargs) -> Optional[str]:
        """
        Пытается получить перевод из источника данных
        
        Args:
            key: Ключ перевода
            language: Язык
            source_data: Данные источника
            **kwargs: Параметры форматирования
            
        Returns:
            Перевод или None
        """
        try:
            # Парсим ключ для определения типа и ID
            key_parts = key.split('.')
            if len(key_parts) < 3:
                return None
            
            content_type = key_parts[0]  # product, component, interface
            content_id = key_parts[1]    # business_id, component_id, section
            field = key_parts[2]         # title, description, etc.
            
            # Ищем в соответствующей секции
            if content_type in source_data:
                content_section = source_data[content_type]
                if content_id in content_section:
                    content_data = content_section[content_id]
                    if field in content_data:
                        translation = content_data[field]
                        return self._format_translation(translation, **kwargs)
            
            return None
            
        except Exception as e:
            self.logger.error(f"[FallbackLocalizationService] Ошибка при попытке получения перевода: {e}")
            return None
    
    def _extract_key_fallback(self, key: str) -> Optional[str]:
        """
        Извлекает fallback из ключа перевода
        
        Args:
            key: Ключ перевода
            
        Returns:
            Fallback строка или None
        """
        try:
            key_parts = key.split('.')
            if len(key_parts) >= 3:
                field = key_parts[2]
                # Возвращаем читаемый fallback на основе поля
                return f"[{field.replace('_', ' ').title()}]"
            return None
            
        except Exception as e:
            self.logger.error(f"[FallbackLocalizationService] Ошибка извлечения key fallback: {e}")
            return None
    
    def _get_placeholder(self, key: str, default: Optional[str] = None) -> str:
        """
        Получает placeholder для ключа
        
        Args:
            key: Ключ перевода
            default: Значение по умолчанию
            
        Returns:
            Placeholder строка
        """
        try:
            if default:
                return default
            
            key_parts = key.split('.')
            if len(key_parts) >= 3:
                content_type = key_parts[0]
                field = key_parts[2]
                
                # Ищем в шаблонах placeholder'ов
                if content_type in self.placeholder_templates:
                    if field in self.placeholder_templates[content_type]:
                        return self.placeholder_templates[content_type][field]
                
                # Общий fallback
                return f"[{field.replace('_', ' ').title()}]"
            
            return key
            
        except Exception as e:
            self.logger.error(f"[FallbackLocalizationService] Ошибка получения placeholder: {e}")
            return key
    
    def _format_translation(self, translation: str, **kwargs) -> str:
        """
        Форматирует перевод с подстановкой параметров
        
        Args:
            translation: Текст перевода
            **kwargs: Параметры для подстановки
            
        Returns:
            Отформатированный текст
        """
        try:
            if kwargs:
                return translation.format(**kwargs)
            return translation
        except Exception as e:
            self.logger.error(f"[FallbackLocalizationService] Ошибка форматирования: {e}")
            return translation
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получает статистику fallback операций с экспортом всех метрик
        
        Возвращает основные метрики:
        - total_requests: общее количество запросов
        - requested_language_hits: попадания на запрошенном языке
        - default_language_hits: попадания на языке по умолчанию
        - translation_key_hits: попадания на ключ перевода
        - placeholder_hits: использования placeholder'ов
        - errors: количество ошибок
        
        И производные метрики:
        - requested_language_rate_percent: процент попаданий на запрошенном языке (requested_language_hits / total_requests * 100)
        - default_language_rate_percent: процент попаданий на языке по умолчанию (default_language_hits / total_requests * 100)
        - placeholder_rate_percent: процент использования placeholder'ов (placeholder_hits / total_requests * 100)
        - error_rate_percent: процент ошибок (errors / total_requests * 100)
        
        Дополнительные метрики:
        - default_language: язык по умолчанию для fallback
        
        Returns:
            Dict[str, Any]: Статистика fallback операций с основными и производными метриками
        """
        total_requests = self.fallback_stats['total_requests']
        
        # Вычисляем производные метрики (защита от деления на ноль)
        if total_requests == 0:
            requested_language_rate = 0.0
            default_language_rate = 0.0
            placeholder_rate = 0.0
            error_rate = 0.0
        else:
            requested_language_rate = (self.fallback_stats['requested_language_hits'] / total_requests) * 100
            default_language_rate = (self.fallback_stats['default_language_hits'] / total_requests) * 100
            placeholder_rate = (self.fallback_stats['placeholder_hits'] / total_requests) * 100
            error_rate = (self.fallback_stats['errors'] / total_requests) * 100
        
        return {
            # Основные метрики
            'total_requests': total_requests,
            'requested_language_hits': self.fallback_stats['requested_language_hits'],
            'default_language_hits': self.fallback_stats['default_language_hits'],
            'translation_key_hits': self.fallback_stats['translation_key_hits'],
            'placeholder_hits': self.fallback_stats['placeholder_hits'],
            'errors': self.fallback_stats['errors'],
            # Производные метрики
            'requested_language_rate_percent': round(requested_language_rate, 2),
            'default_language_rate_percent': round(default_language_rate, 2),
            'placeholder_rate_percent': round(placeholder_rate, 2),
            'error_rate_percent': round(error_rate, 2),
            # Дополнительные метрики
            'default_language': self.default_language
        }
    
    def get_fallback_statistics(self) -> Dict[str, Any]:
        """
        Возвращает статистику fallback операций
        
        Returns:
            Словарь со статистикой
        """
        total_requests = self.fallback_stats['total_requests']
        if total_requests == 0:
            return {
                'total_requests': 0,
                'fallback_distribution': {},
                'success_rate': 0.0,
                'error_rate': 0.0
            }
        
        # Распределение по уровням fallback
        distribution = {
            'requested_language': self.fallback_stats['requested_language_hits'],
            'default_language': self.fallback_stats['default_language_hits'],
            'translation_key': self.fallback_stats['translation_key_hits'],
            'placeholder': self.fallback_stats['placeholder_hits']
        }
        
        # Процентное распределение
        fallback_distribution = {
            level: round((count / total_requests) * 100, 2)
            for level, count in distribution.items()
        }
        
        success_rate = round(((total_requests - self.fallback_stats['errors']) / total_requests) * 100, 2)
        error_rate = round((self.fallback_stats['errors'] / total_requests) * 100, 2)
        
        return {
            'total_requests': total_requests,
            'fallback_distribution': fallback_distribution,
            'success_rate': success_rate,
            'error_rate': error_rate,
            'confidence_threshold': self.fallback_config['confidence_threshold']
        }
    
    def configure_fallback(self, **config) -> None:
        """
        Настраивает параметры fallback
        
        Args:
            **config: Параметры конфигурации
        """
        for key, value in config.items():
            if key in self.fallback_config:
                self.fallback_config[key] = value
                self.logger.info(f"[FallbackLocalizationService] Настроен параметр {key}: {value}")
    
    def add_placeholder_template(self, content_type: str, field: str, template: str) -> None:
        """
        Добавляет шаблон placeholder'а
        
        Args:
            content_type: Тип контента (product, component, interface)
            field: Поле (title, description, etc.)
            template: Шаблон placeholder'а
        """
        if content_type not in self.placeholder_templates:
            self.placeholder_templates[content_type] = {}
        
        self.placeholder_templates[content_type][field] = template
        self.logger.info(f"[FallbackLocalizationService] Добавлен placeholder шаблон: {content_type}.{field}")
    
    def clear_statistics(self) -> None:
        """Очищает статистику fallback операций"""
        self.fallback_stats = {
            'total_requests': 0,
            'requested_language_hits': 0,
            'default_language_hits': 0,
            'translation_key_hits': 0,
            'placeholder_hits': 0,
            'errors': 0
        }
        self.logger.info("[FallbackLocalizationService] Статистика очищена")
    
    def get_confidence_score(self, result: FallbackResult) -> float:
        """
        Возвращает оценку уверенности в качестве перевода
        
        Args:
            result: Результат fallback операции
            
        Returns:
            Оценка уверенности (0.0-1.0)
        """
        return result.confidence
    
    def is_high_quality_translation(self, result: FallbackResult) -> bool:
        """
        Проверяет, является ли перевод высококачественным
        
        Args:
            result: Результат fallback операции
            
        Returns:
            True если перевод высококачественный
        """
        return (result.confidence >= self.fallback_config['confidence_threshold'] and
                result.level in [FallbackLevel.REQUESTED_LANGUAGE, FallbackLevel.DEFAULT_LANGUAGE])
