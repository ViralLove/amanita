from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto
from bot.services.common.localization import Localization
from bot.model.user_settings import UserSettings
from bot.services.product.registry_singleton import product_registry_service
from bot.services.core.blockchain import BlockchainService
from bot.services.core.ipfs_factory import IPFSFactory
from bot.services.product.validation import ProductValidationService
from bot.services.core.account import AccountService
from bot.keyboards.common import get_product_keyboard, get_product_details_keyboard_no_duplicate, get_product_details_keyboard_with_scroll
# Импортируем сервис форматирования и dependency providers
from .common.formatting import ProductFormatterService
from .dependencies import get_product_formatter_service
import logging
import tempfile
import aiohttp
import os
from typing import Dict

router = Router()
logger = logging.getLogger(__name__)

# ================== ФУНКЦИИ ФОРМАТИРОВАНИЯ ВЫНЕСЕНЫ В МОДУЛЬ .common.formatting ==================

# Создаем экземпляр сервиса форматирования
formatter_service = get_product_formatter_service()

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
        products = await product_registry_service.get_all_products()
        
        # Удаляем сообщение о загрузке
        await loading_message.delete()
        
        if not products:
            logger.info("[CATALOG] Каталог пуст")
            await callback.message.answer(loc.t("catalog.empty"))
            return

        logger.info(f"[CATALOG] Найдено {len(products)} продуктов")

        # Отправляем сообщение о прогрессе с хэштегами для навигации
        progress_message = await callback.message.answer(
            f"📦 Загружаем каталог: 0/{len(products)} продуктов...\n\n"
            f"🔍 <b>Навигация:</b> #catalog"
        )

        # Отправляем каждый продукт отдельным сообщением
        for i, product in enumerate(products):
            try:
                # 🔧 ИСПРАВЛЕНО: Используем сервис форматирования
                try:
                    formatted_sections = formatter_service.format_product_for_telegram(product, loc)
                    
                    # Объединяем все секции в единый текст (без навигации - она только в сообщении статуса)
                    product_text = (
                        formatted_sections['main_info'] +
                        formatted_sections['composition'] +
                        formatted_sections['pricing'] +
                        formatted_sections['details']
                    )
                except Exception as e:
                    logger.error(f"[CATALOG] Ошибка сервиса форматирования для продукта {getattr(product, 'id', 'unknown')}: {e}")
                    # Fallback форматирование
                    product_text = f"🏷️ <b>{getattr(product, 'title', 'Продукт')}</b>\n❌ Ошибка при форматировании"
                
                # Обрезаем текст если он слишком длинный для Telegram
                original_length = len(product_text)
                product_text = formatter_service._truncate_text(product_text)
                final_length = len(product_text)
                
                if original_length != final_length:
                    logger.info(f"[CATALOG] Текст продукта {getattr(product, 'id', 'unknown')} обрезан: {original_length} -> {final_length} символов")
                
                # Отправляем сообщение с изображением если есть
                if product.cover_image_url:
                    try:
                        # 🔧 ИСПРАВЛЕНО: Используем storage service для формирования URL
                        image_url = storage_service.get_public_url(product.cover_image_url)
                        logger.info(f"[CATALOG] Сформирован URL для изображения: {image_url}")
                        
                        # Создаем временный файл для изображения
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_url) as response:
                                if response.status == 200:
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                                        tmp_file.write(await response.read())
                                        image_path = tmp_file.name
                                    
                                    # 🔧 ИСПРАВЛЕНО: Добавляем клавиатуру с кнопками для продукта
                                    product_id = getattr(product, 'id', getattr(product, 'business_id', 'unknown'))
                                    keyboard = get_product_keyboard(product_id, loc)
                                    
                                    await callback.message.answer_photo(
                                        FSInputFile(image_path),
                                        caption=product_text,
                                        parse_mode="HTML",
                                        reply_markup=keyboard
                                    )
                                    # Удаляем временный файл
                                    os.unlink(image_path)
                                    logger.info(f"[CATALOG] Изображение успешно отправлено для продукта {getattr(product, 'id', 'unknown')}")
                                else:
                                    logger.error(f"[CATALOG] Ошибка загрузки изображения (HTTP {response.status}): {image_url}")
                                    # Fallback: отправляем только текст с клавиатурой
                                    product_id = getattr(product, 'id', getattr(product, 'business_id', 'unknown'))
                                    keyboard = get_product_keyboard(product_id, loc)
                                    await callback.message.answer(product_text, parse_mode="HTML", reply_markup=keyboard)
                    except Exception as e:
                        logger.error(f"[CATALOG] Ошибка при отправке изображения для продукта {getattr(product, 'id', 'unknown')}: {e}")
                        # Fallback: отправляем только текст с клавиатурой
                        product_id = getattr(product, 'id', getattr(product, 'business_id', 'unknown'))
                        keyboard = get_product_keyboard(product_id, loc)
                        await callback.message.answer(product_text, parse_mode="HTML", reply_markup=keyboard)
                else:
                    # 🔧 ИСПРАВЛЕНО: Добавляем клавиатуру с кнопками для продукта
                    product_id = getattr(product, 'id', getattr(product, 'business_id', 'unknown'))
                    keyboard = get_product_keyboard(product_id, loc)
                    await callback.message.answer(product_text, parse_mode="HTML", reply_markup=keyboard)
                
                # Обновляем прогресс
                await progress_message.edit_text(f"📦 Загружаем каталог: {i+1}/{len(products)} продуктов...")
                
                # Добавляем разделитель между продуктами (кроме последнего)
                if i < len(products) - 1:
                    await callback.message.answer("☀️" * 8)

            except Exception as e:
                logger.error(f"[CATALOG] Ошибка при отправке продукта {product.id}: {e}")
                continue
        
        # Удаляем сообщение о прогрессе и отправляем финальное сообщение
        await progress_message.delete()
        await callback.message.answer(f"✅ Каталог загружен! Всего продуктов: {len(products)}")
        
        logger.info(f"[CATALOG] Каталог успешно отправлен: {len(products)} продуктов")
        
    except Exception as e:
        logger.error(f"[CATALOG] Ошибка при получении каталога: {e}")
        await callback.message.answer(loc.t("catalog.error"))
    
    finally:
        await callback.answer()

