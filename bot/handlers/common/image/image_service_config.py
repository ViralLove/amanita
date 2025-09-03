"""
Конфигурация для сервиса работы с изображениями.
Настройки для загрузки, обработки и отправки изображений.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import logging
import os


@dataclass
class ImageServiceConfig:
    """
    Конфигурация для ImageService.
    
    Содержит настройки для:
    - Загрузки изображений
    - Обработки файлов
    - Создания медиа-групп
    - Логирования
    """
    
    # Настройки загрузки
    download_timeout: int = 30
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Настройки файлов
    temp_dir: str = field(default_factory=lambda: os.path.join(os.getcwd(), "temp_images"))
    allowed_extensions: List[str] = field(default_factory=lambda: [".jpg", ".jpeg", ".png", ".webp"])
    max_images_per_product: int = 10
    
    # Настройки Telegram
    max_media_group_size: int = 10
    caption_max_length: int = 1024
    enable_html_caption: bool = True
    
    # Настройки обработки
    resize_large_images: bool = True
    max_image_dimension: int = 1920
    compression_quality: int = 85
    
    # Настройки кэширования
    enable_cache: bool = True
    cache_duration: int = 3600  # 1 час
    cache_dir: str = field(default_factory=lambda: os.path.join(os.getcwd(), "image_cache"))
    
    # Настройки логирования
    logging_level: int = logging.INFO
    enable_debug_logging: bool = False
    log_download_progress: bool = True
    
    # Настройки безопасности
    validate_urls: bool = True
    allowed_domains: List[str] = field(default_factory=list)
    block_suspicious_urls: bool = True
    
    # Настройки fallback
    enable_fallback_images: bool = True
    fallback_image_url: Optional[str] = None
    show_error_placeholders: bool = True
    
    def __post_init__(self):
        """Инициализация после создания объекта."""
        # Создаем директории если они не существуют
        os.makedirs(self.temp_dir, exist_ok=True)
        if self.enable_cache:
            os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_temp_file_path(self, product_id: str, index: int = 0) -> str:
        """
        Генерирует путь для временного файла.
        
        Args:
            product_id: ID продукта
            index: Индекс изображения
            
        Returns:
            str: Путь к временному файлу
        """
        filename = f"product_{product_id}_{index}.jpg"
        return os.path.join(self.temp_dir, filename)
    
    def get_cache_file_path(self, url: str) -> str:
        """
        Генерирует путь для кэшированного файла.
        
        Args:
            url: URL изображения
            
        Returns:
            str: Путь к кэшированному файлу
        """
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.jpg")
    
    def is_valid_extension(self, filename: str) -> bool:
        """
        Проверяет допустимость расширения файла.
        
        Args:
            filename: Имя файла
            
        Returns:
            bool: True если расширение допустимо
        """
        _, ext = os.path.splitext(filename.lower())
        return ext in self.allowed_extensions
    
    def is_valid_domain(self, url: str) -> bool:
        """
        Проверяет допустимость домена URL.
        
        Args:
            url: URL для проверки
            
        Returns:
            bool: True если домен допустим
        """
        if not self.allowed_domains:
            return True
        
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc
            return any(allowed in domain for allowed in self.allowed_domains)
        except Exception:
            return False
    
    def should_resize_image(self, width: int, height: int) -> bool:
        """
        Определяет нужно ли изменять размер изображения.
        
        Args:
            width: Ширина изображения
            height: Высота изображения
            
        Returns:
            bool: True если нужно изменить размер
        """
        return self.resize_large_images and (width > self.max_image_dimension or height > self.max_image_dimension)
    
    def get_resized_dimensions(self, width: int, height: int) -> tuple:
        """
        Вычисляет новые размеры для изображения.
        
        Args:
            width: Текущая ширина
            height: Текущая высота
            
        Returns:
            tuple: (новая_ширина, новая_высота)
        """
        if width > height:
            new_width = self.max_image_dimension
            new_height = int(height * (self.max_image_dimension / width))
        else:
            new_height = self.max_image_dimension
            new_width = int(width * (self.max_image_dimension / height))
        
        return (new_width, new_height)
    
    def validate_config(self) -> List[str]:
        """
        Валидирует конфигурацию.
        
        Returns:
            List[str]: Список ошибок валидации
        """
        errors = []
        
        if self.download_timeout <= 0:
            errors.append("download_timeout должен быть положительным")
        
        if self.max_file_size <= 0:
            errors.append("max_file_size должен быть положительным")
        
        if self.retry_attempts < 0:
            errors.append("retry_attempts не может быть отрицательным")
        
        if self.max_images_per_product <= 0:
            errors.append("max_images_per_product должен быть положительным")
        
        if self.max_media_group_size <= 0:
            errors.append("max_media_group_size должен быть положительным")
        
        if self.max_image_dimension <= 0:
            errors.append("max_image_dimension должен быть положительным")
        
        if not (0 <= self.compression_quality <= 100):
            errors.append("compression_quality должен быть от 0 до 100")
        
        return errors
