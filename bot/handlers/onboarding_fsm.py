from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.filters.command import Command
from bot.fsm.onboarding_states import OnboardingStates
from bot.services.common.localization import Localization
from bot.model.user_settings import UserSettings
from bot.services.core.blockchain import BlockchainService
import logging
import re
import os

router = Router()
logger = logging.getLogger(__name__)
user_settings = UserSettings()
blockchain = BlockchainService()

WALLET_APP_URL = os.getenv("WALLET_APP_URL")

LANG_KEYBOARD = [
    ["🇷🇺 ru", "🇪🇸 es", "🇬🇧 en", "🇫🇷 fr"],
    ["🇪🇪 et", "🇮🇹 it", "🇵🇹 pt", "🇩🇪 de"],
    ["🇵🇱 pl", "🇫🇮 fi", "🇳🇴 no", "🇸🇪 sv"]
]

def get_language_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=lang) for lang in row] for row in LANG_KEYBOARD],
        resize_keyboard=True
    )

lang_map = {
    "🇷🇺 ru": "ru",
    "🇪🇸 es": "es",
    "🇬🇧 en": "en",
    "🇫🇷 fr": "fr",
    "🇪🇪 et": "et",
    "🇮🇹 it": "it",
    "🇵🇹 pt": "pt",
    "🇩🇪 de": "de",
    "🇵🇱 pl": "pl",
    "🇫🇮 fi": "fi",
    "🇳🇴 no": "no",
    "🇸🇪 sv": "sv"
}

@router.message(F.text == "/start")
async def start_onboarding(message: types.Message, state: FSMContext):
    await state.set_state(OnboardingStates.LanguageSelection)
    await message.answer("Пожалуйста, выберите язык:", reply_markup=get_language_keyboard())

@router.message(OnboardingStates.LanguageSelection, F.text.in_(lang_map.keys()))
async def set_language(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = lang_map[message.text]
    user_settings.set_language(user_id, lang)
    logger.info(f"[ONBOARDING] Установлен язык: {lang} для user_id={user_id}")

    await state.set_state(OnboardingStates.OnboardingPathChoice)
    loc = Localization(lang)
    welcome_message = (
        f"{loc.t('onboarding.welcome_title')}\n\n"
        f"{loc.t('onboarding.welcome_description')}\n\n"
        f"{loc.t('onboarding.welcome_instruction')}\n\n"
        f"{loc.t('onboarding.welcome_choose')}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=loc.t("onboarding.btn_have_invite"), callback_data="onboarding:have_invite")],
        [InlineKeyboardButton(text=loc.t("onboarding.btn_restore"), callback_data="onboarding:restore")]
    ])
    await message.answer(welcome_message, reply_markup=keyboard)

@router.callback_query(F.data == "onboarding:have_invite")
async def process_invite_choice(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)
    await callback.message.answer(loc.t("onboarding.input_invite_label"))
    await state.set_state(OnboardingStates.InviteInput)

@router.message(OnboardingStates.InviteInput)
async def process_invite_code(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)
    invite_code = message.text.strip()

    logger.info(f"[INVITE] Получен инвайт-код для проверки: {invite_code}")

    if not re.match(r"^AMANITA-[A-Za-z0-9]{4}-[A-Za-z0-9]{4}$", invite_code):
        logger.warning(f"[INVITE] Неверный формат инвайт-кода: {invite_code}")
        await message.answer(loc.t("onboarding.invalid_invite"))
        await message.answer(loc.t("onboarding.retry"))
        return

    logger.info("[INVITE] Начинаем валидацию через блокчейн...")
    validation = blockchain.validate_invite_code(invite_code)
    logger.info(f"[INVITE] Результат валидации: {validation}")

    if not validation.get("success"):
        logger.error(f"[INVITE] Ошибка валидации: {validation.get('reason')}")
        await message.answer(loc.t("onboarding.invalid_invite"))
        await message.answer(loc.t("onboarding.retry"))
        return

    await state.set_data(data={"invite_code": invite_code})

    success_text = (
        f"{loc.t('onboarding.invite_validated')}\n\n"
        f"{loc.t('onboarding.invite_validated_instruction')}\n\n"
        f"{loc.t('onboarding.invite_security_notice')}"
    )

    # Формируем URL для WebApp
    webapp_url = f"{WALLET_APP_URL}?mode=create_new&invite_verified=true&source=onboarding&debug=1"
    
    logger.info(f"[INVITE] Открываем WebApp для создания кошелька: {webapp_url}")

    # Используем ReplyKeyboardMarkup вместо InlineKeyboardMarkup
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(
                text=loc.t("onboarding.btn_connect"),
                web_app=WebAppInfo(url=webapp_url)
            )
        ]],
        resize_keyboard=True,
        one_time_keyboard=True  # Клавиатура скроется после использования
    )
    
    await state.set_state(OnboardingStates.WebAppConnecting)
    await message.answer(success_text, reply_markup=keyboard)

@router.callback_query(F.data == "onboarding:restore")
async def process_restore_access(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    webapp_url = f"{WALLET_APP_URL}?mode=recovery_only&invite_verified=false&source=onboarding"
    logger.info(f"Opening webapp (recovery): {webapp_url}")

    # Также меняем на ReplyKeyboardMarkup для восстановления
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(
                text=loc.t("onboarding.btn_restore_connect"),
                web_app=WebAppInfo(url=webapp_url)
            )
        ]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await state.set_state(OnboardingStates.RestoreAccess)
    await callback.message.answer(loc.t("onboarding.restore_intro"), reply_markup=keyboard)

@router.message(Command("view_seed"))
async def view_seed_access(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)
    wallet_address = user_settings.get_wallet_address(user_id)

    if not wallet_address:
        await message.answer("⚠️ Адрес кошелька не найден. Сначала подключите кошелёк через онбординг.")
        return

    logger.info(f"Opening WebApp to view seed phrase for: {wallet_address}")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=loc.t("onboarding.btn_access_settings"),
            web_app=WebAppInfo(
                url=f"{WALLET_APP_URL}?mode=view_seed"
            )
        )]
    ])
    await message.answer("🔐 Доступ к ключ-траве (seed phrase):", reply_markup=keyboard)

@router.message(Command("sign_discount"))
async def sign_discount_tx(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    # Пример данных — в реальности они должны приходить из логики оформления заказа
    order_id = "ORDER123"
    discount_tokens = 88
    wallet_address = user_settings.get_wallet_address(user_id)

    if not wallet_address:
        await message.answer("⚠️ Адрес кошелька не найден. Сначала подключите кошелёк через онбординг.")
        return

    logger.info(f"Opening WebApp to sign tx: order={order_id}, tokens={discount_tokens}, addr={wallet_address}")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Подписать скидку",
            web_app=WebAppInfo(
                url=f"{WALLET_APP_URL}?mode=sign_tx&tx_type=discount&order_id={order_id}&discount_tokens={discount_tokens}&address={wallet_address}"
            )
        )]
    ])
    await message.answer("🔏 Подпишите транзакцию для использования скидки AMANITA:", reply_markup=keyboard)
