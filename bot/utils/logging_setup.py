import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import json

def setup_logging(log_level="INFO", log_file=None, max_size=10485760, backup_count=5):
    logger = logging.getLogger("amanita_api")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Очищаем существующие обработчики
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Файловый обработчик
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_size, backupCount=backup_count, encoding='utf-8'
        )
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                for key, value in record.__dict__.items():
                    if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                                   'filename', 'module', 'lineno', 'funcName', 'created',
                                   'msecs', 'relativeCreated', 'thread', 'threadName',
                                   'processName', 'process', 'getMessage', 'exc_info',
                                   'exc_text', 'stack_info']:
                        log_entry[key] = value
                return json.dumps(log_entry, ensure_ascii=False)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    return logger
