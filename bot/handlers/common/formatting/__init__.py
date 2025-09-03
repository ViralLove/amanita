"""
Модуль форматирования для Telegram handlers.
Содержит утилиты для форматирования текста и продуктов.
"""

from .text_formatter import truncate_text_for_telegram
from .product_formatter import (
    format_product_for_telegram,
    format_main_info_ux,
    format_composition_ux,
    format_pricing_ux,
    format_details_ux,
    format_product_details_for_telegram
)
# Новые методы доступны через ProductFormatterService
from .section_tracker import SectionTracker
from .product_formatter_interface import IProductFormatter
from .product_formatter_adapter import ProductFormatterAdapter
from .product_formatter_config import ProductFormatterConfig
from .product_formatter_service import ProductFormatterService

__all__ = [
    'truncate_text_for_telegram',
    'format_product_for_telegram',
    'format_main_info_ux',
    'format_composition_ux',
    'format_pricing_ux',
    'format_details_ux',
    'format_product_details_for_telegram',
    'SectionTracker',
    'IProductFormatter',
    'ProductFormatterAdapter',
    'ProductFormatterConfig',
    'ProductFormatterService'
]