@router.callback_query(F.data == "scroll:catalog")
async def scroll_to_catalog(callback: CallbackQuery):
    """
    Обработчик для скролла к каталогу вместо перезагрузки.
    Отправляет сообщение с хэштегами для быстрой навигации и поиска.
    """
    logger.info(f"[SCROLL_CATALOG] scroll_to_catalog вызван! callback.data={callback.data}, from_user={callback.from_user.id}")
    
    try:
        # Получаем язык пользователя
        user_id = callback.from_user.id
        lang = user_settings.get_language(user_id)
        loc = Localization(lang)
        
        # Создаем улучшенное сообщение с хэштегами для навигации
        scroll_message = (
            f"📚 <b>Каталог продуктов</b>\n\n"
            f"• #catalog - основной каталог\n"
            f"💡 <i>Нажмите на хэштег для быстрого перехода к нужному разделу</i>"
        )
        
        await callback.message.answer(
            scroll_message,
            parse_mode="HTML"
        )
        
        logger.info(f"[SCROLL_CATALOG] Улучшенное сообщение со скроллом к каталогу отправлено для пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"[SCROLL_CATALOG] Ошибка при скролле к каталогу: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Отправляем сообщение об ошибке пользователю
        try:
            await callback.message.answer("❌ Произошла ошибка при переходе к каталогу")
        except:
            pass
    
    finally:
        await callback.answer()



@router.callback_query(F.data.startswith("product:details:"))
async def show_product_details(callback: CallbackQuery):
    """
    Обработчик для показа детальной информации о продукте.
    Вызывается при нажатии кнопки "📖 Подробнее" в каталоге.
    """
    logger.info(f"[PRODUCT_DETAILS] show_product_details вызван! callback.data={callback.data}, from_user={callback.from_user.id}")
    
    try:
        # Извлекаем product_id из callback.data
        # Формат: "product:details:{product_id}"
        product_id = callback.data.split(":")[-1]
        logger.info(f"[PRODUCT_DETAILS] Извлечен product_id: {product_id}")
        
        if not product_id or product_id == "details":
            logger.error("[PRODUCT_DETAILS] Некорректный product_id")
            await callback.message.answer("❌ Ошибка: не удалось определить продукт")
            await callback.answer()
            return
        
        # Получаем язык пользователя
        user_id = callback.from_user.id
        lang = user_settings.get_language(user_id)
        loc = Localization(lang)
        
        logger.info(f"[PRODUCT_DETAILS] Запрос детальной информации для продукта {product_id}")
        
        # Отправляем сообщение о загрузке
        loading_message = await callback.message.answer(loc.t("catalog.loading") if hasattr(loc, 't') else "🔄 Загружаем информацию о продукте...")
        
        # Получаем продукт через сервис
        # Пока используем get_all_products и ищем по ID
        # TODO: Добавить метод get_product_by_id в ProductRegistryService
        products = await product_registry_service.get_all_products()
        product = None
        
        for p in products:
            if (getattr(p, 'id', None) == product_id or 
                getattr(p, 'business_id', None) == product_id):
                product = p
                break
        
        # Удаляем сообщение о загрузке
        await loading_message.delete()
        
        if not product:
            logger.error(f"[PRODUCT_DETAILS] Продукт с ID {product_id} не найден")
            await callback.message.answer("❌ Продукт не найден")
            await callback.answer()
            return
        
        logger.info(f"[PRODUCT_DETAILS] Продукт найден: {product.title}")
        
        # Форматируем основную информацию и детальное описание через сервис
        try:
            # Сообщение 1: Основная информация для caption (оптимизировано для 1024 символов)
            main_info_text = formatter_service.format_product_main_info_for_telegram(product, loc)
            
            # Сообщение 2: Детальное описание (без ограничений длины, без навигации)
            description_text = formatter_service.format_product_description_for_telegram(product, loc)
            
            logger.info(f"[PRODUCT_DETAILS] Основная информация: {len(main_info_text)} символов")
            logger.info(f"[PRODUCT_DETAILS] Детальное описание: {len(description_text)} символов")
            
        except Exception as e:
            logger.error(f"[PRODUCT_DETAILS] Ошибка сервиса форматирования для продукта {product_id}: {e}")
            # Fallback форматирование
            main_info_text = f"🏷️ <b>{getattr(product, 'title', 'Продукт')}</b>\n❌ Ошибка при загрузке основной информации"
            description_text = f"❌ Ошибка при загрузке детальной информации"
        
        # Создаем клавиатуру для детального просмотра с умной навигацией
        keyboard = get_product_details_keyboard_with_scroll(product_id, loc)
        
        # Отправляем детальную информацию
        if product.cover_image_url:
            try:
                # Получаем URL изображения через storage service
                image_url = storage_service.get_public_url(product.cover_image_url)
                logger.info(f"[PRODUCT_DETAILS] Сформирован URL для изображения: {image_url}")
                
                # Создаем временный файл для изображения
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as response:
                        if response.status == 200:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                                tmp_file.write(await response.read())
                                image_path = tmp_file.name
                            
                            # Сообщение 1: Изображение + основная информация + кнопки
                            await callback.message.answer_photo(
                                FSInputFile(image_path),
                                caption=main_info_text,
                                parse_mode="HTML",
                                reply_markup=keyboard
                            )
                            
                            # Сообщение 2: Детальное описание + кнопки
                            await callback.message.answer(
                                description_text,
                                parse_mode="HTML",
                                reply_markup=keyboard
                            )
                            
                            # Удаляем временный файл
                            os.unlink(image_path)
                            logger.info(f"[PRODUCT_DETAILS] Двухуровневое отображение отправлено: изображение + основная информация + детальное описание")
                        else:
                            logger.error(f"[PRODUCT_DETAILS] Ошибка загрузки изображения (HTTP {response.status}): {image_url}")
                            # Fallback: отправляем два текстовых сообщения с клавиатурой
                            await callback.message.answer(main_info_text, parse_mode="HTML", reply_markup=keyboard)
                            await callback.message.answer(description_text, parse_mode="HTML", reply_markup=keyboard)
            except Exception as e:
                logger.error(f"[PRODUCT_DETAILS] Ошибка при отправке изображения: {e}")
                # Fallback: отправляем два текстовых сообщения с клавиатурой
                await callback.message.answer(main_info_text, parse_mode="HTML", reply_markup=keyboard)
                await callback.message.answer(description_text, parse_mode="HTML", reply_markup=keyboard)
        else:
            # Отправляем два текстовых сообщения без изображения с клавиатурой
            await callback.message.answer(main_info_text, parse_mode="HTML", reply_markup=keyboard)
            await callback.message.answer(description_text, parse_mode="HTML", reply_markup=keyboard)
            logger.info(f"[PRODUCT_DETAILS] Двухуровневое отображение отправлено (без изображения)")
        
        logger.info(f"[PRODUCT_DETAILS] Детальная информация успешно отправлена для продукта {product_id}")
        
    except Exception as e:
        logger.error(f"[PRODUCT_DETAILS] Ошибка при показе детальной информации: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Отправляем сообщение об ошибке пользователю
        try:
            await callback.message.answer("❌ Произошла ошибка при загрузке информации о продукте")
        except:
            pass
    
    finally:
        await callback.answer() 