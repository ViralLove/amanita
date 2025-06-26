from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto
from bot.services.localization import Localization
from bot.model.user_settings import UserSettings
from bot.services.product_registry import ProductRegistryService
from bot.services.blockchain import BlockchainService
from bot.services.ar_weave import ArWeaveUploader
import logging
import tempfile
import aiohttp
import os

router = Router()
logger = logging.getLogger(__name__)

# Инициализируем сервисы
user_settings = UserSettings()
blockchain_service = BlockchainService()
arweave_uploader = ArWeaveUploader()
product_registry_service = ProductRegistryService(blockchain_service, arweave_uploader)

@router.callback_query(F.data == "menu:catalog")
async def show_catalog(callback: CallbackQuery):
    """
    Обработчик для показа каталога товаров.
    Архитектурная цепочка:
    1. Получаем user_id и язык пользователя
    2. Проверяем наличие подключенного кошелька в user_settings
    3. Получаем каталог через ProductRegistryService (с кэшированием)
    4. Для каждого продукта загружаем медиа из Arweave и отправляем в чат
    """
    user_id = callback.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    try:
        logger.info("[CATALOG] Запрос каталога товаров")
        
        # Получаем адрес кошелька из настроек пользователя
        wallet_address = user_settings.get_wallet_address(user_id)
        if not wallet_address:
            logger.warning(f"[CATALOG] Кошелек не подключен для user_id={user_id}")
            await callback.message.answer("⚠️ Сначала подключите кошелёк через кнопку 🔐 Криптокошелёк в меню")
            return

        logger.info(f"[CATALOG] Получаем товары для адреса: {wallet_address}")
        
        # Получаем товары через сервис (с кэшированием)
        products = await product_registry_service.get_all_products()
        
        if not products:
            logger.info(f"[CATALOG] Каталог пуст для адреса {wallet_address}")
            await callback.message.answer("🤷‍♂️ Каталог пуст")
            return

        # Отправляем каждый продукт отдельным сообщением с медиа
        for product in products:
            try:
                # Загружаем изображение обложки из Arweave
                if product.cover_image_url:
                    # Создаем временный файл для изображения
                    async with aiohttp.ClientSession() as session:
                        async with session.get(product.cover_image_url) as response:
                            if response.status == 200:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                                    tmp_file.write(await response.read())
                                    image_path = tmp_file.name
                            else:
                                logger.error(f"[CATALOG] Ошибка загрузки изображения: {product.cover_image_url}")
                                image_path = None

                # Формируем текст описания
                product_text = (
                    f"🏷 {product.title}\n\n"
                    f"📝 {product.description}\n\n"
                f"💰 Цена: {product.price} USDT\n"
                    f"🏷 Категории: {', '.join(product.categories)}\n"
                )

                # Отправляем фото с описанием
                if image_path:
                    await callback.message.answer_photo(
                        FSInputFile(image_path),
                        caption=product_text
                    )
                    # Удаляем временный файл
                    os.unlink(image_path)
                else:
                    await callback.message.answer(product_text)

            except Exception as e:
                logger.error(f"[CATALOG] Ошибка при отправке продукта {product.id}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"[CATALOG] Ошибка при получении каталога: {e}")
        await callback.message.answer("⚠️ Произошла ошибка при загрузке каталога")
    
    finally:
        await callback.answer() 