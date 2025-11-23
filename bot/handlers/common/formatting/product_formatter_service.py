"""
Сервис форматирования продуктов для Telegram.
Реализует интерфейс IProductFormatter с поддержкой конфигурации и мультиязычности.
"""

import logging
from typing import Dict, Any, Optional, List
from services.common.localization import Localization
from services.common.localization_service import LocalizationService
from .product_formatter_interface import IProductFormatter
from .product_formatter_config import ProductFormatterConfig
from .section_tracker import SectionTracker, SectionTypes


class ProductFormatterService(IProductFormatter):
    """
    Сервис форматирования продуктов для Telegram.
    
    Этот сервис реализует интерфейс IProductFormatter и предоставляет:
    - Конфигурируемое форматирование
    - Логирование операций
    - Обработку ошибок
    - Расширяемость для различных стратегий
    """
    
    def __init__(self, config: Optional[ProductFormatterConfig] = None, localization_service: Optional[LocalizationService] = None):
        """
        Инициализация сервиса форматирования.
        
        Args:
            config: Конфигурация форматирования (если не указана, используется по умолчанию)
            localization_service: Сервис локализации для мультиязычности
        """
        self.config = config or ProductFormatterConfig()
        self.localization_service = localization_service
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.config.logging_level)
        
        self.logger.info(f"[ProductFormatterService] Инициализирован с конфигурацией: "
                        f"max_length={self.config.max_text_length}, "
                        f"emoji={self.config.enable_emoji}, "
                        f"html={self.config.enable_html}")
    
    def format_product_for_telegram(self, product: Any, loc: Localization) -> Dict[str, str]:
        """
        Форматирует продукт для отображения в Telegram с UX-оптимизированным подходом.
        
        Args:
            product: Объект Product для форматирования
            loc: Объект локализации
            
        Returns:
            Dict[str, str]: Словарь с отформатированными секциями
        """
        try:
            self.logger.debug(f"[ProductFormatterService] Форматирование продукта: {getattr(product, 'title', 'unknown')}")
            
            result = {
                'main_info': self.format_main_info_ux(product, loc),
                'composition': self.format_composition_ux(product, loc),
                'pricing': self.format_pricing_ux(product, loc),
                'details': self.format_details_ux(product, loc)
            }
            
            self.logger.debug(f"[ProductFormatterService] Продукт отформатирован успешно")
            return result
            
        except Exception as e:
            self.logger.error(f"[ProductFormatterService] Ошибка при форматировании продукта: {e}")
            # Fallback форматирование
            return self._fallback_formatting(product, loc)
    
    def format_main_info_ux(self, product: Any, loc: Localization) -> str:
        """
        Форматирует основную информацию о продукте для покупателей.
        
        Args:
            product: Объект Product
            loc: Объект локализации
            
        Returns:
            str: Отформатированная основная информация
        """
        try:
            # 🏷️ Название продукта - самое важное (используем локализованное название)
            product_title = self._get_product_title(product, loc)
            main_info = f"{self.config.get_emoji('product')} <b>{product_title}</b>{self.config.get_template('section_separator')}"
            
            # 🌿 Вид продукта - важно для понимания что это
            if product.species:
                main_info += f"{self.config.get_emoji('species')} <b>{product.species}</b>{self.config.get_template('section_separator')}"
            
            # ✅ Статус - активен ли продукт для покупки
            if product.status == 1:
                status_emoji = self.config.get_emoji('status_available')
                status_text = loc.t('catalog.product.available_for_order')
                main_info += f"{status_emoji} <b>{status_text}</b>{self.config.get_template('section_separator')}"
            else:
                status_emoji = self.config.get_emoji('status_unavailable')
                status_text = loc.t('catalog.product.temporarily_unavailable')
                main_info += f"{status_emoji} <b>{status_text}</b>{self.config.get_template('section_separator')}"
            
            return main_info
            
        except Exception as e:
            self.logger.error(f"[ProductFormatterService] Ошибка при форматировании основной информации: {e}")
            return f"{self.config.get_emoji('product')} <b>{getattr(product, 'title', 'Продукт')}</b>"
    
    def format_composition_ux(self, product: Any, loc: Localization) -> str:
        """
        Форматирует состав продукта для покупателей (краткая версия для каталога).
        
        Использует новую логику SINGLE/MULTI детекции с type detection.
        Backward compatible с продуктами без scientific_title.
        
        Args:
            product: Объект Product
            loc: Объект локализации
            
        Returns:
            str: Отформатированный состав (краткий)
        """
        try:
            if not hasattr(product, 'organic_components') or not product.organic_components:
                composition_emoji = self.config.get_emoji('composition')
                composition_text = f"{composition_emoji} <b>{loc.t('catalog.product.composition')}</b>: {loc.t('catalog.product.composition_not_specified')}{self.config.get_template('section_separator')}"
                return composition_text
            
            # Детекция типа продукта (SINGLE/MULTI)
            product_type = self._detect_product_type(product)
            
            composition_text = f"{self.config.get_emoji('composition')} <b>{loc.t('catalog.product.composition_title')}</b>{self.config.get_template('section_separator')}"
            
            if product_type == "SINGLE":
                # Краткое отображение для монокомпонентного
                component = product.organic_components[0]
                
                if hasattr(component, 'scientific_title') and component.scientific_title:
                    composition_text += f"   🧬 <b>{component.scientific_title}</b>"
                else:
                    composition_text += f"   {component.component_id}"
                
                if hasattr(component, 'proportion') and component.proportion:
                    composition_text += f" • {component.proportion}"
                
                composition_text += self.config.get_template('component_separator')
            else:
                # Список для мультикомпонентного (MULTI)
                for i, component in enumerate(product.organic_components, 1):
                    comp_name = self._get_component_display_name(component, loc)
                    composition_text += f"   {i}. <b>{comp_name}</b>"
                    
                    if hasattr(component, 'proportion') and component.proportion:
                        composition_text += f" • {component.proportion}"
                    
                    composition_text += self.config.get_template('component_separator')
            
            return composition_text
            
        except Exception as e:
            self.logger.error(f"[ProductFormatterService] Ошибка при форматировании состава: {e}")
            return f"{self.config.get_emoji('composition')} <b>{loc.t('catalog.product.composition')}</b>: {loc.t('catalog.product.composition_not_specified')}"
    
    def format_pricing_ux(self, product: Any, loc: Localization) -> str:
        """
        Форматирует информацию о ценах для покупателей.
        
        Args:
            product: Объект Product
            loc: Объект локализации
            
        Returns:
            str: Отформатированная информация о ценах
        """
        try:
            if not product.prices:
                pricing_emoji = self.config.get_emoji('pricing')
                pricing_text = f"{pricing_emoji} <b>{loc.t('catalog.product.pricing')}</b>: {loc.t('catalog.product.pricing_not_specified')}{self.config.get_template('section_separator')}"
                return pricing_text
            
            pricing_text = f"{self.config.get_emoji('pricing')} <b>{loc.t('catalog.product.pricing_title')}</b>{self.config.get_template('section_separator')}"
            
            for i, price in enumerate(product.prices, 1):
                pricing_text += f"   {i}. "
                
                # Цена - самое важное для покупателя
                if hasattr(price, 'price') and price.price:
                    pricing_text += f"<b>{price.price} {price.currency}</b>"
                
                # Вес или объем - важно для понимания количества
                if hasattr(price, 'weight') and price.weight:
                    pricing_text += f"{self.config.get_template('price_separator')}<b>{price.weight} {price.weight_unit}</b>"
                elif hasattr(price, 'volume') and price.volume:
                    pricing_text += f"{self.config.get_template('price_separator')}<b>{price.volume} {price.volume_unit}</b>"
                
                # Форма продукта - важно для выбора
                if hasattr(price, 'form') and price.form:
                    pricing_text += f"{self.config.get_template('form_separator')}{price.form}"
                
                pricing_text += self.config.get_template('component_separator')
            
            return pricing_text
            
        except Exception as e:
            self.logger.error(f"[ProductFormatterService] Ошибка при форматировании цен: {e}")
            return f"{self.config.get_emoji('pricing')} <b>{loc.t('catalog.product.pricing')}</b>: {loc.t('catalog.product.pricing_not_specified')}"
    
    def format_details_ux(self, product: Any, loc: Localization) -> str:
        """
        Форматирует детали продукта для покупателей.
        
        Args:
            product: Объект Product
            loc: Объект локализации
            
        Returns:
            str: Отформатированные детали
        """
        try:
            details_text = f"{self.config.get_emoji('details')} <b>{loc.t('catalog.product.details')}</b>{self.config.get_template('section_separator')}"
            
            # 📦 Формы продукта - важно для выбора
            if product.forms:
                forms_text = ', '.join(product.forms)
                details_text += f"{self.config.get_emoji('forms')} <b>{loc.t('catalog.product.forms_label')}</b>: {forms_text}{self.config.get_template('section_separator')}"
            
            # 🏷️ Категории - для понимания типа продукта
            if product.categories:
                categories_text = ', '.join(product.categories)
                details_text += f"{self.config.get_emoji('categories')} <b>{loc.t('catalog.product.category_label')}</b>: {categories_text}{self.config.get_template('section_separator')}"
            
            return details_text
            
        except Exception as e:
            self.logger.error(f"[ProductFormatterService] Ошибка при форматировании деталей: {e}")
            return f"{self.config.get_emoji('details')} <b>{loc.t('catalog.product.details')}</b>"
    
    def format_product_details_for_telegram(self, product: Any, loc: Localization):
        """
        Форматирует детальную информацию о продукте для Telegram.
        
        Args:
            product: Объект продукта
            loc: Объект локализации
            
        Returns:
            Dict or str: Словарь с 'text' и 'inline_keyboard' (если есть description)
                        или строка (для backward compatibility)
        """
        try:
            self.logger.debug(f"[ProductFormatterService] Детальное форматирование продукта: {getattr(product, 'title', 'unknown')}")
            
            # Инициализация отслеживания секций для предотвращения дублирования
            section_tracker = SectionTracker()
            
            # 🏷️ Заголовок и основная информация (используем локализованное название)
            product_title = self._get_product_title(product, loc)
            details_text = f"{self.config.get_emoji('product')} <b>{product_title}</b>{self.config.get_template('section_separator')}"
            details_text += f"{self.config.get_emoji('species')} <b>Вид:</b> {product.species}{self.config.get_template('section_separator')}"
            
            # ✅ Статус продукта
            if product.status == 1:
                status_emoji = self.config.get_emoji('status_available')
                status_text = loc.t('catalog.product.available_for_order')
                details_text += f"{status_emoji} <b>Статус:</b> {status_text}{self.config.get_template('section_separator')}"
            else:
                status_emoji = self.config.get_emoji('status_unavailable')
                status_text = loc.t('catalog.product.temporarily_unavailable')
                details_text += f"{status_emoji} <b>Статус:</b> {status_text}{self.config.get_template('section_separator')}"
            
            # 🔬 Научное название (если доступно)
            if hasattr(product, 'scientific_name') and product.scientific_name:
                details_text += f"{self.config.get_emoji('scientific_name')} <b>Научное название:</b> {product.scientific_name}{self.config.get_template('section_separator')}"
                section_tracker.mark_section_outputted(SectionTypes.SCIENTIFIC_NAME)
            
            details_text += self.config.get_template('section_separator')
            
            # 🔬 Состав продукта - НОВАЯ ЛОГИКА с детекцией типа продукта
            if hasattr(product, 'organic_components') and product.organic_components:
                # Детекция типа продукта (SINGLE/MULTI)
                product_type = self._detect_product_type(product)
                self.logger.info(f"[ProductFormatterService] Detected product type: {product_type}")
                
                # Роутинг на соответствующий форматтер
                if product_type == "SINGLE":
                    # ✅ Task 2.1 DONE: используем новый SINGLE форматтер
                    self.logger.info("[ProductFormatterService] Using SINGLE component formatter")
                    composition_text = self._format_single_component_product(product, loc, section_tracker)
                    
                elif product_type == "MULTI":
                    # ✅ Task 3.1 DONE: используем новый MULTI форматтер
                    self.logger.info("[ProductFormatterService] Using MULTI component formatter")
                    composition_text = self._format_multi_component_product(product, loc, section_tracker)
                    
                else:
                    # Fallback для EMPTY/UNKNOWN
                    self.logger.warning(f"[ProductFormatterService] Product type {product_type}, showing fallback")
                    composition_text = f"{self.config.get_emoji('composition')} <b>Состав:</b> информация недоступна{self.config.get_template('section_separator')}"
                
                details_text += composition_text
                details_text += self.config.get_template('section_separator')
            
            # 📝 Общее описание продукта (только если не выведено компонентами)
            if (hasattr(product, 'generic_description') and product.generic_description and 
                section_tracker.can_output_section(SectionTypes.GENERIC_DESCRIPTION, 'product')):
                details_text += f"{self.config.get_emoji('description')} <b>Описание</b>{self.config.get_template('section_separator')}{product.generic_description}{self.config.get_template('section_separator')}{self.config.get_template('section_separator')}"
                section_tracker.mark_section_outputted(SectionTypes.GENERIC_DESCRIPTION)
            
            # ✨ Эффекты продукта (только если не выведены компонентами)
            if (hasattr(product, 'effects') and product.effects and 
                section_tracker.can_output_section(SectionTypes.EFFECTS, 'product')):
                details_text += f"{self.config.get_emoji('effects')} <b>Эффекты</b>{self.config.get_template('section_separator')}{product.effects}{self.config.get_template('section_separator')}{self.config.get_template('section_separator')}"
                section_tracker.mark_section_outputted(SectionTypes.EFFECTS)
            
            # 💰 Цены и формы - структурированное отображение
            if hasattr(product, 'prices') and product.prices:
                details_text += f"{self.config.get_emoji('pricing')} <b>Цены</b>{self.config.get_template('section_separator')}"
                section_tracker.mark_section_outputted(SectionTypes.PRICES)
                for i, price in enumerate(product.prices, 1):
                    details_text += f"• <b>{price.format_price()}</b>"
                    
                    # Вес или объем
                    if price.is_weight_based:
                        details_text += f"{self.config.get_template('price_separator')}<b>{price.format_amount()}</b>"
                    elif price.is_volume_based:
                        details_text += f"{self.config.get_template('price_separator')}<b>{price.format_amount()}</b>"
                    
                    # Форма продукта
                    if hasattr(price, 'form') and price.form:
                        details_text += f" <i>{price.form}</i>"
                    
                    # Дополнительная информация о цене
                    if hasattr(price, 'description') and price.description:
                        details_text += f" - {price.description}"
                    
                    details_text += self.config.get_template('component_separator')
                details_text += self.config.get_template('section_separator')
            
            # 📦 Формы продукта
            if hasattr(product, 'forms') and product.forms:
                forms_text = ', '.join(product.forms)
                details_text += f"{self.config.get_emoji('forms')} <b>Формы</b>{self.config.get_template('section_separator')}{forms_text}{self.config.get_template('section_separator')}{self.config.get_template('section_separator')}"
                section_tracker.mark_section_outputted(SectionTypes.FORMS)
            
            # 💊 Инструкции по дозировке продукта (только если не выведены ранее)
            if (hasattr(product, 'dosage_instructions') and product.dosage_instructions and 
                section_tracker.can_output_section(SectionTypes.DOSAGE_INSTRUCTIONS, 'product')):
                details_text += f"{self.config.get_emoji('dosage')} <b>Дозировка</b>{self.config.get_template('section_separator')}"
                for instruction in product.dosage_instructions:
                    details_text += f"<b>{instruction.title}</b>{self.config.get_template('section_separator')}"
                    details_text += f"{instruction.description}{self.config.get_template('component_separator')}"
                    
                    # Тип дозировки
                    if hasattr(instruction, 'type') and instruction.type:
                        details_text += f"<i>Тип: {instruction.type}</i>{self.config.get_template('component_separator')}"
                    
                    details_text += self.config.get_template('section_separator')
                details_text += self.config.get_template('section_separator')
                section_tracker.mark_section_outputted(SectionTypes.DOSAGE_INSTRUCTIONS)
            
            # 🧙‍♂️ Шаманская перспектива продукта (только если не выведена ранее)
            if (hasattr(product, 'shamanic') and product.shamanic and 
                section_tracker.can_output_section(SectionTypes.SHAMANIC, 'product')):
                details_text += f"{self.config.get_emoji('shamanic')} <b>Шаманская перспектива</b>{self.config.get_template('section_separator')}{product.shamanic}{self.config.get_template('section_separator')}{self.config.get_template('section_separator')}"
                section_tracker.mark_section_outputted(SectionTypes.SHAMANIC)
            
            # ⚠️ Предупреждения продукта (только если не выведены ранее)
            if (hasattr(product, 'warnings') and product.warnings and 
                section_tracker.can_output_section(SectionTypes.WARNINGS, 'product')):
                details_text += f"{self.config.get_emoji('warnings')} <b>Предупреждения</b>{self.config.get_template('section_separator')}{product.warnings}{self.config.get_template('section_separator')}{self.config.get_template('section_separator')}"
                section_tracker.mark_section_outputted(SectionTypes.WARNINGS)
            
            # 🏷️ Категории
            if hasattr(product, 'categories') and product.categories:
                categories_text = ', '.join(product.categories)
                details_text += f"{self.config.get_emoji('categories')} <b>Категории</b>{self.config.get_template('section_separator')}{categories_text}{self.config.get_template('section_separator')}{self.config.get_template('section_separator')}"
                section_tracker.mark_section_outputted(SectionTypes.CATEGORIES)
            
            # 🌟 Особенности продукта (только если не выведены ранее)
            if (hasattr(product, 'features') and product.features and 
                section_tracker.can_output_section(SectionTypes.FEATURES, 'product')):
                details_text += f"{self.config.get_emoji('features')} <b>Особенности</b>{self.config.get_template('section_separator')}"
                for feature in product.features:
                    details_text += f"• {feature}{self.config.get_template('component_separator')}"
                details_text += self.config.get_template('section_separator')
                section_tracker.mark_section_outputted(SectionTypes.FEATURES)
            
            # Обрезаем текст если он слишком длинный
            if self.config.should_truncate(details_text):
                original_length = len(details_text)
                details_text = self._truncate_text(details_text)
                final_length = len(details_text)
                self.logger.info(f"[ProductFormatterService] Текст обрезан: {original_length} -> {final_length} символов")
            
            # 🆕 Task 10.3 + 11.1: Create inline keyboard if description available
            inline_keyboard = None
            
            if hasattr(product, 'organic_components') and product.organic_components:
                component_count = len(product.organic_components)
                
                # SINGLE component product
                if component_count == 1:
                    component = product.organic_components[0]
                    
                    # Check if component has description
                    if (hasattr(component, 'description') and 
                        component.description and 
                        hasattr(component, 'component_id')):
                        
                        self.logger.info(f"[ProductFormatterService] Adding description keyboard for SINGLE component: {component.component_id}")
                        
                        inline_keyboard = self._create_component_description_keyboard(
                            component.component_id,
                            loc.language,
                            getattr(product, 'business_id', '')
                        )
                
                # 🆕 Task 11.1: MULTI component product
                elif component_count > 1:
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    
                    inline_keyboard_rows = []
                    
                    for component in product.organic_components:
                        # Only add button if description available
                        if (hasattr(component, 'description') and 
                            component.description and 
                            hasattr(component, 'component_id')):
                            
                            # Get display name (scientific title or component_id)
                            display_name = self._get_component_display_name(component, loc)
                            
                            inline_keyboard_rows.append([
                                InlineKeyboardButton(
                                    text=f"📖 {display_name}",
                                    callback_data=f"component_menu:{component.component_id}:{loc.language}"
                                )
                            ])
                    
                    if inline_keyboard_rows:
                        inline_keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard_rows)
                        self.logger.info(f"[ProductFormatterService] Adding description keyboard for MULTI product: {len(inline_keyboard_rows)} components")
            
            self.logger.debug(f"[ProductFormatterService] Детальное форматирование завершено успешно")
            
            # Return dict if keyboard present, str for backward compatibility
            if inline_keyboard:
                return {
                    'text': details_text,
                    'inline_keyboard': inline_keyboard
                }
            else:
                return details_text
            
        except Exception as e:
            self.logger.error(f"[ProductFormatterService] Ошибка при детальном форматировании: {e}")
            return self._fallback_formatting(product, loc)
    
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
        try:
            self.logger.debug(f"[ProductFormatterService] Основное форматирование продукта: {getattr(product, 'title', 'unknown')}")
            
            # Инициализация отслеживания секций для предотвращения дублирования
            section_tracker = SectionTracker()
            
            # 🏷️ Заголовок и основная информация (используем локализованное название)
            product_title = self._get_product_title(product, loc)
            main_info_text = f"{self.config.get_emoji('product')} <b>{product_title}</b>{self.config.get_template('section_separator')}"
            main_info_text += f"{self.config.get_emoji('species')} <b>Вид:</b> {product.species}{self.config.get_template('section_separator')}"
            
            # ✅ Статус продукта
            if product.status == 1:
                status_emoji = self.config.get_emoji('status_available')
                status_text = loc.t('catalog.product.available_for_order')
                main_info_text += f"{status_emoji} <b>Статус:</b> {status_text}{self.config.get_template('section_separator')}"
            else:
                status_emoji = self.config.get_emoji('status_unavailable')
                status_text = loc.t('catalog.product.temporarily_unavailable')
                main_info_text += f"{status_emoji} <b>Статус:</b> {status_text}{self.config.get_template('section_separator')}"
            
            # 🔬 Научное название (если доступно)
            if hasattr(product, 'scientific_name') and product.scientific_name:
                main_info_text += f"{self.config.get_emoji('scientific_name')} <b>Научное название:</b> {product.scientific_name}{self.config.get_template('section_separator')}"
                section_tracker.mark_section_outputted(SectionTypes.SCIENTIFIC_NAME)
            
            main_info_text += self.config.get_template('section_separator')
            
            # 🔬 Состав продукта - базовая информация
            if hasattr(product, 'organic_components') and product.organic_components:
                main_info_text += f"{self.config.get_emoji('composition')} <b>Состав</b>{self.config.get_template('section_separator')}"
                
                # Добавляем картинку продукта в секцию состава для лучшего визуального восприятия
                if hasattr(product, 'cover_image_url') and product.cover_image_url:
                    main_info_text += f"🖼️ <i>Визуальное представление продукта</i>{self.config.get_template('section_separator')}{self.config.get_template('section_separator')}"
                
                for i, component in enumerate(product.organic_components, 1):
                    main_info_text += f"• <b>{component.component_id}</b> - <b>{component.proportion}</b>{self.config.get_template('component_separator')}"
                    
                    # Добавляем "воздух" между ингредиентами
                    main_info_text += self.config.get_template('section_separator')
                main_info_text += self.config.get_template('section_separator')
            
            # 💰 Цены и формы - структурированное отображение
            if hasattr(product, 'prices') and product.prices:
                main_info_text += f"{self.config.get_emoji('pricing')} <b>Цены</b>{self.config.get_template('section_separator')}"
                section_tracker.mark_section_outputted(SectionTypes.PRICES)
                for i, price in enumerate(product.prices, 1):
                    main_info_text += f"• <b>{price.format_price()}</b>"
                    
                    # Вес или объем
                    if price.is_weight_based:
                        main_info_text += f"{self.config.get_template('price_separator')}<b>{price.format_amount()}</b>"
                    elif price.is_volume_based:
                        main_info_text += f"{self.config.get_template('price_separator')}<b>{price.format_amount()}</b>"
                    
                    # Форма продукта
                    if hasattr(price, 'form') and price.form:
                        main_info_text += f" <i>{price.form}</i>"
                    
                    # Дополнительная информация о цене
                    if hasattr(price, 'description') and price.description:
                        main_info_text += f" - {price.description}"
                    
                    main_info_text += self.config.get_template('component_separator')
                main_info_text += self.config.get_template('section_separator')
            
            # 📦 Формы продукта
            if hasattr(product, 'forms') and product.forms:
                forms_text = ', '.join(product.forms)
                main_info_text += f"{self.config.get_emoji('forms')} <b>Формы</b>{self.config.get_template('section_separator')}{forms_text}{self.config.get_template('section_separator')}{self.config.get_template('section_separator')}"
                section_tracker.mark_section_outputted(SectionTypes.FORMS)
            
            # 🏷️ Категории
            if hasattr(product, 'categories') and product.categories:
                categories_text = ', '.join(product.categories)
                main_info_text += f"{self.config.get_emoji('categories')} <b>Категории</b>{self.config.get_template('section_separator')}{categories_text}{self.config.get_template('section_separator')}{self.config.get_template('section_separator')}"
                section_tracker.mark_section_outputted(SectionTypes.CATEGORIES)
            
            self.logger.debug(f"[ProductFormatterService] Основное форматирование завершено успешно")
            return main_info_text
            
        except Exception as e:
            self.logger.error(f"[ProductFormatterService] Ошибка при основном форматировании: {e}")
            return self._fallback_formatting(product, loc)
    
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
        try:
            self.logger.debug(f"[ProductFormatterService] Детальное описание продукта: {getattr(product, 'title', 'unknown')}")
            
            # Инициализация отслеживания секций для предотвращения дублирования
            section_tracker = SectionTracker()
            
            description_text = ""
            
            # 🔬 Состав продукта - детальная информация о компонентах
            if hasattr(product, 'organic_components') and product.organic_components:
                description_text += f"{self.config.get_emoji('composition')} <b>Детальный состав</b>{self.config.get_template('section_separator')}"
                
                for i, component in enumerate(product.organic_components, 1):
                    description_text += f"• <b>{component.component_id}</b> - <b>{component.proportion}</b>{self.config.get_template('component_separator')}"
                    
                    # Детальное описание компонента из ComponentDescription
                    if hasattr(component, 'description') and component.description:
                        desc = component.description
                        
                        # Основное описание компонента
                        if (hasattr(desc, 'generic_description') and desc.generic_description and 
                            section_tracker.can_output_section(SectionTypes.GENERIC_DESCRIPTION, 'component')):
                            description_text += f"  {self.config.get_emoji('description')} <b>Описание</b>{self.config.get_template('section_separator')}    {desc.generic_description}{self.config.get_template('component_separator')}"
                            section_tracker.mark_section_outputted(SectionTypes.GENERIC_DESCRIPTION)
                        
                        # Эффекты компонента
                        if (hasattr(desc, 'effects') and desc.effects and 
                            section_tracker.can_output_section(SectionTypes.EFFECTS, 'component')):
                            description_text += f"  {self.config.get_emoji('effects')} <b>Эффекты</b>{self.config.get_template('section_separator')}    {desc.effects}{self.config.get_template('component_separator')}"
                            section_tracker.mark_section_outputted(SectionTypes.EFFECTS)
                        
                        # Шаманская перспектива компонента (приоритет)
                        if (hasattr(desc, 'shamanic') and desc.shamanic and 
                            section_tracker.can_output_section(SectionTypes.SHAMANIC, 'component')):
                            description_text += f"  {self.config.get_emoji('shamanic')} <b>Шаманская перспектива</b>{self.config.get_template('section_separator')}    {desc.shamanic}{self.config.get_template('component_separator')}"
                            section_tracker.mark_section_outputted(SectionTypes.SHAMANIC)
                        
                        # Предупреждения компонента (приоритет)
                        if (hasattr(desc, 'warnings') and desc.warnings and 
                            section_tracker.can_output_section(SectionTypes.WARNINGS, 'component')):
                            description_text += f"  {self.config.get_emoji('warnings')} <b>Предупреждения</b>{self.config.get_template('section_separator')}    {desc.warnings}{self.config.get_template('component_separator')}"
                            section_tracker.mark_section_outputted(SectionTypes.WARNINGS)
                        
                        # Инструкции по дозировке компонента
                        if (hasattr(desc, 'dosage_instructions') and desc.dosage_instructions and 
                            section_tracker.can_output_section(SectionTypes.DOSAGE_INSTRUCTIONS, 'component')):
                            description_text += f"  {self.config.get_emoji('dosage')} <b>Дозировка</b>{self.config.get_template('section_separator')}"
                            for instruction in desc.dosage_instructions:
                                description_text += f"    • {instruction.title}: {instruction.description}{self.config.get_template('component_separator')}"
                            section_tracker.mark_section_outputted(SectionTypes.DOSAGE_INSTRUCTIONS)
                        
                        # Особенности компонента
                        if (hasattr(desc, 'features') and desc.features and 
                            section_tracker.can_output_section(SectionTypes.FEATURES, 'component')):
                            description_text += f"  {self.config.get_emoji('features')} <b>Особенности</b>{self.config.get_template('section_separator')}    {', '.join(desc.features)}{self.config.get_template('component_separator')}"
                            section_tracker.mark_section_outputted(SectionTypes.FEATURES)
                    
                    # Дополнительные свойства компонента
                    if hasattr(component, 'properties') and component.properties:
                        description_text += f"  {component.properties}{self.config.get_template('component_separator')}"
                    
                    # Добавляем "воздух" между ингредиентами
                    description_text += self.config.get_template('section_separator')
                description_text += self.config.get_template('section_separator')
            
            # 📝 Общее описание продукта (только если не выведено компонентами)
            if (hasattr(product, 'generic_description') and product.generic_description and 
                section_tracker.can_output_section(SectionTypes.GENERIC_DESCRIPTION, 'product')):
                description_text += f"{self.config.get_emoji('description')} <b>Описание</b>{self.config.get_template('section_separator')}{product.generic_description}{self.config.get_template('section_separator')}{self.config.get_template('section_separator')}"
                section_tracker.mark_section_outputted(SectionTypes.GENERIC_DESCRIPTION)
            
            # ✨ Эффекты продукта (только если не выведены компонентами)
            if (hasattr(product, 'effects') and product.effects and 
                section_tracker.can_output_section(SectionTypes.EFFECTS, 'product')):
                description_text += f"{self.config.get_emoji('effects')} <b>Эффекты</b>{self.config.get_template('section_separator')}{product.effects}{self.config.get_template('section_separator')}{self.config.get_template('section_separator')}"
                section_tracker.mark_section_outputted(SectionTypes.EFFECTS)
            
            # 💊 Инструкции по дозировке продукта (только если не выведены ранее)
            if (hasattr(product, 'dosage_instructions') and product.dosage_instructions and 
                section_tracker.can_output_section(SectionTypes.DOSAGE_INSTRUCTIONS, 'product')):
                description_text += f"{self.config.get_emoji('dosage')} <b>Дозировка</b>{self.config.get_template('section_separator')}"
                for instruction in product.dosage_instructions:
                    description_text += f"<b>{instruction.title}</b>{self.config.get_template('section_separator')}"
                    description_text += f"{instruction.description}{self.config.get_template('component_separator')}"
                    
                    # Тип дозировки
                    if hasattr(instruction, 'type') and instruction.type:
                        description_text += f"<i>Тип: {instruction.type}</i>{self.config.get_template('component_separator')}"
                    
                    description_text += self.config.get_template('section_separator')
                description_text += self.config.get_template('section_separator')
                section_tracker.mark_section_outputted(SectionTypes.DOSAGE_INSTRUCTIONS)
            
            # 🧙‍♂️ Шаманская перспектива продукта (только если не выведена ранее)
            if (hasattr(product, 'shamanic') and product.shamanic and 
                section_tracker.can_output_section(SectionTypes.SHAMANIC, 'product')):
                description_text += f"{self.config.get_emoji('shamanic')} <b>Шаманская перспектива</b>{self.config.get_template('section_separator')}{product.shamanic}{self.config.get_template('section_separator')}{self.config.get_template('section_separator')}"
                section_tracker.mark_section_outputted(SectionTypes.SHAMANIC)
            
            # ⚠️ Предупреждения продукта (только если не выведены ранее)
            if (hasattr(product, 'warnings') and product.warnings and 
                section_tracker.can_output_section(SectionTypes.WARNINGS, 'product')):
                description_text += f"{self.config.get_emoji('warnings')} <b>Предупреждения</b>{self.config.get_template('section_separator')}{product.warnings}{self.config.get_template('section_separator')}{self.config.get_template('section_separator')}"
                section_tracker.mark_section_outputted(SectionTypes.WARNINGS)
            
            # 🌟 Особенности продукта (только если не выведены ранее)
            if (hasattr(product, 'features') and product.features and 
                section_tracker.can_output_section(SectionTypes.FEATURES, 'product')):
                description_text += f"{self.config.get_emoji('features')} <b>Особенности</b>{self.config.get_template('section_separator')}"
                for feature in product.features:
                    description_text += f"• {feature}{self.config.get_template('component_separator')}"
                description_text += self.config.get_template('section_separator')
                section_tracker.mark_section_outputted(SectionTypes.FEATURES)
            
            self.logger.debug(f"[ProductFormatterService] Детальное описание завершено успешно")
            return description_text
            
        except Exception as e:
            self.logger.error(f"[ProductFormatterService] Ошибка при детальном описании: {e}")
            return self._fallback_formatting(product, loc)
    
    def _truncate_text(self, text: str) -> str:
        """
        Обрезает текст для Telegram.
        
        Args:
            text: Исходный текст
            
        Returns:
            str: Обрезанный текст
        """
        if len(text) <= self.config.max_text_length:
            return text
        
        # Обрезаем текст и добавляем индикатор
        truncated = text[:self.config.max_text_length-100]  # Оставляем место для индикатора
        
        # Ищем последний полный абзац
        last_newline = truncated.rfind('\n\n')
        if last_newline > self.config.max_text_length * 0.8:  # Если последний абзац не слишком далеко от конца
            truncated = truncated[:last_newline]
        
        truncated += self.config.get_template('truncate_indicator')
        return truncated
    
    def _fallback_formatting(self, product: Any, loc: Localization) -> str:
        """
        Fallback форматирование в случае ошибки.
        
        Args:
            product: Объект продукта
            loc: Объект локализации
            
        Returns:
            str: Простое форматирование
        """
        try:
            title = getattr(product, 'title', 'Продукт')
            return f"{self.config.get_emoji('product')} <b>{title}</b>{self.config.get_template('section_separator')}❌ Ошибка при загрузке детальной информации"
        except:
            return f"{self.config.get_emoji('product')} <b>Продукт</b>{self.config.get_template('section_separator')}❌ Ошибка при загрузке информации"
    
    def get_config(self) -> ProductFormatterConfig:
        """
        Возвращает текущую конфигурацию сервиса.
        
        Returns:
            ProductFormatterConfig: Текущая конфигурация
        """
        return self.config
    
    def update_config(self, new_config: ProductFormatterConfig) -> None:
        """
        Обновляет конфигурацию сервиса.
        
        Args:
            new_config: Новая конфигурация
        """
        self.config = new_config
        self.logger.setLevel(self.config.logging_level)
        self.logger.info(f"[ProductFormatterService] Конфигурация обновлена")
    
    def create_custom_config(self, **kwargs) -> ProductFormatterConfig:
        """
        Создает кастомную конфигурацию на основе текущей.
        
        Args:
            **kwargs: Параметры для переопределения
            
        Returns:
            ProductFormatterConfig: Новая конфигурация
        """
        from dataclasses import replace
        return replace(self.config, **kwargs)
    
    def _get_localized_text(self, key: str, default: str = None, **kwargs) -> str:
        """
        Получает локализованный текст с поддержкой мультиязычности
        
        Args:
            key: Ключ перевода
            default: Значение по умолчанию
            **kwargs: Параметры для подстановки
            
        Returns:
            str: Локализованный текст
        """
        try:
            if self.localization_service:
                return self.localization_service.t(key, default, **kwargs)
            else:
                # Fallback на базовую локализацию
                return default or key
        except Exception as e:
            self.logger.error(f"[ProductFormatterService] Ошибка получения локализации для ключа '{key}': {e}")
            return default or key
    
    def _get_product_title(self, product: Any, loc: Localization) -> str:
        """
        Получает локализованное название продукта
        
        Args:
            product: Объект продукта
            loc: Объект локализации
            
        Returns:
            str: Локализованное название
        """
        try:
            business_id = getattr(product, 'business_id', getattr(product, 'id', 'unknown'))
            
            # Пытаемся получить локализованное название
            if self.localization_service:
                localized_title = self.localization_service.t(f'product.{business_id}.title')
                if localized_title and localized_title != f'product.{business_id}.title':
                    return localized_title
            
            # Fallback на оригинальное название
            return getattr(product, 'title', 'Продукт')
            
        except Exception as e:
            self.logger.error(f"[ProductFormatterService] Ошибка получения названия продукта: {e}")
            return getattr(product, 'title', 'Продукт')
    
    def _get_product_description(self, product: Any, loc: Localization) -> str:
        """
        Получает локализованное описание продукта
        
        Args:
            product: Объект продукта
            loc: Объект локализации
            
        Returns:
            str: Локализованное описание
        """
        try:
            business_id = getattr(product, 'business_id', getattr(product, 'id', 'unknown'))
            
            # Пытаемся получить локализованное описание
            if self.localization_service:
                localized_description = self.localization_service.t(f'product.{business_id}.description')
                if localized_description and localized_description != f'product.{business_id}.description':
                    return localized_description
            
            # Fallback на оригинальное описание
            return getattr(product, 'description', 'Описание недоступно')
            
        except Exception as e:
            self.logger.error(f"[ProductFormatterService] Ошибка получения описания продукта: {e}")
            return getattr(product, 'description', 'Описание недоступно')
    
    def _get_component_name(self, component: Any, loc: Localization) -> str:
        """
        Получает локализованное название компонента
        
        Args:
            component: Объект компонента
            loc: Объект локализации
            
        Returns:
            str: Локализованное название
        """
        try:
            component_id = getattr(component, 'component_id', getattr(component, 'id', 'unknown'))
            
            # Пытаемся получить локализованное название
            if self.localization_service:
                localized_name = self.localization_service.t(f'component.{component_id}.name')
                if localized_name and localized_name != f'component.{component_id}.name':
                    return localized_name
            
            # Fallback на оригинальное название
            return getattr(component, 'name', 'Компонент')
            
        except Exception as e:
            self.logger.error(f"[ProductFormatterService] Ошибка получения названия компонента: {e}")
            return getattr(component, 'name', 'Компонент')
    
    def _get_component_description(self, component: Any, loc: Localization) -> str:
        """
        Получает локализованное описание компонента
        
        Args:
            component: Объект компонента
            loc: Объект локализации
            
        Returns:
            str: Локализованное описание
        """
        try:
            component_id = getattr(component, 'component_id', getattr(component, 'id', 'unknown'))
            
            # Пытаемся получить локализованное описание
            if self.localization_service:
                localized_description = self.localization_service.t(f'component.{component_id}.description')
                if localized_description and localized_description != f'component.{component_id}.description':
                    return localized_description
            
            # Fallback на оригинальное описание
            return getattr(component, 'description', 'Описание недоступно')
            
        except Exception as e:
            self.logger.error(f"[ProductFormatterService] Ошибка получения описания компонента: {e}")
            return getattr(component, 'description', 'Описание недоступно')
    
    def _detect_product_type(self, product: Any) -> str:
        """
        Определяет тип продукта: SINGLE или MULTI.
        
        Используется для выбора стратегии форматирования:
        - SINGLE: монокомпонентный продукт (1 компонент)
        - MULTI: мультикомпонентный продукт (2+ компонента)
        - EMPTY: продукт без компонентов
        - UNKNOWN: organic_components поле отсутствует
        
        Args:
            product: Объект Product
            
        Returns:
            str: "SINGLE" | "MULTI" | "EMPTY" | "UNKNOWN"
        """
        try:
            # Проверка наличия поля organic_components
            if not hasattr(product, 'organic_components'):
                self.logger.warning(f"[ProductFormatterService] Product без поля organic_components")
                return "UNKNOWN"
            
            # Получение количества компонентов
            component_count = len(product.organic_components)
            
            # Детекция типа
            if component_count == 0:
                self.logger.debug(f"[ProductFormatterService] Product type: EMPTY (0 components)")
                return "EMPTY"
            elif component_count == 1:
                self.logger.debug(f"[ProductFormatterService] Product type: SINGLE (1 component)")
                return "SINGLE"
            else:
                self.logger.debug(f"[ProductFormatterService] Product type: MULTI ({component_count} components)")
                return "MULTI"
                
        except Exception as e:
            self.logger.error(f"[ProductFormatterService] Ошибка при детекции типа продукта: {e}")
            return "UNKNOWN"
    
    def _format_single_component_product(self, product: Any, loc: Localization, section_tracker: SectionTracker) -> str:
        """
        Форматирует монокомпонентный продукт.
        
        Отображает:
        - Маркер "Монокомпонентный продукт"
        - Научное название компонента (или component_id как fallback)
        - Features компонента (топ-5 + счётчик оставшихся)
        - Доступные формы компонента
        
        Args:
            product: Объект Product с 1 компонентом
            loc: Объект локализации
            section_tracker: Трекер секций для предотвращения дублирования
            
        Returns:
            str: Отформатированный текст для монокомпонентного продукта
        """
        component = product.organic_components[0]
        
        text = ""
        
        # Маркер монокомпонентного продукта
        marker_text = loc.t('catalog.product.single_component_marker')
        text += f"{self.config.get_emoji('composition')} <b>{marker_text}</b>{self.config.get_template('section_separator')}"
        
        # Научное название + component_id
        if hasattr(component, 'scientific_title') and component.scientific_title:
            text += f"🧬 <b>{component.scientific_title}</b> <i>({component.component_id})</i>"
        else:
            text += f"🧬 <b>{component.component_id}</b>"
        
        # Пропорция (если есть)
        if hasattr(component, 'proportion') and component.proportion:
            text += f" • {component.proportion}"
        
        text += self.config.get_template('section_separator')
        text += self.config.get_template('section_separator')
        
        # Features компонента
        features_text = self._format_component_features(component, loc, max_features=5)
        if features_text:
            text += features_text
            text += self.config.get_template('section_separator')
        
        # Формы компонента
        forms_text = self._format_component_forms(component, loc)
        if forms_text:
            text += forms_text
            text += self.config.get_template('section_separator')
        
        # 🆕 Task 10.3: Hint about detailed description (if available)
        if hasattr(component, 'description') and component.description:
            text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            text += "📖 <i>Детальное описание компонента доступно через кнопки ниже</i>\n"
            text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            self.logger.info(f"[ProductFormatterService] Added description hint for component: {component.component_id}")
        
        self.logger.debug(f"[ProductFormatterService] Formatted SINGLE component: {component.component_id}")
        
        return text
    
    def _format_multi_component_product(self, product: Any, loc: Localization, section_tracker: SectionTracker) -> str:
        """
        Форматирует мультикомпонентный продукт.
        
        Отображает:
        - Локализованный маркер "Мультикомпонентный продукт (N компонентов)"
        - Для каждого компонента:
          - Разделитель с научным названием
          - Пропорция
          - Features (адаптивное количество)
          - Доступные формы
        
        Args:
            product: Объект Product с 2+ компонентами
            loc: Объект локализации
            section_tracker: Трекер секций для предотвращения дублирования
            
        Returns:
            str: Отформатированный текст для мультикомпонентного продукта
        """
        comp_count = len(product.organic_components)
        
        text = ""
        
        # Маркер с количеством компонентов (локализованный)
        marker_text = loc.t('catalog.product.multi_component_marker').format(comp_count)
        text += f"{self.config.get_emoji('composition')} <b>{marker_text}</b>{self.config.get_template('section_separator')}"
        text += self.config.get_template('section_separator')
        
        # Адаптивное количество features на компонент
        max_features = self._calculate_max_features_per_component(comp_count)
        
        # Каждый компонент
        for i, component in enumerate(product.organic_components, 1):
            # Разделитель с названием компонента
            comp_name = self._get_component_display_name(component, loc)
            component_header = loc.t('catalog.product.component_number').format(i, comp_name)
            text += f"━━━ <b>{component_header}</b> ━━━{self.config.get_template('section_separator')}"
            
            # Пропорция
            if hasattr(component, 'proportion') and component.proportion:
                proportion_label = loc.t('catalog.product.component_proportion')
                text += f"📊 <b>{proportion_label}</b> {component.proportion}{self.config.get_template('section_separator')}"
            
            # Научное название (если не совпадает с заголовком)
            if hasattr(component, 'scientific_title') and component.scientific_title and component.scientific_title != comp_name:
                sci_name_label = loc.t('catalog.product.component_scientific_name')
                text += f"{self.config.get_emoji('scientific_name')} <b>{sci_name_label}</b> {component.scientific_title} <i>({component.component_id})</i>{self.config.get_template('section_separator')}"
            
            # Features (адаптивное количество)
            features_text = self._format_component_features(component, loc, max_features=max_features)
            if features_text:
                text += features_text
            
            # Forms
            forms_text = self._format_component_forms(component, loc)
            if forms_text:
                text += forms_text
            
            # 🆕 Task 11.1: Hint about detailed description (if available)
            if hasattr(component, 'description') and component.description:
                text += f"\n📖 <i>[Описание доступно через кнопку ниже]</i>\n"
            
            # Разделитель между компонентами
            text += self.config.get_template('section_separator')
        
        # 🆕 Task 11.1: Global hint if any component has description
        descriptions_count = sum(
            1 for comp in product.organic_components 
            if hasattr(comp, 'description') and comp.description
        )
        
        if descriptions_count > 0:
            text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            text += f"📖 <i>Детальные описания {descriptions_count} компонент(ов) доступны через кнопки ниже</i>\n"
            text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        self.logger.debug(f"[ProductFormatterService] Formatted MULTI product: {comp_count} components, {descriptions_count} with descriptions")
        
        return text
    
    def _format_component_features(self, component: Any, loc: Localization, max_features: int = 5) -> str:
        """
        Форматирует features компонента.
        
        Args:
            component: Объект OrganicComponent
            loc: Объект локализации
            max_features: Максимум features для отображения
            
        Returns:
            str: Отформатированные features или пустая строка
        """
        if not hasattr(component, 'features') or not component.features:
            return ""
        
        common_features = component.features.get('common', [])
        if not common_features:
            return ""
        
        features_title = loc.t('catalog.product.component_features_title')
        text = f"{self.config.get_emoji('features')} <b>{features_title}</b>{self.config.get_template('section_separator')}"
        
        # Показываем первые N features
        features_to_show = common_features[:max_features]
        for feature in features_to_show:
            text += f"   • {feature}{self.config.get_template('component_separator')}"
        
        # Счётчик оставшихся
        if len(common_features) > max_features:
            remaining = len(common_features) - max_features
            remaining_text = loc.t('catalog.product.component_features_more').format(remaining)
            text += f"   <i>{remaining_text}</i>{self.config.get_template('component_separator')}"
        
        return text
    
    def _format_component_forms(self, component: Any, loc: Localization) -> str:
        """
        Форматирует доступные формы компонента.
        
        Args:
            component: Объект OrganicComponent
            loc: Объект локализации
            
        Returns:
            str: Отформатированные формы или пустая строка
        """
        if not hasattr(component, 'forms') or not component.forms:
            return ""
        
        forms_title = loc.t('catalog.product.component_forms_title')
        forms_text = ", ".join(component.forms)
        return f"{self.config.get_emoji('forms')} <b>{forms_title}</b> {forms_text}{self.config.get_template('component_separator')}"
    
    def _calculate_max_features_per_component(self, component_count: int) -> int:
        """
        Вычисляет максимальное количество features на компонент.
        Адаптивная логика: чем больше компонентов, тем меньше features.
        
        Args:
            component_count: Количество компонентов в продукте
            
        Returns:
            int: Макс. количество features для отображения
        """
        if component_count <= 2:
            return 5  # До 5 features для 1-2 компонентов
        elif component_count <= 4:
            return 3  # До 3 features для 3-4 компонентов
        else:
            return 2  # До 2 features для 5+ компонентов
    
    def _get_component_display_name(self, component: Any, loc: Localization = None) -> str:
        """
        Получает отображаемое название компонента с локализацией.
        
        Приоритет:
        1. Локализованное название через LocalizationService (если доступно)
        2. scientific_title (если есть)
        3. component_id (fallback)
        
        Args:
            component: Объект OrganicComponent
            loc: Объект локализации (опционально, для обратной совместимости)
            
        Returns:
            str: Название для отображения
        """
        # Используем локализованное название, если доступно
        if self.localization_service and loc:
            try:
                component_id = getattr(component, 'component_id', getattr(component, 'id', 'unknown'))
                localized_name = self.localization_service.t(f'component.{component_id}.name')
                if localized_name and localized_name != f'component.{component_id}.name':
                    return localized_name
            except Exception as e:
                self.logger.debug(f"[ProductFormatterService] Ошибка получения локализованного названия компонента: {e}")
        
        # Fallback на scientific_title или component_id
        if hasattr(component, 'scientific_title') and component.scientific_title:
            return component.scientific_title
        else:
            return getattr(component, 'component_id', getattr(component, 'id', 'unknown'))
    
    def _format_composition_legacy(self, product: Any, loc: Localization, section_tracker: SectionTracker) -> str:
        """
        LEGACY: Старая логика форматирования состава.
        Используется временно до реализации _format_single_component_product() и _format_multi_component_product().
        
        TODO: Удалить после реализации Tasks 2.1 и 3.1
        
        Args:
            product: Объект продукта
            loc: Объект локализации
            section_tracker: Трекер секций для предотвращения дублирования
            
        Returns:
            str: Отформатированный состав (legacy format)
        """
        details_text = f"{self.config.get_emoji('composition')} <b>Состав</b>{self.config.get_template('section_separator')}"
        
        # Добавляем картинку продукта в секцию состава для лучшего визуального восприятия
        if hasattr(product, 'cover_image_url') and product.cover_image_url:
            details_text += f"🖼️ <i>Визуальное представление продукта</i>{self.config.get_template('section_separator')}{self.config.get_template('section_separator')}"
        
        for i, component in enumerate(product.organic_components, 1):
            details_text += f"• <b>{component.component_id}</b> - <b>{component.proportion}</b>{self.config.get_template('component_separator')}"
            
            # Детальное описание компонента из ComponentDescription
            if hasattr(component, 'description') and component.description:
                desc = component.description
                
                # Основное описание компонента
                if (hasattr(desc, 'generic_description') and desc.generic_description and 
                    section_tracker.can_output_section(SectionTypes.GENERIC_DESCRIPTION, 'component')):
                    details_text += f"  {self.config.get_emoji('description')} <b>Описание</b>{self.config.get_template('section_separator')}    {desc.generic_description}{self.config.get_template('component_separator')}"
                    section_tracker.mark_section_outputted(SectionTypes.GENERIC_DESCRIPTION)
                
                # Эффекты компонента
                if (hasattr(desc, 'effects') and desc.effects and 
                    section_tracker.can_output_section(SectionTypes.EFFECTS, 'component')):
                    details_text += f"  {self.config.get_emoji('effects')} <b>Эффекты</b>{self.config.get_template('section_separator')}    {desc.effects}{self.config.get_template('component_separator')}"
                    section_tracker.mark_section_outputted(SectionTypes.EFFECTS)
                
                # Шаманская перспектива компонента (приоритет)
                if (hasattr(desc, 'shamanic') and desc.shamanic and 
                    section_tracker.can_output_section(SectionTypes.SHAMANIC, 'component')):
                    details_text += f"  {self.config.get_emoji('shamanic')} <b>Шаманская перспектива</b>{self.config.get_template('section_separator')}    {desc.shamanic}{self.config.get_template('component_separator')}"
                    section_tracker.mark_section_outputted(SectionTypes.SHAMANIC)
                
                # Предупреждения компонента (приоритет)
                if (hasattr(desc, 'warnings') and desc.warnings and 
                    section_tracker.can_output_section(SectionTypes.WARNINGS, 'component')):
                    details_text += f"  {self.config.get_emoji('warnings')} <b>Предупреждения</b>{self.config.get_template('section_separator')}    {desc.warnings}{self.config.get_template('component_separator')}"
                    section_tracker.mark_section_outputted(SectionTypes.WARNINGS)
                
                # Инструкции по дозировке компонента
                if (hasattr(desc, 'dosage_instructions') and desc.dosage_instructions and 
                    section_tracker.can_output_section(SectionTypes.DOSAGE_INSTRUCTIONS, 'component')):
                    details_text += f"  {self.config.get_emoji('dosage')} <b>Дозировка</b>{self.config.get_template('section_separator')}"
                    for instruction in desc.dosage_instructions:
                        details_text += f"    • {instruction.title}: {instruction.description}{self.config.get_template('component_separator')}"
                    section_tracker.mark_section_outputted(SectionTypes.DOSAGE_INSTRUCTIONS)
                
                # Особенности компонента
                if (hasattr(desc, 'features') and desc.features and 
                    section_tracker.can_output_section(SectionTypes.FEATURES, 'component')):
                    details_text += f"  {self.config.get_emoji('features')} <b>Особенности</b>{self.config.get_template('section_separator')}    {', '.join(desc.features)}{self.config.get_template('component_separator')}"
                    section_tracker.mark_section_outputted(SectionTypes.FEATURES)
            
            # Дополнительные свойства компонента
            if hasattr(component, 'properties') and component.properties:
                details_text += f"  {component.properties}{self.config.get_template('component_separator')}"
            
            # Добавляем "воздух" между ингредиентами
            details_text += self.config.get_template('section_separator')
        
        return details_text
    
    def _create_component_description_keyboard(
        self, 
        component_id: str, 
        language: str,
        product_id: str
    ):
        """
        Создаёт inline клавиатуру для секций ComponentDescription.
        
        Args:
            component_id: ID компонента
            language: Язык для отображения
            product_id: ID продукта (для навигации назад)
            
        Returns:
            InlineKeyboardMarkup with 4 section buttons
            
        Note: Button text uses hardcoded localization since inline keyboard
        is created outside of handler context where loc is available.
        Alternative would be to pass loc as parameter, but buttons are
        static and don't require dynamic localization.
        """
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Note: Hardcoded for now (inline keyboard text is less critical)
        # TODO: Consider passing loc parameter if dynamic localization needed
        buttons = [
            [InlineKeyboardButton(
                text="🔬 Активные компоненты",
                callback_data=f"component_desc:{component_id}:generic:{language}"
            )],
            [InlineKeyboardButton(
                text="🌿 Целительное действие",
                callback_data=f"component_desc:{component_id}:effects:{language}"
            )],
            [InlineKeyboardButton(
                text="🌀 Шаманская перспектива",
                callback_data=f"component_desc:{component_id}:shamanic:{language}"
            )],
            [InlineKeyboardButton(
                text="⚠️ Предостережения",
                callback_data=f"component_desc:{component_id}:warnings:{language}"
            )]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)