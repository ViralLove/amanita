import csv
import json
import os
from typing import Dict, List
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

def load_image_cids(mapping_path: str) -> Dict[str, str]:
    """
    Загружает маппинг имен файлов изображений и их CID
    
    Args:
        mapping_path: Путь к файлу с маппингом
    """
    try:
        with open(mapping_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"😱 Ошибка при загрузке маппинга изображений: {e}")
        return {}

def load_description_cids(mapping_path: str) -> Dict[str, str]:
    """
    Загружает маппинг biounit_id и их CID описаний
    
    Args:
        mapping_path: Путь к файлу с маппингом
    """
    try:
        with open(mapping_path, 'r', encoding='utf-8') as file:
            mapping = json.load(file)
            # Преобразуем структуру в простой словарь biounit_id -> cid
            return {biounit_id: data["cid"] for biounit_id, data in mapping.items()}
    except Exception as e:
        logger.error(f"😱 Ошибка при загрузке маппинга описаний: {e}")
        return {}

def parse_prices(prices_str: str) -> List[Dict]:
    """Преобразует строку с ценами в структурированный формат"""
    result = []
    # Разделяем несколько цен, если они есть
    price_variants = prices_str.split(';')
    
    for price_var in price_variants:
        price_var = price_var.strip()
        if not price_var:
            continue
            
        # Разбираем компоненты цены
        components = price_var.split('|')
        if len(components) != 4:
            logger.warning(f"⚠️ Пропущена некорректная цена: {price_var}")
            continue
            
        amount, unit, price, currency = components
        
        # Определяем тип единицы измерения
        if unit.lower() in ['g', 'gram', 'гр']:
            price_dict = {
                "weight": amount,
                "weight_unit": "g",
                "price": price,
                "currency": currency
            }
        elif unit.lower() in ['ml', 'мл']:
            price_dict = {
                "volume": amount,
                "volume_unit": "ml",
                "price": price,
                "currency": currency
            }
        else:
            logger.warning(f"⚠️ Неизвестная единица измерения: {unit}")
            continue
            
        result.append(price_dict)
    
    return result

def convert_catalog_to_json(
    csv_path: str,
    images_mapping_path: str,
    descriptions_mapping_path: str,
    output_path: str
) -> List[Dict]:
    """
    Конвертирует CSV каталог в JSON формат
    
    Args:
        csv_path: Путь к CSV файлу каталога
        images_mapping_path: Путь к файлу с маппингом CID'ов изображений
        descriptions_mapping_path: Путь к файлу с маппингом CID'ов описаний
        output_path: Путь для сохранения JSON каталога
        
    Returns:
        List[Dict]: Список продуктов в формате JSON
    """
    # Загружаем маппинги
    image_cids = load_image_cids(images_mapping_path)
    description_cids = load_description_cids(descriptions_mapping_path)
    catalog_items = []

    try:
        # Читаем CSV файл
        with open(csv_path, 'r', encoding='utf-8') as file:
            # Пропускаем BOM если есть
            content = file.read()
            if content.startswith('\ufeff'):
                content = content[1:]
            
            # Читаем CSV
            reader = csv.DictReader(content.splitlines(), skipinitialspace=True)
            
            # Обрабатываем каждую строку
            for row in reader:
                # Очищаем значения от пробелов
                row = {k.strip(): v.strip() for k, v in row.items()}
                
                # Получаем CID изображения
                image_file = row['image_file'].strip()
                cover_image_cid = image_cids.get(image_file, "")
                
                # Получаем CID описания из маппинга
                biounit_id = row['biounit_id']
                description_cid = description_cids.get(biounit_id)
                if not description_cid:
                    logger.warning(f"⚠️ Не найден CID описания для biounit_id: {biounit_id}")
                
                # Обрабатываем цены
                prices = parse_prices(row['prices'])
                
                # Формируем элемент каталога
                catalog_item = {
                    "business_id": row['product_id'],
                    "title": row['product_name'],
                    "organic_components": [
                        {
                            "biounit_id": biounit_id,
                            "description_cid": description_cid or "",
                            "proportion": "100%"
                        }
                    ] if description_cid else [],
                    "categories": [category.strip() for category in row['categories'].split(',')],
                    "cover_image_url": cover_image_cid,
                    "forms": [row['form']],
                    "species": row['species'],
                    "prices": prices
                }
                
                catalog_items.append(catalog_item)
                logger.info(f"✨ Обработан продукт: {catalog_item['title']}")

        # Создаем директорию для выходного файла если её нет
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Сохраняем результат
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(catalog_items, file, ensure_ascii=False, indent=2)
        logger.info(f"🎉 Каталог успешно сохранен в {output_path}")
        
        return catalog_items

    except Exception as e:
        logger.error(f"😱 Ошибка при конвертации каталога: {e}")
        raise

def main():
    """Точка входа для самостоятельного запуска скрипта"""
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    
    # Используем дефолтные пути при запуске через main
    csv_path = os.path.join("bot", "catalog", "Iveta_catalog.csv")
    images_mapping_path = os.path.join("bot", "catalog", "catalog_images.json")
    descriptions_mapping_path = os.path.join("bot", "catalog", "organic_cid_mapping.json")
    output_path = os.path.join("bot", "catalog", "active_catalog.json")
    
    convert_catalog_to_json(
        csv_path=csv_path,
        images_mapping_path=images_mapping_path,
        descriptions_mapping_path=descriptions_mapping_path,
        output_path=output_path
    )

def process_catalog_conversion(
    csv_path: str,
    images_mapping_json: str,
    descriptions_mapping_json: str,
    output_json: str
) -> List[Dict]:
    """
    Фасадный метод для конвертации CSV каталога в JSON
    
    Args:
        csv_path: Путь к CSV файлу каталога
        images_mapping_json: Путь к файлу с маппингом CID'ов изображений
        descriptions_mapping_json: Путь к файлу с маппингом CID'ов описаний
        output_json: Путь для сохранения JSON каталога
        
    Returns:
        List[Dict]: Список продуктов в формате JSON
    """
    return convert_catalog_to_json(
        csv_path=csv_path,
        images_mapping_path=images_mapping_json,
        descriptions_mapping_path=descriptions_mapping_json,
        output_path=output_json
    )

if __name__ == "__main__":
    main()
