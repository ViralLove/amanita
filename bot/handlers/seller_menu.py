from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.command import Command
from bot.services.common.localization import Localization
from bot.model.user_settings import UserSettings
from bot.services.core.blockchain import BlockchainService
import logging

router = Router()
logger = logging.getLogger(__name__)

user_settings = UserSettings()
blockchain = BlockchainService()

# Кнопки меню продавца
def get_seller_menu_keyboard(loc):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=loc.t("seller_menu.btn_my_products"), callback_data="seller:products_list")],
        [InlineKeyboardButton(text=loc.t("seller_menu.btn_add_product"), callback_data="seller:add_product")],
        [InlineKeyboardButton(text=loc.t("seller_menu.btn_orders"), callback_data="seller:orders")],
        [InlineKeyboardButton(text=loc.t("seller_menu.btn_settings"), callback_data="seller:settings")]
    ])

@router.message(F.text == "/seller")
async def show_seller_menu(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    text = loc.t("seller_menu.welcome")
    keyboard = get_seller_menu_keyboard(loc)

    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data == "seller:products_list")
async def handle_seller_products_list(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    # Заглушка: загружаем список товаров из блокчейна (пример)
    products = blockchain.get_all_products()

    if not products:
        await callback.message.answer(loc.t("seller_menu.no_products"))
        return

    text = loc.t("seller_menu.my_products") + "\n\n"
    for idx, product in enumerate(products, start=1):
        text += f"{idx}. {product}\n"

    await callback.message.answer(text)

@router.callback_query(F.data == "seller:add_product")
async def handle_seller_add_product(callback: types.CallbackQuery, state: FSMContext):
    # Просто перенаправляем пользователя к команде /create_product
    await callback.message.answer("/create_product")

@router.callback_query(F.data == "seller:orders")
async def handle_seller_orders(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    # Заглушка: получаем заказы (пример)
    orders = ["Order #1 (В пути)", "Order #2 (Завершён)"]

    if not orders:
        await callback.message.answer(loc.t("seller_menu.no_orders"))
        return

    text = loc.t("seller_menu.my_orders") + "\n\n"
    for order in orders:
        text += f"• {order}\n"

    await callback.message.answer(text)

@router.callback_query(F.data == "seller:settings")
async def handle_seller_settings(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    text = loc.t("seller_menu.settings_intro")
    await callback.message.answer(text)
