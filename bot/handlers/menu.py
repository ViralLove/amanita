"""
Обработчик основного меню
"""

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from bot.services.common.localization import Localization
from bot.model.user_settings import UserSettings
from bot.config import WALLET_APP_URL
import logging
import json
import os

router = Router()

# Получаем единый экземпляр UserSettings (Singleton)
user_settings = UserSettings()

# Логируем URL для WebApp кошелька
logging.info(f"[MENU] WALLET_APP_URL из config: {WALLET_APP_URL}")

def get_main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру основного меню"""
    lang_code = user_settings.get_language(user_id)
    logging.info(f"[MENU] get_main_menu_keyboard: user_id={user_id}, lang_code={lang_code}")
    loc = Localization(lang_code)
    keyboard = [
        [
            InlineKeyboardButton(
            text=loc.t("menu.catalog"),
            callback_data="menu:catalog"
        )

        ],
        [
            InlineKeyboardButton(
                text=loc.t("menu.cart"),
                callback_data="menu:cart"
            ),
            InlineKeyboardButton(
                text=loc.t("menu.profile"),
                callback_data="menu:profile"
            )
        ],
        [
            InlineKeyboardButton(
                text=loc.t("menu.orders"),
                callback_data="menu:orders"
            ),
            InlineKeyboardButton(
                text=loc.t("menu.support"),
                callback_data="menu:support"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔐 Криптокошелёк",
                callback_data="menu:wallet"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("menu"))
async def show_main_menu(message: types.Message):
    """Показывает основное меню"""
    user_id = message.from_user.id
    lang_code = user_settings.get_language(user_id)
    logging.info(f"[MENU] show_main_menu: user_id={user_id}, lang_code={lang_code}")
    
    # Проверим все пользовательские настройки
    all_user_settings = user_settings.get_all_settings(user_id)
    logging.info(f"[MENU] Все настройки пользователя: {json.dumps(all_user_settings, default=str)}")
    
    loc = Localization(lang_code)
    
    # Проверяем наличие необходимых ключей
    logging.info(f"[MENU] Проверка наличия ключа 'menu.welcome'")
    welcome_text = loc.t("menu.welcome")
    logging.info(f"[MENU] Текст приветствия в меню: '{welcome_text[:50]}...'")
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(user_id)
    )

@router.message(Command("wallet"))
async def show_wallet(message: types.Message):
    """Показывает страницу с криптокошельком через WebApp"""
    user_id = message.from_user.id
    lang_code = user_settings.get_language(user_id)
    logging.info(f"[WALLET] show_wallet: user_id={user_id}, lang_code={lang_code}, wallet_url={WALLET_APP_URL}")
    
    # Проверяем статус инвайта пользователя
    invite_verified = user_settings.get_setting(user_id, 'invite_verified', False)
    logging.info(f"[WALLET] invite_verified для user_id={user_id}: {invite_verified}")
    
    # Формируем базовый URL и добавляем параметр статуса инвайта
    wallet_url = WALLET_APP_URL
    if '?' not in wallet_url:
        wallet_url += f"?invite_verified={str(invite_verified).lower()}"
    else:
        wallet_url += f"&invite_verified={str(invite_verified).lower()}"
        
    logging.info(f"[WALLET][DEBUG] Создание WebAppInfo с URL и параметрами: {wallet_url}")
    
    # Создаем клавиатуру с одной кнопкой для открытия WebApp
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔐 Открыть криптокошелёк",
                web_app=WebAppInfo(url=wallet_url)
            )
        ]
    ])
    
    # Отправляем сообщение с инструкцией и кнопкой
    await message.answer(
        "Нажмите на кнопку ниже, чтобы открыть ваш криптокошелёк. "
        "Вы сможете создать новый кошелёк или восстановить существующий по сид-фразе.",
        reply_markup=keyboard
    )
    logging.info(f"[WALLET][DEBUG] Сообщение с кнопкой WebApp отправлено: url={wallet_url}")

# Добавляем обработчик для получения ошибок WebApp (если они есть)
@router.callback_query(lambda c: c.data == "webapp_error")
async def handle_webapp_error(callback_query: types.CallbackQuery):
    """Обрабатывает ошибки WebApp"""
    error_data = callback_query.data
    logging.error(f"[WALLET][ERROR] Получена ошибка от WebApp: {error_data}")
    await callback_query.answer("Ошибка WebApp зарегистрирована")

@router.callback_query(lambda c: c.data.startswith("menu:"))
async def process_menu_callback(callback_query: types.CallbackQuery):
    """Обрабатывает нажатия на кнопки меню"""
    user_id = callback_query.from_user.id
    action = callback_query.data.split(":")[1]
    lang_code = user_settings.get_language(user_id)
    loc = Localization(lang_code)

    logging.info(f"[MENU] process_menu_callback: user_id={user_id}, action={action}, lang_code={lang_code}")
    logging.info(f"hahaha")
    if action == "catalog":
        # Не обрабатываем здесь, чтобы сработал обработчик из catalog.py
        logging.info(f"Catalog callback detected")
        return

    # Остальные действия меню
    if action == "cart":
        await callback_query.message.edit_text(
            text=loc.t("menu.cart") + " (в разработке)",
            reply_markup=get_main_menu_keyboard(user_id)
        )
    elif action == "profile":
        await callback_query.message.edit_text(
            text=loc.t("menu.profile") + " (в разработке)",
            reply_markup=get_main_menu_keyboard(user_id)
        )
    elif action == "orders":
        await callback_query.message.edit_text(
            text=loc.t("menu.orders") + " (в разработке)",
            reply_markup=get_main_menu_keyboard(user_id)
        )
    elif action == "support":
        await callback_query.message.edit_text(
            text=loc.t("menu.support") + " (в разработке)",
            reply_markup=get_main_menu_keyboard(user_id)
        )
    
    await callback_query.answer()

@router.callback_query(lambda c: c.data == "menu:wallet")
async def open_wallet(callback: types.CallbackQuery):
    """Открывает WebApp кошелька через inline режим"""
    lang_code = user_settings.get_language(callback.from_user.id)
    loc = Localization(lang_code)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=loc.t("menu.open_wallet"),
            web_app=WebAppInfo(url=f"{WALLET_APP_URL}?source=inline")
        )
    ]])
    
    await callback.message.answer(
        loc.t("menu.wallet_instruction"),
        reply_markup=keyboard
    )
    await callback.answer()