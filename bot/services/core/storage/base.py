from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Union
import logging

logger = logging.getLogger(__name__)

class BaseStorageProvider(ABC):
    """
    Базовый класс для провайдеров хранилищ.
    Определяет общий интерфейс для всех провайдеров.
    """
    
    @abstractmethod
    def upload_file(self, file_path_or_data: Union[str, dict], file_name: Optional[str] = None) -> str:
        """
        Загружает файл в хранилище.
        
        Args:
            file_path_or_data: Путь к файлу или данные для загрузки
            file_name: Имя файла (опционально)
            
        Returns:
            str: Идентификатор загруженного файла (CID или transaction ID)
        """
        pass
    
    @abstractmethod
    def download_json(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Загружает JSON данные из хранилища.
        
        Args:
            identifier: Идентификатор файла (CID или transaction ID)
            
        Returns:
            Optional[Dict[str, Any]]: Загруженные данные или None при ошибке
        """
        pass
    
    @abstractmethod
    def get_public_url(self, identifier: str) -> str:
        """
        Формирует публичный URL для доступа к файлу.
        
        Args:
            identifier: Идентификатор файла (CID или transaction ID)
            
        Returns:
            str: Полный публичный URL для доступа к файлу
        """
        pass
    
    def is_valid_identifier(self, identifier: str) -> bool:
        """
        Проверяет валидность идентификатора для текущего типа хранилища.
        
        Args:
            identifier: Идентификатор файла
            
        Returns:
            bool: True если идентификатор валиден
        """
        if not identifier:
            return False
        
        # Базовая проверка - должен быть непустой строкой
        return isinstance(identifier, str) and len(identifier) > 0
