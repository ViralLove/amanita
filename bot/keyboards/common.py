# Общие кнопки для разных сценариев

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.common.localization import Localization

def get_product_keyboard(product_id: str, loc: Localization) -> InlineKeyboardMarkup:
    """
    Создает inline клавиатуру для продукта с кнопками действий.
    
    Args:
        product_id: Идентификатор продукта
        loc: Объект локализации для текста кнопок
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для продукта
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="📖 Подробнее",
                callback_data=f"product:details:{product_id}"
            ),
            InlineKeyboardButton(
                text="🛒 В корзину",
                callback_data=f"product:cart:{product_id}"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_product_details_keyboard(product_id: str, loc: Localization) -> InlineKeyboardMarkup:
    """
    Создает inline клавиатуру для детального просмотра продукта.
    
    Args:
        product_id: Идентификатор продукта
        loc: Объект локализации для текста кнопок
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для детального просмотра
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="🛒 В корзину",
                callback_data=f"product:cart:{product_id}"
            ),
            InlineKeyboardButton(
                text="🔙 Назад к каталогу",
                callback_data="menu:catalog"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_product_details_keyboard_no_duplicate(product_id: str, loc: Localization) -> InlineKeyboardMarkup:
    """
    Создает inline клавиатуру для детального просмотра продукта без дублирования.
    Кнопки размещаются только под изображением с текстом.
    
    Args:
        product_id: Идентификатор продукта
        loc: Объект локализации для текста кнопок
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для детального просмотра
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="🛒 В корзину",
                callback_data=f"product:cart:{product_id}"
            ),
            InlineKeyboardButton(
                text="🔙 Назад к каталогу",
                callback_data="menu:catalog"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_product_details_keyboard_with_scroll(product_id: str, loc: Localization) -> InlineKeyboardMarkup:
    """
    Создает inline клавиатуру для детального просмотра продукта с умной навигацией.
    Вместо перезагрузки каталога используется скролл к хэштегу #catalog.
    
    Args:
        product_id: Идентификатор продукта
        loc: Объект локализации для текста кнопок
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для детального просмотра и умной навигации
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="🛒 В корзину",
                callback_data=f"product:cart:{product_id}"
            ),
            InlineKeyboardButton(
                text="🔙 К каталогу",
                callback_data="scroll:catalog"
            )
        ],

    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 