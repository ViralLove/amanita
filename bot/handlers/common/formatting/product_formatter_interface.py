"""
Интерфейс для форматирования продуктов в Telegram.
Определяет контракт для всех реализаций форматирования.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from bot.services.common.localization import Localization


class IProductFormatter(ABC):
    """
    Абстрактный интерфейс для форматирования продуктов в Telegram.
    
    Этот интерфейс определяет контракт для всех реализаций форматирования,
    обеспечивая возможность легкой замены логики форматирования
    и упрощение тестирования через mock'и.
    """
    
    @abstractmethod
    def format_product_for_telegram(self, product: Any, loc: Localization) -> Dict[str, str]:
        """
        Форматирует продукт для отображения в Telegram с UX-оптимизированным подходом.
        Показывает только информацию, важную для покупателей.
        
        Args:
            product: Объект Product для форматирования
            loc: Объект локализации
            
        Returns:
            Dict[str, str]: Словарь с отформатированными секциями
        """
        pass
    
    @abstractmethod
    def format_main_info_ux(self, product: Any, loc: Localization) -> str:
        """
        Форматирует основную информацию о продукте для покупателей.
        
        Args:
            product: Объект Product
            loc: Объект локализации
            
        Returns:
            str: Отформатированная основная информация
        """
        pass
    
    @abstractmethod
    def format_composition_ux(self, product: Any, loc: Localization) -> str:
        """
        Форматирует состав продукта для покупателей.
        
        Args:
            product: Объект Product
            loc: Объект локализации
            
        Returns:
            str: Отформатированный состав
        """
        pass
    
    @abstractmethod
    def format_pricing_ux(self, product: Any, loc: Localization) -> str:
        """
        Форматирует информацию о ценах для покупателей.
        
        Args:
            product: Объект Product
            loc: Объект локализации
            
        Returns:
            str: Отформатированная информация о ценах
        """
        pass
    
    @abstractmethod
    def format_details_ux(self, product: Any, loc: Localization) -> str:
        """
        Форматирует детали продукта для покупателей.
        
        Args:
            product: Объект Product
            loc: Объект локализации
            
        Returns:
            str: Отформатированные детали
        """
        pass
    
    @abstractmethod
    def format_product_details_for_telegram(self, product: Any, loc: Localization) -> str:
        """
        Форматирует детальную информацию о продукте для Telegram.
        Создает полное описание с учетом всех доступных данных.
        Предотвращает дублирование заголовков секций.
        Оптимизировано для мобильных устройств и эзотерических продуктов.
        
        Args:
            product: Объект продукта
            loc: Объект локализации
            
        Returns:
            str: Отформатированный HTML текст с детальной информацией
        """
        pass
    
    @abstractmethod
    def format_product_main_info_for_telegram(self, product: Any, loc: Localization) -> str:
        """
        Форматирует основную информацию о продукте для первого сообщения с изображением.
        Содержит ключевые характеристики: название, вид, статус, состав, цены, категории.
        
        Args:
            product: Объект продукта
            loc: Объект локализации
            
        Returns:
            str: Отформатированный HTML текст с основной информацией
        """
        pass
    
    @abstractmethod
    def format_product_description_for_telegram(self, product: Any, loc: Localization) -> str:
        """
        Форматирует детальное описание продукта для второго сообщения.
        Содержит нарративный контент: активные компоненты, эффекты, шаманская перспектива, предостережения.
        
        Args:
            product: Объект продукта
            loc: Объект локализации
            
        Returns:
            str: Отформатированный HTML текст с детальным описанием
        """
        pass
