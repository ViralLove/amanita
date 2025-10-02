#!/usr/bin/env python3
"""
Скрипт для трансформации organic_descriptions.json в мультиязычную структуру
Создает SIMPLE и COMPLEX поля с заглушками для переводов
"""

import json
import os
from pathlib import Path
import argparse
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_directories(base_dir: Path):
    """Создает необходимые директории (с очисткой)"""
    # Очищаем папку если существует
    if base_dir.exists():
        import shutil
        shutil.rmtree(base_dir)
        logger.info(f"🧹 Очищена папка: {base_dir}")
    
    simple_dir = base_dir / "simple_fields"
    complex_dir = base_dir / "complex_fields"
    mappings_dir = base_dir / "mappings"
    
    simple_dir.mkdir(parents=True, exist_ok=True)
    complex_dir.mkdir(parents=True, exist_ok=True)
    mappings_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"✅ Созданы директории: {simple_dir}, {complex_dir}, {mappings_dir}")
    return simple_dir, complex_dir, mappings_dir

def extract_simple_fields(organic_items: dict, simple_dir: Path, languages: list):
    """Извлекает SIMPLE поля - один файл на компонент.поле со всеми языками"""
    
    file_count = 0
    
    for biounit_id, item in organic_items.items():
        # 1. ComponentDescription.title для каждого компонента
        title_data = {}
        for lang in languages:
            if lang == 'ru':
                title_data[lang] = item.get('title', '')
            else:
                title_data[lang] = f"[{item.get('title', '')}]"  # Заглушка
        
        filename = f"{biounit_id}.ComponentDescription.title.json"
        with open(simple_dir / filename, 'w', encoding='utf-8') as f:
            json.dump(title_data, f, ensure_ascii=False, indent=2)
        file_count += 1
        
        # 2. Description.scientific_name для каждого компонента
        scientific_name_data = {}
        for lang in languages:
            if lang == 'ru':
                scientific_name_data[lang] = item.get('scientific_name', '')
            else:
                scientific_name_data[lang] = item.get('scientific_name', '')  # Научные названия обычно одинаковые
        
        filename = f"{biounit_id}.Description.scientific_name.json"
        with open(simple_dir / filename, 'w', encoding='utf-8') as f:
            json.dump(scientific_name_data, f, ensure_ascii=False, indent=2)
        file_count += 1
        
        # 3. DosageInstruction.type для каждого компонента (если есть инструкции)
        dosage_instructions = item.get('dosage_instructions', [])
        if dosage_instructions:
            dosage_types = set()
            for instruction in dosage_instructions:
                dosage_type = instruction.get('type', '')
                if dosage_type:
                    dosage_types.add(dosage_type)
            
            if dosage_types:
                dosage_type_data = {}
                for dosage_type in sorted(dosage_types):
                    dosage_type_data[dosage_type] = {}
                    for lang in languages:
                        if lang == 'ru':
                            dosage_type_data[dosage_type][lang] = dosage_type
                        else:
                            dosage_type_data[dosage_type][lang] = f"[{dosage_type}]"  # Заглушка
                
                filename = f"{biounit_id}.DosageInstruction.type.json"
                with open(simple_dir / filename, 'w', encoding='utf-8') as f:
                    json.dump(dosage_type_data, f, ensure_ascii=False, indent=2)
                file_count += 1
    
    logger.info(f"✅ Создано {file_count} SIMPLE файлов (один файл на компонент.поле)")
    
    return file_count

def extract_complex_fields(organic_items: dict, complex_dir: Path, languages: list):
    """Извлекает COMPLEX поля и создает файлы по компонент.класс.язык"""
    
    component_count = 0
    dosage_count = 0
    
    for biounit_id, item in organic_items.items():
        # 1. ComponentDescription для каждого языка - ВСЕ поля должны быть
        for lang in languages:
            component_data = {
                "generic_description": item.get('generic_description', '') if lang == 'ru' else f"[{item.get('generic_description', '')[:50]}...]",
                "effects": item.get('effects', '') if lang == 'ru' else f"[{item.get('effects', '')[:50]}...]",
                "shamanic": item.get('shamanic', '') if lang == 'ru' else f"[{item.get('shamanic', '')[:50]}...]",
                "warnings": item.get('warnings', '') if lang == 'ru' else f"[{item.get('warnings', '')[:50]}...]",
                "features": []  # Пока пустой, можно добавить позже
            }
            
            # Для заглушек заменяем пустые поля на заглушки, но оставляем структуру
            if lang != 'ru':
                for key, value in component_data.items():
                    if not value or value == '':
                        component_data[key] = f"[{key} placeholder]"
            
            filename = f"{biounit_id}.ComponentDescription.{lang}.json"
            with open(complex_dir / filename, 'w', encoding='utf-8') as f:
                json.dump(component_data, f, ensure_ascii=False, indent=2)
            
            component_count += 1
        
        # 2. DosageInstruction для каждого языка (только если есть инструкции)
        dosage_instructions = item.get('dosage_instructions', [])
        if dosage_instructions:
            for lang in languages:
                dosage_data = {}
                for instruction in dosage_instructions:
                    dosage_type = instruction.get('type', '')
                    if dosage_type:
                        if lang == 'ru':
                            dosage_data[dosage_type] = {
                                "title": instruction.get('title', ''),
                                "description": instruction.get('description', '')
                            }
                        else:
                            # Заглушки для всех полей
                            dosage_data[dosage_type] = {
                                "title": f"[{instruction.get('title', '')}]",
                                "description": f"[{instruction.get('description', '')[:100]}...]"
                            }
                
                if dosage_data:  # Создаем файл только если есть данные
                    filename = f"{biounit_id}.DosageInstruction.{lang}.json"
                    with open(complex_dir / filename, 'w', encoding='utf-8') as f:
                        json.dump(dosage_data, f, ensure_ascii=False, indent=2)
                    
                    dosage_count += 1
    
    logger.info(f"✅ Создано {component_count} файлов ComponentDescription")
    logger.info(f"✅ Создано {dosage_count} файлов DosageInstruction")
    
    return {
        "ComponentDescription": component_count,
        "DosageInstruction": dosage_count
    }

