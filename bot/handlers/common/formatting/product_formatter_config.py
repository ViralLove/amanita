"""
Конфигурация для ProductFormatterService.
Определяет настройки форматирования продуктов.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import logging


@dataclass
class ProductFormatterConfig:
    """
    Конфигурация для сервиса форматирования продуктов.
    
    Attributes:
        max_text_length: Максимальная длина текста для Telegram
        enable_emoji: Включить использование эмодзи
        enable_html: Включить HTML разметку
        truncate_text: Обрезать длинный текст
        emoji_mapping: Кастомное сопоставление эмодзи
        text_templates: Шаблоны для различных типов текста
        logging_level: Уровень логирования для сервиса
    """
    
    # Основные настройки форматирования
    max_text_length: int = 4000
    enable_emoji: bool = True
    enable_html: bool = True
    truncate_text: bool = True
    
    # Кастомные настройки
    emoji_mapping: Dict[str, str] = field(default_factory=lambda: {
        'product': '🏷️',
        'species': '🌿',
        'status_available': '✅',
        'status_unavailable': '⏸️',
        'composition': '🔬',
        'pricing': '💰',
        'details': '📋',
        'forms': '📦',
        'categories': '🏷️',
        'description': '📖',
        'effects': '✨',
        'shamanic': '🧙‍♂️',
        'warnings': '⚠️',
        'dosage': '💊',
        'features': '🌟',
        'scientific_name': '🔬'
    })
    
    text_templates: Dict[str, str] = field(default_factory=lambda: {
        'truncate_indicator': '... <i>Текст обрезан для Telegram. Полное описание доступно в детальном просмотре.</i>',
        'section_separator': '\n',
        'component_separator': '\n',
        'price_separator': ' за ',
        'form_separator': ' • '
    })
    
    # Настройки логирования
    logging_level: int = logging.INFO
    enable_debug_logging: bool = False
    
    def __post_init__(self):
        """Валидация конфигурации после инициализации."""
        if self.max_text_length < 100:
            raise ValueError("max_text_length должен быть не менее 100 символов")
        
        if self.max_text_length > 10000:
            raise ValueError("max_text_length не должен превышать 10000 символов")
        
        # Устанавливаем уровень логирования
        logging.getLogger(__name__).setLevel(self.logging_level)
    
    def get_emoji(self, key: str, default: str = "•") -> str:
        """
        Получает эмодзи по ключу.
        
        Args:
            key: Ключ эмодзи
            default: Значение по умолчанию
            
        Returns:
            str: Эмодзи или значение по умолчанию
        """
        if not self.enable_emoji:
            return ""
        return self.emoji_mapping.get(key, default)
    
    def get_template(self, key: str, default: str = "") -> str:
        """
        Получает шаблон по ключу.
        
        Args:
            key: Ключ шаблона
            default: Значение по умолчанию
            
        Returns:
            str: Шаблон или значение по умолчанию
        """
        return self.text_templates.get(key, default)
    
    def should_truncate(self, text: str) -> bool:
        """
        Определяет, нужно ли обрезать текст.
        
        Args:
            text: Проверяемый текст
            
        Returns:
            bool: True если текст нужно обрезать
        """
        return self.truncate_text and len(text) > self.max_text_length
