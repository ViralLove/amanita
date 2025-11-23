"""
Component description handlers for Telegram bot.
Handles display of detailed component descriptions in multiple languages.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from services.common.localization import Localization
from dependencies import get_product_registry_service

logger = logging.getLogger(__name__)
router = Router()


def get_component_service():
    """Helper to get ComponentService instance"""
    from services.product.component_service import ComponentService
    return ComponentService()


@router.callback_query(F.data.startswith("component_desc:"))
async def show_component_description_section(
    callback: CallbackQuery,
    loc: Localization
):
    """
    Показывает конкретную секцию ComponentDescription.
    
    Callback data format:
    component_desc:{component_id}:{section}:{language}
    
    Section values:
    - generic: Активные компоненты
    - effects: Целительное действие
    - shamanic: Шаманская перспектива
    - warnings: Предостережения
    """
    try:
        # Parse callback data
        parts = callback.data.split(":")
        if len(parts) != 4:
            await callback.answer(loc.t('catalog.product.component_description.error_format'))
            return
        
        _, component_id, section, language = parts
        
        logger.info(f"[ComponentHandler] Show section: {section} for {component_id} (lang: {language})")
        
        # Get component service
        component_service = get_component_service()
        
        # Fetch ComponentDescription
        description = component_service.get_component_description(
            component_id,
            language
        )
        
        if not description:
            await callback.answer(loc.t('catalog.product.component_description.unavailable'))
            return
        
        # Get component full for scientific title
        component = component_service.get_component_full(component_id)
        
        # Format section content (use localized titles)
        section_title = {
            "generic": loc.t('catalog.product.component_description.section_generic'),
            "effects": loc.t('catalog.product.component_description.section_effects'),
            "shamanic": loc.t('catalog.product.component_description.section_shamanic'),
            "warnings": loc.t('catalog.product.component_description.section_warnings')
        }.get(section, "📖 Описание")
        
        section_content = {
            "generic": description.generic_description,
            "effects": description.effects,
            "shamanic": description.shamanic,
            "warnings": description.warnings
        }.get(section, "")
        
        if not section_content:
            await callback.answer(loc.t('catalog.product.component_description.section_empty'))
            return
        
        # Format message
        text = f"{section_title}\n"
        if component and hasattr(component, 'scientific_title'):
            text += f"<b>{component.scientific_title}</b>\n\n"
        text += section_content
        
        # Create navigation buttons
        keyboard = _create_section_navigation_keyboard(
            component_id,
            section,
            language,
            has_generic=bool(description.generic_description),
            has_effects=bool(description.effects),
            has_shamanic=bool(description.shamanic),
            has_warnings=bool(description.warnings)
        )
        
        # Send message
        await callback.message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"[ComponentHandler] Error showing section: {e}", exc_info=True)
        await callback.answer(loc.t('catalog.product.component_description.error_loading'))


def _create_section_navigation_keyboard(
    component_id: str,
    current_section: str,
    language: str,
    has_generic: bool,
    has_effects: bool,
    has_shamanic: bool,
    has_warnings: bool
) -> InlineKeyboardMarkup:
    """Create navigation keyboard for section display"""
    
    # Section order for navigation
    sections = []
    if has_generic:
        sections.append(("generic", "🔬 Активные компоненты"))
    if has_effects:
        sections.append(("effects", "🌿 Целительное действие"))
    if has_shamanic:
        sections.append(("shamanic", "🌀 Шаманская перспектива"))
    if has_warnings:
        sections.append(("warnings", "⚠️ Предостережения"))
    
    # Find current index
    current_idx = next((i for i, (s, _) in enumerate(sections) if s == current_section), -1)
    
    buttons = []
    
    # Previous/Next buttons (Note: can't use loc.t() here as it's not passed, keeping hardcoded for now)
    # TODO: Consider refactoring to pass loc parameter
    nav_row = []
    if current_idx > 0:
        prev_section = sections[current_idx - 1][0]
        nav_row.append(InlineKeyboardButton(
            text="⬅️ Назад",  # Note: hardcoded (inline keyboard text is less critical)
            callback_data=f"component_desc:{component_id}:{prev_section}:{language}"
        ))
    
    if current_idx < len(sections) - 1:
        next_section = sections[current_idx + 1][0]
        next_title = sections[current_idx + 1][1].split()[1]  # Get emoji + first word
        nav_row.append(InlineKeyboardButton(
            text=f"➡️ {next_title}",  # Note: uses localized title from caller
            callback_data=f"component_desc:{component_id}:{next_section}:{language}"
        ))
    
    if nav_row:
        buttons.append(nav_row)
    
    # Back to product button
    # (В реальности нужно хранить product_id, пока оставляем без него)
    buttons.append([InlineKeyboardButton(
        text="⬅️ Закрыть",  # Note: hardcoded (inline keyboard text is less critical)
        callback_data=f"close_description"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data.startswith("component_menu:"))
async def show_component_description_menu(
    callback: CallbackQuery,
    loc: Localization
):
    """
    Показывает меню секций ComponentDescription.
    Используется для MULTI products для избежания перегрузки UI.
    
    Callback data format:
    component_menu:{component_id}:{language}
    """
    try:
        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer(loc.t('catalog.product.component_description.error_format'))
            return
        
        _, component_id, language = parts
        
        logger.info(f"[ComponentHandler] Show menu for {component_id} (lang: {language})")
        
        # Get component
        component_service = get_component_service()
        component = component_service.get_component_full(component_id)
        
        if not component:
            await callback.answer(loc.t('catalog.product.component_description.component_not_found'))
            return
        
        # Format message
        text = loc.t('catalog.product.component_description.menu_title') + "\n"
        if hasattr(component, 'scientific_title'):
            text += f"<b>{component.scientific_title}</b>\n\n"
        text += loc.t('catalog.product.component_description.select_section')
        
        # Create keyboard (same as product card)
        from handlers.dependencies import get_product_formatter_service
        formatter = get_product_formatter_service()
        keyboard = formatter._create_component_description_keyboard(
            component_id,
            language,
            ""  # product_id TODO
        )
        
        # Send message
        await callback.message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"[ComponentHandler] Error showing menu: {e}", exc_info=True)
        await callback.answer(loc.t('catalog.product.component_description.error_menu'))


@router.callback_query(F.data == "close_description")
async def close_description(callback: CallbackQuery):
    """Close description message"""
    try:
        await callback.message.delete()
        await callback.answer()
    except Exception as e:
        logger.error(f"[ComponentHandler] Error closing description: {e}")
        await callback.answer()

