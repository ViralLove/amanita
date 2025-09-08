import os
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import logging

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.core.ipfs_factory import IPFSFactory

# Настройка логирования
logger = logging.getLogger(__name__)

def prepare_registry_data(
    input_json: Path,
    output_dir: Path,
    output_registry_json: Path
) -> List[Dict]:
    """
    Подготавливает данные продуктов для загрузки в реестр
    
    Args:
        input_json: Путь к JSON файлу с готовыми UX-данными
        output_dir: Путь к директории для сохранения отдельных JSON файлов
        output_registry_json: Путь для сохранения данных реестра
        
    Returns:
        List[Dict]: Список продуктов для загрузки в реестр
    """
    if not input_json.exists():
        logger.error("❌ Файл каталога не найден!")
        raise FileNotFoundError(f"Файл не найден: {input_json}")

    # Создаем выходные директории
    output_dir.mkdir(parents=True, exist_ok=True)
    output_registry_json.parent.mkdir(parents=True, exist_ok=True)

    # Загружаем все продукты
    with open(input_json, "r", encoding="utf-8") as f:
        products_data = json.load(f)

    # Инициализируем IPFS клиент
    uploader = IPFSFactory().get_storage()

    # Итоговый список для загрузки в контракт
    contract_upload_data = []

    # Обрабатываем каждый продукт
    for idx, product in enumerate(products_data, start=1):
        product_id = product.get("business_id")
        if not product_id:
            logger.warning(f"⚠️ Продукт #{idx} без business_id — пропускаем!")
            continue

        # Сохраняем отдельный JSON-файл
        product_filename = output_dir / f"{product_id}.json"
        with open(product_filename, "w", encoding="utf-8") as pf:
            json.dump(product, pf, ensure_ascii=False, indent=2)
        
        logger.info(f"☀️ Создан файл {product_filename}")

        # Загружаем JSON в IPFS
        try:
            logger.info(f"🔥 Загружаем {product_filename} в IPFS")
            cid = uploader.upload_file(str(product_filename))
            logger.info(f"✅ Загружен {product_id}: {cid}")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки {product_id}: {e}")
            continue

        # Формируем запись для вызова контракта
        contract_entry = {
            "id": product_id,
            "ipfsCID": cid,
            "active": True
        }
        contract_upload_data.append(contract_entry)

    # Сохраняем итоговый JSON
    with open(output_registry_json, "w", encoding="utf-8") as outf:
        json.dump(contract_upload_data, outf, ensure_ascii=False, indent=2)

    logger.info("\n🎉 Все продукты обработаны и готовы для загрузки в контракт!")
    logger.info(f"📝 Итоговый файл: {output_registry_json}")
    
    return contract_upload_data

def main():
    """Точка входа для самостоятельного запуска скрипта"""
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    
    # Используем дефолтные пути при запуске через main
    input_json = Path("bot/catalog/active_catalog.json")
    output_dir = Path("bot/catalog/product_jsons")
    output_registry_json = Path("bot/catalog/product_registry_upload_data.json")
    
    prepare_registry_data(input_json, output_dir, output_registry_json)

def process_registry_preparation(
    catalog_json: str,
    output_dir: str,
    output_registry_json: str
) -> List[Dict]:
    """
    Фасадный метод для подготовки продуктов к загрузке в реестр
    
    Args:
        catalog_json: Путь к JSON файлу каталога
        output_dir: Путь к директории для сохранения отдельных JSON файлов
        output_registry_json: Путь для сохранения данных реестра
        
    Returns:
        List[Dict]: Список продуктов для загрузки в реестр
    """
    # Настраиваем логирование для фасадного метода
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    
    return prepare_registry_data(
        input_json=Path(catalog_json),
        output_dir=Path(output_dir),
        output_registry_json=Path(output_registry_json)
    )

if __name__ == "__main__":
    main()
