"""
Сервис для централизованной сборки продуктов из данных блокчейна и IPFS метаданных.

Этот сервис устраняет дублирование логики сборки продуктов между
ProductRegistryService и ProductMetadataService, предоставляя единый
интерфейс для создания объектов Product.
"""

from typing import Dict, Any, Optional, Tuple, List
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
    
    def __init__(self, component_service, validation_service=None):
        """
        Инициализирует ProductAssembler (clean break: только NEW система).
        
        Args:
            component_service: ComponentService (REQUIRED) для работы с реестром компонентов
            validation_service: Сервис валидации (опционально)
        
        Raises:
            ValueError: Если component_service не передан
        """
        self.logger = logging.getLogger(__name__)
        if not component_service:
            raise ValueError("component_service is REQUIRED for ProductAssembler")
        self.component_service = component_service
        self.validation_service = validation_service
        
        self.logger.info("✅ ProductAssembler initialized with ComponentService (clean break)")
    
    async def assemble_product(self, blockchain_data: Tuple, metadata: Dict[str, Any], language: str = "ru") -> Optional[Product]:
        """
        Собирает продукт из данных блокчейна и IPFS метаданных.
        
        Args:
            blockchain_data: Кортеж с данными блокчейна (id, seller, componentIds, metadataCID, active)
                - [0] id: blockchain_id продукта
                - [1] seller: адрес продавца
                - [2] componentIds: список component_id из OrganicComponentRegistry
                - [3] metadataCID: IPFS CID метаданных
                - [4] active: статус активности
            metadata: Словарь с метаданными продукта из IPFS (с organic_components массивом)
            language: Язык для загрузки ComponentDescription (по умолчанию "ru")
            
        Returns:
            Product: Собранный объект продукта или None при ошибке
            
        Raises:
            ValueError: При некорректных данных блокчейна или метаданных
        """
        try:
            self.logger.info(f"🔍 Начинаем сборку продукта: blockchain_data={blockchain_data}, language={language}")
            
            # Шаг 1: Валидация и извлечение данных блокчейна
            blockchain_info = self._extract_blockchain_data(blockchain_data)
            if not blockchain_info:
                self.logger.error("❌ Не удалось извлечь данные блокчейна")
                return None
            
            product_id, seller, component_ids, ipfs_cid, is_active = blockchain_info
            self.logger.info(
                f"✅ Данные блокчейна извлечены: "
                f"blockchain_id={product_id}, seller={seller}, "
                f"componentIds={len(component_ids)} items, CID={ipfs_cid}, Active={is_active}"
            )
            
            # Шаг 2: Валидация базовых метаданных через ValidationFactory
            validation_result = self._validate_metadata(metadata)
            if not validation_result:
                self.logger.error("❌ Валидация базовых метаданных не прошла")
                return None
            
            self.logger.info("✅ Базовые метаданные успешно валидированы")
            
            # Шаг 3: Валидация соответствия componentIds из blockchain и organic_components из metadata
            if not self._validate_component_ids_match(component_ids, metadata):
                self.logger.warning(
                    "⚠️ Несоответствие componentIds между blockchain и metadata "
                    "(продолжаем сборку, но это может указывать на проблему)"
                )
            
            # Шаг 4: Создание объекта Product из метаданных (с обогащением)
            product = await self._create_product_from_metadata(metadata, language)
            if not product:
                self.logger.error("❌ Не удалось создать продукт из метаданных")
                return None
            
            self.logger.info("✅ Объект Product создан из метаданных")
            
            # Шаг 5: Установка блокчейн-данных
            self._set_blockchain_data(product, product_id, ipfs_cid, is_active)
            
            self.logger.info(f"🎉 Продукт {product.business_id} (blockchain_id={product_id}) успешно собран")
            return product
            
        except Exception as e:
            self.logger.error(f"�� Критическая ошибка при сборке продукта: {e}")
            return None
    
    def _extract_blockchain_data(self, blockchain_data: Tuple) -> Optional[Tuple[int, str, List[str], str, bool]]:
        """
        Извлекает и валидирует данные из кортежа блокчейна (новая структура с componentIds).
        
        Args:
            blockchain_data: Кортеж (id, seller, componentIds, metadataCID, active)
            
        Returns:
            Tuple[int, str, List[str], str, bool]: 
            (product_id, seller, component_ids, ipfs_cid, is_active) или None при ошибке
        
        Структура:
            - [0] id (blockchain_id)
            - [1] seller
            - [2] componentIds (список)
            - [3] metadataCID
            - [4] active
        """
        try:
            if not hasattr(blockchain_data, '__getitem__') or len(blockchain_data) < 5:
                self.logger.error(
                    f"Некорректная структура blockchain_data: ожидается 5 элементов, "
                    f"получено {len(blockchain_data) if hasattr(blockchain_data, '__len__') else 'N/A'}. "
                    f"Данные: {blockchain_data}"
                )
                return None
            
            product_id = blockchain_data[0]      # blockchain_id продукта
            seller = blockchain_data[1]          # Адрес продавца
            component_ids = blockchain_data[2]   # componentIds (список)
            ipfs_cid = blockchain_data[3]        # metadataCID
            is_active = bool(blockchain_data[4]) # Статус активности
            
            # Валидация извлеченных данных
            if not isinstance(product_id, (int, str)) or not product_id:
                self.logger.error(f"Некорректный blockchain_id: {product_id}")
                return None
            
            if not isinstance(component_ids, list):
                self.logger.error(f"Некорректный componentIds: ожидается список, получен {type(component_ids)}")
                return None
            
            if not ipfs_cid or not isinstance(ipfs_cid, str):
                self.logger.error(f"Некорректный metadataCID: {ipfs_cid}")
                return None
            
            self.logger.info(
                f"✅ Извлечены данные блокчейна: "
                f"id={product_id}, seller={seller}, componentIds={len(component_ids)} items, "
                f"CID={ipfs_cid}, active={is_active}"
            )
            
            return product_id, seller, component_ids, ipfs_cid, is_active
            
        except Exception as e:
            self.logger.error(f"Ошибка извлечения данных блокчейна: {e}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
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
    
    def _validate_component_ids_match(
        self, 
        component_ids: List[str], 
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Валидирует соответствие componentIds из blockchain и organic_components из metadata.
        
        Args:
            component_ids: Список component_id из blockchain (Product.componentIds[])
            metadata: Метаданные продукта с organic_components массивом
        
        Returns:
            bool: True если соответствуют, False если нет
        
        Логика:
            - Извлекает component_id из каждого элемента organic_components
            - Сравнивает множества (set) для игнорирования порядка
            - Логирует предупреждение при несоответствии (не блокирует сборку)
        """
        try:
            # Извлекаем component_id из метаданных
            if 'organic_components' not in metadata:
                self.logger.warning(
                    "⚠️ Валидация componentIds: отсутствует поле 'organic_components' в metadata"
                )
                return False
            
            if not isinstance(metadata['organic_components'], list):
                self.logger.warning(
                    "⚠️ Валидация componentIds: 'organic_components' должен быть списком"
                )
                return False
            
            metadata_component_ids = []
            for i, comp in enumerate(metadata['organic_components']):
                if isinstance(comp, dict):
                    comp_id = comp.get('component_id')
                    if comp_id:
                        metadata_component_ids.append(str(comp_id))
                    else:
                        self.logger.warning(
                            f"⚠️ Валидация componentIds: компонент {i} не содержит 'component_id'"
                        )
                else:
                    self.logger.warning(
                        f"⚠️ Валидация componentIds: компонент {i} не является словарем"
                    )
            
            # Нормализуем component_ids из blockchain (все в строки)
            blockchain_component_ids = [str(cid) for cid in component_ids]
            
            # Сравниваем множества (игнорируем порядок)
            blockchain_set = set(blockchain_component_ids)
            metadata_set = set(metadata_component_ids)
            
            if blockchain_set != metadata_set:
                self.logger.warning(
                    f"⚠️ Несоответствие componentIds:\n"
                    f"   Blockchain: {blockchain_component_ids}\n"
                    f"   Metadata:   {metadata_component_ids}\n"
                    f"   Blockchain set: {blockchain_set}\n"
                    f"   Metadata set:   {metadata_set}"
                )
                return False
            
            self.logger.info(
                f"✅ Валидация componentIds: соответствие подтверждено "
                f"({len(blockchain_component_ids)} компонентов)"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка валидации соответствия componentIds: {e}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            return False
    
    async def _enrich_components(self, metadata: Dict[str, Any], language: str) -> Dict[str, Any]:
        """
        Обогащает метаданные продукта данными из реестра компонентов.
        
        Работает с organic_components массивом (всегда массив, даже для 1 компонента).
        Не зависит от количества компонентов.
        
        Процесс:
            Для каждого компонента в массиве:
            1. Получить component_id и proportion
            2. Загрузить полные данные компонента из реестра через ComponentService
            3. Создать product component с proportion через OrganicComponent.for_product()
            4. Загрузить ComponentDescription с указанным языком
            5. Добавить обогащенный компонент в массив
        
        Args:
            metadata: Метаданные продукта с organic_components массивом
            language: Язык для загрузки ComponentDescription
        
        Returns:
            Dict: Обогащенные метаданные с полными данными всех компонентов
        
        Raises:
            ValueError: Если компонент не найден в реестре или отсутствуют обязательные поля
        """
        try:
            enriched_metadata = metadata.copy()
            enriched_components = []
            
            # Валидация наличия organic_components
            if 'organic_components' not in metadata:
                raise ValueError(
                    "Отсутствует обязательное поле 'organic_components'. "
                    "Метаданные должны содержать массив компонентов."
                )
            
            if not isinstance(metadata['organic_components'], list):
                raise ValueError(
                    f"organic_components должен быть массивом, получен: {type(metadata['organic_components'])}"
                )
            
            components_count = len(metadata['organic_components'])
            if components_count == 0:
                raise ValueError(
                    "organic_components не может быть пустым. "
                    "Продукт должен содержать хотя бы один компонент."
                )
            
            self.logger.info(f"🔍 Обогащаем продукт: {components_count} компонент(ов) (lang: {language})")
            
            # ──────────────────────────────────────────────────────────────────────
            # Итерация по каждому компоненту в массиве
            # ──────────────────────────────────────────────────────────────────────
            for i, comp_ref in enumerate(metadata['organic_components']):
                component_id = comp_ref.get('component_id')
                proportion = comp_ref.get('proportion')
                
                # Валидация обязательных полей
                if not component_id:
                    raise ValueError(
                        f"Компонент {i+1}/{components_count}: Отсутствует component_id. "
                        f"Каждый компонент должен содержать component_id из реестра."
                    )
                if not proportion:
                    raise ValueError(
                        f"Компонент {i+1}/{components_count} ('{component_id}'): Отсутствует proportion. "
                        f"Каждый компонент должен содержать proportion (например, '50g')."
                    )
                
                self.logger.info(f"   [{i+1}/{components_count}] Загружаем '{component_id}' (proportion: {proportion})")
                
                # ──────────────────────────────────────────────────────────────────
                # Step 1: Load full registry component (OrganicComponentRegistry + root metadata via CID)
                # ──────────────────────────────────────────────────────────────────
                registry_component = self.component_service.get_component_full(component_id)
                
                if not registry_component:
                    raise ValueError(
                        f"Компонент '{component_id}' не найден в OrganicComponentRegistry. "
                        f"Убедитесь что компонент зарегистрирован в реестре."
                    )
                
                self.logger.info(f"      ✅ Загружен: {registry_component.scientific_title}")
                
                # ──────────────────────────────────────────────────────────────────
                # Step 2: Create a product component (registry component + proportion)
                # ──────────────────────────────────────────────────────────────────
                from model.organic_component import OrganicComponent
                
                product_component = OrganicComponent.for_product(
                    registry_component=registry_component,
                    proportion=proportion
                )
                
                component_dict = product_component.to_dict()
                
                # ──────────────────────────────────────────────────────────────────
                # Step 3: Fetch ComponentDescription for this component_id + language
                #
                # Data path (SSOT):
                # - ComponentService.get_component_description(...)
                #   → MultilingualIPFSService (AmanitaInternational getComplexFieldCID)
                #   → ProductStorageService.download_json(cid)
                #
                # Note: Real ComponentDescription payloads are often "plain dict fields" and are
                # normalized upstream in MultilingualIPFSService.
                # ──────────────────────────────────────────────────────────────────
                try:
                    self.logger.info(f"      🌍 Fetching ComponentDescription for '{component_id}' (lang: {language})")
                    description = await self.component_service.get_component_description(
                        component_id,
                        language
                    )
                    
                    if description:
                        component_dict['description'] = description.to_dict()
                        self.logger.info(f"      ✅ ComponentDescription добавлен (generic: {len(description.generic_description)} chars)")
                    else:
                        self.logger.warning(f"      ⚠️ ComponentDescription не найден (graceful skip)")
                        
                except Exception as e:
                    # Graceful degradation: description опциональное поле
                    self.logger.warning(f"      ⚠️ Error fetching description (graceful skip): {e}")
                
                enriched_components.append(component_dict)
                
                self.logger.info(f"      ✅ Обогащен: {component_id} ({proportion}) [desc: {'✅' if 'description' in component_dict else '⚠️'}]")
            
            # ──────────────────────────────────────────────────────────────────────
            # ШАГ 4: Заменить массив компонентов на обогащенные данные
            # ──────────────────────────────────────────────────────────────────────
            enriched_metadata['organic_components'] = enriched_components
            
            self.logger.info(f"✅ Продукт обогащен:")
            self.logger.info(f"   Все {len(enriched_components)} компонент(ов) загружены из реестра")
            for i, comp in enumerate(enriched_components):
                self.logger.info(f"   [{i+1}] {comp['component_id']} ({comp['proportion']})")
            
            return enriched_metadata
            
        except ValueError:
            # Пробрасываем ValueError (компонент не найден или отсутствуют обязательные поля)
            raise
        except Exception as e:
            self.logger.error(f"❌ Ошибка обогащения продукта: {e}")
            import traceback
            self.logger.error(f"   Stack trace: {traceback.format_exc()}")
            raise ValueError(f"Ошибка обогащения продукта: {e}")
    
    async def _create_product_from_metadata(self, metadata: Dict[str, Any], language: str) -> Optional[Product]:
        """
        Создает объект Product из метаданных с обогащением через ComponentService.
        
        Все продукты используют единый формат с organic_components массивом.
        
        Процесс:
            1. Обогатить метаданные данными из реестра через _enrich_components()
            2. Валидировать обогащенные метаданные
            3. Создать Product объект через Product.from_dict()
        
        Args:
            metadata: Метаданные продукта из Arweave (с organic_components массивом)
            language: Язык для загрузки ComponentDescription
        
        Returns:
            Product: Созданный объект продукта или None при ошибке
        """
        try:
            business_id = metadata.get('business_id', 'N/A')
            self.logger.info(f"🔍 Создание Product из метаданных: business_id='{business_id}', language='{language}'")
            self.logger.info(f"📋 Структура метаданных: {list(metadata.keys())}")
            
            # ──────────────────────────────────────────────────────────────────────
            # ШАГ 1: Обогатить метаданные данными из реестра компонентов
            # ──────────────────────────────────────────────────────────────────────
            self.logger.info("🔧 Обогащаем продукт через ComponentService...")
            enriched_metadata = await self._enrich_components(metadata, language)
            
            # ──────────────────────────────────────────────────────────────────────
            # ШАГ 2: Валидация обогащенных метаданных
            # ──────────────────────────────────────────────────────────────────────
            self.logger.info("🔍 Валидация обогащенных метаданных...")
            self._validate_product_metadata(enriched_metadata)
            
            # ──────────────────────────────────────────────────────────────────────
            # ШАГ 3: Создание Product объекта
            # ──────────────────────────────────────────────────────────────────────
            self.logger.info("🏗️ Создание Product объекта через Product.from_dict()...")
            product = Product.from_dict(enriched_metadata)
            
            self.logger.info(f"✅ Продукт создан:")
            self.logger.info(f"   business_id: {product.business_id}")
            self.logger.info(f"   title: {product.title}")
            self.logger.info(f"   components: {len(product.organic_components)}")
            
            return product
            
        except ValueError as e:
            # Явные ошибки валидации/обогащения
            self.logger.error(f"❌ Ошибка валидации/обогащения продукта: {e}")
            return None
            
        except Exception as e:
            # Неожиданные ошибки
            self.logger.error(f"❌ Неожиданная ошибка создания продукта: {e}")
            self.logger.error(f"📋 Тип ошибки: {type(e).__name__}")
            import traceback
            self.logger.error(f"🔍 Stack trace: {traceback.format_exc()}")
            return None
    
    def _validate_product_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Валидирует обогащенные метаданные продукта перед созданием Product объекта.
        
        Вызывается ПОСЛЕ обогащения через _enrich_single/multi_component(),
        поэтому компоненты должны уже содержать полные данные из реестра.
        
        Args:
            metadata: Обогащенные метаданные продукта для валидации
            
        Raises:
            ValueError: Если валидация не прошла
        """
        self.logger.info("🔍 Валидация обогащенных метаданных продукта...")
        
        # ──────────────────────────────────────────────────────────────────────
        # ШАГ 1: Проверка обязательных полей продукта
        # ──────────────────────────────────────────────────────────────────────
        required_fields = ['business_id', 'title', 'organic_components', 'categories', 'forms', 'species']
        # Поля, которым разрешено быть пустыми (но они обязаны существовать в metadata)
        allow_empty_fields = {'categories'}
        for field in required_fields:
            if field not in metadata:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
            if field in allow_empty_fields:
                continue
            if not metadata[field]:
                raise ValueError(f"Поле {field} не может быть пустым")
        
        # ──────────────────────────────────────────────────────────────────────
        # ШАГ 2: Валидация organic_components массива
        # ──────────────────────────────────────────────────────────────────────
        if not isinstance(metadata['organic_components'], list):
            raise ValueError("organic_components должен быть списком")
        
        if len(metadata['organic_components']) == 0:
            raise ValueError("organic_components не может быть пустым")
        
        # ──────────────────────────────────────────────────────────────────────
        # ШАГ 3: Валидация каждого обогащенного компонента
        # ──────────────────────────────────────────────────────────────────────
        # После обогащения компоненты должны содержать полные данные из реестра
        
        for i, component in enumerate(metadata['organic_components']):
            if not isinstance(component, dict):
                raise ValueError(f"Компонент {i} должен быть словарем")
            
            # Обязательные поля для обогащенного компонента
            component_required_fields = ['component_id', 'proportion']
            for field in component_required_fields:
                if field not in component:
                    raise ValueError(f"Отсутствует поле {field} в компоненте {i}")
                if not component[field] or not str(component[field]).strip():
                    raise ValueError(f"Поле {field} в компоненте {i} не может быть пустым")
            
            # После обогащения должны появиться поля из реестра
            if 'scientific_title' not in component:
                self.logger.warning(
                    f"⚠️ Компонент {i} ({component.get('component_id')}): "
                    f"отсутствует scientific_title (обогащение могло не сработать)"
                )
            
            self.logger.info(f"   ✅ Компонент {i+1} валиден: {component.get('component_id')} ({component.get('proportion')})")
        
        # ──────────────────────────────────────────────────────────────────────
        # ШАГ 4: Опциональная валидация cover_image_url
        # ──────────────────────────────────────────────────────────────────────
        if 'cover_image_url' in metadata and metadata['cover_image_url']:
            cover_image_url = metadata['cover_image_url'].strip()
            if cover_image_url:
                # Единая валидация CID: IPFS (Qm/bafy) или Arweave txId (43 base64url)
                cid_validator = ValidationFactory.get_cid_validator()
                cid_result = cid_validator.validate(cover_image_url)
                if not cid_result.is_valid:
                    raise ValueError(f"cover_image_url: {cid_result.error_message} ({cover_image_url})")
        
        self.logger.info("✅ Валидация метаданных продукта прошла успешно")
    
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