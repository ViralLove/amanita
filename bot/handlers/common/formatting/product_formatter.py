"""
Форматирование продуктов для Telegram.
"""

from typing import Dict, Any
from services.common.localization import Localization
from .section_tracker import SectionTracker, SectionTypes

def format_product_for_telegram(product, loc: Localization) -> Dict[str, str]:
    """
    Форматирует продукт для отображения в Telegram с UX-оптимизированным подходом.
    Показывает только информацию, важную для покупателей.
    
    Args:
        product: Объект Product для форматирования
        loc: Объект локализации
        
    Returns:
        Dict[str, str]: Словарь с отформатированными секциями
    """
    return {
        'main_info': format_main_info_ux(product, loc),
        'composition': format_composition_ux(product, loc),
        'pricing': format_pricing_ux(product, loc),
        'details': format_details_ux(product, loc)
    }

def format_main_info_ux(product, loc: Localization) -> str:
    """
    Форматирует основную информацию о продукте для покупателей.
    
    Args:
        product: Объект Product
        loc: Объект локализации
        
    Returns:
        str: Отформатированная основная информация
    """
    # 🏷️ Название продукта - самое важное
    main_info = f"🏷️ <b>{product.title}</b>\n\n"
    
    # 🌿 Вид продукта - важно для понимания что это
    if product.species:
        main_info += f"🌿 <b>{product.species}</b>\n"
    
    # ✅ Статус - активен ли продукт для покупки
    if product.status == 1:
        main_info += f"✅ <b>{loc.t('catalog.product.available_for_order')}</b>\n"
    else:
        main_info += f"⏸️ <b>{loc.t('catalog.product.temporarily_unavailable')}</b>\n"
    
    return main_info

def format_composition_ux(product, loc: Localization) -> str:
    """
    Форматирует состав продукта для покупателей.
    
    Args:
        product: Объект Product
        loc: Объект локализации
        
    Returns:
        str: Отформатированный состав
    """
    if not hasattr(product, 'organic_components') or not product.organic_components:
        return f"🔬 <b>{loc.t('catalog.product.composition')}</b>: {loc.t('catalog.product.composition_not_specified')}\n\n"
    
    composition_text = f"🔬 <b>{loc.t('catalog.product.composition_title')}</b>\n"
    
    for i, component in enumerate(product.organic_components, 1):
        # Основная информация о компоненте
        composition_text += f"   {i}. <b>{component.biounit_id}</b>"
        
        # Пропорция - важно для понимания концентрации
        if hasattr(component, 'proportion') and component.proportion:
            composition_text += f" • {component.proportion}"
        
        composition_text += "\n"
    
    return composition_text

def format_pricing_ux(product, loc: Localization) -> str:
    """
    Форматирует информацию о ценах для покупателей.
    
    Args:
        product: Объект Product
        loc: Объект локализации
        
    Returns:
        str: Отформатированная информация о ценах
    """
    if not product.prices:
        return f"💰 <b>{loc.t('catalog.product.pricing')}</b>: {loc.t('catalog.product.pricing_not_specified')}\n\n"
    
    pricing_text = f"💰 <b>{loc.t('catalog.product.pricing_title')}</b>\n"
    
    for i, price in enumerate(product.prices, 1):
        pricing_text += f"   {i}. "
        
        # Цена - самое важное для покупателя
        if hasattr(price, 'price') and price.price:
            pricing_text += f"<b>{price.price} {price.currency}</b>"
        
        # Вес или объем - важно для понимания количества
        if hasattr(price, 'weight') and price.weight:
            pricing_text += f" за <b>{price.weight} {price.weight_unit}</b>"
        elif hasattr(price, 'volume') and price.volume:
            pricing_text += f" за <b>{price.volume} {price.volume_unit}</b>"
        
        # Форма продукта - важно для выбора
        if hasattr(price, 'form') and price.form:
            pricing_text += f" • {price.form}"
        
        pricing_text += "\n"
    
    return pricing_text

def format_details_ux(product, loc: Localization) -> str:
    """
    Форматирует детали продукта для покупателей.
    
    Args:
        product: Объект Product
        loc: Объект локализации
        
    Returns:
        str: Отформатированные детали
    """
    details_text = f"📋 <b>{loc.t('catalog.product.details')}</b>\n"
    
    # 📦 Формы продукта - важно для выбора
    if product.forms:
        forms_text = ', '.join(product.forms)
        details_text += f"📦 <b>{loc.t('catalog.product.forms_label')}</b>: {forms_text}\n"
    
    # 🏷️ Категории - для понимания типа продукта
    if product.categories:
        categories_text = ', '.join(product.categories)
        details_text += f"🏷️ <b>{loc.t('catalog.product.category_label')}</b>: {categories_text}\n"
    
    return details_text

