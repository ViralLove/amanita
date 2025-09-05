"""
Сервис для работы с изображениями продуктов.
Содержит логику загрузки, обработки и отправки изображений.
"""

import logging
import tempfile
import aiohttp
import os
from typing import Any, Optional
from aiogram.types import CallbackQuery, FSInputFile
from bot.services.common.localization import Localization
from bot.services.core.ipfs_factory import IPFSFactory
from bot.keyboards.common import get_product_keyboard, get_product_details_keyboard_with_scroll

logger = logging.getLogger(__name__)


class ImageService:
    """Сервис для работы с изображениями продуктов"""
    
    def __init__(self, storage_service=None):
        """
        Инициализация сервиса изображений
        
        Args:
            storage_service: Сервис хранилища для получения URL изображений
        """
        self.storage_service = storage_service or IPFSFactory().get_storage()
        self.logger = logging.getLogger(__name__)
    
    async def download_image(self, image_url: str) -> Optional[str]:
        """
        Загружает изображение по URL и сохраняет во временный файл
        
        Args:
            image_url: URL изображения для загрузки
            
        Returns:
            Optional[str]: Путь к временному файлу или None в случае ошибки
        """
        try:
            self.logger.info(f"[ImageService] Загрузка изображения: {image_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                            tmp_file.write(await response.read())
                            image_path = tmp_file.name
                        
                        self.logger.info(f"[ImageService] Изображение загружено: {image_path}")
                        return image_path
                    else:
                        self.logger.error(f"[ImageService] Ошибка загрузки изображения (HTTP {response.status}): {image_url}")
                        return None
                        
        except Exception as e:
            self.logger.error(f"[ImageService] Ошибка при загрузке изображения {image_url}: {e}")
            return None
    
    def _validate_image_url(self, image_url: str) -> bool:
        """
        Валидирует URL изображения
        
        Args:
            image_url: URL изображения для валидации
            
        Returns:
            bool: True если URL валиден
        """
        try:
            if not image_url or not isinstance(image_url, str):
                return False
            if not image_url.startswith(('http://', 'https://')):
                return False
            return True
        except Exception as e:
            self.logger.error(f"[ImageService] Ошибка валидации URL изображения: {e}")
            return False
    
    async def cleanup_temp_files(self, *file_paths: str) -> None:
        """
        Удаляет временные файлы
        
        Args:
            *file_paths: Пути к файлам для удаления
        """
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    self.logger.debug(f"[ImageService] Временный файл удален: {file_path}")
                except Exception as e:
                    self.logger.error(f"[ImageService] Ошибка при удалении временного файла {file_path}: {e}")
    
    async def send_image_with_caption(self, callback: CallbackQuery, image_path: str, caption: str, 
                                    reply_markup=None, parse_mode: str = "HTML") -> None:
        """
        Отправляет изображение с подписью
        
        Args:
            callback: Callback запрос от пользователя
            image_path: Путь к изображению
            caption: Подпись к изображению
            reply_markup: Клавиатура для сообщения
            parse_mode: Режим парсинга (HTML/Markdown)
        """
        try:
            await callback.message.answer_photo(
                FSInputFile(image_path),
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            self.logger.info(f"[ImageService] Изображение с подписью отправлено")
            
        except Exception as e:
            self.logger.error(f"[ImageService] Ошибка при отправке изображения с подписью: {e}")
            raise
    
    async def send_product_with_image(self, callback: CallbackQuery, product: Any, 
                                    product_text: str, loc: Localization) -> None:
        """
        Отправляет продукт с изображением или без него
        
        Args:
            callback: Callback запрос от пользователя
            product: Продукт для отправки
            product_text: Отформатированный текст продукта
            loc: Объект локализации
        """
        try:
            # Создаем клавиатуру для продукта
            product_id = getattr(product, 'id', getattr(product, 'business_id', 'unknown'))
            keyboard = get_product_keyboard(product_id, loc)
            
            if product.cover_image_url:
                try:
                    # Получаем URL изображения через storage service
                    image_url = self.storage_service.get_public_url(product.cover_image_url)
                    self.logger.info(f"[ImageService] Сформирован URL для изображения: {image_url}")
                    
                    # Загружаем изображение
                    image_path = await self.download_image(image_url)
                    
                    if image_path:
                        # Отправляем изображение с текстом
                        await self.send_image_with_caption(
                            callback=callback,
                            image_path=image_path,
                            caption=product_text,
                            reply_markup=keyboard
                        )
                        
                        # Удаляем временный файл
                        await self.cleanup_temp_files(image_path)
                        self.logger.info(f"[ImageService] Продукт с изображением отправлен: {getattr(product, 'id', 'unknown')}")
                    else:
                        # Fallback: отправляем только текст
                        await self._send_text_only(callback, product_text, keyboard)
                        
                except Exception as e:
                    self.logger.error(f"[ImageService] Ошибка при отправке изображения для продукта {getattr(product, 'id', 'unknown')}: {e}")
                    # Fallback: отправляем только текст
                    await self._send_text_only(callback, product_text, keyboard)
            else:
                # Отправляем только текст без изображения
                await self._send_text_only(callback, product_text, keyboard)
                
        except Exception as e:
            self.logger.error(f"[ImageService] Ошибка при отправке продукта: {e}")
            raise
    
    async def send_product_details_with_image(self, callback: CallbackQuery, product: Any,
                                            main_info_text: str, description_text: str, 
                                            loc: Localization) -> None:
        """
        Отправляет детальную информацию о продукте с изображением или без него
        
        Args:
            callback: Callback запрос от пользователя
            product: Продукт для отправки деталей
            main_info_text: Основная информация для первого сообщения
            description_text: Детальное описание для второго сообщения
            loc: Объект локализации
        """
        try:
            # Создаем клавиатуру для детального просмотра
            product_id = getattr(product, 'id', getattr(product, 'business_id', 'unknown'))
            keyboard = get_product_details_keyboard_with_scroll(product_id, loc)
            
            if product.cover_image_url:
                try:
                    # Получаем URL изображения через storage service
                    image_url = self.storage_service.get_public_url(product.cover_image_url)
                    self.logger.info(f"[ImageService] Сформирован URL для изображения: {image_url}")
                    
                    # Загружаем изображение
                    image_path = await self.download_image(image_url)
                    
                    if image_path:
                        # Сообщение 1: Изображение + основная информация + кнопки
                        await self.send_image_with_caption(
                            callback=callback,
                            image_path=image_path,
                            caption=main_info_text,
                            reply_markup=keyboard
                        )
                        
                        # Сообщение 2: Детальное описание + кнопки
                        await callback.message.answer(
                            description_text,
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                        
                        # Удаляем временный файл
                        await self.cleanup_temp_files(image_path)
                        self.logger.info(f"[ImageService] Двухуровневое отображение отправлено: изображение + основная информация + детальное описание")
                    else:
                        # Fallback: отправляем два текстовых сообщения
                        await self._send_text_details(callback, main_info_text, description_text, keyboard)
                        
                except Exception as e:
                    self.logger.error(f"[ImageService] Ошибка при отправке изображения: {e}")
                    # Fallback: отправляем два текстовых сообщения
                    await self._send_text_details(callback, main_info_text, description_text, keyboard)
            else:
                # Отправляем два текстовых сообщения без изображения
                await self._send_text_details(callback, main_info_text, description_text, keyboard)
                self.logger.info(f"[ImageService] Двухуровневое отображение отправлено (без изображения)")
                
        except Exception as e:
            self.logger.error(f"[ImageService] Ошибка при отправке детальной информации: {e}")
            raise
    
    async def _send_text_only(self, callback: CallbackQuery, text: str, keyboard) -> None:
        """Отправляет только текст без изображения"""
        await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    
    async def _send_text_details(self, callback: CallbackQuery, main_text: str, 
                               description_text: str, keyboard) -> None:
        """Отправляет два текстовых сообщения с деталями"""
        await callback.message.answer(main_text, parse_mode="HTML", reply_markup=keyboard)
        await callback.message.answer(description_text, parse_mode="HTML", reply_markup=keyboard)
