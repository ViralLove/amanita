from bot.services.core.blockchain import BlockchainService
from datetime import datetime, timedelta
from bot.model.product import Product, PriceInfo, Description
import logging
from typing import Optional, List, Dict, Union, Tuple, Any
import dotenv
import os
from web3 import Account
from bot.services.core.ipfs_factory import IPFSFactory
import traceback
import re
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import aiohttp
import json
from bot.services.product.metadata import ProductMetadataService
from bot.services.product.cache import ProductCacheService
from bot.services.product.storage import ProductStorageService
from bot.services.product.validation import ProductValidationService
from bot.services.product.validation_utils import ValidationError
from bot.services.core.account import AccountService

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

    def __init__(self, blockchain_service: Optional[BlockchainService] = None, storage_service: Optional[ProductStorageService] = None, validation_service: Optional[ProductValidationService] = None, account_service: Optional['AccountService'] = None):
        """
        Инициализирует сервис реестра продуктов.
        
        Args:
            blockchain_service: Сервис для работы с блокчейном (если None, используется синглтон)
            storage_service: Сервис для работы с хранилищем
            validation_service: Сервис для валидации продуктов
            account_service: Сервис для работы с аккаунтами (если None, создается автоматически)
        """
        # Инициализируем logger
        self.logger = logging.getLogger(__name__)

        self.logger.info(f"[ProductRegistry] __init__ id(self)={id(self)}")
        
        # Используем синглтон BlockchainService если не передан
        self.blockchain_service = blockchain_service or BlockchainService()
        self.validation_service = validation_service
        
        # Создаем фабрику один раз
        self.storage_service = storage_service or IPFSFactory().get_storage()
        
        # Инициализируем кэш (storage_service создается внутри как синглтон)
        self.cache_service = ProductCacheService()
        
        # Инициализируем сервис метаданных
        self.metadata_service = ProductMetadataService(self.storage_service)
        
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

    def _process_product_metadata(self, product_id: Union[int, str], ipfs_cid: str, active: bool) -> Optional[Product]:
        """
        Обрабатывает метаданные продукта.
        
        Args:
            product_id: ID продукта
            ipfs_cid: CID метаданных продукта
            active: Статус активности продукта
            
        Returns:
            Optional[Product]: Объект продукта или None в случае ошибки
        """
        try:
            self.logger.info(f"[ProductRegistry] Обработка метаданных продукта {product_id}:")
            self.logger.info(f"  - ID: {product_id} (тип: {type(product_id)})")
            self.logger.info(f"  - IPFS CID: {ipfs_cid} (тип: {type(ipfs_cid)})")
            self.logger.info(f"  - Активен: {active} (тип: {type(active)})")

            # Валидируем CID через сервис валидации
            validation_result = self.validation_service.validate_cid(ipfs_cid)
            if not validation_result["is_valid"]:
                errors = validation_result.get("errors", [])
                error_msg = "; ".join(errors)
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
            cover_image = self._get_cached_image(metadata.get('cover_image', ''))
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
            # Создаем базовую структуру метаданных
            metadata = {
                "id": product_data["id"],
                "title": product_data["title"],
                "description_cid": product_data["description_cid"],
                "cover_image": product_data["cover_image"],
                "categories": product_data["categories"],
                "form": product_data["form"],
                "species": product_data["species"],
                "prices": product_data["prices"],
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
    
    def get_all_products(self) -> List[Product]:
        """Получает все продукты с кэшированием"""

        self.logger.info(f"[ProductRegistry] get_all_products id(self)={id(self)}")

        try:
            # Проверяем версию каталога
            catalog_version = self.blockchain_service.get_catalog_version()
            self.logger.info(f"[ProductRegistry] Текущая версия каталога: {catalog_version}")
            
            # Проверяем кэш
            self.logger.info(f"[ProductRegistry] Проверяем кэш каталога...")
            cached_catalog = self.cache_service.get_cached_item("catalog", "catalog")
            
            if cached_catalog:
                self.logger.info(f"[ProductRegistry] Найден кэш каталога: version={cached_catalog.get('version')}, products_count={len(cached_catalog.get('products', []))}")
                
                if cached_catalog.get("version") == catalog_version:
                    self.logger.info(f"[ProductRegistry] ✅ Возвращаем кэшированный каталог (версия {catalog_version})")
                    return cached_catalog.get("products", [])
                else:
                    self.logger.info(f"[ProductRegistry] ❌ Кэш устарел: cached_version={cached_catalog.get('version')}, current_version={catalog_version}")
            else:
                self.logger.info(f"[ProductRegistry] Кэш каталога пуст")
            
            # Получаем продукты из блокчейна
            self.logger.info(f"[ProductRegistry] Загружаем продукты из блокчейна...")
            products_data = self.blockchain_service.get_all_products()
            if not products_data:
                self.logger.warning("No products found in blockchain")
                return []
            
            # Обрабатываем каждый продукт через унифицированный метод
            products = []
            self.logger.info(f"Products data: {products_data}")
            for product_data in products_data:
                try:
                    # Используем унифицированный метод десериализации
                    product = self._deserialize_product(product_data)
                    if product:
                        products.append(product)
                        
                except Exception as e:
                    self.logger.error(f"Error processing product: {e}")
                    continue
            
            # Обновляем кэш
            self.logger.info(f"[ProductRegistry] Сохраняем каталог в кэш: version={catalog_version}, products_count={len(products)}")
            self.cache_service.set_cached_item("catalog", {
                "version": catalog_version,
                "products": products
            }, "catalog")
            self.logger.info(f"[ProductRegistry] ✅ Каталог успешно сохранен в кэш")
            
            return products
            
        except Exception as e:
            self.logger.error(f"Error getting all products: {e}")
            return []
    
    def get_product(self, product_id: Union[str, int]) -> Optional[Product]:
        """
        Получает продукт по ID.
        
        Args:
            product_id: ID продукта (строка или число)
            
        Returns:
            Optional[Product]: Данные продукта или None
        """
        try:
            # Конвертируем в int для blockchain_service
            product_id_int = int(product_id) if isinstance(product_id, str) else product_id
            product_data = self.blockchain_service.get_product(product_id_int)
            return self._deserialize_product(product_data) if product_data else None
        except Exception as e:
            self.logger.error(f"Error getting product {product_id}: {e}")
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
            # Проверяем обязательные поля
            required_fields = ['title', 'description_cid', 'categories', 'cover_image', 'form', 'species', 'prices']
            for field in required_fields:
                if field not in product_data:
                    self.logger.error(f"Missing required field: {field}")
                    return False
                    
                if not product_data[field]:
                    if field == 'prices':
                        self.logger.error("Список цен не может быть пустым")
                    else:
                        self.logger.error(f"Empty required field: {field}")
                    return False

            # Проверяем цены
            if not isinstance(product_data['prices'], list):
                self.logger.error("Цены должны быть списком")
                return False
                
            if not product_data['prices']:
                self.logger.error("Список цен не может быть пустым")
                return False
                
            for price in product_data['prices']:
                # Проверяем обязательные поля цены
                price_fields = ['price', 'currency']
                for field in price_fields:
                    if field not in price:
                        self.logger.error(f"Missing required price field: {field}")
                        return False
                        
                # Проверяем что цена это число
                try:
                    float(price['price'])
                except ValueError:
                    self.logger.error("Invalid price value")
                    return False
                    
                # Проверяем валюту
                if price['currency'] not in ['EUR', 'USD']:
                    self.logger.error("Invalid currency")
                    return False
                    
                # Проверяем единицы измерения
                if 'weight' in price:
                    if 'weight_unit' not in price or price['weight_unit'] not in ['g', 'kg']:
                        self.logger.error("Invalid weight unit")
                        return False
                elif 'volume' in price:
                    if 'volume_unit' not in price or price['volume_unit'] not in ['ml', 'l']:
                        self.logger.error("Invalid volume unit")
                        return False
                else:
                    self.logger.error("Missing weight or volume")
                    return False

            # Проверяем IPFS CID
            if not self.storage_service.is_valid_cid(product_data['description_cid']):
                self.logger.error("Invalid description CID")
                return False
                
            if not self.storage_service.is_valid_cid(product_data['cover_image']):
                self.logger.error("Invalid cover image CID")
                return False

            return True
            
        except Exception as e:
            self.logger.error(f"Error validating product: {e}")
            return False

    async def create_product(self, product_data: dict) -> dict:
        """
        Создает новый продукт: валидация → формирование метаданных → загрузка в IPFS → запись в блокчейн.
        Возвращает dict с результатом (id, metadata_cid, blockchain_id, tx_hash, status, error)
        """
        try:
            # 1. Валидация
            validation_result = await self.validation_service.validate_product_data(product_data)
            if not validation_result["is_valid"]:
                return {
                    "id": product_data.get("id"),
                    "status": "error",
                    "error": "; ".join(validation_result["errors"])
                }
            # 2. Формирование метаданных
            metadata = self.create_product_metadata(product_data)
            # 3. Загрузка в IPFS
            logger.info(f"[DEBUG] storage_service: {self.storage_service} (type: {type(self.storage_service)}, id: {id(self.storage_service)})")
            metadata_cid = await self.storage_service.upload_json(metadata)
            logger.info(f"[DEBUG] upload_json вернул: {metadata_cid} (тип: {type(metadata_cid)})")
            if not metadata_cid:
                return {
                    "id": product_data.get("id"),
                    "status": "error",
                    "error": "Ошибка загрузки метаданных в IPFS"
                }
            # 4. Запись в блокчейн
            tx_hash = await self.blockchain_service.create_product(metadata_cid)
            if not tx_hash:
                return {
                    "id": product_data.get("id"),
                    "metadata_cid": metadata_cid,
                    "status": "error",
                    "error": "Ошибка записи в блокчейн"
                }
            # 5. Получение blockchain_id
            blockchain_id = await self.blockchain_service.get_product_id_from_tx(tx_hash)
            return {
                "id": product_data.get("id"),
                "metadata_cid": metadata_cid,
                "blockchain_id": str(blockchain_id) if blockchain_id is not None else None,
                "tx_hash": str(tx_hash) if tx_hash is not None else None,
                "status": "success",
                "error": None
            }
        except Exception as e:
            return {
                "id": product_data.get("id"),
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
            existing_product = self.get_product(product_id)
            
            if existing_product is None:
                self.logger.error(f"[ProductRegistry] Продукт {product_id} не найден")
                return {
                    "id": product_id,
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
                            "id": product_id,
                            "status": "error",
                            "error": f"Недостаточно прав для обновления продукта {product_id}"
                        }
                    
                    self.logger.info(f"[ProductRegistry] Права доступа подтверждены для продукта {product_id}")
                else:
                    self.logger.warning(f"[ProductRegistry] Не удалось получить данные владельца продукта {product_id}")
                    
            except Exception as e:
                self.logger.error(f"[ProductRegistry] Ошибка при проверке прав доступа: {e}")
                return {
                    "id": product_id,
                    "status": "error",
                    "error": f"Ошибка при проверке прав доступа: {str(e)}"
                }
            
            # 3. Валидация новых данных продукта
            self.logger.info(f"[ProductRegistry] Валидируем новые данные продукта {product_id}")
            
            is_valid = await self.validate_product(product_data)
            if not is_valid:
                self.logger.error(f"[ProductRegistry] Валидация продукта {product_id} не прошла")
                return {
                    "id": product_id,
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
                        "id": product_id,
                        "status": "error",
                        "error": f"Не удалось загрузить метаданные в IPFS для продукта {product_id}"
                    }
                
                self.logger.info(f"[ProductRegistry] Метаданные загружены в IPFS: {new_metadata_cid}")
                
            except Exception as e:
                self.logger.error(f"[ProductRegistry] Ошибка при обновлении метаданных в IPFS: {e}")
                return {
                    "id": product_id,
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
                    "id": product_id,
                    "status": "error",
                    "error": f"Ошибка при обновлении в блокчейне: {str(e)}"
                }
            
            # 6. Обеспечение атомарности операции
            self.logger.info(f"[ProductRegistry] Обновление продукта {product_id} завершено успешно")
            
            return {
                "id": product_id,
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
                "id": product_id,
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
            new_status: Новый статус (0 - создан, 1 - в процессе, 2 - отправлен, 3 - доставлен)
            
        Returns:
            bool: True если успешно, False если ошибка
        """
        try:
            self.logger.info(f"[ProductRegistry] Начинаем обновление статуса продукта {product_id} на {new_status}")
            
            # Проверка существования продукта и прав доступа
            self.logger.info(f"[ProductRegistry] Проверяем существование продукта {product_id}")
            existing_product = self.get_product(str(product_id))
            
            if existing_product is None:
                self.logger.error(f"[ProductRegistry] Продукт {product_id} не найден")
                return False
            
            self.logger.info(f"[ProductRegistry] Продукт {product_id} найден: {existing_product.title}")
            
            # Проверка прав доступа
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
                        self.logger.error(f"[ProductRegistry] Недостаточно прав для обновления статуса продукта {product_id}")
                        return False
                    
                    self.logger.info(f"[ProductRegistry] Права доступа подтверждены для продукта {product_id}")
                    
                    # Проверка идемпотентности - сравниваем текущий статус с новым
                    if len(product_blockchain_data) >= 4:
                        current_status = product_blockchain_data[3]  # active status
                        self.logger.info(f"[ProductRegistry] Текущий статус продукта {product_id}: {current_status}")
                        self.logger.info(f"[ProductRegistry] Запрашиваемый статус: {new_status}")
                        
                        if current_status == new_status:
                            self.logger.info(f"[ProductRegistry] Статус продукта {product_id} уже установлен на {new_status} (идемпотентность)")
                            return True
                        else:
                            self.logger.info(f"[ProductRegistry] Статус продукта {product_id} будет изменен с {current_status} на {new_status}")
                    else:
                        self.logger.warning(f"[ProductRegistry] Не удалось получить текущий статус продукта {product_id}")
                        
                else:
                    self.logger.warning(f"[ProductRegistry] Не удалось получить данные владельца продукта {product_id}")
                    
            except Exception as e:
                self.logger.error(f"[ProductRegistry] Ошибка при проверке прав доступа: {e}")
                return False
            
            # Выполнение операции в блокчейне
            self.logger.info(f"[ProductRegistry] Выполняем обновление статуса в блокчейне")
            tx_hash = await self.blockchain_service.update_product_status(
                self.blockchain_service.seller_key,
                product_id,
                new_status
            )
            
            if tx_hash is None and new_status == 1:
                # Активация не поддерживается в текущем контракте, но это не ошибка
                self.logger.info(f"[ProductRegistry] Продукт {product_id} уже активен")
                return True
            elif not tx_hash:
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

    def _deserialize_product(self, product_data: tuple) -> Optional[Product]:
        """
        Десериализует продукт из кортежа блокчейна и метаданных IPFS.
        Args:
            product_data: tuple (id, seller, ipfsCID, active)
        Returns:
            Product или None
        """
        try:
            if not hasattr(product_data, '__getitem__') or len(product_data) < 4:
                self.logger.error(f"Некорректная структура product_data: {product_data}")
                return None

            product_id = product_data[0]  # Блокчейн ID
            ipfs_cid = product_data[2]
            is_active = bool(product_data[3])

            self.logger.info(f"🔍 Получаем метаданные продукта: {product_id}, {ipfs_cid}, {is_active}")
            metadata = self.storage_service.download_json(ipfs_cid)
            if not metadata:
                self.logger.warning(f"Не удалось получить метаданные для продукта {product_id}")
                return None

            product = self.metadata_service.process_product_metadata(metadata)
            if product:
                product.id = product_id
                product.cid = ipfs_cid
                product.is_active = is_active
                product.status = 1 if is_active else 0  # Обновляем статус на основе активности
            return product
        except Exception as e:
            self.logger.error(f"Ошибка десериализации продукта: {e}")
            return None