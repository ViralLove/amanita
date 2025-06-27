from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from bot.fsm.product_creation_states import ProductCreationStates
from bot.services.common.localization import Localization
from bot.model.user_settings import UserSettings
from bot.services.product.registry import ProductRegistryService
from bot.services.core.blockchain import BlockchainService
from bot.services.core.storage.ar_weave import ArWeaveUploader
import logging
import os

router = Router()
logger = logging.getLogger(__name__)
user_settings = UserSettings()

# Инициализируем зависимости
blockchain_service = BlockchainService()
arweave_uploader = ArWeaveUploader()
product_registry_service = ProductRegistryService(blockchain_service, arweave_uploader)

@router.message(F.text == "/create_product")
async def start_product_creation(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    # Сбрасываем все предыдущие состояния
    await state.clear()
    await state.set_state(ProductCreationStates.TitleInput)

    # Сообщение пользователю
    await message.answer(
        loc.t("e-catalog.product_creation.start") + "\n\n" + loc.t("e-catalog.product_creation.ask_title")
    )


@router.message(ProductCreationStates.TitleInput)
async def collect_title(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    # Сохраняем заголовок
    await state.update_data(title=message.text.strip())

    # Переводим в следующее состояние
    await state.set_state(ProductCreationStates.DescriptionInput)

    # Отправляем пользователю запрос на описание
    await message.answer(loc.t("e-catalog.product_creation.ask_description"))


@router.message(ProductCreationStates.DescriptionInput)
async def collect_description(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    # Сохраняем описание
    await state.update_data(description=message.text.strip())

    # Переводим в следующее состояние
    await state.set_state(ProductCreationStates.PriceInput)

    # Отправляем запрос на цену
    await message.answer(loc.t("e-catalog.product_creation.ask_price"))


@router.message(ProductCreationStates.PriceInput)
async def collect_price(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    price_text = message.text.strip()
    if not price_text.isdigit():
        await message.answer(loc.t("e-catalog.product_creation.invalid_price"))
        return

    # Сохраняем цену
    await state.update_data(price=int(price_text))

    # Переводим в следующее состояние
    await state.set_state(ProductCreationStates.CoverImageInput)

    # Запрашиваем обложку
    await message.answer(loc.t("e-catalog.product_creation.ask_cover_image"))


@router.message(ProductCreationStates.CoverImageInput)
async def upload_cover_image(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    if not message.photo:
        await message.answer("⚠️ Пожалуйста, отправьте фото в качестве обложки.")
        return

    # Получаем фото (берём лучшее качество — последнюю в списке)
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_path = file.file_path

    # Сохраняем фото локально
    file_name = f"cover_{user_id}.jpg"
    await message.bot.download_file(file_path, file_name)

    # Сохраняем путь к файлу
    await state.update_data(cover_image_path=file_name)

    # Переводим в следующее состояние
    await state.set_state(ProductCreationStates.GalleryInput)

    # Запрашиваем галерею
    await message.answer(loc.t("e-catalog.product_creation.ask_gallery"))


@router.message(ProductCreationStates.GalleryInput)
async def upload_gallery_images(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    # Проверяем, что пришло хотя бы одно фото
    if not message.photo:
        await message.answer(loc.t("e-catalog.product_creation.invalid_gallery"))
        return

    # Обрабатываем все фото
    gallery_paths = []
    for photo in message.photo:
        file = await message.bot.get_file(photo.file_id)
        file_path = file.file_path
        file_name = f"gallery_{user_id}_{photo.file_id}.jpg"
        await message.bot.download_file(file_path, file_name)
        gallery_paths.append(file_name)

    # Сохраняем пути к файлам
    await state.update_data(gallery_paths=gallery_paths)

    # Переводим в следующее состояние
    await state.set_state(ProductCreationStates.VideoInput)

    # Запрашиваем видео
    await message.answer(loc.t("e-catalog.product_creation.ask_video"))

@router.message(ProductCreationStates.VideoInput)
async def upload_video(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    video_path = None
    # Проверяем: "Пропустить" или видео
    if message.text and message.text.strip().lower() == "пропустить":
        video_path = None
    elif message.video:
        file = await message.bot.get_file(message.video.file_id)
        file_path = file.file_path
        video_path = f"video_{user_id}.mp4"
        await message.bot.download_file(file_path, video_path)
    else:
        await message.answer(loc.t("e-catalog.product_creation.invalid_video"))
        return

    # Сохраняем путь к видео
    await state.update_data(video_path=video_path)

    # Переходим к следующему шагу
    await state.set_state(ProductCreationStates.CategoriesInput)
    await message.answer(loc.t("e-catalog.product_creation.ask_categories"))

@router.message(ProductCreationStates.CategoriesInput)
async def collect_categories(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    text = message.text.strip()
    if not text:
        await message.answer(loc.t("e-catalog.product_creation.invalid_categories"))
        return

    categories = [cat.strip() for cat in text.split(",") if cat.strip()]
    if not categories:
        await message.answer(loc.t("e-catalog.product_creation.invalid_categories"))
        return

    # Сохраняем категории
    await state.update_data(categories=categories)

    # Переводим в следующее состояние
    await state.set_state(ProductCreationStates.AttributesInput)
    await message.answer(loc.t("e-catalog.product_creation.ask_attributes"))

@router.message(ProductCreationStates.AttributesInput)
async def collect_attributes(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    text = message.text.strip()
    attributes = {}
    
    if text.lower() != "пропустить":
        # Парсим атрибуты в формате "ключ: значение, ключ2: значение2"
        pairs = [pair.strip() for pair in text.split(",")]
        for pair in pairs:
            if ":" not in pair:
                await message.answer(loc.t("e-catalog.product_creation.invalid_attributes"))
                return

            key, value = pair.split(":", 1)
            attributes[key.strip()] = value.strip()

    # Сохраняем атрибуты
    await state.update_data(attributes=attributes)

    # Переводим в состояние подтверждения
    await state.set_state(ProductCreationStates.Confirmation)
    
    # Показываем собранные данные
    data = await state.get_data()
    preview = (
        f"📝 Предварительный просмотр:\n\n"
        f"Название: {data['title']}\n"
        f"Описание: {data['description']}\n"
        f"Цена: {data['price']} USDT\n"
        f"Категории: {', '.join(data['categories'])}\n"
        f"Атрибуты: {attributes}\n\n"
        f"Для подтверждения напишите 'да'"
    )
    await message.answer(preview)

@router.message(ProductCreationStates.Confirmation)
async def finalize_product_creation(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)

    if message.text.strip().lower() != "да":
        await message.answer(loc.t("e-catalog.product_creation.cancelled"))
        await state.clear()
        return

    try:
        # Получаем все собранные данные
        data = await state.get_data()
        
        # Создаем продукт через сервис
        tx_hash = await product_registry_service.create_product(
            title=data['title'],
            description=data['description'],
            price=data['price'],
            cover_image_path=data['cover_image_path'],
            gallery_paths=data.get('gallery_paths', []),
            video_path=data.get('video_path'),
            categories=data['categories'],
            attributes=data.get('attributes', {})
        )

        if tx_hash:
            await message.answer(loc.t("e-catalog.product_creation.success"))
        else:
            await message.answer(loc.t("e-catalog.product_creation.error"))

    except Exception as e:
        logger.error(f"Error creating product: {e}")
        await message.answer(loc.t("e-catalog.product_creation.error"))
        
    finally:
        # Очищаем временные файлы
        try:
            if 'cover_image_path' in data:
                os.unlink(data['cover_image_path'])
            if 'gallery_paths' in data:
                for path in data['gallery_paths']:
                    os.unlink(path)
            if 'video_path' in data and data['video_path']:
                os.unlink(data['video_path'])
        except Exception as e:
            logger.error(f"Error cleaning up files: {e}")
            
        # Очищаем состояние
        await state.clear()

