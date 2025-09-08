import os
import json
import csv
from pathlib import Path
import time
from typing import Dict, Optional
import mimetypes
import logging
from dotenv import load_dotenv

#from services.ar_weave import ArWeaveUploader
from services.core.ipfs_factory import IPFSFactory

# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv(dotenv_path="bot/.env")

# Конфигурация путей из .env
CATALOG_DIR = os.getenv("CATALOG_DIR", "bot/catalog")
LOGS_DIR = os.getenv("LOGS_DIR", "bot/catalog")
METRICS_DIR = os.getenv("METRICS_DIR", "metrics")

def validate_file(file_path: Path) -> Optional[str]:
    """Проверяет файл на безопасность и допустимость"""
    try:
        # Проверка размера
        size = file_path.stat().st_size
        if size > 50 * 1024 * 1024:  # 50MB
            return f"Файл слишком большой: {size} байт"
            
        # Проверка MIME типа
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type or not mime_type.startswith('image/'):
            return f"Недопустимый тип файла: {mime_type}"
            
        return None
    except Exception as e:
        return f"Ошибка при проверке файла: {e}"

def upload_images(
    image_dir: Path,
    json_log_path: Path,
    csv_log_path: Path,
    logger: logging.Logger
) -> Dict[str, Dict]:
    """
    Основная функция для загрузки изображений в IPFS
    
    Args:
        image_dir: Путь к директории с изображениями
        json_log_path: Путь для сохранения JSON лога
        csv_log_path: Путь для сохранения CSV лога
        logger: Логгер для записи сообщений
        
    Returns:
        Dict[str, Dict]: Маппинг имен файлов и информации о загрузке
    """
    start_time = time.time()
    total_size = 0
    processed_files = 0
    failed_files = 0
    upload_log: Dict[str, Dict] = {}
    
    # Проверяем существование директории
    if not image_dir.exists():
        logger.error(f"❌ Папка {image_dir} не найдена!")
        return upload_log

    # Создаем директории для логов
    json_log_path.parent.mkdir(parents=True, exist_ok=True)
    csv_log_path.parent.mkdir(parents=True, exist_ok=True)

    # Инициализируем загрузчик
    uploader = IPFSFactory().get_storage()
    logger.info(f"🔧 Инициализирован загрузчик: {uploader.__class__.__name__}")

    # Собираем информацию о файлах
    files = list(image_dir.iterdir())
    logger.info(f"📊 Найдено файлов для обработки: {len(files)}")

    # Проходимся по всем файлам в папке
    for file_path in files:
        if not file_path.is_file():
            continue
            
        file_start_time = time.time()
        file_info = {
            "size": 0,
            "mime_type": None,
            "status": "failed",
            "error": None,
            "upload_time": 0,
            "cid": None
        }

        try:
            # Валидация файла
            file_size = file_path.stat().st_size
            file_info["size"] = file_size
            total_size += file_size
            
            mime_type, _ = mimetypes.guess_type(str(file_path))
            file_info["mime_type"] = mime_type
            
            error = validate_file(file_path)
            if error:
                file_info["error"] = error
                logger.warning(f"⚠️ Пропуск {file_path.name}: {error}")
                failed_files += 1
                continue

            logger.info(f"🚀 Загружаем {file_path.name} (размер: {file_size/1024:.1f}KB, тип: {mime_type})")
            
            try:
                # Загрузка файла
                cid = uploader.upload_file(str(file_path))
                upload_time = time.time() - file_start_time
                
                file_info.update({
                    "status": "success",
                    "upload_time": upload_time,
                    "cid": cid
                })
                
                logger.info(f"✅ Загружен {file_path.name} -> {cid} за {upload_time:.1f}с")
                processed_files += 1
                
            except Exception as e:
                error_msg = f"Ошибка при загрузке: {str(e)}"
                file_info["error"] = error_msg
                logger.error(f"❌ Ошибка при загрузке {file_path.name}: {error_msg}")
                failed_files += 1
            
        finally:
            upload_log[file_path.name] = file_info

    # Сохраняем расширенный лог в JSON
    with open(json_log_path, "w", encoding="utf-8") as f:
        json.dump(upload_log, f, ensure_ascii=False, indent=2)

    # Сохраняем базовый лог в CSV для совместимости
    with open(csv_log_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["File Name", "CID", "Status", "Size (bytes)", "Upload Time (s)"])
        for file_name, info in upload_log.items():
            writer.writerow([
                file_name,
                info.get("cid", ""),
                info["status"],
                info["size"],
                f"{info.get('upload_time', 0):.1f}"
            ])

    total_time = time.time() - start_time
    
    # Итоговая статистика
    logger.info("\n" + "="*50)
    logger.info("📊 Итоги загрузки:")
    logger.info(f"✅ Успешно загружено: {processed_files} файлов")
    logger.info(f"❌ Ошибок загрузки: {failed_files}")
    logger.info(f"📦 Общий размер: {total_size/1024/1024:.1f}MB")
    logger.info(f"⏱️ Общее время: {total_time:.1f}с")
    logger.info(f"📈 Средняя скорость: {(total_size/1024/1024)/total_time:.1f}MB/s")
    logger.info("="*50)
    
    return upload_log

def main():
    """Точка входа для самостоятельного запуска скрипта"""
    image_dir = Path(CATALOG_DIR)
    json_log_path = Path(LOGS_DIR) / "images_upload_log.json"
    csv_log_path = Path(LOGS_DIR) / "images_upload_log.csv"
    
    upload_log = upload_images(image_dir, json_log_path, csv_log_path, logger)
    
    logger.info("📝 Подробный лог сохранён в:")
    logger.info(f"   - {json_log_path}")
    logger.info(f"   - {csv_log_path}")
    logger.info(f"   - {Path(LOGS_DIR) / 'upload_catalog.log'}")

def process_catalog_images(images_dir: str, output_json: str, log_json: str, log_csv: str) -> Dict[str, str]:
    """
    Фасадный метод для загрузки изображений каталога в IPFS
    
    Args:
        images_dir: Путь к директории с изображениями
        output_json: Путь для сохранения маппинга CID'ов
        log_json: Путь для JSON лога
        log_csv: Путь для CSV лога
        
    Returns:
        Dict[str, str]: Маппинг имен файлов и их CID'ов
    """
    # Создаем локальный логгер для фасадного метода
    local_logger = logging.getLogger(__name__ + ".facade")
    local_logger.setLevel(logging.INFO)
    
    # Загружаем изображения
    upload_log = upload_images(
        image_dir=Path(images_dir),
        json_log_path=Path(log_json),
        csv_log_path=Path(log_csv),
        logger=local_logger
    )
    
    # Создаем упрощенный маппинг для вывода
    cid_mapping = {
        filename: info["cid"]
        for filename, info in upload_log.items()
        if info["status"] == "success" and info["cid"]
    }
    
    # Сохраняем маппинг CID'ов
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(cid_mapping, f, ensure_ascii=False, indent=2)
    
    return cid_mapping

if __name__ == "__main__":
    main()
