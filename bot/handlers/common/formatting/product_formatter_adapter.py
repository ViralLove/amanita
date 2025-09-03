"""
Адаптер для существующих функций форматирования продуктов.
Реализует интерфейс IProductFormatter, используя текущие функции.
"""

from .product_formatter_interface import IProductFormatter
from .product_formatter import (
    format_product_for_telegram as _format_product_for_telegram,
    format_main_info_ux as _format_main_info_ux,
    format_composition_ux as _format_composition_ux,
    format_pricing_ux as _format_pricing_ux,
    format_details_ux as _format_details_ux,
    format_product_details_for_telegram as _format_product_details_for_telegram
)
from bot.services.common.localization import Localization
from typing import Dict, Any


class ProductFormatterAdapter(IProductFormatter):
    """
    Адаптер для существующих функций форматирования.
    
    Этот класс реализует интерфейс IProductFormatter, используя
    существующие функции форматирования. Это обеспечивает:
    - Совместимость с существующим кодом
    - Возможность постепенного перехода на новый интерфейс
    - Легкое тестирование через mock'и
    """
    
    def format_product_for_telegram(self, product: Any, loc: Localization) -> Dict[str, str]:
        """
        Форматирует продукт для отображения в Telegram.
        
        Args:
            product: Объект Product для форматирования
            loc: Объект локализации
            
        Returns:
            Dict[str, str]: Словарь с отформатированными секциями
        """
        return _format_product_for_telegram(product, loc)
    
    def format_main_info_ux(self, product: Any, loc: Localization) -> str:
        """
        Форматирует основную информацию о продукте.
        
        Args:
            product: Объект Product
            loc: Объект локализации
            
        Returns:
            str: Отформатированная основная информация
        """
        return _format_main_info_ux(product, loc)
    
    def format_composition_ux(self, product: Any, loc: Localization) -> str:
        """
        Форматирует состав продукта.
        
        Args:
            product: Объект Product
            loc: Объект локализации
            
        Returns:
            str: Отформатированный состав
        """
        return _format_composition_ux(product, loc)
    
    def format_pricing_ux(self, product: Any, loc: Localization) -> str:
        """
        Форматирует информацию о ценах.
        
        Args:
            product: Объект Product
            loc: Объект локализации
            
        Returns:
            str: Отформатированная информация о ценах
        """
        return _format_pricing_ux(product, loc)
    
    def format_details_ux(self, product: Any, loc: Localization) -> str:
        """
        Форматирует детали продукта.
        
        Args:
            product: Объект Product
            loc: Объект локализации
            
        Returns:
            str: Отформатированные детали
        """
        return _format_details_ux(product, loc)
    
    def format_product_details_for_telegram(self, product: Any, loc: Localization) -> str:
        """
        Форматирует детальную информацию о продукте.
        
        Args:
            product: Объект продукта
            loc: Объект локализации
            
        Returns:
            str: Отформатированный HTML текст с детальной информацией
        """
        return _format_product_details_for_telegram(product, loc)
