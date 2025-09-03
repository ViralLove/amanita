"""
Абстрактный интерфейс для работы с изображениями.
Определяет контракт для сервисов обработки изображений.
"""

from abc import ABC, abstractmethod
from typing import List, Any
from aiogram.types import InputMediaPhoto
from bot.services.common.localization import Localization


class IImageService(ABC):
    """
    Абстрактный интерфейс для сервиса работы с изображениями.
    
    Определяет основные методы для:
    - Загрузки изображений
    - Создания медиа-групп
    - Отправки продуктов с изображениями
    - Управления временными файлами
    """
    
    @abstractmethod
    async def download_image(self, url: str, product_id: str) -> str:
        """
        Загружает изображение по URL и сохраняет во временный файл.
        
        Args:
            url: URL изображения для загрузки
            product_id: ID продукта для именования файла
            
        Returns:
            str: Путь к сохраненному временному файлу
            
        Raises:
            Exception: При ошибках загрузки или сохранения
        """
        pass
    
    @abstractmethod
    async def create_media_group(
        self, 
        product: Any, 
        images: List[str], 
        loc: Localization
    ) -> List[InputMediaPhoto]:
        """
        Создает медиа-группу для отправки в Telegram.
        
        Args:
            product: Объект продукта
            images: Список путей к изображениям
            loc: Объект локализации
            
        Returns:
            List[InputMediaPhoto]: Список медиа-объектов для Telegram
            
        Raises:
            Exception: При ошибках создания медиа-группы
        """
        pass
    
    @abstractmethod
    async def send_product_with_images(
        self, 
        message, 
        product: Any, 
        images: List[str], 
        loc: Localization
    ) -> None:
        """
        Отправляет продукт с изображениями в Telegram.
        
        Args:
            message: Объект сообщения Telegram
            product: Объект продукта
            images: Список путей к изображениям
            loc: Объект локализации
            
        Raises:
            Exception: При ошибках отправки
        """
        pass
    
    @abstractmethod
    async def cleanup_temp_files(self, file_paths: List[str]) -> None:
        """
        Очищает временные файлы изображений.
        
        Args:
            file_paths: Список путей к файлам для удаления
            
        Raises:
            Exception: При ошибках удаления файлов
        """
        pass
    
    @abstractmethod
    async def validate_image_url(self, url: str) -> bool:
        """
        Проверяет доступность изображения по URL.
        
        Args:
            url: URL изображения для проверки
            
        Returns:
            bool: True если изображение доступно, False иначе
        """
        pass
    
    @abstractmethod
    async def get_image_info(self, file_path: str) -> dict:
        """
        Получает информацию об изображении.
        
        Args:
            file_path: Путь к файлу изображения
            
        Returns:
            dict: Информация об изображении (размер, формат, etc.)
            
        Raises:
            Exception: При ошибках получения информации
        """
        pass