def format_product_details_for_telegram(product, loc: Localization) -> str:
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
    try:
        # Инициализация отслеживания секций для предотвращения дублирования
        section_tracker = SectionTracker()
        
        # 🏷️ Заголовок и основная информация
        details_text = f"🏷️ <b>{product.title}</b>\n"
        details_text += f"🌿 <b>Вид:</b> {product.species}\n"
        
        # ✅ Статус продукта
        if product.status == 1:
            details_text += f"✅ <b>Статус:</b> {loc.t('catalog.product.available_for_order')}\n"
        else:
            details_text += f"⏸️ <b>Статус:</b> {loc.t('catalog.product.temporarily_unavailable')}\n"
        
        # 🔬 Научное название (если доступно)
        if hasattr(product, 'scientific_name') and product.scientific_name:
            details_text += f"🔬 <b>Научное название:</b> {product.scientific_name}\n"
            section_tracker.mark_section_outputted(SectionTypes.SCIENTIFIC_NAME)
        
        details_text += "\n"
        
        # 🔬 Состав продукта - детальная информация о компонентах
        if hasattr(product, 'organic_components') and product.organic_components:
            details_text += f"🔬 <b>Состав</b>\n"
            
            # Добавляем картинку продукта в секцию состава для лучшего визуального восприятия
            if hasattr(product, 'cover_image_url') and product.cover_image_url:
                details_text += f"🖼️ <i>Визуальное представление продукта</i>\n\n"
            
            for i, component in enumerate(product.organic_components, 1):
                details_text += f"• <b>{component.biounit_id}</b> - <b>{component.proportion}</b>\n"
                
                # Детальное описание компонента из ComponentDescription
                if hasattr(component, 'description') and component.description:
                    desc = component.description
                    
                    # Основное описание компонента
                    if (hasattr(desc, 'generic_description') and desc.generic_description and 
                        section_tracker.can_output_section(SectionTypes.GENERIC_DESCRIPTION, 'component')):
                        details_text += f"  📖 <b>Описание</b>\n    {desc.generic_description}\n"
                        section_tracker.mark_section_outputted(SectionTypes.GENERIC_DESCRIPTION)
                    
                    # Эффекты компонента
                    if (hasattr(desc, 'effects') and desc.effects and 
                        section_tracker.can_output_section(SectionTypes.EFFECTS, 'component')):
                        details_text += f"  ✨ <b>Эффекты</b>\n    {desc.effects}\n"
                        section_tracker.mark_section_outputted(SectionTypes.EFFECTS)
                    
                    # Шаманская перспектива компонента (приоритет)
                    if (hasattr(desc, 'shamanic') and desc.shamanic and 
                        section_tracker.can_output_section(SectionTypes.SHAMANIC, 'component')):
                        details_text += f"  🧙‍♂️ <b>Шаманская перспектива</b>\n    {desc.shamanic}\n"
                        section_tracker.mark_section_outputted(SectionTypes.SHAMANIC)
                    
                    # Предупреждения компонента (приоритет)
                    if (hasattr(desc, 'warnings') and desc.warnings and 
                        section_tracker.can_output_section(SectionTypes.WARNINGS, 'component')):
                        details_text += f"  ⚠️ <b>Предупреждения</b>\n    {desc.warnings}\n"
                        section_tracker.mark_section_outputted(SectionTypes.WARNINGS)
                    
                    # Инструкции по дозировке компонента
                    if (hasattr(desc, 'dosage_instructions') and desc.dosage_instructions and 
                        section_tracker.can_output_section(SectionTypes.DOSAGE_INSTRUCTIONS, 'component')):
                        details_text += f"  💊 <b>Дозировка</b>\n"
                        for instruction in desc.dosage_instructions:
                            details_text += f"    • {instruction.title}: {instruction.description}\n"
                        section_tracker.mark_section_outputted(SectionTypes.DOSAGE_INSTRUCTIONS)
                    
                    # Особенности компонента
                    if (hasattr(desc, 'features') and desc.features and 
                        section_tracker.can_output_section(SectionTypes.FEATURES, 'component')):
                        details_text += f"  🌟 <b>Особенности</b>\n    {', '.join(desc.features)}\n"
                        section_tracker.mark_section_outputted(SectionTypes.FEATURES)
                
                # Дополнительные свойства компонента
                if hasattr(component, 'properties') and component.properties:
                    details_text += f"  {component.properties}\n"
                
                # Добавляем "воздух" между ингредиентами
                details_text += "\n"
            details_text += "\n"
        
        # 📝 Общее описание продукта (только если не выведено компонентами)
        if (hasattr(product, 'generic_description') and product.generic_description and 
            section_tracker.can_output_section(SectionTypes.GENERIC_DESCRIPTION, 'product')):
            details_text += f"📖 <b>Описание</b>\n{product.generic_description}\n\n"
            section_tracker.mark_section_outputted(SectionTypes.GENERIC_DESCRIPTION)
        
        # ✨ Эффекты продукта (только если не выведены компонентами)
        if (hasattr(product, 'effects') and product.effects and 
            section_tracker.can_output_section(SectionTypes.EFFECTS, 'product')):
            details_text += f"✨ <b>Эффекты</b>\n{product.effects}\n\n"
            section_tracker.mark_section_outputted(SectionTypes.EFFECTS)
        
        # 💰 Цены и формы - структурированное отображение
        if hasattr(product, 'prices') and product.prices:
            details_text += f"💰 <b>Цены</b>\n"
            section_tracker.mark_section_outputted(SectionTypes.PRICES)
            for i, price in enumerate(product.prices, 1):
                details_text += f"• <b>{price.format_price()}</b>"
                
                # Вес или объем
                if price.is_weight_based:
                    details_text += f" за <b>{price.format_amount()}</b>"
                elif price.is_volume_based:
                    details_text += f" за <b>{price.format_amount()}</b>"
                
                # Форма продукта
                if hasattr(price, 'form') and price.form:
                    details_text += f" <i>{price.form}</i>"
                
                # Дополнительная информация о цене
                if hasattr(price, 'description') and price.description:
                    details_text += f" - {price.description}"
                
                details_text += "\n"
            details_text += "\n"
        
        # 📦 Формы продукта
        if hasattr(product, 'forms') and product.forms:
            forms_text = ', '.join(product.forms)
            details_text += f"📦 <b>Формы</b>\n{forms_text}\n\n"
            section_tracker.mark_section_outputted(SectionTypes.FORMS)
        
        # 💊 Инструкции по дозировке продукта (только если не выведены ранее)
        if (hasattr(product, 'dosage_instructions') and product.dosage_instructions and 
            section_tracker.can_output_section(SectionTypes.DOSAGE_INSTRUCTIONS, 'product')):
            details_text += f"💊 <b>Дозировка</b>\n"
            for instruction in product.dosage_instructions:
                details_text += f"<b>{instruction.title}</b>\n"
                details_text += f"{instruction.description}\n"
                
                # Тип дозировки
                if hasattr(instruction, 'type') and instruction.type:
                    details_text += f"<i>Тип: {instruction.type}</i>\n"
                
                details_text += "\n"
            details_text += "\n"
            section_tracker.mark_section_outputted(SectionTypes.DOSAGE_INSTRUCTIONS)
        
        # 🧙‍♂️ Шаманская перспектива продукта (только если не выведена ранее)
        if (hasattr(product, 'shamanic') and product.shamanic and 
            section_tracker.can_output_section(SectionTypes.SHAMANIC, 'product')):
            details_text += f"🧙‍♂️ <b>Шаманская перспектива</b>\n{product.shamanic}\n\n"
            section_tracker.mark_section_outputted(SectionTypes.SHAMANIC)
        
        # ⚠️ Предупреждения продукта (только если не выведены ранее)
        if (hasattr(product, 'warnings') and product.warnings and 
            section_tracker.can_output_section(SectionTypes.WARNINGS, 'product')):
            details_text += f"⚠️ <b>Предупреждения</b>\n{product.warnings}\n\n"
            section_tracker.mark_section_outputted(SectionTypes.WARNINGS)
        
        # 🏷️ Категории
        if hasattr(product, 'categories') and product.categories:
            categories_text = ', '.join(product.categories)
            details_text += f"🏷️ <b>Категории</b>\n{categories_text}\n\n"
            section_tracker.mark_section_outputted(SectionTypes.CATEGORIES)
        
        # 🌟 Особенности продукта (только если не выведены ранее)
        if (hasattr(product, 'features') and product.features and 
            section_tracker.can_output_section(SectionTypes.FEATURES, 'product')):
            details_text += f"🌟 <b>Особенности</b>\n"
            for feature in product.features:
                details_text += f"• {feature}\n"
            details_text += "\n"
            section_tracker.mark_section_outputted(SectionTypes.FEATURES)
        
        return details_text
        
    except Exception as e:
        # Fallback в случае ошибки форматирования
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[FORMATTING] Ошибка при форматировании продукта {getattr(product, 'title', 'unknown')}: {e}")
        return f"🏷️ <b>{getattr(product, 'title', 'Продукт')}</b>\n❌ Ошибка при загрузке детальной информации"
