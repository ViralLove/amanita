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
        
        # Используем синглтон BlockchainService если не передан
        self.blockchain = blockchain_service or BlockchainService()
        self.validation_service = validation_service
        
        # Создаем фабрику один раз
        self.storage_service = IPFSFactory().get_storage()
        
        # Инициализируем кэш (storage_service создается внутри как синглтон)
        self.cache_service = ProductCacheService()
        
        # Инициализируем сервис метаданных
        self.metadata_service = ProductMetadataService(self.storage_service)
        
        # Инициализируем AccountService
        if account_service is None:
            self.account_service = AccountService(self.blockchain)
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
            
            version = self.blockchain.get_catalog_version()
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
            tx_hash = self.blockchain.create_product(ipfs_cid)
            
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
        try:
            # Проверяем версию каталога
            catalog_version = self.blockchain.get_catalog_version()
            
            # Проверяем кэш
            cached_catalog = self.cache_service.get_cached_item("catalog", "catalog")
            if cached_catalog and cached_catalog.get("version") == catalog_version:
                self.logger.info("Returning cached catalog")
                return cached_catalog.get("products", [])
            
            # Получаем продукты из блокчейна
            products_data = self.blockchain.get_all_products()
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
            self.cache_service.set_cached_item("catalog", {
                "version": catalog_version,
                "products": products
            }, "catalog")
            
            return products
            
        except Exception as e:
            self.logger.error(f"Error getting all products: {e}")
            return []
    
    def get_product(self, product_id: str) -> Optional[Product]:
        """
        Получает продукт по ID.
        
        Args:
            product_id: ID продукта
            
        Returns:
            Optional[Product]: Данные продукта или None
        """
        try:
            product_data = self.blockchain.get_product(product_id)
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

    async def create_product(self, product_data: dict) -> Optional[str]:
        """
        Создает новый продукт.
        
        Args:
            product_data: Данные продукта
            
        Returns:
            Optional[str]: ID продукта или None в случае ошибки
        """
        try:
            self.logger.info("🚀 Начинаем создание продукта")
            self.logger.info(f"📝 Входные данные: {json.dumps(product_data, indent=2)}")

            # Валидируем данные продукта
            self.logger.info("🔍 Валидация данных продукта")
            validation_result = await self.validation_service.validate_product_data(product_data)
            if not validation_result["is_valid"]:
                errors = validation_result.get("errors", [])
                error_msg = "; ".join(errors)
                self.logger.error(f"❌ Ошибка валидации данных продукта: {error_msg}")
                return None

            self.logger.info("✅ Валидация успешна")

            # Создаем метаданные продукта
            self.logger.info("📦 Создаем метаданные продукта")
            metadata = self.create_product_metadata(product_data)
            self.logger.info(f"📄 Метаданные: {json.dumps(metadata, indent=2)}")

            # Загружаем метаданные в IPFS
            self.logger.info("☁️ Загружаем метаданные в IPFS")
            metadata_cid = await self.storage_service.upload_json(metadata)
            if not metadata_cid:
                self.logger.error("❌ Не удалось загрузить метаданные в IPFS")
                return None
            
            self.logger.info(f"✅ Метаданные загружены, CID: {metadata_cid}")

            # Создаем продукт в блокчейне
            self.logger.info("⛓️ Создаем продукт в блокчейне")
            tx_hash = await self.blockchain.create_product(metadata_cid)
            if not tx_hash:
                self.logger.error("❌ Не удалось создать продукт в блокчейне")
                return None

            self.logger.info(f"✅ Продукт создан в блокчейне, хэш транзакции: {tx_hash}")

            # Получаем ID продукта из логов транзакции
            self.logger.info("🔍 Получаем ID продукта из логов транзакции")
            product_id = await self.blockchain.get_product_id_from_tx(tx_hash)
            if not product_id:
                self.logger.error("❌ Не удалось получить ID продукта из логов транзакции")
                return None

            self.logger.info(f"✅ Успешно получен ID продукта: {product_id}")
            return product_id

        except Exception as e:
            self.logger.error(f"❌ Ошибка при создании продукта: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None
    
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
            tx_hash = await self.blockchain.update_product_status(
                self.blockchain.seller_key,
                product_id,
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
    
    async def set_product_active(self, product_id: int, is_active: bool) -> bool:
        """
        Устанавливает активность продукта.
        
        Args:
            product_id: ID продукта
            is_active: True - продукт активен, False - не активен
            
        Returns:
            bool: True если успешно, False если ошибка
        """
        try:
            tx_hash = await self.blockchain.set_product_active(
                self.blockchain.seller_key,
                product_id,
                is_active
            )
            
            if not tx_hash:
                self.logger.error(f"[ProductRegistry] Ошибка установки активности продукта {product_id}")
                return False
                
            self.logger.info(f"[ProductRegistry] Активность продукта {product_id} установлена: {is_active}")
            return True
            
        except Exception as e:
            self.logger.error(f"[ProductRegistry] Ошибка установки активности продукта {product_id}: {e}")
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

            product_id = product_data[0]
            ipfs_cid = product_data[2]
            active = product_data[3]

            self.logger.info(f"🔍 Получаем метаданные продукта: {product_id}, {ipfs_cid}, {active}")
            metadata = self.storage_service.download_json(ipfs_cid)
            self.logger.info(f"📥 Получены метаданные для продукта {product_id}: {type(metadata)}, {metadata}")
            
            if not metadata:
                self.logger.error(f"Не удалось загрузить метаданные для продукта {product_id}")
                return None
            
            # Проверяем, что metadata является словарем
            if not isinstance(metadata, dict):
                self.logger.error(f"Метаданные должны быть словарем, получено: {type(metadata)} для продукта {product_id}")
                return None
            
            # Обрабатываем метаданные через metadata_service
            product = self.metadata_service.process_product_metadata(metadata)
            if not product:
                self.logger.error(f"Не удалось десериализовать продукт {product_id}")
                return None

            # Устанавливаем дополнительные поля из блокчейна
            product.status = 1 if active else 0
            product.id = product_id
            product.cid = ipfs_cid

            return product

        except Exception as e:
            self.logger.error(f"Ошибка десериализации продукта: {e}")
            return None