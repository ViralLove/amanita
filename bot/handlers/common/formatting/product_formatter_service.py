"""
Сервис форматирования продуктов для Telegram.
Реализует интерфейс IProductFormatter с поддержкой конфигурации.
"""

import logging
from typing import Dict, Any, Optional, List
from services.common.localization import Localization
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
    
    def __init__(self, config: Optional[ProductFormatterConfig] = None):
        """
        Инициализация сервиса форматирования.
        
        Args:
            config: Конфигурация форматирования (если не указана, используется по умолчанию)
        """
        self.config = config or ProductFormatterConfig()
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
            # 🏷️ Название продукта - самое важное
            main_info = f"{self.config.get_emoji('product')} <b>{product.title}</b>{self.config.get_template('section_separator')}"
            
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
        Форматирует состав продукта для покупателей.
        
        Args:
            product: Объект Product
            loc: Объект локализации
            
        Returns:
            str: Отформатированный состав
        """
        try:
            if not hasattr(product, 'organic_components') or not product.organic_components:
                composition_emoji = self.config.get_emoji('composition')
                composition_text = f"{composition_emoji} <b>{loc.t('catalog.product.composition')}</b>: {loc.t('catalog.product.composition_not_specified')}{self.config.get_template('section_separator')}"
                return composition_text
            
            composition_text = f"{self.config.get_emoji('composition')} <b>{loc.t('catalog.product.composition_title')}</b>{self.config.get_template('section_separator')}"
            
            for i, component in enumerate(product.organic_components, 1):
                # Основная информация о компоненте
                composition_text += f"   {i}. <b>{component.biounit_id}</b>"
                
                # Пропорция - важно для понимания концентрации
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
    
    def format_product_details_for_telegram(self, product: Any, loc: Localization) -> str:
        """
        Форматирует детальную информацию о продукте для Telegram.
        
        Args:
            product: Объект продукта
            loc: Объект локализации
            
        Returns:
            str: Отформатированный HTML текст с детальной информацией
        """
        try:
            self.logger.debug(f"[ProductFormatterService] Детальное форматирование продукта: {getattr(product, 'title', 'unknown')}")
            
            # Инициализация отслеживания секций для предотвращения дублирования
            section_tracker = SectionTracker()
            
            # 🏷️ Заголовок и основная информация
            details_text = f"{self.config.get_emoji('product')} <b>{product.title}</b>{self.config.get_template('section_separator')}"
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
            
            # 🔬 Состав продукта - детальная информация о компонентах
            if hasattr(product, 'organic_components') and product.organic_components:
                details_text += f"{self.config.get_emoji('composition')} <b>Состав</b>{self.config.get_template('section_separator')}"
                
                # Добавляем картинку продукта в секцию состава для лучшего визуального восприятия
                if hasattr(product, 'cover_image_url') and product.cover_image_url:
                    details_text += f"🖼️ <i>Визуальное представление продукта</i>{self.config.get_template('section_separator')}{self.config.get_template('section_separator')}"
                
                for i, component in enumerate(product.organic_components, 1):
                    details_text += f"• <b>{component.biounit_id}</b> - <b>{component.proportion}</b>{self.config.get_template('component_separator')}"
                    
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
            
            self.logger.debug(f"[ProductFormatterService] Детальное форматирование завершено успешно")
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
            
            # 🏷️ Заголовок и основная информация
            main_info_text = f"{self.config.get_emoji('product')} <b>{product.title}</b>{self.config.get_template('section_separator')}"
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
                    main_info_text += f"• <b>{component.biounit_id}</b> - <b>{component.proportion}</b>{self.config.get_template('component_separator')}"
                    
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
                    description_text += f"• <b>{component.biounit_id}</b> - <b>{component.proportion}</b>{self.config.get_template('component_separator')}"
                    
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
