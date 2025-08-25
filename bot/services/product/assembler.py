"""
Сервис для централизованной сборки продуктов из данных блокчейна и IPFS метаданных.

Этот сервис устраняет дублирование логики сборки продуктов между
ProductRegistryService и ProductMetadataService, предоставляя единый
интерфейс для создания объектов Product.
"""

from typing import Dict, Any, Optional, Tuple
import logging
import json
from bot.model.product import Product
from bot.validation import ValidationFactory, ValidationResult


class ProductAssembler:
    """
    Сервис для сборки продуктов из данных блокчейна и IPFS метаданных.
    
    Ответственности:
    - Оркестрация процесса сборки продукта
    - Валидация метаданных через ValidationFactory
    - Создание объектов Product с правильными данными
    - Обработка ошибок и логирование процесса
    """
    
    def __init__(self, validation_service=None, cache_service=None):
        """
        Инициализирует ProductAssembler.
        
        Args:
            validation_service: Сервис валидации (опционально, для будущего расширения)
            cache_service: Сервис кэширования (опционально, для будущего расширения)
        """
        self.logger = logging.getLogger(__name__)
        self.validation_service = validation_service
        self.cache_service = cache_service
        
        self.logger.info("�� ProductAssembler инициализирован")
    
    def assemble_product(self, blockchain_data: Tuple, metadata: Dict[str, Any]) -> Optional[Product]:
        """
        Собирает продукт из данных блокчейна и IPFS метаданных.
        
        Args:
            blockchain_data: Кортеж с данными блокчейна (id, seller, ipfsCID, active)
            metadata: Словарь с метаданными продукта из IPFS
            
        Returns:
            Product: Собранный объект продукта или None при ошибке
            
        Raises:
            ValueError: При некорректных данных блокчейна
        """
        try:
            self.logger.info(f"🔍 Начинаем сборку продукта: blockchain_data={blockchain_data}")
            
            # Шаг 1: Валидация и извлечение данных блокчейна
            blockchain_info = self._extract_blockchain_data(blockchain_data)
            if not blockchain_info:
                self.logger.error("❌ Не удалось извлечь данные блокчейна")
                return None
            
            product_id, ipfs_cid, is_active = blockchain_info
            self.logger.info(f"✅ Данные блокчейна извлечены: blockchain_id={product_id}, CID={ipfs_cid}, Active={is_active}")
            
            # Шаг 2: Валидация метаданных через ValidationFactory
            validation_result = self._validate_metadata(metadata)
            if not validation_result:
                self.logger.error("❌ Валидация метаданных не прошла")
                return None
            
            self.logger.info("✅ Метаданные успешно валидированы")
            
            # Шаг 3: Создание объекта Product из метаданных
            product = self._create_product_from_metadata(metadata)
            if not product:
                self.logger.error("❌ Не удалось создать продукт из метаданных")
                return None
            
            self.logger.info("✅ Объект Product создан из метаданных")
            
            # Шаг 4: Установка блокчейн-данных
            self._set_blockchain_data(product, product_id, ipfs_cid, is_active)
            
            self.logger.info(f"🎉 Продукт {product.business_id} (blockchain_id={product_id}) успешно собран")
            return product
            
        except Exception as e:
            self.logger.error(f"�� Критическая ошибка при сборке продукта: {e}")
            return None
    
    def _extract_blockchain_data(self, blockchain_data: Tuple) -> Optional[Tuple[int, str, bool]]:
        """
        Извлекает и валидирует данные из кортежа блокчейна.
        
        Args:
            blockchain_data: Кортеж (id, seller, ipfsCID, active)
            
        Returns:
            Tuple[int, str, bool]: (product_id, ipfs_cid, is_active) или None при ошибке
        """
        try:
            if not hasattr(blockchain_data, '__getitem__') or len(blockchain_data) < 4:
                self.logger.error(f"Некорректная структура blockchain_data: {blockchain_data}")
                return None
            
            product_id = blockchain_data[0]  # blockchain_id продукта
            seller = blockchain_data[1]      # Адрес продавца
            ipfs_cid = blockchain_data[2]    # IPFS CID
            is_active = bool(blockchain_data[3])  # Статус активности
            
            # Валидация извлеченных данных
            if not isinstance(product_id, (int, str)) or not product_id:
                self.logger.error(f"Некорректный blockchain_id: {product_id}")
                return None
            
            if not ipfs_cid or not isinstance(ipfs_cid, str):
                self.logger.error(f"Некорректный ipfs_cid: {ipfs_cid}")
                return None
            
            return product_id, ipfs_cid, is_active
            
        except Exception as e:
            self.logger.error(f"Ошибка извлечения данных блокчейна: {e}")
            return None
    
    def _validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """
        Валидирует метаданные продукта через ValidationFactory.
        
        Args:
            metadata: Словарь с метаданными
            
        Returns:
            bool: True если валидация прошла успешно
        """
        try:
            if not isinstance(metadata, dict):
                self.logger.error(f"Метаданные должны быть словарем, получен: {type(metadata)}")
                return False
            
            # 🔍 ДЕТАЛЬНЫЙ ВЫВОД JSON МЕТАДАННЫХ
            self.logger.info(f"📋 ПОЛНЫЙ JSON ПРОДУКТА:")
            self.logger.info(f"{json.dumps(metadata, ensure_ascii=False, indent=2)}")
            
            # Используем единую систему валидации
            validator = ValidationFactory.get_product_validator()
            validation_result = validator.validate(metadata)
            
            if not validation_result.is_valid:
                self.logger.error(f"Валидация метаданных не прошла: {validation_result.error_message}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка валидации метаданных: {e}")
            return False
    
    def _create_product_from_metadata(self, metadata: Dict[str, Any]) -> Optional[Product]:
        """
        Создает объект Product из валидированных метаданных.
        
        Args:
            metadata: Валидированные метаданные продукта
            
        Returns:
            Product: Созданный объект продукта или None при ошибке
        """
        try:
            self.logger.info(f"🔍 Начинаем создание Product из метаданных")
            self.logger.info(f"📋 Структура метаданных: {list(metadata.keys())}")
            
            # Логируем business_id и organic_components детально
            business_id = metadata.get('business_id', 'N/A')
            self.logger.info(f"🏷️ Business ID: {business_id}")
            
            if 'organic_components' in metadata:
                self.logger.info(f"🔬 Найдены organic_components: {len(metadata['organic_components'])} компонентов")
                for i, comp in enumerate(metadata['organic_components']):
                    self.logger.info(f"  Компонент {i+1}: biounit_id='{comp.get('biounit_id', 'N/A')}', description_cid='{comp.get('description_cid', 'N/A')}', proportion='{comp.get('proportion', 'N/A')}'")
            else:
                self.logger.warning("⚠️ organic_components не найдены в метаданных")
            
            # 🔧 УНИФИКАЦИЯ: Используем from_dict вместо from_json для единообразного интерфейса
            self.logger.info("🏗️ Вызываем Product.from_dict()...")
            product = Product.from_dict(metadata)
            self.logger.info(f"✅ Продукт создан с business_id: {product.business_id}, заголовком: {product.title}")
            return product
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания продукта из метаданных: {e}")
            self.logger.error(f"📋 Тип ошибки: {type(e).__name__}")
            import traceback
            self.logger.error(f"🔍 Stack trace: {traceback.format_exc()}")
            return None
    
    def _set_blockchain_data(self, product: Product, product_id: int, ipfs_cid: str, is_active: bool) -> None:
        """
        Устанавливает блокчейн-данные в объект продукта.
        
        Args:
            product: Объект продукта для обновления
            product_id: ID продукта из блокчейна (blockchain_id)
            ipfs_cid: IPFS CID из блокчейна
            is_active: Статус активности из блокчейна
        """
        try:
            # Устанавливаем блокчейн-данные в правильные поля
            product.blockchain_id = product_id  # blockchain_id из блокчейна
            product.cid = ipfs_cid              # IPFS CID из блокчейна
            product.status = 1 if is_active else 0  # Статус активности
            
            self.logger.info(f"✅ Блокчейн-данные установлены: blockchain_id={product_id}, CID={ipfs_cid}, Status={product.status}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка установки блокчейн-данных: {e}")
            raise