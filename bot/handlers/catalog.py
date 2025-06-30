from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto
from bot.services.common.localization import Localization
from bot.model.user_settings import UserSettings
from bot.services.product.registry_singleton import product_registry_service
from bot.services.core.blockchain import BlockchainService
from bot.services.core.ipfs_factory import IPFSFactory
from bot.services.product.validation import ProductValidationService
from bot.services.core.account import AccountService
import logging
import tempfile
import aiohttp
import os

router = Router()
logger = logging.getLogger(__name__)

logger.info("[CATALOG] Инициализация сервисов...")
try:
    logger.info("[CATALOG] Инициализация UserSettings...")
    user_settings = UserSettings()
    logger.info("[CATALOG] UserSettings инициализирован")

    logger.info("[CATALOG] Инициализация BlockchainService...")
    blockchain_service = BlockchainService()
    logger.info("[CATALOG] BlockchainService инициализирован")

    logger.info("[CATALOG] Инициализация IPFSFactory...")
    storage_service = IPFSFactory().get_storage()
    logger.info("[CATALOG] IPFSFactory инициализирован")

    logger.info("[CATALOG] Инициализация ProductValidationService...")
    validation_service = ProductValidationService()
    logger.info("[CATALOG] ProductValidationService инициализирован")

    logger.info("[CATALOG] Инициализация AccountService...")
    account_service = AccountService(blockchain_service)
    logger.info("[CATALOG] AccountService инициализирован")

    # Используем глобальный экземпляр product_registry_service
    logger.info("[CATALOG] Используется глобальный экземпляр product_registry_service")
    logger.info("[CATALOG] Все сервисы успешно инициализированы!")
except Exception as e:
    logger.error(f"[CATALOG] Ошибка при инициализации сервисов: {e}")
    import traceback
    logger.error(traceback.format_exc())

@router.callback_query(F.data == "menu:catalog")
async def show_catalog(callback: CallbackQuery):
    logger.info(f"[CATALOG] show_catalog вызван! callback.data={callback.data}, from_user={callback.from_user.id}")
    """
    Обработчик для показа каталога товаров.
    Архитектурная цепочка:
    1. Получаем user_id и язык пользователя
    2. Получаем каталог через ProductRegistryService (с кэшированием)
    3. Для каждого продукта формируем описание и отправляем в чат
    """
    user_id = callback.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    try:
        logger.info("[CATALOG] Запрос каталога товаров")
        
        # Отправляем сообщение о загрузке
        loading_message = await callback.message.answer(loc.t("catalog.loading"))
        
        # Получаем каталог через сервис (с кэшированием)
        products = product_registry_service.get_all_products()
        
        # Удаляем сообщение о загрузке
        await loading_message.delete()
        
        if not products:
            logger.info("[CATALOG] Каталог пуст")
            await callback.message.answer(loc.t("catalog.empty"))
            return

        logger.info(f"[CATALOG] Найдено {len(products)} продуктов")

        # Отправляем каждый продукт отдельным сообщением
        for i, product in enumerate(products):
            try:
                # Формируем текст описания продукта
                product_text = (
                    f"🏷 <b>{product.title}</b>\n\n"
                )
                
                # Добавляем описание если есть
                if product.description and product.description.generic_description:
                    product_text += f"📝 {product.description.generic_description[:200]}...\n\n"
                
                # Добавляем вид и формы
                if product.species:
                    product_text += f"{loc.t('catalog.product.species')}: <b>{product.species}</b>\n"
                
                if product.forms:
                    product_text += f"{loc.t('catalog.product.forms')}: <b>{', '.join(product.forms)}</b>\n"
                
                # Добавляем категории
                if product.categories:
                    product_text += f"{loc.t('catalog.product.categories')}: <b>{', '.join(product.categories)}</b>\n"
                
                # Добавляем цены
                if product.prices:
                    product_text += f"{loc.t('catalog.product.prices')}:\n"
                    for price in product.prices:
                        product_text += f"   • {price.format_full()}\n"
                
                # Добавляем статус
                status_text = loc.t('catalog.product.active') if product.is_active else loc.t('catalog.product.inactive')
                product_text += f"\n{status_text}"
                
                # Отправляем сообщение с изображением если есть
                if product.cover_image_url:
                    try:
                        # Создаем временный файл для изображения
                        async with aiohttp.ClientSession() as session:
                            async with session.get(product.cover_image_url) as response:
                                if response.status == 200:
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                                        tmp_file.write(await response.read())
                                        image_path = tmp_file.name
                                    
                                    await callback.message.answer_photo(
                                        FSInputFile(image_path),
                                        caption=product_text,
                                        parse_mode="HTML"
                                    )
                                    # Удаляем временный файл
                                    os.unlink(image_path)
                                else:
                                    logger.error(f"[CATALOG] Ошибка загрузки изображения: {product.cover_image_url}")
                                    await callback.message.answer(product_text, parse_mode="HTML")
                    except Exception as e:
                        logger.error(f"[CATALOG] Ошибка при отправке изображения: {e}")
                        await callback.message.answer(product_text, parse_mode="HTML")
                else:
                    await callback.message.answer(product_text, parse_mode="HTML")
                
                # Добавляем разделитель между продуктами (кроме последнего)
                if i < len(products) - 1:
                    await callback.message.answer("☀️" * 20)

            except Exception as e:
                logger.error(f"[CATALOG] Ошибка при отправке продукта {product.id}: {e}")
                continue
        
        logger.info(f"[CATALOG] Каталог успешно отправлен: {len(products)} продуктов")
        
    except Exception as e:
        logger.error(f"[CATALOG] Ошибка при получении каталога: {e}")
        await callback.message.answer(loc.t("catalog.error"))
    
    finally:
        await callback.answer() 