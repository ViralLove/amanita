import json
import logging
import os
from typing import Dict
from bot.services.core.ipfs_factory import IPFSFactory
import traceback
import argparse
import sys

# Настройка логирования
logger = logging.getLogger(__name__)

def setup_logging(level=logging.INFO):
    """Настраивает логирование"""
    # Форматтер для логов
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    
    # Хендлер для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Удаляем существующие хендлеры и добавляем новый
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    root_logger.addHandler(console_handler)
    
    # Настройка логгера модуля
    logger.setLevel(level)

def parse_args():
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser(description='Загрузка описаний продуктов в IPFS')
    parser.add_argument('-v', '--verbose', action='store_true', help='Включить подробное логирование')
    parser.add_argument('-s', '--silent', action='store_true', help='Минимальное логирование')
    parser.add_argument('--log-cli-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      help='Уровень логирования')
    return parser.parse_args()

def get_file_name(item_data: Dict) -> str:
    """Генерирует имя файла на основе данных продукта"""
    # Используем id как основу для имени файла
    base_name = item_data.get('id', '').lower()
    # Заменяем пробелы и специальные символы
    base_name = base_name.replace(' ', '_').replace('×', 'x')
    # Если scientific_name пуст, используем id
    if not base_name:
        base_name = item_data.get('id', 'unknown')
    return f"biounit_{base_name}_description.json"

class ProductDescriptionUploader:
    def __init__(self, descriptions_path: str, mapping_path: str):
        self.storage = IPFSFactory().get_storage()
        self.descriptions_path = descriptions_path
        self.mapping_path = mapping_path
        
    def load_descriptions(self) -> Dict:
        """Загружает описания продуктов из JSON файла"""
        try:
            logger.info(f"Загружаем описания из {self.descriptions_path}")
            with open(self.descriptions_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                items = data.get('organic_items', {})
                logger.info(f"Загружено {len(items)} описаний")
                return items
        except FileNotFoundError:
            logger.error(f"Файл описаний не найден: {self.descriptions_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON в файле описаний: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при чтении файла описаний: {e}")
            raise

    def save_mapping(self, mapping: Dict):
        """Сохраняет маппинг CID-product_id в JSON файл"""
        try:
            # Создаем директорию для маппинга если её нет
            os.makedirs(os.path.dirname(self.mapping_path), exist_ok=True)
            
            with open(self.mapping_path, 'w', encoding='utf-8') as file:
                json.dump(mapping, file, ensure_ascii=False, indent=2)
            logger.info(f"Маппинг CID сохранен в {self.mapping_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении маппинга: {e}")
            raise

    def upload_descriptions(self) -> Dict[str, str]:
        """
        Загружает описания продуктов в IPFS и создает маппинг CID
        
        Returns:
            Dict[str, str]: Упрощенный маппинг biounit_id -> cid
        """
        organic_items = self.load_descriptions()
        logger.info(f"Загружено {len(organic_items)} описаний для обработки")
        cid_mapping = {}

        for item_id, item_data in organic_items.items():
            try:
                logger.info(f"Обработка item_id: {item_id}")
                logger.debug(f"Данные для загрузки: {json.dumps(item_data, ensure_ascii=False, indent=2)}")
                
                # Форматируем JSON с отступами для читаемости
                json_data = json.dumps(item_data, ensure_ascii=False, indent=2)
                logger.debug(f"Размер JSON данных: {len(json_data)} байт")
                
                # Генерируем имя файла
                file_name = get_file_name(item_data)
                logger.info(f"Имя файла для загрузки: {file_name}")
                
                # Загружаем в IPFS с именем файла
                logger.info(f"Начинаем загрузку в IPFS для {item_id}")
                cid = self.storage.upload_file(json_data, file_name=file_name)
                logger.info(f"☀️ Ура! Биологическая единица проросла в блокчейн! {item_id}, получен CID: {cid}")
                
                # Проверяем полученный CID
                if not cid or len(cid) < 10:
                    logger.error(f"❌ Получен некорректный CID для {item_id}: {cid}")
                    continue
                
                # Добавляем в маппинг
                cid_mapping[item_id] = {
                    "cid": cid,
                    "file_name": file_name
                }
                logger.info(f"✅ Успешно добавлен в маппинг: {item_id} -> {cid} ({file_name})")
                
            except Exception as e:
                logger.error(f"😱 Ошибка при загрузке биологической единицы {item_id}: {e}")
                logger.error(f"Stacktrace: {traceback.format_exc()}")
                continue

        # Сохраняем маппинг
        logger.info(f"Всего успешно загружено: {len(cid_mapping)} из {len(organic_items)}")
        self.save_mapping(cid_mapping)
        
        # Возвращаем упрощенный маппинг для пайплайна
        return {
            item_id: info["cid"]
            for item_id, info in cid_mapping.items()
        }

def main():
    """Основная функция для запуска загрузки"""
    # Парсим аргументы
    args = parse_args()
    
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
    setup_logging(level)
    
    logger.info("🚀 Начинаем загрузку описаний в IPFS")
    
    # Используем дефолтные пути при запуске через main
    descriptions_path = os.path.join("bot", "catalog", "organic_descriptions.json")
    mapping_path = os.path.join("bot", "catalog", "organic_cid_mapping.json")
    
    uploader = ProductDescriptionUploader(descriptions_path, mapping_path)
    uploader.upload_descriptions()
    logger.info("✨ Загрузка завершена")

def process_organic_descriptions(
    descriptions_json: str,
    output_mapping_json: str
) -> Dict[str, str]:
    """
    Фасадный метод для загрузки описаний биоединиц в IPFS
    
    Args:
        descriptions_json: Путь к JSON файлу с описаниями
        output_mapping_json: Путь для сохранения маппинга CID'ов
        
    Returns:
        Dict[str, str]: Маппинг biounit_id и их CID'ов
    """
    # Создаем и запускаем загрузчик с указанными путями
    uploader = ProductDescriptionUploader(descriptions_json, output_mapping_json)
    return uploader.upload_descriptions()

if __name__ == "__main__":
    main()