def create_mappings(simple_dir: Path, complex_dir: Path, mappings_dir: Path):
    """Создает маппинги для загрузки в AmanitaInternational"""
    
    # SIMPLE поля маппинг (пока пустые CID)
    simple_mapping = {}
    for file_path in simple_dir.glob("*.json"):
        filename = file_path.stem
        # Формат: biounit_id.ClassName.field
        parts = filename.split('.')
        if len(parts) >= 3:
            biounit_id = parts[0]
            class_name = parts[1]
            field_name = parts[2]
            key = f"{class_name}.{field_name}"  # Ключ для контракта
            if key not in simple_mapping:
                simple_mapping[key] = []
            simple_mapping[key].append({
                "biounit_id": biounit_id,
                "cid": "",  # Будет заполнен после загрузки в IPFS
                "file_path": str(file_path)
            })
    
    with open(mappings_dir / "simple_field_mapping.json", 'w', encoding='utf-8') as f:
        json.dump(simple_mapping, f, ensure_ascii=False, indent=2)
    
    # COMPLEX поля маппинг (пока пустые CID)
    complex_mapping = {}
    for file_path in complex_dir.glob("*.json"):
        filename = file_path.stem
        # Формат: biounit_id.ClassName.lang
        parts = filename.split('.')
        if len(parts) >= 3:
            biounit_id = parts[0]
            class_name = parts[1]
            language = parts[2]
            key = f"{biounit_id}.{class_name}.{language}"
            complex_mapping[key] = {
                "cid": "",  # Будет заполнен после загрузки в IPFS
                "file_path": str(file_path)
            }
    
    with open(mappings_dir / "complex_field_mapping.json", 'w', encoding='utf-8') as f:
        json.dump(complex_mapping, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ Создан simple_field_mapping.json с {len(simple_mapping)} полями")
    logger.info(f"✅ Создан complex_field_mapping.json с {len(complex_mapping)} полями")
    
    return len(simple_mapping), len(complex_mapping)

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description='Трансформация organic_descriptions.json в мультиязычную структуру')
    parser.add_argument('--input', default='bot/catalog/organic_descriptions.json', 
                       help='Путь к исходному файлу organic_descriptions.json')
    parser.add_argument('--output', default='bot/catalog/multilingual_components', 
                       help='Путь к выходной директории')
    parser.add_argument('--languages', nargs='+', default=['ru', 'en', 'de', 'fr', 'es'], 
                       help='Список языков для создания заглушек')
    parser.add_argument('--verbose', '-v', action='store_true', help='Подробное логирование')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Пути
    input_file = Path(args.input)
    output_dir = Path(args.output)
    
    if not input_file.exists():
        logger.error(f"❌ Файл не найден: {input_file}")
        return 1
    
    logger.info(f"🚀 Трансформация {input_file} в мультиязычную структуру")
    logger.info(f"📁 Выходная директория: {output_dir}")
    logger.info(f"🌍 Языки: {', '.join(args.languages)}")
    
    # Загружаем исходные данные
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    organic_items = data.get('organic_items', {})
    logger.info(f"📊 Найдено {len(organic_items)} компонентов")
    
    # Создаем директории
    simple_dir, complex_dir, mappings_dir = setup_directories(output_dir)
    
    # Извлекаем SIMPLE поля
    logger.info("🔧 Извлечение SIMPLE полей...")
    simple_results = extract_simple_fields(organic_items, simple_dir, args.languages)
    
    # Извлекаем COMPLEX поля
    logger.info("🔧 Извлечение COMPLEX полей...")
    complex_results = extract_complex_fields(organic_items, complex_dir, args.languages)
    
    # Создаем маппинги
    logger.info("🔧 Создание маппингов...")
    simple_mapping_count, complex_mapping_count = create_mappings(simple_dir, complex_dir, mappings_dir)
    
    # Итоговая статистика
    total_files = simple_results + complex_results["ComponentDescription"] + complex_results["DosageInstruction"]
    
    logger.info("🎉 Трансформация завершена!")
    logger.info(f"📊 Статистика:")
    logger.info(f"   - SIMPLE поля: {simple_results} файлов")
    logger.info(f"   - COMPLEX поля: {complex_results['ComponentDescription'] + complex_results['DosageInstruction']} файлов")
    logger.info(f"   - Маппинги: {simple_mapping_count + complex_mapping_count} записей")
    logger.info(f"   - Всего файлов: {total_files}")
    
    return 0

if __name__ == "__main__":
    exit(main())
