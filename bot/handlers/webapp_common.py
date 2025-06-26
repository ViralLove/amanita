from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineQueryResultArticle, InputTextMessageContent
from bot.services.localization import Localization
from bot.fsm.onboarding_states import OnboardingStates
from bot.model.user_settings import UserSettings
from bot.services.blockchain import BlockchainService
from bot.services.account import AccountService
import logging
import json

router = Router()
logger = logging.getLogger(__name__)
user_settings = UserSettings()
blockchain = BlockchainService()
account_service = AccountService(blockchain)

@router.message(F.web_app_data)
async def handle_web_app_data(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    logger.info(f"[WEBAPP] Получены данные от WebApp для user_id={user_id}: {message.web_app_data.data}")
    logger.info(f"[WEBAPP] Тип сообщения: {type(message)}")
    logger.info(f"[WEBAPP] Атрибуты сообщения: {dir(message)}")

    try:
        data = json.loads(message.web_app_data.data)
        event = data.get("event")
        wallet_address = data.get("address")
        query_id = data.get("query_id")
        
        logger.info(f"[WEBAPP] Разобранные данные: event={event}, address={wallet_address}, query_id={query_id}")
        logger.info(f"[WEBAPP] Полные данные: {json.dumps(data, indent=2)}")

        if not wallet_address or not wallet_address.startswith('0x') or len(wallet_address) != 42:
            logger.warning(f"[WEBAPP][WARNING] Неверный формат адреса: {wallet_address}")
            await message.answer(loc.t("onboarding.invalid_address_format"))
            return

        # Проверка Invite NFT при восстановлении
        if event == "restored_access":
            has_invite = await account_service.validate_invite_code(wallet_address)
            if not has_invite:
                logger.warning(f"[WEBAPP][BLOCKED] Адрес {wallet_address} не владеет Invite NFT")
                await message.answer(loc.t("onboarding.no_invite_nft"))
                return

        # Сохраняем адрес и флаг подключения
        logger.info(f"[WEBAPP] Сохраняем адрес {wallet_address} для user_id={user_id}")
        user_settings.set_web3_credentials(user_id, wallet_address, None)
        user_settings.set_setting(user_id, 'wallet_connected', True)

        # FSM-переход для created_access
        current_state = await state.get_state()
        logger.info(f"[WEBAPP] Текущее состояние FSM: {current_state}, event: {event}")

        if event == "created_access" and current_state == OnboardingStates.WebAppConnecting.state:
            logger.info(f"[WEBAPP] Завершаем онбординг для user_id={user_id}")
            user_settings.set_setting(user_id, 'invite_verified', True)
            await state.set_state(OnboardingStates.Completed)

            # Получаем invite_code из состояния FSM
            data = await state.get_data()
            logger.info(f"[WEBAPP] Данные из FSM: {data}")
            invite_code = data.get('invite_code')
            
            new_invite_codes = await account_service.activate_and_mint_invites(invite_code, wallet_address)
            
            if invite_code and wallet_address and new_invite_codes:
                logger.info(f"[WEBAPP][INVITE] Инвайт {invite_code} для адреса {wallet_address} успешно активирован")
                try:
                    
                    # 1. Отправляем сообщение об успешном подключении
                    final_message = (
                        f"{loc.t('onboarding.onboarding_complete')}\n\n"
                        f"{loc.t('onboarding.onboarding_complete_summary')}\n\n"
                        f"{loc.t('onboarding.onboarding_reminder')}"
                    )
                    await message.answer(final_message)

                    # 2. Отправляем каждый инвайт-код отдельным сообщением
                    await message.answer("🎁 Твои инвайт-коды для приглашения друзей:")
                    for i, code in enumerate(new_invite_codes, 1):
                        await message.answer(f"Инвайт #{i}:\n`{code}`", parse_mode="Markdown")

                    # 3. Отправляем кнопку для перехода в каталог
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=loc.t("onboarding.btn_catalog"), callback_data="menu:catalog")]
                    ])
                    await message.answer("🛍 Теперь ты можешь перейти в каталог:", reply_markup=keyboard)

                except Exception as e:
                    logger.error(f"[WEBAPP][INVITE] Ошибка при активации инвайта: {str(e)}")
                    await message.answer("⚠️ Произошла ошибка при активации инвайта. Пожалуйста, обратитесь в поддержку.")
            
            return

        # Подпись транзакции
        if event == "tx_signed":
            signature = data.get("signature")
            order_id = data.get("order_id")
            tx_type = data.get("tx_type")

            if not signature or not order_id or not tx_type:
                logger.error("[WEBAPP][TX_SIGNED] Недостаточно данных для подписи транзакции")
                await message.answer(loc.t("onboarding.signature_incomplete"))
                return

            # Сокращаем подпись для отображения
            short_signature = f"{signature[:10]}...{signature[-10:]}"

            logger.info(f"[WEBAPP][TX_SIGNED] Подпись от {wallet_address}: {signature} для заказа {order_id}")
            await message.answer(
                loc.t("onboarding.signature_received", tx_type, order_id, short_signature),
                parse_mode="Markdown"
            )
            return

        # По умолчанию: сообщение об успешном подключении
        # Сокращаем адрес для отображения
        short_address = f"{wallet_address[:10]}...{wallet_address[-8:]}"
        
        logger.info(f"[WEBAPP] Успешно подключен кошелек для user_id={user_id}")
        await message.answer(
            loc.t("onboarding.wallet_connected", short_address),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"[WEBAPP][ERROR] Ошибка при разборе web_app_data: {str(e)}")
        await message.answer(loc.t("onboarding.webapp_error"))