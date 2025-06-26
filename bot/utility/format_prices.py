import csv
import json
import os
from typing import Dict, List, Tuple

def parse_price_string(price_str: str) -> List[Tuple[str, str, str, str]]:
    """
    Парсит строку с ценами из CSV в список кортежей (количество, единица, цена, валюта)
    Примеры входных данных:
    - "100g — 80€"
    - "30g — 60€; 50g — 100€; powder 50g — 90€"
    - "50ml — 15€"
    """
    result = []
    # Разбиваем на отдельные ценовые позиции
    price_items = [p.strip() for p in price_str.split(';')]
    
    for item in price_items:
        # Убираем упоминание "powder" если есть
        item = item.replace('powder', '').strip()
        
        # Разбиваем на количество и цену
        quantity_part, price_part = item.split('—')
        
        # Парсим количество и единицу измерения
        quantity_part = quantity_part.strip()
        if 'ml' in quantity_part:
            quantity = quantity_part.replace('ml', '').strip()
            unit = 'ml'
        elif 'g' in quantity_part:
            quantity = quantity_part.replace('g', '').strip()
            unit = 'g'
        else:
            raise ValueError(f"Неизвестная единица измерения в {quantity_part}")
        
        # Парсим цену и валюту
        price_part = price_part.strip()
        if '€' in price_part:
            price = price_part.replace('€', '').strip()
            currency = 'EUR'
        else:
            raise ValueError(f"Неизвестная валюта в {price_part}")
            
        result.append((quantity, unit, price, currency))
    
    return result

def convert_to_structured_format():
    """Конвертирует цены в структурированный формат"""
    # Загружаем текущий JSON каталог
    with open(os.path.join("bot", "catalog", "active_catalog.json"), 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    # Создаем словарь для быстрого поиска по ID
    catalog_dict = {item['id']: item for item in catalog}
    print("Loaded catalog IDs:", list(catalog_dict.keys()))
    
    # Читаем CSV и создаем новый с обновленными ценами
    csv_rows = []
    with open(os.path.join("bot", "catalog", "Iveta_catalog.csv"), 'r', encoding='utf-8') as f:
        # Читаем и очищаем заголовки от пробелов
        content = f.read()
        if content.startswith('\ufeff'):
            content = content[1:]
        
        lines = content.splitlines()
        headers = [h.strip() for h in lines[0].split(',')]
        print("CSV Headers:", headers)
        
        reader = csv.DictReader(lines, fieldnames=headers)
        next(reader)  # Пропускаем строку с заголовками
        
        # Создаем новые заголовки, заменяя 'price' на 'prices'
        new_headers = headers.copy()
        price_index = new_headers.index('price')
        new_headers[price_index] = 'prices'
        csv_rows.append(new_headers)
        
        for row in reader:
            # Очищаем все ключи и значения от пробелов
            clean_row = {k.strip(): v.strip() for k, v in row.items()}
            print("\nProcessing row:")
            print("Original row:", clean_row)
            
            product_id = clean_row['product_id']
            print("Product ID:", product_id)
            
            if product_id in catalog_dict:
                print(f"Found product in catalog: {product_id}")
                # Парсим текущую строку с ценой
                try:
                    price_tuples = parse_price_string(clean_row['price'])
                    print("Parsed price tuples:", price_tuples)
                    
                    # Форматируем в новый формат
                    structured_prices = []
                    for quantity, unit, price, currency in price_tuples:
                        price_str = f"{quantity}|{unit}|{price}|{currency}"
                        structured_prices.append(price_str)
                    
                    # Создаем новую строку с обновленными ценами
                    new_row = clean_row.copy()
                    new_row['prices'] = ';'.join(structured_prices)
                    del new_row['price']
                    print("Structured prices:", new_row['prices'])
                    
                    csv_rows.append(list(new_row.values()))
                except Exception as e:
                    print(f"Error processing prices for {product_id}: {e}")
                    csv_rows.append(list(clean_row.values()))
            else:
                print(f"Product not found in catalog: {product_id}")
                csv_rows.append(list(clean_row.values()))
    
    # Сохраняем обновленный CSV
    output_path = os.path.join("bot", "catalog", "Iveta_catalog_structured.csv")
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(csv_rows)
    
    print(f"\n✨ CSV с структурированными ценами сохранен в {output_path}")

if __name__ == "__main__":
    convert_to_structured_format() 