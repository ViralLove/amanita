import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import argparse
import traceback

# Импортируем фасадные методы
from bot.utility.upload_catalog_images import process_catalog_images
from bot.utility.upload_organic_descriptions import process_organic_descriptions
from bot.utility.catalog_csv2json import process_catalog_conversion
from bot.utility.prepare_products_for_registry import process_registry_preparation
from bot.services.product_registry import ProductRegistryService
from bot.services.blockchain import BlockchainService
from bot.services.service_factory import ServiceFactory

# Настройка логирования
logger = logging.getLogger(__name__)

def setup_logging(level=logging.INFO, log_file=None):
    """
    Настраивает логирование для всего пайплайна
    
    Args:
        level: Уровень логирования
        log_file: Путь к файлу для логирования (опционально)
    """
    # Форматтер для логов
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    
    # Хендлер для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Удаляем существующие хендлеры
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Добавляем консольный хендлер
    root_logger.addHandler(console_handler)
    
    # Если указан файл лога, добавляем файловый хендлер
    if log_file:
        # Создаем директорию для лога если нужно
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Отключаем логи от библиотек
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('web3').setLevel(logging.WARNING)

@dataclass
class CatalogPipelineConfig:
    """Конфигурация путей и настроек для пайплайна каталога"""
    # Входные данные
    IMAGES_DIR: str
    CATALOG_CSV: str
    ORGANIC_DESCRIPTIONS_JSON: str
    
    # Промежуточные файлы
    CATALOG_IMAGES_JSON: str
    ORGANIC_CID_MAPPING_JSON: str
    ACTIVE_CATALOG_JSON: str
    
    # Выходные данные
    PRODUCT_JSONS_DIR: str
    PRODUCT_REGISTRY_DATA_JSON: str
    
    # Логи
    UPLOAD_LOG_JSON: str
    UPLOAD_LOG_CSV: str
    PROCESS_LOG: str

def load_pipeline_config() -> CatalogPipelineConfig:
    """Загружает конфигурацию из .env файла"""
    load_dotenv(os.path.join("bot", ".env"))
    base_dir = os.path.join("bot", "catalog")

    serviceFactory = ServiceFactory()
    productRegistry = serviceFactory.create_product_registry_service()
    
    return CatalogPipelineConfig(
        # Входные данные
        IMAGES_DIR=os.getenv("CATALOG_IMAGES_DIR", os.path.join(base_dir)),
        CATALOG_CSV=os.getenv("CATALOG_CSV_PATH", os.path.join(base_dir, "Iveta_catalog.csv")),
        ORGANIC_DESCRIPTIONS_JSON=os.getenv("ORGANIC_DESCRIPTIONS_JSON", os.path.join(base_dir, "organic_descriptions.json")),
        
        # Промежуточные файлы
        CATALOG_IMAGES_JSON=os.getenv("CATALOG_IMAGES_JSON", os.path.join(base_dir, "catalog_images.json")),
        ORGANIC_CID_MAPPING_JSON=os.getenv("ORGANIC_CID_MAPPING_JSON", os.path.join(base_dir, "organic_cid_mapping.json")),
        ACTIVE_CATALOG_JSON=os.getenv("ACTIVE_CATALOG_JSON", os.path.join(base_dir, "active_catalog.json")),
        
        # Выходные данные
        PRODUCT_JSONS_DIR=os.getenv("PRODUCT_JSONS_DIR", os.path.join(base_dir, "product_jsons")),
        PRODUCT_REGISTRY_DATA_JSON=os.getenv("PRODUCT_REGISTRY_DATA_JSON", os.path.join(base_dir, "product_registry_upload_data.json")),
        
        # Логи
        UPLOAD_LOG_JSON=os.getenv("UPLOAD_LOG_JSON", os.path.join(base_dir, "images_upload_log.json")),
        UPLOAD_LOG_CSV=os.getenv("UPLOAD_LOG_CSV", os.path.join(base_dir, "images_upload_log.csv")),
        PROCESS_LOG=os.getenv("PROCESS_LOG", os.path.join(base_dir, "upload_catalog.log"))
    )

