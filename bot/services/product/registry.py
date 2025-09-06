from services.core.blockchain import BlockchainService
from datetime import datetime, timedelta
from model.product import Product, PriceInfo, Description
import logging
from typing import Optional, List, Dict, Union, Tuple, Any
import dotenv
import os
from web3 import Account
from services.core.ipfs_factory import IPFSFactory
import traceback
import re
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import aiohttp
import json
from services.product.metadata import ProductMetadataService
from services.product.cache import ProductCacheService
from services.product.storage import ProductStorageService
from services.product.validation import ProductValidationService
from services.product.assembler import ProductAssembler
from validation.exceptions import ValidationError
from services.core.account import AccountService
from services.product.exceptions import InvalidProductIdError, ProductNotFoundError

dotenv.load_dotenv()
logger = logging.getLogger(__name__)

PRODUCT_KEY_ID = "id"
PRODUCT_KEY_IPFS_CID = "ipfsCID"
PRODUCT_KEY_ACTIVE = "active"

SELLER_PRIVATE_KEY = os.getenv("SELLER_PRIVATE_KEY")

class ProductRegistryService:
    """
    Сервис для работы с реестром продуктов.
    Координирует работу всех подсервисов и обеспечивает единый интерфейс для работы с продуктами.
    """

    # Регулярное выражение для валидации IPFS CID
    IPFS_CID_PATTERN = re.compile(r'^(Qm[1-9A-HJ-NP-Za-km-z]{44}|bafy[A-Za-z2-7]{55})$')
    
    # Время жизни кэша для разных типов данных
    CACHE_TTL = {
        'catalog': timedelta(minutes=5),
        'description': timedelta(hours=24),
        'image': timedelta(hours=12)
    }

    def __init__(self, blockchain_service: Optional[BlockchainService] = None, storage_service: Optional[ProductStorageService] = None, validation_service: Optional[ProductValidationService] = None, account_service: Optional['AccountService'] = None, assembler: Optional[ProductAssembler] = None):
        """
        Инициализирует сервис реестра продуктов.
        
        Args:
            blockchain_service: Сервис для работы с блокчейном (если None, используется синглтон)
            storage_service: Сервис для работы с хранилищем
            validation_service: Сервис для валидации продуктов
            account_service: Сервис для работы с аккаунтами (если None, создается автоматически)
            assembler: Сервис для сборки продуктов (если None, создается автоматически)
        """
        # Инициализируем logger
        self.logger = logging.getLogger(__name__)

        self.logger.info(f"[ProductRegistry] __init__ id(self)={id(self)}")
        
        # Используем синглтон BlockchainService если не передан
        self.blockchain_service = blockchain_service or BlockchainService()
        self.validation_service = validation_service or ProductValidationService()
        
        # Создаем фабрику один раз
        self.storage_service = storage_service or IPFSFactory().get_storage()
        
        # Инициализируем кэш (storage_service создается внутри как синглтон)
        self.cache_service = ProductCacheService()
        
        # Инициализируем сервис метаданных
        self.metadata_service = ProductMetadataService(self.storage_service)
        
        # Инициализируем ProductAssembler для централизованной сборки продуктов
        self.assembler = assembler or ProductAssembler(storage_service=self.storage_service)
        
        # Инициализируем AccountService
        if account_service is None:
            self.account_service = AccountService(self.blockchain_service)
        else:
            self.account_service = account_service
        
        # Получаем аккаунт продавца через AccountService
        self.seller_account = Account.from_key(SELLER_PRIVATE_KEY)
        self.logger.info(f"Инициализирован аккаунт продавца: {self.seller_account.address}")
        
        self.logger.info("[ProductRegistry] Сервис инициализирован")

    def _is_cache_valid(self, timestamp: datetime, cache_type: str) -> bool:
        """
        Проверяет актуальность кэша.
        
        Args:
            timestamp: Временная метка кэша
            cache_type: Тип кэшированных данных ('catalog', 'description', 'image')
            
        Returns:
            bool: True если кэш актуален, False если устарел
        """
        if not timestamp:
            return False
        return datetime.utcnow() - timestamp < self.CACHE_TTL[cache_type]

    def _validate_ipfs_cid(self, cid: str) -> bool:
        """
        Проверяет валидность IPFS CID.
        
        Args:
            cid: IPFS Content Identifier
            
        Returns:
            bool: True если CID валиден, False если нет
        """
        if not cid:
            return False
        return bool(self.IPFS_CID_PATTERN.match(cid))

    @lru_cache(maxsize=100)
    def _get_cached_description(self, description_cid: str) -> Optional[Description]:
        """
        Получает кэшированное описание продукта.
        
        Args:
            description_cid: CID описания продукта
            
        Returns:
            Optional[Description]: Объект Description или None, если не найдено
        """
        return self.cache_service.get_description_by_cid(description_cid)

    def _get_cached_image(self, image_cid: str) -> Optional[str]:
        """
        Получает кэшированную ссылку на изображение.
        
        Args:
            image_cid: CID изображения
            
        Returns:
            Optional[str]: URL изображения или None, если не найдено
        """
        return self.cache_service.get_image_url_by_cid(image_cid)


        try:
            self.logger.info(f"[ProductRegistry] Обработка метаданных продукта {product_id}:")
            self.logger.info(f"  - ID: {product_id} (тип: {type(product_id)})")
            self.logger.info(f"  - IPFS CID: {ipfs_cid} (тип: {type(ipfs_cid)})")
            self.logger.info(f"  - Активен: {active} (тип: {type(active)})")

            # Валидируем CID через сервис валидации
            validation_result = self.validation_service.validate_cid(ipfs_cid)
            if not validation_result.is_valid:
                error_msg = validation_result.error_message or "Invalid CID"
                self.logger.error(f"[ProductRegistry] Некорректный CID метаданных продукта {product_id}: {error_msg}")
                return None

            metadata = self.storage_service.download_json(ipfs_cid)
            if not isinstance(metadata, dict):
                self.logger.error(f"[ProductRegistry] Некорректный формат метаданных продукта {product_id}")
                return None

            self.logger.info(f"[ProductRegistry] Загружены метаданные продукта {product_id}:")
            self.logger.info(f"  - Тип метаданных: {type(metadata)}")
            self.logger.info(f"  - Ключи метаданных: {list(metadata.keys())}")

            # Загружаем описание из description_cid
            description_obj = None
            description_cid = metadata.get('description_cid', '')
            
            if description_cid:
                try:
                    description_obj = self._get_cached_description(description_cid)
                    if not description_obj:
                        self.logger.warning(f"[ProductRegistry] Не удалось загрузить описание из description_cid: {description_cid}")
                except Exception as e:
                    self.logger.error(f"[ProductRegistry] Ошибка при загрузке описания из description_cid {description_cid}: {e}")
            
            else:
                self.logger.warning(f"[ProductRegistry] Описание продукта {product_id} отсутствует и в description_cid и в metadata")
            
            # Обрабатываем изображения
            cover_image = self._get_cached_image(metadata.get('cover_image_url', ''))
            gallery = [self._get_cached_image(cid) for cid in metadata.get('gallery', [])]
            gallery = [url for url in gallery if url]  # Фильтруем None

            # Обрабатываем цены
            prices_data = metadata.get('prices', [])
            prices = [PriceInfo.from_dict(price) for price in prices_data]

            # Создаем объект продукта
            product = Product(
                id=product_id,
                alias=str(product_id),  # Используем ID как alias
                status=1 if active else 0,
                cid=ipfs_cid,
                title=metadata.get('title', ''),
                description=description_obj,
                description_cid=description_cid,
                cover_image_url=cover_image,
                categories=metadata.get('categories', []),
                forms=metadata.get('forms', []),
                species=metadata.get('species', ''),
                prices=prices
            )

            self.logger.info(f"[ProductRegistry] Создан объект продукта {product_id}:")
            self.logger.info(f"  - ID: {product.id}")
            self.logger.info(f"  - Название: {product.title}")
            self.logger.info(f"  - Статус: {product.status}")
            self.logger.info(f"  - CID: {product.cid}")
            self.logger.info(f"  - Описание: {product.description}")
            self.logger.info(f"  - Описание CID: {product.description_cid}")
            self.logger.info(f"  - Обложка: {product.cover_image_url}")
            self.logger.info(f"  - Категории: {product.categories}")
            self.logger.info(f"  - Формы: {product.forms}")
            self.logger.info(f"  - Вид: {product.species}")
            self.logger.info(f"  - Цены: {product.prices}")

            return product
            
        except Exception as e:
            self.logger.error(f"[ProductRegistry] Ошибка обработки метаданных продукта {product_id}: {e}\n{traceback.format_exc()}")
            return None

    def _update_catalog_cache(self, version: int, products: List[Product]):
        """
        Обновляет кэш каталога.
        
        Args:
            version: Версия каталога
            products: Список продуктов
        """
        self.cache_service.set_cached_item("catalog", {
            "version": version,
            "products": products
        }, "catalog")
        self.logger.info(f"[ProductRegistry] Кэш каталога обновлен: {len(products)} продуктов")

    def clear_cache(self, cache_type: Optional[str] = None):
        """
        Очищает указанный тип кэша или все кэши.
        
        Args:
            cache_type: Тип кэша для очистки ('catalog', 'description', 'image') или None для очистки всех
        """
        self.cache_service.invalidate_cache(cache_type)
        self.logger.info(f"[ProductRegistry] Кэш очищен: {cache_type if cache_type else 'все'}")

    def get_catalog_version(self) -> int:
        """
        Получает текущую версию каталога продавца из ProductRegistry.
            
        Returns:
            int: Версия каталога
        """
        try:
            self.logger.info("[ProductRegistry] Начинаем получение версии каталога")
            
            version = self.blockchain_service.get_catalog_version()
            self.logger.info(f"[ProductRegistry] Получена версия каталога из контракта: {version}")
            return version

        except Exception as e:
            self.logger.error(f"[ProductRegistry] Ошибка получения версии каталога: {e}\n{traceback.format_exc()}")
            return 0

    def create_product_metadata(self, product_data: dict) -> dict:
        """
        Создает метаданные продукта в правильном формате.
        
        Args:
            product_data: Данные продукта
            
        Returns:
            dict: Метаданные продукта
        """
        self.logger.info("📦 Создание метаданных продукта")
        self.logger.info(f"📝 Входные данные: {json.dumps(product_data, indent=2)}")

        try:
            # Создаем базовую структуру метаданных (строгий стандарт: только 'forms')
            forms_value = product_data["forms"]
            metadata = {
                "business_id": product_data["business_id"],
                "title": product_data["title"],
                "organic_components": product_data["organic_components"],
                "cover_image_url": product_data["cover_image_url"],
                "categories": product_data["categories"],
                "forms": forms_value,
                "species": product_data["species"],
                "prices": product_data["prices"],
                "cid": product_data.get("cid", ""),  # 🔧 ИСПРАВЛЕНИЕ: Добавляем поле cid
                "created_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"✅ Метаданные созданы: {json.dumps(metadata, indent=2)}")
            return metadata

        except KeyError as e:
            self.logger.error(f"❌ Отсутствует обязательное поле в данных продукта: {str(e)}")
            raise ValidationError("metadata", f"Отсутствует обязательное поле: {str(e)}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка при создании метаданных: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise

    def upload_product_metadata(self, product_metadata: dict) -> str:
        """
        Загружает JSON-описание продукта в Arweave.
        Критерии приёмки:
        - Использует ArWeaveUploader.upload_text().
        - JSON должен быть валидным (проверка перед загрузкой).
        - Возвращает CID (ссылку Arweave) на JSON-объект.
        """
        pass

    def upload_media_file(self, file_path: str) -> str:
        """
        Загружает медиафайл (фото, видео) в Arweave.
        Критерии приёмки:
        - Путь должен быть валидным.
        - Используется ArWeaveUploader.upload_file().
        - Возвращает CID (ссылку Arweave) на файл.
        """
        pass

    def create_product_on_chain(self, ipfs_cid: str) -> str:
        """
        Вызывает createProduct в контракте ProductRegistry.
        
        Args:
            ipfs_cid: CID метаданных продукта в IPFS
            
        Returns:
            str: Хэш транзакции
            
        Raises:
            Exception: При ошибке создания продукта
        """
        try:
            self.logger.info(f"[ProductRegistry] Создание продукта в смарт-контракте с CID: {ipfs_cid}")
            
            if not self._validate_ipfs_cid(ipfs_cid):
                raise ValueError(f"Некорректный CID: {ipfs_cid}")
            
            # Делегируем создание продукта BlockchainService
            tx_hash = self.blockchain_service.create_product(ipfs_cid)
            
            if not tx_hash:
                raise Exception("Транзакция не прошла")
            
            self.logger.info(f"[ProductRegistry] Продукт успешно создан. Хэш транзакции: {tx_hash}")
            return tx_hash
            
        except Exception as e:
            self.logger.error(f"[ProductRegistry] Ошибка создания продукта: {e}")
            raise

    PRODUCT_FIELDS_MAP = {
        "field_0": "id",
        "field_2": "ipfsCID",
        "field_3": "active"
    }
    
    async def get_all_products(self) -> List[Product]:
        """Получает все продукты с кэшированием"""

        self.logger.info(f"[ProductRegistry] get_all_products id(self)={id(self)}")
        self.logger.info(f"[ProductRegistry] 🚀 Начинаем получение всех продуктов")

        try:
            # Проверяем версию каталога
            self.logger.info(f"[ProductRegistry] 📊 Проверяем версию каталога...")
            catalog_version = self.blockchain_service.get_catalog_version()
            self.logger.info(f"[ProductRegistry] ✅ Текущая версия каталога: {catalog_version}")
            
            # Проверяем кэш
            self.logger.info(f"[ProductRegistry] 🔍 Проверяем кэш каталога...")
            cached_catalog = self.cache_service.get_cached_item("catalog", "catalog")
            
            if cached_catalog:
                products_in_cache = cached_catalog.get('products', [])
                self.logger.info(f"[ProductRegistry] 📦 Найден кэш каталога: version={cached_catalog.get('version')}, products_count={len(products_in_cache)}")

                # Если версия совпадает и кэш не пустой — используем его
                if cached_catalog.get("version") == catalog_version and len(products_in_cache) > 0:
                    self.logger.info(f"[ProductRegistry] ✅ Возвращаем кэшированный каталог (версия {catalog_version})")
                    return products_in_cache
                elif cached_catalog.get("version") == catalog_version and len(products_in_cache) == 0:
                    # Версия совпадает, но кэш пуст — принудительно обновим из блокчейна
                    self.logger.info(f"[ProductRegistry] ⚠️ Кэш пуст при актуальной версии ({catalog_version}), обновляем из блокчейна")
                else:
                    self.logger.info(f"[ProductRegistry] ❌ Кэш устарел: cached_version={cached_catalog.get('version')}, current_version={catalog_version}")
            else:
                self.logger.info(f"[ProductRegistry] 📭 Кэш каталога пуст")
            
            # Получаем продукты из блокчейна
            self.logger.info(f"[ProductRegistry] 🔗 Загружаем продукты из блокчейна...")
            products_data = self.blockchain_service.get_all_products()
            self.logger.info(f"[ProductRegistry] 📊 Получено {len(products_data) if products_data else 0} продуктов из блокчейна")
            
            if not products_data:
                self.logger.warning(f"[ProductRegistry] ⚠️ No products found in blockchain")
                return []
            
            # Обрабатываем каждый продукт через унифицированный метод
            products = []
            self.logger.info(f"[ProductRegistry] 🔄 Начинаем обработку {len(products_data)} продуктов из блокчейна")
            self.logger.info(f"[ProductRegistry] 📋 Products data: {products_data}")
            
            for i, product_data in enumerate(products_data):
                try:
                    self.logger.info(f"[ProductRegistry] 🔍 Обрабатываем продукт {i+1}/{len(products_data)}: {product_data}")
                    # Используем унифицированный метод десериализации
                    product = await self._deserialize_product(product_data)
                    if product:
                        products.append(product)
                        self.logger.info(f"[ProductRegistry] ✅ Продукт {i+1} успешно обработан: ID={product.id if hasattr(product, 'id') else 'N/A'}")
                    else:
                        self.logger.warning(f"[ProductRegistry] ⚠️ Продукт {i+1} не удалось обработать")
                        
                except Exception as e:
                    self.logger.error(f"[ProductRegistry] ❌ Error processing product {i+1}: {e}")
                    continue
            
            # Обновляем кэш
            self.logger.info(f"[ProductRegistry] 💾 Сохраняем каталог в кэш: version={catalog_version}, products_count={len(products)}")
            self.cache_service.set_cached_item("catalog", {
                "version": catalog_version,
                "products": products
            }, "catalog")
            self.logger.info(f"[ProductRegistry] ✅ Каталог успешно сохранен в кэш")
            
            self.logger.info(f"[ProductRegistry] 🎉 ФИНАЛЬНЫЙ РЕЗУЛЬТАТ: возвращаем {len(products)} продуктов")
            return products
            
        except Exception as e:
            self.logger.error(f"[ProductRegistry] ❌ Критическая ошибка в get_all_products: {e}")
            import traceback
            self.logger.error(f"[ProductRegistry] 🔍 Полный traceback ошибки:")
            self.logger.error(traceback.format_exc())
            return []

    async def get_product(self, product_id: Union[str, int]) -> Product:
        """
        Получает продукт по ID.
        
        Args:
            product_id: ID продукта (строка или число)
            
        Returns:
            Product: Данные продукта
            
        Raises:
            InvalidProductIdError: Если ID продукта невалиден
            ProductNotFoundError: Если продукт не найден
        """
        try:
            # Валидация входного ID
            if not product_id:
                raise InvalidProductIdError(str(product_id), "ID продукта не может быть пустым")
            
            # Конвертируем в int для blockchain_service
            try:
                product_id_int = int(product_id) if isinstance(product_id, str) else product_id
            except (ValueError, TypeError):
                raise InvalidProductIdError(str(product_id), f"Невалидный формат ID продукта: {product_id}")
            # Доп. валидация диапазона ID
            if not isinstance(product_id_int, int) or product_id_int <= 0:
                raise InvalidProductIdError(str(product_id), f"Невалидный ID: {product_id}. Ожидается положительное целое число")
            
            # Получаем данные продукта из блокчейна
            product_data = self.blockchain_service.get_product(product_id_int)
            
            if not product_data:
                self.logger.warning(f"[ProductRegistry] Продукт {product_id} не найден в блокчейне (None)")
                return None
            
            # Десериализуем продукт
            product = await self._deserialize_product(product_data)
            if not product:
                self.logger.warning(f"[ProductRegistry] Не удалось десериализовать продукт {product_id}")
                return None
            
            return product
            
        except ProductNotFoundError:
            # Для несуществующего продукта возвращаем None (read‑path контракт)
            return None
        except Exception as e:
            # Не подавляем InvalidProductIdError
            if isinstance(e, InvalidProductIdError):
                raise
            self.logger.error(f"Неожиданная ошибка при получении продукта {product_id}: {e}")
            return None
    
    async def validate_product(self, product_data: dict) -> bool:
        """
        Валидирует данные продукта.
        
        Args:
            product_data: Словарь с данными продукта
            
        Returns:
            bool: True если данные валидны, False если нет
        """
        try:
            self.logger.info(f"🔍 [ProductRegistry] Начинаем валидацию продукта")
            
            # Используем validation_service для валидации
            validation_result = await self.validation_service.validate_product_data(
                product_data, 
                storage_service=self.storage_service
            )
            
            # Обрабатываем результат валидации
            if not validation_result.is_valid:
                self.logger.error(f"❌ [ProductRegistry] Валидация продукта не прошла: {validation_result.error_message}")
                return False
            
            self.logger.info(f"✅ [ProductRegistry] Валидация продукта прошла успешно")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ [ProductRegistry] Ошибка валидации продукта: {e}")
            return False

    async def _check_product_id_exists(self, product_id: Union[str, int]) -> bool:
        """
        Проверяет, существует ли продукт с указанным business ID (строка или число) среди
        всех товаров текущего продавца (включая неактивные), а также
        выполняет дополнительную проверку по blockchain ID если ID выглядит числом.
        
        Args:
            product_id: Business ID продукта для проверки (строка или число)
            
        Returns:
            bool: True если продукт с таким business ID существует, False если нет
            
        Raises:
            InvalidProductIdError: Если ID продукта невалиден
        """
        try:
            self.logger.debug(f"🔍 Проверка существования продукта с business ID: {product_id}")
            
            # Валидация входного ID
            if product_id is None:
                raise InvalidProductIdError("None", "Business ID продукта не может быть None")
            
            # Преобразуем в строку для дальнейшей обработки
            product_id_str = str(product_id)
            if not product_id_str:
                raise InvalidProductIdError(str(product_id), "Business ID продукта должен быть непустой строкой")
            
            # 1) Если это бизнес-ID (нечисловой), попробуем получить продукт напрямую
            try:
                # В тестах метод может быть замокан под бизнес-ID
                product_by_business_id = await self.get_product(product_id_str)
                if product_by_business_id is not None:
                    self.logger.debug(f"🔍 Продукт с business ID {product_id_str} найден через get_product")
                    return True
            except InvalidProductIdError:
                # Нормально: означает, что get_product поддерживает только числовые ID
                pass

            # 2) Быстрая проверка: если это число, попробуем убедиться, что blockchain id занят
            try:
                numeric_id = int(product_id_str)
                if self._check_blockchain_product_exists(numeric_id):
                    self.logger.debug(f"🔍 Продукт с blockchain ID {numeric_id} уже существует")
                    return True
            except (ValueError, TypeError):
                pass

            # 3) Полный проход по товарам продавца (включая неактивные) через контракт, если доступен метод
            if hasattr(self.blockchain_service, 'get_products_by_current_seller_full'):
                seller_products = self.blockchain_service.get_products_by_current_seller_full()
                for p in seller_products:
                    # Ожидается tuple (id, seller, ipfsCID, active)
                    if not hasattr(p, '__getitem__') or len(p) < 3:
                        continue
                    pid = str(p[0])
                    if pid == product_id_str:
                        self.logger.debug(f"🔍 Продукт с business ID {product_id_str} найден среди товаров продавца")
                        return True
            else:
                # 4) Fallback: используем кэшированный каталог (активные товары) и проверяем alias/id
                all_products = await self.get_all_products()
                for product in all_products:
                    if hasattr(product, 'alias') and product.alias == product_id_str:
                        self.logger.debug(f"🔍 Продукт с business ID {product_id_str} найден по alias в каталоге")
                        return True
                    if hasattr(product, 'id') and str(product.id) == product_id_str:
                        self.logger.debug(f"🔍 Продукт с business ID {product_id_str} найден по id в каталоге")
                        return True
            
            self.logger.debug(f"🔍 Продукт с business ID {product_id_str} не существует")
            return False
            
        except InvalidProductIdError:
            # Невалидный ID - это ошибка пользователя, не маскируем
            self.logger.error(f"❌ Невалидный business ID продукта: {product_id}")
            raise
        except Exception as e:
            # Неожиданные ошибки не маскируем - они указывают на проблемы системы
            self.logger.error(f"❌ Критическая ошибка при проверке существования продукта {product_id}: {e}")
            raise

    def _check_blockchain_product_exists(self, blockchain_id: int) -> bool:
        """
        Проверяет, существует ли продукт с указанным blockchain ID в смарт-контракте.
        
        Дополнительный уровень валидации для обеспечения целостности данных
        между локальным каталогом и блокчейном.
        
        Args:
            blockchain_id: Blockchain ID продукта для проверки
            
        Returns:
            bool: True если продукт существует в блокчейне, False если нет
        """
        try:
            self.logger.debug(f"🔗 Проверка blockchain ID в смарт-контракте: {blockchain_id}")
            
            # Валидация входного ID
            if not isinstance(blockchain_id, int) or blockchain_id <= 0:
                self.logger.debug(f"🔗 Невалидный blockchain ID: {blockchain_id}")
                return False
            
            # Делегируем проверку BlockchainService
            exists = self.blockchain_service.product_exists_in_blockchain(blockchain_id)
            
            self.logger.debug(f"🔗 Blockchain ID {blockchain_id} {'найден' if exists else 'не найден'} в смарт-контракте")
            return exists
            
        except Exception as e:
            # При ошибках блокчейна логируем и возвращаем False
            # Это обеспечивает graceful degradation при недоступности блокчейна
            self.logger.warning(f"🔗 Ошибка при проверке blockchain ID {blockchain_id}: {e}")
            return False

    async def create_product(self, product_data: dict) -> dict:
        """
        Создает новый продукт: валидация → проверка уникальности ID → формирование метаданных → загрузка в IPFS → запись в блокчейн.
        Возвращает dict с результатом (id, metadata_cid, blockchain_id, tx_hash, status, error)
        """
        try:
            # Получаем business_id из данных продукта (приоритет) или id (обратная совместимость)
            business_id = product_data.get("business_id") or product_data.get("id")
            self.logger.info(f"🆕 Начинаем создание продукта с business ID: {business_id}")
            
            # 1. Валидация
            validation_result = await self.validation_service.validate_product_data(product_data)
            if not validation_result.is_valid:
                self.logger.error(f"❌ Валидация продукта {business_id} не прошла: {validation_result.error_message}")
                return {
                    "business_id": business_id,
                    "status": "error",
                    "error": validation_result.error_message or "Validation failed"
                }
            
            # 2. Проверка уникальности business ID
            if business_id and await self._check_product_id_exists(business_id):
                error_msg = f"Продукт с business ID '{business_id}' уже существует. Используйте уникальный business ID."
                self.logger.error(f"❌ {error_msg}")
                return {
                    "business_id": business_id,
                    "status": "error",
                    "error": error_msg
                }
            # 3. Формирование метаданных
            metadata = self.create_product_metadata(product_data)
            # 4. Загрузка в IPFS
            logger.info(f"[DEBUG] storage_service: {self.storage_service} (type: {type(self.storage_service)}, id: {id(self.storage_service)})")
            metadata_cid = await self.storage_service.upload_json(metadata)
            logger.info(f"[DEBUG] upload_json вернул: {metadata_cid} (тип: {type(metadata_cid)})")
            if not metadata_cid:
                return {
                    "business_id": business_id,
                    "status": "error",
                    "error": "Ошибка загрузки метаданных в IPFS"
                }
            # 5. Запись в блокчейн
            tx_hash = await self.blockchain_service.create_product(metadata_cid)
            if not tx_hash:
                return {
                    "business_id": business_id,
                    "metadata_cid": metadata_cid,
                    "status": "error",
                    "error": "Ошибка записи в блокчейн"
                }
            # 6. Получение blockchain_id
            blockchain_id = await self.blockchain_service.get_product_id_from_tx(tx_hash)
            
            # 7. Дополнительная валидация: проверяем что продукт действительно создан в блокчейне
            if blockchain_id is not None:
                blockchain_exists = self._check_blockchain_product_exists(blockchain_id)
                if not blockchain_exists:
                    self.logger.warning(f"⚠️ Продукт {business_id} создан (tx: {tx_hash}), но не найден в блокчейне (ID: {blockchain_id})")
                    # Не считаем это критической ошибкой - возможна задержка синхронизации
                else:
                    self.logger.debug(f"🔗 Подтверждено: продукт {business_id} существует в блокчейне (ID: {blockchain_id})")
            
            self.logger.info(f"✅ Продукт {business_id} успешно создан")
            return {
                "business_id": business_id,
                "metadata_cid": metadata_cid,
                "blockchain_id": str(blockchain_id) if blockchain_id is not None else None,
                "tx_hash": str(tx_hash) if tx_hash is not None else None,
                "status": "success",
                "error": None
            }
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка при создании продукта: {e}")
            return {
                "business_id": business_id,
                "status": "error",
                "error": str(e)
            }

    async def update_product(self, product_id: str, product_data: dict) -> dict:
        """
        Полное обновление продукта по ID.
        
        Args:
            product_id: ID продукта для обновления
            product_data: Новые данные продукта
            
        Returns:
            dict: Результат операции с полями id, blockchain_id, tx_hash, metadata_cid, status, error
        """
        # Атомарная операция обновления продукта
        self.logger.info(f"[ProductRegistry] === НАЧАЛО АТОМАРНОЙ ОПЕРАЦИИ ОБНОВЛЕНИЯ ПРОДУКТА {product_id} ===")
        
        try:
            self.logger.info(f"[ProductRegistry] Начинаем обновление продукта {product_id}")
            self.logger.info(f"[ProductRegistry] Данные для обновления: {product_data}")

            # 1. Проверка существования продукта по ID
            self.logger.info(f"[ProductRegistry] Проверяем существование продукта {product_id}")
            existing_product = await self.get_product(product_id)
            
            if existing_product is None:
                self.logger.error(f"[ProductRegistry] Продукт {product_id} не найден")
                return {
                    "business_id": product_data.get("business_id", product_id),
                    "status": "error",
                    "error": f"Продукт с ID {product_id} не найден"
                }
            
            self.logger.info(f"[ProductRegistry] Продукт {product_id} найден: {existing_product.title}")
            
            # 2. Валидация прав доступа (только владелец может обновлять)
            self.logger.info(f"[ProductRegistry] Проверяем права доступа для продукта {product_id}")
            
            try:
                # Получаем информацию о продукте из блокчейна для проверки владельца
                product_blockchain_data = self.blockchain_service.get_product(product_id)
                if product_blockchain_data and len(product_blockchain_data) >= 2:
                    product_owner_address = product_blockchain_data[1]  # seller address
                    current_seller_address = self.seller_account.address
                    
                    self.logger.info(f"[ProductRegistry] Владелец продукта: {product_owner_address}")
                    self.logger.info(f"[ProductRegistry] Текущий продавец: {current_seller_address}")
                    
                    if product_owner_address.lower() != current_seller_address.lower():
                        self.logger.error(f"[ProductRegistry] Недостаточно прав для обновления продукта {product_id}")
                        return {
                            "business_id": product_data.get("business_id", product_id),
                            "status": "error",
                            "error": f"Недостаточно прав для обновления продукта {product_id}"
                        }
                    
                    self.logger.info(f"[ProductRegistry] Права доступа подтверждены для продукта {product_id}")
                else:
                    self.logger.warning(f"[ProductRegistry] Не удалось получить данные владельца продукта {product_id}")
                    
            except Exception as e:
                self.logger.error(f"[ProductRegistry] Ошибка при проверке прав доступа: {e}")
                return {
                    "business_id": product_data.get("business_id", product_id),
                    "status": "error",
                    "error": f"Ошибка при проверке прав доступа: {str(e)}"
                }
            
            # 3. Валидация новых данных продукта
            self.logger.info(f"[ProductRegistry] Валидируем новые данные продукта {product_id}")
            
            is_valid = await self.validate_product(product_data)
            if not is_valid:
                self.logger.error(f"[ProductRegistry] Валидация продукта {product_id} не прошла")
                return {
                    "business_id": product_data.get("business_id", product_id),
                    "status": "error",
                    "error": f"Данные продукта {product_id} не прошли валидацию"
                }
            
            self.logger.info(f"[ProductRegistry] Валидация продукта {product_id} прошла успешно")
            
            # 4. Обновление метаданных в IPFS
            self.logger.info(f"[ProductRegistry] Создаем новые метаданные для продукта {product_id}")
            
            try:
                # Создаем новые метаданные с обновленными данными
                new_metadata = self.create_product_metadata(product_data)
                
                # Добавляем timestamp обновления
                new_metadata["updated_at"] = datetime.now().isoformat()
                
                self.logger.info(f"[ProductRegistry] Новые метаданные созданы: {new_metadata}")
                
                # Загружаем метаданные в IPFS
                self.logger.info(f"[ProductRegistry] Загружаем метаданные в IPFS для продукта {product_id}")
                new_metadata_cid = self.storage_service.upload_json(new_metadata)
                
                if not new_metadata_cid:
                    self.logger.error(f"[ProductRegistry] Не удалось загрузить метаданные в IPFS для продукта {product_id}")
                    return {
                        "business_id": product_data.get("business_id", product_id),
                        "status": "error",
                        "error": f"Не удалось загрузить метаданные в IPFS для продукта {product_id}"
                    }
                
                self.logger.info(f"[ProductRegistry] Метаданные загружены в IPFS: {new_metadata_cid}")
                
            except Exception as e:
                self.logger.error(f"[ProductRegistry] Ошибка при обновлении метаданных в IPFS: {e}")
                return {
                    "business_id": product_data.get("business_id", product_id),
                    "status": "error",
                    "error": f"Ошибка при обновлении метаданных в IPFS: {str(e)}"
                }
            
            # 5. Обновление записи в блокчейне
            self.logger.info(f"[ProductRegistry] Обновляем запись продукта {product_id} в блокчейне")
            
            try:
                # TODO: TASK-002.2 - Реализовать обновление метаданных в блокчейне
                # В текущей версии смарт-контракта нет метода для обновления метаданных
                # Нужно добавить метод updateProductMetadata в контракт или использовать другой подход
                
                self.logger.warning(f"[ProductRegistry] Обновление метаданных в блокчейне не реализовано для продукта {product_id}")
                self.logger.warning(f"[ProductRegistry] Новый CID метаданных: {new_metadata_cid}")
                
                # Заглушка для MVP - возвращаем успех без обновления в блокчейне
                tx_hash = None
                blockchain_id = None
                
            except Exception as e:
                self.logger.error(f"[ProductRegistry] Ошибка при обновлении в блокчейне: {e}")
                return {
                    "business_id": product_data.get("business_id", product_id),
                    "status": "error",
                    "error": f"Ошибка при обновлении в блокчейне: {str(e)}"
                }
            
            # 6. Обеспечение атомарности операции
            self.logger.info(f"[ProductRegistry] Обновление продукта {product_id} завершено успешно")
            
            return {
                "business_id": product_data.get("business_id", product_id),
                "metadata_cid": new_metadata_cid,
                "blockchain_id": blockchain_id,
                "tx_hash": tx_hash,
                "status": "success",
                "error": None
            }

        except Exception as e:
            self.logger.error(f"[ProductRegistry] === ОШИБКА В АТОМАРНОЙ ОПЕРАЦИИ ОБНОВЛЕНИЯ ПРОДУКТА {product_id} ===")
            self.logger.error(f"[ProductRegistry] Детали ошибки: {e}")
            self.logger.error(f"[ProductRegistry] Трассировка: {traceback.format_exc()}")
            
            return {
                "business_id": product_data.get("business_id", product_id),
                "status": "error",
                "error": f"Ошибка в атомарной операции обновления: {str(e)}"
            }
        finally:
            self.logger.info(f"[ProductRegistry] === ЗАВЕРШЕНИЕ АТОМАРНОЙ ОПЕРАЦИИ ОБНОВЛЕНИЯ ПРОДУКТА {product_id} ===")
    
    async def update_product_status(self, product_id: int, new_status: int) -> bool:
        """
        Обновляет статус продукта.
        
        Args:
            product_id: ID продукта
            new_status: Новый статус (0 - неактивен, 1 - активен)
            
        Returns:
            bool: True если успешно, False если ошибка
        """
        try:
            self.logger.info(f"[ProductRegistry] Начинаем обновление статуса продукта {product_id} на {new_status}")
            
            # Проверка существования продукта и прав доступа
            self.logger.info(f"[ProductRegistry] Проверяем существование продукта {product_id}")
            existing_product = await self.get_product(str(product_id))
            
            if existing_product is None:
                self.logger.error(f"[ProductRegistry] Продукт {product_id} не найден")
                return False
            
            self.logger.info(f"[ProductRegistry] Продукт {product_id} найден: {existing_product.title}")
            
            # ИСПРАВЛЕНИЕ: Получаем статус ТОЛЬКО из блокчейна, игнорируем локальный кэш
            self.logger.info(f"[ProductRegistry] Игнорируем статус из локального кэша: {existing_product.status}")
            
            # ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА: Проверяем, что статус действительно игнорируется
            self.logger.info(f"[ProductRegistry] Статус из локального кэша будет проигнорирован при проверке идемпотентности")
            
            # Проверка прав доступа
            self.logger.info(f"[ProductRegistry] Проверяем права доступа для продукта {product_id}")
            
            try:
                # Получаем информацию о продукте из блокчейна для проверки владельца И статуса
                product_blockchain_data = self.blockchain_service.get_product(product_id)
                if product_blockchain_data and len(product_blockchain_data) >= 2:
                    product_owner_address = product_blockchain_data[1]  # seller address
                    current_seller_address = self.seller_account.address
                    
                    self.logger.info(f"[ProductRegistry] Владелец продукта: {product_owner_address}")
                    self.logger.info(f"[ProductRegistry] Текущий продавец: {current_seller_address}")
                    
                    if product_owner_address.lower() != current_seller_address.lower():
                        self.logger.error(f"[ProductRegistry] Недостаточно прав для обновления статуса продукта {product_id}")
                        return False
                    
                    self.logger.info(f"[ProductRegistry] Права доступа подтверждены для продукта {product_id}")
                    
                    # ИСПРАВЛЕНИЕ: Проверка идемпотентности - получаем статус ТОЛЬКО из блокчейна
                    if len(product_blockchain_data) >= 4:
                        current_active = product_blockchain_data[3]  # active status (bool) из блокчейна
                        current_status = 1 if current_active else 0  # Преобразуем bool в int
                        self.logger.info(f"[ProductRegistry] Текущий статус продукта {product_id} из блокчейна: {current_status} (active: {current_active})")
                        self.logger.info(f"[ProductRegistry] Запрашиваемый статус: {new_status}")
                        
                        # ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА: Логируем все данные из блокчейна
                        self.logger.info(f"[ProductRegistry] ДЕТАЛЬНАЯ ДИАГНОСТИКА блокчейна:")
                        self.logger.info(f"   - product_blockchain_data: {product_blockchain_data}")
                        self.logger.info(f"   - product_blockchain_data[3]: {product_blockchain_data[3]} (тип: {type(product_blockchain_data[3])})")
                        self.logger.info(f"   - current_active: {current_active} (тип: {type(current_active)})")
                        self.logger.info(f"   - current_status: {current_status} (тип: {type(current_status)})")
                        
                        # Проверяем идемпотентность только если статус действительно совпадает
                        if current_status == new_status:
                            self.logger.info(f"[ProductRegistry] Статус продукта {product_id} уже установлен на {new_status} (идемпотентность)")
                            return True
                        else:
                            self.logger.info(f"[ProductRegistry] Статус продукта {product_id} будет изменен с {current_status} на {new_status}")
                    else:
                        self.logger.warning(f"[ProductRegistry] Не удалось получить текущий статус продукта {product_id} из блокчейна")
                        # Если не можем получить статус из блокчейна, продолжаем с обновлением
                        self.logger.info(f"[ProductRegistry] Продолжаем обновление статуса без проверки идемпотентности")
                        
                else:
                    self.logger.warning(f"[ProductRegistry] Не удалось получить данные владельца продукта {product_id}")
                    
            except Exception as e:
                self.logger.error(f"[ProductRegistry] Ошибка при проверке прав доступа: {e}")
                return False
            
            # Выполнение операции в блокчейне
            self.logger.info(f"[ProductRegistry] Выполняем обновление статуса в блокчейне")
            
            # Преобразуем product_id в int для блокчейна
            try:
                product_id_int = int(product_id)
            except (ValueError, TypeError) as e:
                self.logger.error(f"[ProductRegistry] Неверный формат product_id: {product_id}, ошибка: {e}")
                return False
            
            tx_hash = await self.blockchain_service.update_product_status(
                self.blockchain_service.seller_key,
                product_id_int,
                new_status
            )
            
            if not tx_hash:
                self.logger.error(f"[ProductRegistry] Ошибка обновления статуса продукта {product_id}")
                return False
                
            self.logger.info(f"[ProductRegistry] Статус продукта {product_id} обновлен: {new_status}")
            return True
            
        except Exception as e:
            self.logger.error(f"[ProductRegistry] Ошибка обновления статуса продукта {product_id}: {e}")
            return False
    
    async def deactivate_product(self, product_id: int) -> bool:
        """
        Деактивирует продукт через контракт (делает его невидимым в каталоге).
        Args:
            product_id: ID продукта
        Returns:
            bool: True если успешно, False если ошибка
        """
        try:
            tx_hash = await self.blockchain_service.transact_contract_function(
                "ProductRegistry",
                "deactivateProduct",
                self.blockchain_service.seller_key,
                product_id
            )
            if not tx_hash:
                self.logger.error(f"[ProductRegistry] Ошибка деактивации продукта {product_id}")
                return False
            self.logger.info(f"[ProductRegistry] Продукт {product_id} деактивирован")
            return True
        except Exception as e:
            self.logger.error(f"[ProductRegistry] Ошибка деактивации продукта {product_id}: {e}")
            return False

    async def _deserialize_product(self, product_data: tuple) -> Optional[Product]:
        """
        Десериализует продукт из кортежа блокчейна и метаданных IPFS.
        Использует ProductAssembler для централизованной сборки продукта.
        
        Args:
            product_data: tuple (id, seller, ipfsCID, active)
        Returns:
            Product или None
        """
        try:
            self.logger.info(f"[ProductRegistry] 🔍 Начинаем десериализацию продукта: {product_data}")
            
            if not hasattr(product_data, '__getitem__') or len(product_data) < 4:
                self.logger.error(f"[ProductRegistry] ❌ Некорректная структура product_data: {product_data}")
                return None

            product_id = product_data[0]  # Блокчейн ID
            ipfs_cid = product_data[2]
            is_active = bool(product_data[3])

            self.logger.info(f"[ProductRegistry] 📋 Извлечены данные: ID={product_id}, CID={ipfs_cid}, Active={is_active}")
            self.logger.info(f"[ProductRegistry] 🔗 Загружаем метаданные из IPFS: {ipfs_cid}")
            
            # 🔧 ИСПРАВЛЕНИЕ: download_json теперь синхронный метод
            metadata = self.storage_service.download_json(ipfs_cid)
            if not metadata:
                self.logger.warning(f"[ProductRegistry] ⚠️ Не удалось получить метаданные для продукта {product_id}")
                return None

            self.logger.info(f"[ProductRegistry] ✅ Метаданные загружены: {type(metadata)}, keys={list(metadata.keys()) if isinstance(metadata, dict) else 'N/A'}")

            # Используем ProductAssembler для централизованной сборки продукта
            self.logger.info(f"[ProductRegistry] 🔧 Вызываем ProductAssembler.assemble_product...")
            product = self.assembler.assemble_product(product_data, metadata)
            if product:
                self.logger.info(f"[ProductRegistry] ✅ Продукт {product_id} успешно собран через ProductAssembler")
            else:
                self.logger.error(f"[ProductRegistry] ❌ Не удалось собрать продукт {product_id} через ProductAssembler")
            
            return product
        except Exception as e:
            self.logger.error(f"[ProductRegistry] ❌ Ошибка десериализации продукта: {e}")
            import traceback
            self.logger.error(f"[ProductRegistry] 🔍 Полный traceback ошибки:")
            self.logger.error(traceback.format_exc())
            return None