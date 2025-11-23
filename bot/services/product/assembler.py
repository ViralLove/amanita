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
    
    # ==================================================================================
    # ФОРМАТЫ МЕТАДАННЫХ ПРОДУКТОВ
    # ==================================================================================
    # 
    # Все продукты используют централизованный OrganicComponentRegistry.
    # Два формата метаданных:
    #
    # 1. SINGLE — Чистый компонент (component_id на корневом уровне)
    #    Пример: Blue Lotus Tincture
    #    {
    #      "business_id": "blue_lotus_tincture",
    #      "component_id": "blue_lotus",        ← КЛЮЧ: component_id здесь
    #      "proportion": "100%",
    #      "form": "tincture"
    #    }
    #    → Продукт = один компонент из реестра в определенной форме
    #
    # 2. MULTI — Смесь компонентов (organic_components массив)
    #    Пример: Relaxation Blend
    #    {
    #      "business_id": "relaxation_blend",
    #      "organic_components": [             ← КЛЮЧ: массив компонентов
    #        {"component_id": "amanita_muscaria", "proportion": "50g"},
    #        {"component_id": "lions_mane", "proportion": "30g"}
    #      ]
    #    }
    #    → Продукт = смесь компонентов из реестра
    #
    # Любой другой формат → ValueError с объяснением требований
    #
    # ==================================================================================
    
    FORMAT_SINGLE = 'SINGLE'  # component_id на корневом уровне
    FORMAT_MULTI = 'MULTI'    # organic_components массив с component_id
    
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
    
    async def assemble_product(self, blockchain_data: Tuple, metadata: Dict[str, Any]) -> Optional[Product]:
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
            product = await self._create_product_from_metadata(metadata)
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
    
    def _detect_product_format(self, metadata: Dict[str, Any]) -> str:
        """
        Определяет формат продукта (SINGLE или MULTI).
        
        АЛГОРИТМ:
        =========
        
        1. Проверка SINGLE формата:
           - Ищем 'component_id' на корневом уровне метаданных
           - Если найден → продукт = чистый компонент из реестра
           - Пример: {"business_id": "...", "component_id": "blue_lotus", "proportion": "100%"}
        
        2. Проверка MULTI формата:
           - Ищем 'organic_components' массив в метаданных
           - Проверяем первый элемент на наличие 'component_id'
           - Если найден → продукт = смесь компонентов из реестра
           - Пример: {"business_id": "...", "organic_components": [{"component_id": "...", "proportion": "..."}]}
        
        3. Неподдерживаемый формат:
           - Нет ни 'component_id', ни 'organic_components' → ОШИБКА
           - Метаданные не соответствуют требованиям
        
        ТАБЛИЦА:
        ========
        | Признак                          | Формат  | Действие      |
        |----------------------------------|---------|---------------|
        | component_id на корневом уровне  | SINGLE  | ✅ Обработать |
        | organic_components + component_id| MULTI   | ✅ Обработать |
        | Другое                           | Invalid | ❌ ValueError |
        
        Args:
            metadata: Метаданные продукта из IPFS/Arweave
            
        Returns:
            str: 'SINGLE' или 'MULTI'
            
        Raises:
            ValueError: Если формат не поддерживается
        """
        try:
            # ──────────────────────────────────────────────────────────────────────
            # ШАГ 1: Проверка SINGLE формата
            # ──────────────────────────────────────────────────────────────────────
            # component_id на корневом уровне метаданных
            # Пример: {"business_id": "blue_lotus_tincture", "component_id": "blue_lotus"}
            
            if 'component_id' in metadata and isinstance(metadata['component_id'], str):
                component_id = metadata['component_id']
                if component_id and component_id.strip():
                    self.logger.info(f"📍 Формат: SINGLE (component_id='{component_id}')")
                    return self.FORMAT_SINGLE
            
            # ──────────────────────────────────────────────────────────────────────
            # ШАГ 2: Проверка MULTI формата
            # ──────────────────────────────────────────────────────────────────────
            # organic_components массив с component_id в элементах
            # Пример: [{"component_id": "...", "proportion": "..."}]
            
            if 'organic_components' in metadata and isinstance(metadata['organic_components'], list):
                components = metadata['organic_components']
                
                # Массив не может быть пустым
                if len(components) == 0:
                    raise ValueError(
                        "Пустой массив organic_components. "
                        "Продукт должен содержать хотя бы один компонент."
                    )
                
                # Проверяем первый компонент
                first_comp = components[0]
                
                # Должен содержать component_id
                if 'component_id' in first_comp:
                    component_id = first_comp['component_id']
                    if isinstance(component_id, str) and component_id.strip():
                        self.logger.info(
                            f"📍 Формат: MULTI ({len(components)} компонентов)"
                        )
                        return self.FORMAT_MULTI
                
                # organic_components есть, но нет component_id
                raise ValueError(
                    "Компоненты в organic_components не содержат component_id. "
                    f"Требуется поле component_id в каждом элементе.\n"
                    f"Первый компонент: {first_comp}"
                )
            
            # ──────────────────────────────────────────────────────────────────────
            # ШАГ 3: Неподдерживаемый формат
            # ──────────────────────────────────────────────────────────────────────
            raise ValueError(
                f"Неподдерживаемый формат продукта. "
                f"\n\n"
                f"Требуется:\n"
                f"  - либо 'component_id' на корневом уровне (SINGLE)\n"
                f"  - либо 'organic_components' массив с component_id (MULTI)\n"
                f"\n"
                f"Найденные ключи: {list(metadata.keys())}"
            )
            
        except ValueError:
            # Пробрасываем ValueError как есть (это ожидаемые ошибки)
            raise
        except Exception as e:
            # Логируем неожиданные ошибки
            self.logger.error(f"Ошибка определения формата продукта: {e}")
            raise ValueError(f"Ошибка определения формата продукта: {e}")
    
    async def _enrich_single_component(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обогащает SINGLE продукт данными из реестра компонентов.
        
        Формат SINGLE:
            {
              "component_id": "amanita_muscaria",
              "proportion": "100g",
              ...
            }
        
        Процесс:
            1. Получить component_id из метаданных
            2. Загрузить полные данные компонента из реестра через ComponentService
            3. Создать product component с proportion через OrganicComponent.for_product()
            4. Добавить organic_components массив в метаданные
            5. Вернуть обогащенные метаданные
        
        Args:
            metadata: Метаданные продукта с component_id на корневом уровне
        
        Returns:
            Dict: Обогащенные метаданные с organic_components массивом
        
        Raises:
            ValueError: Если компонент не найден в реестре
        """
        try:
            component_id = metadata.get('component_id')
            proportion = metadata.get('proportion', '100g')
            
            self.logger.info(f"🔍 Обогащаем SINGLE продукт: component_id='{component_id}', proportion='{proportion}'")
            
            # ──────────────────────────────────────────────────────────────────────
            # ШАГ 1: Получить полные данные компонента из реестра
            # ──────────────────────────────────────────────────────────────────────
            self.logger.info(f"   Загружаем компонент из реестра через ComponentService...")
            
            registry_component = self.component_service.get_component_full(component_id)
            
            if not registry_component:
                raise ValueError(
                    f"Компонент '{component_id}' не найден в OrganicComponentRegistry. "
                    f"Убедитесь что компонент зарегистрирован в реестре."
                )
            
            self.logger.info(f"   ✅ Компонент загружен: {registry_component.scientific_title}")
            self.logger.info(f"      Forms: {registry_component.forms}")
            self.logger.info(f"      Features: {len(registry_component.features.get('common', []))} общих")
            
            # ──────────────────────────────────────────────────────────────────────
            # ШАГ 2: Создать product component с proportion
            # ──────────────────────────────────────────────────────────────────────
            from model.organic_component import OrganicComponent
            
            product_component = OrganicComponent.for_product(
                registry_component=registry_component,
                proportion=proportion
            )
            
            self.logger.info(f"   ✅ Product component создан:")
            self.logger.info(f"      component_id: {product_component.component_id}")
            self.logger.info(f"      proportion: {product_component.proportion}")
            self.logger.info(f"      scientific_title: {product_component.scientific_title}")
            
            # ──────────────────────────────────────────────────────────────────────
            # ШАГ 3: Добавить organic_components массив в метаданные
            # ──────────────────────────────────────────────────────────────────────
            enriched_metadata = metadata.copy()
            component_dict = product_component.to_dict()
            
            # ──────────────────────────────────────────────────────────────────────
            # 🆕 ШАГ 4: Fetch ComponentDescription (Task 9.1)
            # ──────────────────────────────────────────────────────────────────────
            try:
                # Определяем язык (по умолчанию "ru" если не передан)
                # TODO: В будущем получать язык из контекста (loc.language)
                language = "ru"  # Default для первой реализации
                
                self.logger.info(f"   🌍 Fetching ComponentDescription for '{component_id}' (lang: {language})")
                description = await self.component_service.get_component_description(
                    component_id,
                    language
                )
                
                if description:
                    component_dict['description'] = description.to_dict()
                    self.logger.info(f"   ✅ ComponentDescription добавлен (generic: {len(description.generic_description)} chars)")
                else:
                    self.logger.warning(f"   ⚠️ ComponentDescription не найден (graceful skip)")
                    
            except Exception as e:
                # Graceful degradation: description опциональное поле
                self.logger.warning(f"   ⚠️ Error fetching description (graceful skip): {e}")
            
            enriched_metadata['organic_components'] = [component_dict]
            
            self.logger.info(f"✅ SINGLE продукт обогащен:")
            self.logger.info(f"   Добавлен organic_components массив с 1 компонентом")
            self.logger.info(f"   Component: {component_id} ({proportion})")
            self.logger.info(f"   Description: {'✅ Added' if 'description' in component_dict else '⚠️ Not available'}")
            
            return enriched_metadata
            
        except ValueError:
            # Пробрасываем ValueError (компонент не найден)
            raise
        except Exception as e:
            self.logger.error(f"❌ Ошибка обогащения SINGLE продукта: {e}")
            import traceback
            self.logger.error(f"   Stack trace: {traceback.format_exc()}")
            raise ValueError(f"Ошибка обогащения SINGLE продукта: {e}")
    
    async def _enrich_multi_component(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обогащает MULTI продукт данными из реестра компонентов.
        
        Формат MULTI:
            {
              "organic_components": [
                {"component_id": "amanita_muscaria", "proportion": "50g"},
                {"component_id": "lions_mane", "proportion": "30g"}
              ]
            }
        
        Процесс:
            Для каждого компонента в массиве:
            1. Получить component_id и proportion
            2. Загрузить полные данные компонента из реестра через ComponentService
            3. Создать product component с proportion через OrganicComponent.for_product()
            4. Заменить минимальную ссылку на полный объект компонента
            5. Вернуть обогащенные метаданные
        
        Args:
            metadata: Метаданные продукта с organic_components (ссылки на реестр)
        
        Returns:
            Dict: Обогащенные метаданные с полными данными всех компонентов
        
        Raises:
            ValueError: Если любой компонент не найден в реестре
        """
        try:
            enriched_metadata = metadata.copy()
            enriched_components = []
            
            components_count = len(metadata['organic_components'])
            self.logger.info(f"🔍 Обогащаем MULTI продукт: {components_count} компонентов")
            
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
                # ШАГ 1: Получить полные данные компонента из реестра
                # ──────────────────────────────────────────────────────────────────
                registry_component = self.component_service.get_component_full(component_id)
                
                if not registry_component:
                    raise ValueError(
                        f"Компонент '{component_id}' не найден в OrganicComponentRegistry. "
                        f"Убедитесь что компонент зарегистрирован в реестре."
                    )
                
                self.logger.info(f"      ✅ Загружен: {registry_component.scientific_title}")
                
                # ──────────────────────────────────────────────────────────────────
                # ШАГ 2: Создать product component с proportion
                # ──────────────────────────────────────────────────────────────────
                from model.organic_component import OrganicComponent
                
                product_component = OrganicComponent.for_product(
                    registry_component=registry_component,
                    proportion=proportion
                )
                
                component_dict = product_component.to_dict()
                
                # ──────────────────────────────────────────────────────────────────
                # 🆕 ШАГ 3: Fetch ComponentDescription (Task 9.2)
                # ──────────────────────────────────────────────────────────────────
                try:
                    # TODO: В будущем получать язык из контекста (loc.language)
                    language = "ru"  # Default для первой реализации
                    
                    self.logger.info(f"      🌍 Fetching description for '{component_id}' (lang: {language})")
                    description = await self.component_service.get_component_description(
                        component_id,
                        language
                    )
                    
                    if description:
                        component_dict['description'] = description.to_dict()
                        self.logger.info(f"      ✅ ComponentDescription added (generic: {len(description.generic_description)} chars)")
                    else:
                        self.logger.warning(f"      ⚠️ ComponentDescription not found (graceful skip)")
                        
                except Exception as e:
                    # Graceful degradation: description опциональное поле
                    self.logger.warning(f"      ⚠️ Error fetching description (graceful skip): {e}")
                
                enriched_components.append(component_dict)
                
                self.logger.info(f"      ✅ Обогащен: {component_id} ({proportion}) [desc: {'✅' if 'description' in component_dict else '⚠️'}]")
            
            # ──────────────────────────────────────────────────────────────────────
            # ШАГ 3: Заменить массив компонентов на обогащенные данные
            # ──────────────────────────────────────────────────────────────────────
            enriched_metadata['organic_components'] = enriched_components
            
            self.logger.info(f"✅ MULTI продукт обогащен:")
            self.logger.info(f"   Все {len(enriched_components)} компонента загружены из реестра")
            for i, comp in enumerate(enriched_components):
                self.logger.info(f"   [{i+1}] {comp['component_id']} ({comp['proportion']})")
            
            return enriched_metadata
            
        except ValueError:
            # Пробрасываем ValueError (компонент не найден или отсутствуют обязательные поля)
            raise
        except Exception as e:
            self.logger.error(f"❌ Ошибка обогащения MULTI продукта: {e}")
            import traceback
            self.logger.error(f"   Stack trace: {traceback.format_exc()}")
            raise ValueError(f"Ошибка обогащения MULTI продукта: {e}")
    
    async def _create_product_from_metadata(self, metadata: Dict[str, Any]) -> Optional[Product]:
        """
        Создает объект Product из метаданных с обогащением через ComponentService.
        
        Только SINGLE и MULTI форматы поддерживаются.
        
        Процесс:
            1. Определить формат продукта (_detect_product_format)
            2. Обогатить данными из реестра:
               - SINGLE → _enrich_single_component()
               - MULTI  → _enrich_multi_component()
            3. Валидировать обогащенные метаданные
            4. Создать Product объект через Product.from_dict()
        
        Args:
            metadata: Метаданные продукта из Arweave
            
        Returns:
            Product: Созданный объект продукта или None при ошибке
        """
        try:
            business_id = metadata.get('business_id', 'N/A')
            self.logger.info(f"🔍 Создание Product из метаданных: business_id='{business_id}'")
            self.logger.info(f"📋 Структура метаданных: {list(metadata.keys())}")
            
            # ──────────────────────────────────────────────────────────────────────
            # ШАГ 1: Определить формат продукта
            # ──────────────────────────────────────────────────────────────────────
            product_format = self._detect_product_format(metadata)
            self.logger.info(f"📍 Определен формат: {product_format}")
            
            # ──────────────────────────────────────────────────────────────────────
            # ШАГ 2: Обогатить метаданные данными из реестра компонентов
            # ──────────────────────────────────────────────────────────────────────
            if product_format == self.FORMAT_SINGLE:
                self.logger.info("🔧 Обогащаем SINGLE продукт через ComponentService...")
                enriched_metadata = await self._enrich_single_component(metadata)
                
            elif product_format == self.FORMAT_MULTI:
                self.logger.info("🔧 Обогащаем MULTI продукт через ComponentService...")
                enriched_metadata = await self._enrich_multi_component(metadata)
                
            else:
                # Никогда не должно произойти (_detect_product_format поднимает ValueError)
                raise ValueError(f"Неподдерживаемый формат: {product_format}")
            
            # ──────────────────────────────────────────────────────────────────────
            # ШАГ 3: Валидация обогащенных метаданных
            # ──────────────────────────────────────────────────────────────────────
            self.logger.info("🔍 Валидация обогащенных метаданных...")
            self._validate_product_metadata(enriched_metadata)
            
            # ──────────────────────────────────────────────────────────────────────
            # ШАГ 4: Создание Product объекта
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
        for field in required_fields:
            if field not in metadata:
                raise ValueError(f"Отсутствует обязательное поле: {field}")
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
            if cover_image_url and not cover_image_url.startswith('Qm'):
                raise ValueError(f"cover_image_url должен быть валидным CID или пустым: {cover_image_url}")
        
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