class CatalogPipeline:
    """Пайплайн для подготовки каталога продуктов"""
    
    def __init__(self):
        self.config = load_pipeline_config()
        self.logger = logger
        
        # Инициализируем сервис реестра продуктов
        service_factory = ServiceFactory()
        self.productRegistry = service_factory.create_product_registry_service()
        self.logger.info("✅ Инициализирован сервис реестра продуктов")
    
    def validate_input_data(self) -> bool:
        """Проверяет наличие и валидность входных данных"""
        required_files = [
            self.config.CATALOG_CSV,
            self.config.ORGANIC_DESCRIPTIONS_JSON
        ]
        required_dirs = [
            self.config.IMAGES_DIR,
            os.path.dirname(self.config.PRODUCT_JSONS_DIR)
        ]
        
        # Проверяем наличие файлов
        for file_path in required_files:
            if not os.path.isfile(file_path):
                self.logger.error(f"❌ Не найден файл: {file_path}")
                return False
                
        # Проверяем наличие директорий
        for dir_path in required_dirs:
            if not os.path.isdir(dir_path):
                self.logger.error(f"❌ Не найдена директория: {dir_path}")
                return False
                
        return True
    
    def upload_images(self) -> Dict[str, str]:
        """Загружает изображения в IPFS"""
        return process_catalog_images(
            images_dir=self.config.IMAGES_DIR,
            output_json=self.config.CATALOG_IMAGES_JSON,
            log_json=self.config.UPLOAD_LOG_JSON,
            log_csv=self.config.UPLOAD_LOG_CSV
        )
    
    def upload_descriptions(self) -> Dict[str, str]:
        """Загружает описания в IPFS"""
        return process_organic_descriptions(
            descriptions_json=self.config.ORGANIC_DESCRIPTIONS_JSON,
            output_mapping_json=self.config.ORGANIC_CID_MAPPING_JSON
        )
    
    def convert_catalog_to_json(self) -> List[Dict]:
        """Конвертирует CSV каталог в JSON"""
        return process_catalog_conversion(
            csv_path=self.config.CATALOG_CSV,
            images_mapping_json=self.config.CATALOG_IMAGES_JSON,
            descriptions_mapping_json=self.config.ORGANIC_CID_MAPPING_JSON,
            output_json=self.config.ACTIVE_CATALOG_JSON
        )
    
    def prepare_products_for_registry(self) -> List[Dict]:
        """Подготавливает продукты для загрузки в реестр"""
        return process_registry_preparation(
            catalog_json=self.config.ACTIVE_CATALOG_JSON,
            output_dir=self.config.PRODUCT_JSONS_DIR,
            output_registry_json=self.config.PRODUCT_REGISTRY_DATA_JSON
        )
    
    def upload_products_to_registry(self) -> List[Dict]:
        """Загружает продукты в смарт-контракт"""
        try:
            self.logger.info("📝 Загрузка продуктов в реестр...")
            
            # Загружаем данные для реестра
            with open(self.config.PRODUCT_REGISTRY_DATA_JSON, 'r') as f:
                registry_data = json.load(f)
            
            results = []
            for product in registry_data:
                try:
                    # Получаем CID (может быть в разных форматах)
                    ipfs_cid = product.get('ipfsCID') or product.get('ipfs_cid')
                    if not ipfs_cid:
                        raise ValueError(f"CID не найден в данных продукта: {product}")
                    
                    # Создаем продукт в смарт-контракте
                    tx_hash = self.productRegistry.create_product_on_chain(ipfs_cid)
                    
                    # Добавляем информацию о транзакции в данные продукта
                    product['tx_hash'] = tx_hash
                    results.append(product)
                    
                    self.logger.info(f"✅ Продукт {product['id']} успешно загружен в смарт контракт. TX: {tx_hash}")
                    
                except Exception as e:
                    self.logger.error(f"❌ Ошибка загрузки продукта {product['id']}: {str(e)}")
                    product['error'] = str(e)
                    results.append(product)
            
            # Сохраняем обновленные данные
            with open(self.config.PRODUCT_REGISTRY_DATA_JSON, 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка в процессе загрузки продуктов: {str(e)}")
            raise
    
    def validate_output_data(self) -> bool:
        """Проверяет корректность выходных данных"""
        try:
            # Проверяем наличие всех выходных файлов
            required_outputs = [
                self.config.CATALOG_IMAGES_JSON,
                self.config.ORGANIC_CID_MAPPING_JSON,
                self.config.ACTIVE_CATALOG_JSON,
                self.config.PRODUCT_REGISTRY_DATA_JSON
            ]
            
            for file_path in required_outputs:
                if not os.path.isfile(file_path):
                    self.logger.error(f"❌ Отсутствует выходной файл: {file_path}")
                    return False
            
            # Проверяем наличие файлов продуктов
            if not os.path.isdir(self.config.PRODUCT_JSONS_DIR) or not os.listdir(self.config.PRODUCT_JSONS_DIR):
                self.logger.error(f"❌ Директория продуктов пуста: {self.config.PRODUCT_JSONS_DIR}")
                return False
            
            # Проверяем валидность JSON файлов
            for file_path in required_outputs:
                try:
                    with open(file_path, 'r') as f:
                        json.load(f)
                except json.JSONDecodeError:
                    self.logger.error(f"❌ Невалидный JSON в файле: {file_path}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка при валидации выходных данных: {str(e)}")
            return False
    
    def run(self) -> bool:
        """Запускает полный процесс подготовки каталога"""
        try:
            # Проверяем входные данные
            if not self.validate_input_data():
                self.logger.error("❌ Ошибка валидации входных данных")
                return False
                
            # Загружаем изображения
            self.logger.info("🖼️ Загрузка изображений...")
            image_cids = self.upload_images()
            self.logger.info(f"🖼️ Загружены изображения: {image_cids}")
            
            # Загружаем описания
            self.logger.info("📝 Загрузка описаний...")
            description_cids = self.upload_descriptions()
            self.logger.info(f"📝 Загружены описания: {description_cids}")
            
            # Конвертируем каталог
            self.logger.info("🔄 Конвертация каталога...")
            catalog_data = self.convert_catalog_to_json()
            self.logger.info(f"🔄 Конвертирован каталог: {catalog_data}")
            
            # Подготавливаем данные для реестра
            self.logger.info("📦 Подготовка данных для реестра...")
            registry_data = self.prepare_products_for_registry()
            self.logger.info(f"📦 Подготовлены данные для реестра: {registry_data}")
            
            # Загружаем продукты в реестр
            self.logger.info("🚀 Загрузка продуктов в реестр...")
            upload_results = self.upload_products_to_registry()
            self.logger.info(f"🚀 Загружены продукты в реестр: {upload_results}")
            
            # Проверяем выходные данные
            if not self.validate_output_data():
                self.logger.error("❌ Ошибка валидации выходных данных")
                return False
            
            self.logger.info("✅ Процесс успешно завершен!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка в процессе: {str(e)}")
            return False

def upload_only(args):
    """Точка входа для запуска только загрузки в смарт-контракт"""
    try:
        # Настраиваем логирование
        pipeline = CatalogPipeline()
        setup_logging(
            level=logging.DEBUG if args.verbose else logging.INFO,
            log_file=pipeline.config.PROCESS_LOG
        )
        
        logger.info("🚀 Запуск загрузки продуктов в смарт-контракт")
        
        # Проверяем существование файла с данными
        if not os.path.exists(pipeline.config.PRODUCT_REGISTRY_DATA_JSON):
            logger.error(f"❌ Файл с данными не найден: {pipeline.config.PRODUCT_REGISTRY_DATA_JSON}")
            return False
            
        # Проверяем инициализацию сервиса
        if not pipeline.productRegistry:
            logger.error("❌ Сервис реестра продуктов не инициализирован")
            return False
            
        logger.info("📦 Загрузка данных из JSON...")
        with open(pipeline.config.PRODUCT_REGISTRY_DATA_JSON, 'r') as f:
            registry_data = json.load(f)
        logger.info(f"📦 Загружено {len(registry_data)} продуктов")
        
        # Загружаем продукты
        results = pipeline.upload_products_to_registry()
        
        # Выводим итоги
        success_count = len([p for p in results if 'tx_hash' in p and 'error' not in p])
        error_count = len([p for p in results if 'error' in p])
        
        logger.info("📊 Итоги загрузки:")
        logger.info(f"✅ Успешно загружено: {success_count}")
        logger.info(f"❌ Ошибок: {error_count}")
        
        if error_count > 0:
            logger.info("🔍 Детали ошибок:")
            for product in results:
                if 'error' in product:
                    logger.error(f"  - Продукт {product['id']}: {product['error']}")
        
        return error_count == 0
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {str(e)}\n{traceback.format_exc()}")
        return False

def parse_args():
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser(description='Пайплайн подготовки каталога продуктов')
    parser.add_argument('-v', '--verbose', action='store_true', help='Включить подробное логирование')
    parser.add_argument('-s', '--silent', action='store_true', help='Минимальное логирование')
    parser.add_argument('--log-cli-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      help='Уровень логирования')
    parser.add_argument('--upload-only', action='store_true', help='Только загрузка в смарт-контракт')
    return parser.parse_args()

def main():
    """Точка входа для запуска пайплайна"""
    # Парсим аргументы
    args = parse_args()
    
    # Если указан флаг upload-only, запускаем только загрузку
    if args.upload_only:
        success = upload_only(args)
    else:
        # Определяем уровень логирования
        if args.log_cli_level:
            level = getattr(logging, args.log_cli_level)
        elif args.verbose:
            level = logging.DEBUG
        elif args.silent:
            level = logging.WARNING
        else:
            level = logging.INFO
        
        # Настраиваем логирование
        pipeline = CatalogPipeline()
        setup_logging(
            level=level,
            log_file=pipeline.config.PROCESS_LOG
        )
        
        # Запускаем пайплайн
        logger.info("🚀 Запуск пайплайна подготовки каталога")
        success = pipeline.run()
    
    if success:
        logger.info("✨ Процесс успешно завершен")
        exit(0)
    else:
        logger.error("❌ Процесс завершился с ошибками")
        exit(1)

if __name__ == "__main__":
    main() 