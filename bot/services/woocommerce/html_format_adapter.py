"""
HTML Format Adapter for WooCommerce Export

Адаптер для форматирования продуктов в HTML для WooCommerce.
Реюзит логику структурирования секций из ProductFormatterService,
применяет HTML-специфичное форматирование напрямую.
"""

import logging
from typing import Dict, Any
from services.common.localization import Localization
from handlers.common.formatting.product_formatter_service import ProductFormatterService
from model.product import Product


class HTMLFormatAdapter:
    """
    Адаптер для форматирования продуктов в HTML для WooCommerce.
    
    ✅ РЕЮЗ: Использует логику структурирования секций из ProductFormatterService
    ❌ РАЗДЕЛЕНИЕ: Применяет HTML-специфичное форматирование (адаптер для WooCommerce)
    
    Архитектурный принцип:
    - Реюзим: структуру секций (что форматировать)
    - Разделяем: HTML форматирование (как отображать)
    """
    
    def __init__(self, formatter_service: ProductFormatterService):
        """
        Инициализация адаптера.
        
        Args:
            formatter_service: ProductFormatterService для получения структуры секций
            
        Raises:
            ValueError: Если formatter_service равен None
        """
        if formatter_service is None:
            raise ValueError("formatter_service не может быть None")
        
        self.formatter_service = formatter_service
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("[HTMLFormatAdapter] Инициализирован")
    
    def _format_main_info_html(self, product: Product, loc: Localization) -> str:
        """
        Форматирует основную информацию о продукте в HTML.
        
        ✅ РЕЮЗ: Логику структурирования из formatter_service.format_main_info_ux()
        ❌ АДАПТЕР: Применяет HTML форматирование напрямую (не конвертирует из Telegram HTML)
        
        Перенесенные элементы из format_main_info_ux():
        - Название продукта (с эмодзи 🏷️)
        - Вид продукта (с эмодзи 🌿)
        - Статус продукта (с эмодзи ✅ или ⏸️)
        
        Примечание: Эмодзи для компонентов (🧬), warnings (⚠️) и dosage (💊) 
        будут реализованы в других методах:
        - _format_composition_html() - для эмодзи компонентов
        - _format_details_html() - для warnings и dosage (если они входят в details)
        
        Args:
            product: Продукт для форматирования
            loc: Объект локализации
            
        Returns:
            str: HTML строка с основной информацией или пустая строка
        """
        try:
            html_parts = []
            
            # ✅ РЕЮЗ: Получаем локализованное название (та же логика что в format_main_info_ux)
            product_title = self.formatter_service._get_product_title(product, loc)
            if product_title:
                # ✅ РЕЮЗ: Эмодзи для продукта (та же логика что в format_main_info_ux)
                product_emoji = self.formatter_service.config.get_emoji('product')
                html_parts.append(f"<p>{product_emoji} <strong>{product_title}</strong></p>")
            
            # ✅ РЕЮЗ: Вид продукта (та же логика что в format_main_info_ux)
            if hasattr(product, 'species') and product.species:
                # ✅ РЕЮЗ: Эмодзи для вида (та же логика что в format_main_info_ux)
                species_emoji = self.formatter_service.config.get_emoji('species')
                html_parts.append(f"<p>{species_emoji} <strong>{product.species}</strong></p>")
            
            # ✅ РЕЮЗ: Статус продукта (та же логика что в format_main_info_ux)
            if hasattr(product, 'status'):
                if product.status == 1:
                    # ✅ РЕЮЗ: Эмодзи для статуса доступен (та же логика что в format_main_info_ux)
                    status_emoji = self.formatter_service.config.get_emoji('status_available')
                    status_text = loc.t('catalog.product.available_for_order')
                    html_parts.append(f"<p>{status_emoji} <strong>{status_text}</strong></p>")
                else:
                    # ✅ РЕЮЗ: Эмодзи для статуса недоступен (та же логика что в format_main_info_ux)
                    status_emoji = self.formatter_service.config.get_emoji('status_unavailable')
                    status_text = loc.t('catalog.product.temporarily_unavailable')
                    html_parts.append(f"<p>{status_emoji} <strong>{status_text}</strong></p>")
            
            # Возвращаем объединенный HTML или пустую строку
            return '\n'.join(html_parts) if html_parts else ''
            
        except Exception as e:
            self.logger.error(
                f"[HTMLFormatAdapter] Ошибка форматирования основной информации для {getattr(product, 'business_id', 'unknown')}: {e}",
                exc_info=True
            )
            # Fallback: возвращаем базовое название если есть
            try:
                title = getattr(product, 'title', 'Продукт')
                return f"<p><strong>{title}</strong></p>"
            except:
                return ''
    
    def _format_composition_html(self, product: Product, loc: Localization) -> str:
        """
        Форматирует состав продукта в HTML.
        
        ✅ РЕЮЗ: Логику структурирования из formatter_service.format_composition_ux()
        ❌ АДАПТЕР: Применяет HTML форматирование напрямую (не конвертирует из Telegram HTML)
        
        Перенесенные элементы из format_composition_ux():
        - Заголовок секции с эмодзи composition (🔬)
        - Проверка наличия organic_components
        - Определение типа продукта (SINGLE/MULTI)
        - Для SINGLE: scientific_title с эмодзи 🧬 или component_id
        - Для MULTI: нумерованный список компонентов
        - Добавление proportion если есть
        
        Args:
            product: Продукт для форматирования
            loc: Объект локализации
            
        Returns:
            str: HTML строка с составом продукта или пустая строка
        """
        try:
            html_parts = []
            
            # ✅ РЕЮЗ: Проверка наличия компонентов (та же логика что в format_composition_ux)
            if not hasattr(product, 'organic_components') or not product.organic_components:
                composition_emoji = self.formatter_service.config.get_emoji('composition')
                composition_text = loc.t('catalog.product.composition')
                not_specified_text = loc.t('catalog.product.composition_not_specified')
                html_parts.append(f"<p>{composition_emoji} <strong>{composition_text}</strong>: {not_specified_text}</p>")
                return '\n'.join(html_parts)
            
            # ✅ РЕЮЗ: Определение типа продукта (та же логика что в format_composition_ux)
            product_type = self.formatter_service._detect_product_type(product)
            
            # ✅ РЕЮЗ: Заголовок секции с эмодзи (та же логика что в format_composition_ux)
            composition_emoji = self.formatter_service.config.get_emoji('composition')
            composition_title = loc.t('catalog.product.composition_title')
            html_parts.append(f"<p>{composition_emoji} <strong>{composition_title}</strong></p>")
            
            if product_type == "SINGLE":
                # ✅ РЕЮЗ: Краткое отображение для монокомпонентного (та же логика что в format_composition_ux)
                component = product.organic_components[0]
                
                component_html = "<p>"
                
                # ✅ РЕЮЗ: Эмодзи 🧬 для scientific_title (та же логика что в format_composition_ux)
                if hasattr(component, 'scientific_title') and component.scientific_title:
                    scientific_emoji = "🧬"
                    component_html += f"   {scientific_emoji} <strong>{component.scientific_title}</strong>"
                else:
                    component_html += f"   {component.component_id}"
                
                # ✅ РЕЮЗ: Добавление proportion (та же логика что в format_composition_ux)
                if hasattr(component, 'proportion') and component.proportion:
                    component_html += f" • {component.proportion}"
                
                component_html += "</p>"
                html_parts.append(component_html)
                
            else:
                # ✅ РЕЮЗ: Список для мультикомпонентного (та же логика что в format_composition_ux)
                html_parts.append("<ul>")
                
                for i, component in enumerate(product.organic_components, 1):
                    # ✅ РЕЮЗ: Получение названия компонента (та же логика что в format_composition_ux)
                    comp_name = self.formatter_service._get_component_display_name(component, loc)
                    
                    component_html = f"<li><strong>{comp_name}</strong>"
                    
                    # ✅ РЕЮЗ: Добавление proportion (та же логика что в format_composition_ux)
                    if hasattr(component, 'proportion') and component.proportion:
                        component_html += f" • {component.proportion}"
                    
                    component_html += "</li>"
                    html_parts.append(component_html)
                
                html_parts.append("</ul>")
            
            return '\n'.join(html_parts) if html_parts else ''
            
        except Exception as e:
            self.logger.error(
                f"[HTMLFormatAdapter] Ошибка форматирования состава для {getattr(product, 'business_id', 'unknown')}: {e}",
                exc_info=True
            )
            # Fallback: возвращаем базовое сообщение
            try:
                composition_emoji = self.formatter_service.config.get_emoji('composition')
                composition_text = loc.t('catalog.product.composition')
                not_specified_text = loc.t('catalog.product.composition_not_specified')
                return f"<p>{composition_emoji} <strong>{composition_text}</strong>: {not_specified_text}</p>"
            except:
                return ''
    
    def _format_pricing_html(self, product: Product, loc: Localization) -> str:
        """
        Форматирует информацию о ценах в HTML.
        
        ✅ РЕЮЗ: Логику структурирования из formatter_service.format_pricing_ux()
        ❌ АДАПТЕР: Применяет HTML форматирование напрямую (не конвертирует из Telegram HTML)
        
        Перенесенные элементы из format_pricing_ux():
        - Заголовок секции с эмодзи pricing (💰)
        - Проверка наличия product.prices
        - Для каждой цены: номер, цена + валюта, вес/объем, форма
        
        Args:
            product: Продукт для форматирования
            loc: Объект локализации
            
        Returns:
            str: HTML строка с ценами или пустая строка
        """
        try:
            html_parts = []
            
            # ✅ РЕЮЗ: Проверка наличия цен (та же логика что в format_pricing_ux)
            if not hasattr(product, 'prices') or not product.prices:
                pricing_emoji = self.formatter_service.config.get_emoji('pricing')
                pricing_text = loc.t('catalog.product.pricing')
                not_specified_text = loc.t('catalog.product.pricing_not_specified')
                html_parts.append(f"<p>{pricing_emoji} <strong>{pricing_text}</strong>: {not_specified_text}</p>")
                return '\n'.join(html_parts)
            
            # ✅ РЕЮЗ: Заголовок секции с эмодзи (та же логика что в format_pricing_ux)
            pricing_emoji = self.formatter_service.config.get_emoji('pricing')
            pricing_title = loc.t('catalog.product.pricing_title')
            html_parts.append(f"<p>{pricing_emoji} <strong>{pricing_title}</strong></p>")
            
            # ✅ РЕЮЗ: Список цен (та же логика что в format_pricing_ux)
            html_parts.append("<ul>")
            
            for i, price in enumerate(product.prices, 1):
                price_html = f"<li>"
                
                # ✅ РЕЮЗ: Цена + валюта (та же логика что в format_pricing_ux)
                if hasattr(price, 'price') and price.price:
                    currency = getattr(price, 'currency', '')
                    price_html += f"<strong>{price.price} {currency}</strong>"
                
                # ✅ РЕЮЗ: Вес или объем (та же логика что в format_pricing_ux)
                price_separator = self.formatter_service.config.get_template('price_separator')  # " за "
                if hasattr(price, 'weight') and price.weight:
                    weight_unit = getattr(price, 'weight_unit', '')
                    price_html += f"{price_separator}<strong>{price.weight} {weight_unit}</strong>"
                elif hasattr(price, 'volume') and price.volume:
                    volume_unit = getattr(price, 'volume_unit', '')
                    price_html += f"{price_separator}<strong>{price.volume} {volume_unit}</strong>"
                
                # ✅ РЕЮЗ: Форма продукта (та же логика что в format_pricing_ux)
                form_separator = self.formatter_service.config.get_template('form_separator')  # " • "
                if hasattr(price, 'form') and price.form:
                    price_html += f"{form_separator}{price.form}"
                
                price_html += "</li>"
                html_parts.append(price_html)
            
            html_parts.append("</ul>")
            
            return '\n'.join(html_parts) if html_parts else ''
            
        except Exception as e:
            self.logger.error(
                f"[HTMLFormatAdapter] Ошибка форматирования цен для {getattr(product, 'business_id', 'unknown')}: {e}",
                exc_info=True
            )
            # Fallback: возвращаем базовое сообщение
            try:
                pricing_emoji = self.formatter_service.config.get_emoji('pricing')
                pricing_text = loc.t('catalog.product.pricing')
                not_specified_text = loc.t('catalog.product.pricing_not_specified')
                return f"<p>{pricing_emoji} <strong>{pricing_text}</strong>: {not_specified_text}</p>"
            except:
                return ''
    
    def _format_details_html(self, product: Product, loc: Localization) -> str:
        """
        Форматирует детали продукта в HTML.
        
        ✅ РЕЮЗ: Логику структурирования из formatter_service.format_details_ux()
        ❌ АДАПТЕР: Применяет HTML форматирование напрямую (не конвертирует из Telegram HTML)
        
        Перенесенные элементы из format_details_ux():
        - Заголовок секции с эмодзи details (📋)
        - Формы продукта с эмодзи forms (📦)
        - Категории продукта с эмодзи categories (🏷️)
        
        Args:
            product: Продукт для форматирования
            loc: Объект локализации
            
        Returns:
            str: HTML строка с деталями или пустая строка
        """
        try:
            html_parts = []
            
            # ✅ РЕЮЗ: Заголовок секции с эмодзи (та же логика что в format_details_ux)
            details_emoji = self.formatter_service.config.get_emoji('details')
            details_text = loc.t('catalog.product.details')
            html_parts.append(f"<p>{details_emoji} <strong>{details_text}</strong></p>")
            
            # ✅ РЕЮЗ: Формы продукта (та же логика что в format_details_ux)
            if hasattr(product, 'forms') and product.forms:
                forms_emoji = self.formatter_service.config.get_emoji('forms')
                forms_label = loc.t('catalog.product.forms_label')
                forms_text = ', '.join(product.forms)
                html_parts.append(f"<p>{forms_emoji} <strong>{forms_label}</strong>: {forms_text}</p>")
            
            # ✅ РЕЮЗ: Категории продукта (та же логика что в format_details_ux)
            if hasattr(product, 'categories') and product.categories:
                categories_emoji = self.formatter_service.config.get_emoji('categories')
                category_label = loc.t('catalog.product.category_label')
                categories_text = ', '.join(product.categories)
                html_parts.append(f"<p>{categories_emoji} <strong>{category_label}</strong>: {categories_text}</p>")
            
            return '\n'.join(html_parts) if html_parts else ''
            
        except Exception as e:
            self.logger.error(
                f"[HTMLFormatAdapter] Ошибка форматирования деталей для {getattr(product, 'business_id', 'unknown')}: {e}",
                exc_info=True
            )
            # Fallback: возвращаем базовое сообщение
            try:
                details_emoji = self.formatter_service.config.get_emoji('details')
                details_text = loc.t('catalog.product.details')
                return f"<p>{details_emoji} <strong>{details_text}</strong></p>"
            except:
                return ''
    
    def format_product_html(self, product: Product, loc: Localization) -> str:
        """
        Форматирует продукт в HTML для WooCommerce.
        
        ✅ РЕЮЗ: Использует логику структурирования секций из ProductFormatterService
        ❌ АДАПТЕР: Применяет HTML-специфичное форматирование напрямую (не конвертирует из Telegram HTML)
        
        Объединяет все секции форматирования:
        - main_info: Название, вид, статус
        - composition: Состав продукта
        - pricing: Цены и формы
        - details: Формы и категории
        
        Примечание: `loc: Localization` используется для UI переводов (templates),
        переводы продуктов берутся из `formatter_service.localization_service` (IPFS).
        
        Args:
            product: Продукт для форматирования
            loc: Объект локализации
            
        Returns:
            str: HTML описание продукта
        """
        try:
            html_parts = []
            
            # ✅ РЕЮЗ: Используем логику структурирования из ProductFormatterService
            # ❌ АДАПТЕР: Применяем HTML форматирование напрямую
            
            # Вызываем методы форматирования секций в правильном порядке
            main_info = self._format_main_info_html(product, loc)
            if main_info and main_info.strip():
                html_parts.append(main_info)
            
            composition = self._format_composition_html(product, loc)
            if composition and composition.strip():
                html_parts.append(composition)
            
            pricing = self._format_pricing_html(product, loc)
            if pricing and pricing.strip():
                html_parts.append(pricing)
            
            details = self._format_details_html(product, loc)
            if details and details.strip():
                html_parts.append(details)
            
            # Объединяем секции через двойной перевод строки для разделения
            return '\n\n'.join(html_parts) if html_parts else ''
            
        except Exception as e:
            self.logger.error(
                f"[HTMLFormatAdapter] Ошибка форматирования продукта для {getattr(product, 'business_id', 'unknown')}: {e}",
                exc_info=True
            )
            # Fallback: возвращаем базовое описание
            try:
                title = getattr(product, 'title', 'Продукт')
                return f"<p>{title}</p>"
            except:
                return '<p>Продукт</p>'
    
    def get_product_title(self, product: Product, language: str) -> str:
        """
        Получает локализованное название продукта.
        
        ✅ РЕЮЗ: Использует логику из ProductFormatterService._get_product_title().
        
        Система локализации (двухуровневая):
        - `Localization(language)` используется для UI переводов (templates)
        - `formatter_service.localization_service` используется для переводов продуктов из IPFS
          (внутри `_get_product_title()` вызывается `localization_service.t(f'product.{business_id}.title')`)
        
        TODO: После рефакторинга ProductFormatterService использовать публичный метод:
        `formatter_service.get_product_title(product, language)` вместо приватного `_get_product_title()`.
        
        Args:
            product: Продукт
            language: Язык локализации (например, "ru", "en")
            
        Returns:
            str: Локализованное название продукта
        """
        try:
            # Создаем объект Localization из языка (для UI переводов, если нужны)
            # Примечание: внутри _get_product_title() используется formatter_service.localization_service
            # для переводов продуктов из IPFS через localization_service.t(f'product.{business_id}.title')
            loc = Localization(language)
            
            # ✅ РЕЮЗ: Используем существующий метод (временно приватный)
            # TODO: После рефакторинга ProductFormatterService использовать публичный метод:
            # return self.formatter_service.get_product_title(product, language)
            return self.formatter_service._get_product_title(product, loc)
            
        except Exception as e:
            self.logger.error(
                f"[HTMLFormatAdapter] Ошибка получения названия для {getattr(product, 'business_id', 'unknown')}: {e}",
                exc_info=True
            )
            # Fallback: возвращаем базовое название
            return getattr(product, 'title', 'Продукт')

