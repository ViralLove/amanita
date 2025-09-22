"""
Сервис для централизованной сборки продуктов из данных блокчейна и IPFS метаданных.

Этот сервис устраняет дублирование логики сборки продуктов между
ProductRegistryService и ProductMetadataService, предоставляя единый
интерфейс для создания объектов Product.
"""

from typing import Dict, Any, Optional, Tuple
import logging
import json
from model.product import Product
from validation import ValidationFactory, ValidationResult
from model.component_description import ComponentDescription


class ProductAssembler:
    """
    Сервис для сборки продуктов из данных блокчейна и IPFS метаданных.
    
    Ответственности:
    - Оркестрация процесса сборки продукта
    - Валидация метаданных через ValidationFactory
    - Создание объектов Product с правильными данными
    - Обработка ошибок и логирование процесса
    """
    
    def __init__(self, validation_service=None, cache_service=None, storage_service=None):
        """
        Инициализирует ProductAssembler.
        
        Args:
            validation_service: Сервис валидации (опционально, для будущего расширения)
            cache_service: Сервис кэширования (опционально, для будущего расширения)
            storage_service: Сервис хранилища для загрузки описаний из IPFS
        """
        self.logger = logging.getLogger(__name__)
        self.validation_service = validation_service
        self.cache_service = cache_service
        self.storage_service = storage_service
        
        # 🔧 ЛОГИРОВАНИЕ STORAGE_SERVICE: Проверяем корректность передачи
        if self.storage_service:
            self.logger.info(f"🔧 ProductAssembler: storage_service инициализирован: {type(self.storage_service).__name__}")
            self.logger.info(f"🔧 ProductAssembler: storage_service доступен: {self.storage_service is not None}")
        else:
            self.logger.warning("⚠️ ProductAssembler: storage_service НЕ передан - описания не будут загружаться")
        
        self.logger.info("🔧 ProductAssembler инициализирован")
    
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
            
            # Шаг 2: Валидация базовых метаданных через ValidationFactory
            validation_result = self._validate_metadata(metadata)
            if not validation_result:
                self.logger.error("❌ Валидация базовых метаданных не прошла")
                return None
            
            self.logger.info("✅ Базовые метаданные успешно валидированы")
            
            # Шаг 3: Создание объекта Product из метаданных (с обогащением)
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
            
            # 🔧 ИЗМЕНЕННАЯ ЛОГИКА: Обогащаем метаданные ПЕРЕД созданием Product
            if self.storage_service:
                self.logger.info("🔧 Обогащаем метаданные описаниями перед созданием Product...")
                enriched_metadata = self._enrich_metadata_with_descriptions(metadata)
                
                # Валидация данных перед созданием Product
                self.logger.info("🔍 Валидируем обогащенные метаданные...")
                self._validate_product_metadata(enriched_metadata)
                
                product = Product.from_dict(enriched_metadata)
            else:
                self.logger.info("⚠️ storage_service недоступен, создаем Product без обогащения")
                
                # Валидация данных перед созданием Product
                self.logger.info("🔍 Валидируем метаданные...")
                self._validate_product_metadata(metadata)
                
                product = Product.from_dict(metadata)
            
            self.logger.info(f"✅ Продукт создан с business_id: {product.business_id}, заголовком: {product.title}")
            return product
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания продукта из метаданных: {e}")
            self.logger.error(f"📋 Тип ошибки: {type(e).__name__}")
            import traceback
            self.logger.error(f"🔍 Stack trace: {traceback.format_exc()}")
            return None
    
    def _validate_product_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Валидирует метаданные продукта перед созданием Product объекта.
        
        Args:
            metadata: Метаданные продукта для валидации
            
        Raises:
            ValueError: Если валидация не прошла
        """
        self.logger.info("🔍 Начинаем валидацию метаданных продукта...")
        
        # Проверяем обязательные поля
        required_fields = ['business_id', 'title', 'organic_components', 'categories', 'forms', 'species']
        for field in required_fields:
            if field not in metadata:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
            if not metadata[field]:
                raise ValueError(f"Поле {field} не может быть пустым")
        
        # Валидация organic_components
        if not isinstance(metadata['organic_components'], list):
            raise ValueError("organic_components должен быть списком")
        
        if len(metadata['organic_components']) == 0:
            raise ValueError("organic_components не может быть пустым")
        
        # Валидация каждого компонента
        for i, component in enumerate(metadata['organic_components']):
            if not isinstance(component, dict):
                raise ValueError(f"Компонент {i} должен быть словарем")
            
            component_required_fields = ['biounit_id', 'description_cid', 'proportion']
            for field in component_required_fields:
                if field not in component:
                    raise ValueError(f"Отсутствует поле {field} в компоненте {i}")
                if not component[field] or not str(component[field]).strip():
                    raise ValueError(f"Поле {field} в компоненте {i} не может быть пустым")
        
        # Валидация cover_image_url (разрешаем пустые значения)
        if 'cover_image_url' in metadata and metadata['cover_image_url']:
            cover_image_url = metadata['cover_image_url'].strip()
            if cover_image_url and not cover_image_url.startswith('Qm'):
                raise ValueError(f"cover_image_url должен быть валидным CID или пустым: {cover_image_url}")
        
        self.logger.info("✅ Валидация метаданных продукта прошла успешно")
    
    def _enrich_metadata_with_descriptions(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обогащает метаданные продукта данными из description_cid.
        
        Args:
            metadata: Базовые метаданные продукта
            
        Returns:
            Dict[str, Any]: Обогащенные метаданные с описаниями
        """
        try:
            if not self.storage_service:
                self.logger.warning("⚠️ storage_service не доступен, пропускаем загрузку описаний")
                return metadata
                
            enriched_metadata = metadata.copy()
            
            # Проверяем наличие organic_components
            if 'organic_components' not in metadata:
                self.logger.warning("⚠️ organic_components отсутствуют в метаданных")
                return enriched_metadata
            
            # Загружаем описания для каждого компонента
            for component in enriched_metadata['organic_components']:
                if 'description_cid' in component and component['description_cid']:
                    description_cid = component['description_cid']
                    biounit_id = component.get('biounit_id', 'unknown')
                    self.logger.info(f"🔍 Загружаем описание для компонента {biounit_id} из {description_cid}")
                    
                    try:
                        # Загружаем описание из IPFS через storage_service
                        description_data = self.storage_service.download_json(description_cid)
                        if description_data and isinstance(description_data, dict):
                            # 🔧 СОЗДАЕМ COMPONENTDESCRIPTION: Вместо простого update()
                            self.logger.info(f"🔍 Получены данные описания для {biounit_id}: {list(description_data.keys())}")
                            
                            try:
                                component_description = ComponentDescription.from_dict(description_data)
                                self.logger.info(f"✅ ComponentDescription создан для компонента {biounit_id}")
                                
                                # 🔧 СТРУКТУРИРУЕМ ДАННЫЕ: Передаем description в правильном формате
                                # Удаляем старые поля описания если они есть
                                description_fields = ['generic_description', 'effects', 'shamanic', 'warnings', 'dosage_instructions', 'features']
                                removed_fields = []
                                for field in description_fields:
                                    if field in component:
                                        removed_fields.append(field)
                                        del component[field]
                                
                                if removed_fields:
                                    self.logger.info(f"🧹 Удалены старые поля описания для {biounit_id}: {removed_fields}")
                                
                                # Добавляем новое поле description с ComponentDescription объектом
                                component['description'] = component_description
                                
                                self.logger.info(f"✅ Описание структурировано для компонента {biounit_id}: {list(description_data.keys())}")
                                self.logger.info(f"📊 Компонент {biounit_id} теперь содержит: {list(component.keys())}")
                                
                            except Exception as e:
                                self.logger.error(f"❌ Ошибка создания ComponentDescription для {biounit_id}: {e}")
                                self.logger.error(f"🔍 Данные, вызвавшие ошибку: {description_data}")
                                # Fallback: используем старый метод для обратной совместимости
                                component.update(description_data)
                                self.logger.warning(f"⚠️ Используем fallback update() для компонента {biounit_id}")
                                self.logger.info(f"📊 Fallback: компонент {biounit_id} содержит: {list(component.keys())}")
                        else:
                            self.logger.warning(f"⚠️ Не удалось загрузить описание из {description_cid}")
                            if description_data:
                                self.logger.warning(f"🔍 Получены данные неверного типа: {type(description_data)}")
                            else:
                                self.logger.warning(f"🔍 Получены пустые данные из {description_cid}")
                    except Exception as e:
                        self.logger.error(f"❌ Ошибка загрузки описания из {description_cid}: {e}")
                        continue
            
            return enriched_metadata
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обогащения метаданных описаниями: {e}")
            return metadata
    
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