#!/usr/bin/env python3
"""
Validation script для проверки HashiCorp Vault integration.

Использование:
    # Тест localhost profile (загрузка из .env)
    python validate_vault_integration.py --profile localhost
    
    # Тест polygon profile (загрузка из Vault)
    VAULT_ADDR=... VAULT_TOKEN=... python validate_vault_integration.py --profile polygon
    
    # Dry-run (без реальной загрузки config.py)
    python validate_vault_integration.py --profile polygon --dry-run

Author: eslinko
Date: 2025-10-10
Related: ADR-001-hashicorp-vault-integration.md
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_localhost_profile():
    """
    Проверка localhost profile: загрузка из .env файла.
    
    Returns:
        bool: True если успешно, False если ошибки
    """
    logger.info("=" * 70)
    logger.info("🧪 ТЕСТ: Localhost Profile (загрузка из .env)")
    logger.info("=" * 70)
    
    # Проверка существования .env (в корне bot/)
    env_path = Path(__file__).parent.parent / ".env"  # bot/utility/../.env = bot/.env
    if not env_path.exists():
        logger.error(f"❌ .env файл не найден: {env_path}")
        logger.info("💡 Создайте .env файл с необходимыми переменными")
        return False
    
    logger.info(f"✅ .env файл найден: {env_path}")
    
    # Установка profile
    os.environ["DEPLOYMENT_PROFILE"] = "localhost"
    
    try:
        # Импорт config.py
        logger.info("📦 Импорт config.py...")
        import config
        
        # Проверка что DEPLOYMENT_PROFILE = localhost
        if config.DEPLOYMENT_PROFILE != "localhost":
            logger.error(f"❌ DEPLOYMENT_PROFILE != 'localhost': {config.DEPLOYMENT_PROFILE}")
            return False
        
        logger.info(f"✅ DEPLOYMENT_PROFILE: {config.DEPLOYMENT_PROFILE}")
        
        # Проверка SELLER_PRIVATE_KEY
        if not config.SELLER_PRIVATE_KEY:
            logger.error("❌ SELLER_PRIVATE_KEY не загружен")
            return False
        
        if not config.SELLER_PRIVATE_KEY.startswith("0x"):
            logger.error(f"❌ SELLER_PRIVATE_KEY должен начинаться с 0x: {config.SELLER_PRIVATE_KEY[:10]}...")
            return False
        
        if len(config.SELLER_PRIVATE_KEY) != 66:
            logger.error(f"❌ SELLER_PRIVATE_KEY неправильная длина: {len(config.SELLER_PRIVATE_KEY)} (ожидается 66)")
            return False
        
        logger.info(f"✅ SELLER_PRIVATE_KEY загружен: {config.SELLER_PRIVATE_KEY[:10]}...{config.SELLER_PRIVATE_KEY[-4:]}")
        
        # Проверка ARWEAVE_PRIVATE_KEY (может быть None для localhost)
        if config.ARWEAVE_PRIVATE_KEY:
            logger.info(f"✅ ARWEAVE_PRIVATE_KEY загружен: {config.ARWEAVE_PRIVATE_KEY[:20]}...")
        else:
            logger.warning("⚠️ ARWEAVE_PRIVATE_KEY не установлен (опционально для localhost)")
        
        # Проверка что Vault НЕ использовался
        if hasattr(config, 'VAULT_AVAILABLE') and config.VAULT_AVAILABLE:
            logger.info("ℹ️ VaultService доступен, но НЕ используется для localhost profile")
        
        logger.info("=" * 70)
        logger.info("✅ LOCALHOST PROFILE: ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
        logger.info("=" * 70)
        return True
        
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта config.py: {e}")
        logger.info("💡 Убедитесь что все зависимости установлены: pip install -r requirements.txt")
        return False
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_polygon_profile(dry_run=False):
    """
    Проверка polygon profile: загрузка из Vault.
    
    Args:
        dry_run: Если True, только проверка переменных без реальной загрузки config.py
        
    Returns:
        bool: True если успешно, False если ошибки
    """
    logger.info("=" * 70)
    logger.info("🧪 ТЕСТ: Polygon Profile (загрузка из Vault)")
    logger.info("=" * 70)
    
    # Проверка Vault environment variables
    vault_addr = os.getenv("VAULT_ADDR")
    vault_token = os.getenv("VAULT_TOKEN")
    vault_path = os.getenv("VAULT_PATH", "secret/data/amanita")
    
    logger.info(f"🔐 VAULT_ADDR: {vault_addr if vault_addr else '❌ НЕ УСТАНОВЛЕН'}")
    logger.info(f"🔐 VAULT_TOKEN: {'✅ Установлен' if vault_token else '❌ НЕ УСТАНОВЛЕН'}")
    logger.info(f"🔐 VAULT_PATH: {vault_path}")
    
    if not vault_addr:
        logger.error("❌ VAULT_ADDR не установлен")
        logger.info("💡 Установите: export VAULT_ADDR='https://....vault.hashicorp.cloud:8200'")
        return False
    
    if not vault_token:
        logger.error("❌ VAULT_TOKEN не установлен")
        logger.info("💡 Установите: export VAULT_TOKEN='hvs.XXXXXXXXX'")
        return False
    
    logger.info("✅ Все Vault переменные установлены")
    
    # Dry-run mode: только проверка переменных
    if dry_run:
        logger.info("🏃 DRY-RUN mode: пропускаем реальное подключение к Vault")
        logger.info("=" * 70)
        logger.info("✅ DRY-RUN: ПРОВЕРКА ПЕРЕМЕННЫХ ПРОЙДЕНА")
        logger.info("=" * 70)
        return True
    
    # Проверка hvac library
    try:
        import hvac
        logger.info("✅ hvac library установлена")
    except ImportError:
        logger.error("❌ hvac library не установлена")
        logger.info("💡 Установите: pip install hvac>=2.1.0")
        return False
    
    # Тест прямого подключения к Vault (без config.py)
    logger.info("🔗 Тест прямого подключения к Vault...")
    try:
        client = hvac.Client(url=vault_addr, token=vault_token)
        
        if not client.is_authenticated():
            logger.error("❌ Vault authentication failed")
            logger.info("💡 Проверьте VAULT_TOKEN (возможно истек TTL)")
            return False
        
        logger.info("✅ Vault authentication успешна")
        
        # Чтение секретов напрямую
        logger.info("📥 Чтение секретов из Vault...")
        response = client.secrets.kv.v2.read_secret_version(
            path=vault_path.replace("secret/data/", "")
        )
        
        if not response or 'data' not in response:
            logger.error("❌ Vault response не содержит 'data'")
            return False
        
        data = response['data']['data']
        logger.info(f"✅ Прочитано {len(data)} секретов из Vault")
        
        # Проверка наличия ключей
        if "SELLER_PRIVATE_KEY" not in data:
            logger.error("❌ SELLER_PRIVATE_KEY не найден в Vault")
            logger.info("💡 Создайте секрет в Vault UI: secret/amanita/SELLER_PRIVATE_KEY")
            return False
        
        logger.info(f"✅ SELLER_PRIVATE_KEY найден: {data['SELLER_PRIVATE_KEY'][:10]}...")
        
        if "ARWEAVE_PRIVATE_KEY" not in data:
            logger.warning("⚠️ ARWEAVE_PRIVATE_KEY не найден в Vault (опционально)")
        else:
            logger.info(f"✅ ARWEAVE_PRIVATE_KEY найден: {data['ARWEAVE_PRIVATE_KEY'][:20]}...")
        
    except hvac.exceptions.InvalidPath as e:
        logger.error(f"❌ Vault path не найден: {vault_path}")
        logger.info("💡 Проверьте что секреты созданы по правильному пути")
        return False
    except hvac.exceptions.VaultError as e:
        logger.error(f"❌ Vault error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка при подключении к Vault: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Тест через config.py
    logger.info("📦 Тест через config.py...")
    
    # Установка profile
    os.environ["DEPLOYMENT_PROFILE"] = "polygon"
    
    try:
        # Импорт config.py
        import config
        
        # Проверка что DEPLOYMENT_PROFILE = polygon
        if config.DEPLOYMENT_PROFILE != "polygon":
            logger.error(f"❌ DEPLOYMENT_PROFILE != 'polygon': {config.DEPLOYMENT_PROFILE}")
            return False
        
        logger.info(f"✅ DEPLOYMENT_PROFILE: {config.DEPLOYMENT_PROFILE}")
        
        # Проверка SELLER_PRIVATE_KEY
        if not config.SELLER_PRIVATE_KEY:
            logger.error("❌ SELLER_PRIVATE_KEY не загружен из Vault")
            return False
        
        if not config.SELLER_PRIVATE_KEY.startswith("0x"):
            logger.error(f"❌ SELLER_PRIVATE_KEY должен начинаться с 0x: {config.SELLER_PRIVATE_KEY[:10]}...")
            return False
        
        logger.info(f"✅ SELLER_PRIVATE_KEY загружен из Vault: {config.SELLER_PRIVATE_KEY[:10]}...{config.SELLER_PRIVATE_KEY[-4:]}")
        
        # Проверка ARWEAVE_PRIVATE_KEY
        if config.ARWEAVE_PRIVATE_KEY:
            logger.info(f"✅ ARWEAVE_PRIVATE_KEY загружен из Vault: {config.ARWEAVE_PRIVATE_KEY[:20]}...")
        else:
            logger.warning("⚠️ ARWEAVE_PRIVATE_KEY не загружен (может быть не установлен в Vault)")
        
        logger.info("=" * 70)
        logger.info("✅ POLYGON PROFILE: ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
        logger.info("=" * 70)
        return True
        
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта config.py: {e}")
        logger.info("💡 Убедитесь что все зависимости установлены: pip install -r requirements.txt")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки config.py с Vault: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Validation script для HashiCorp Vault integration"
    )
    parser.add_argument(
        "--profile",
        choices=["localhost", "polygon"],
        default="localhost",
        help="Deployment profile для тестирования (default: localhost)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run mode: только проверка переменных без реального подключения"
    )
    
    args = parser.parse_args()
    
    logger.info("")
    logger.info("🚀 Vault Integration Validation Script")
    logger.info("=" * 70)
    logger.info(f"Profile: {args.profile}")
    logger.info(f"Dry-run: {args.dry_run}")
    logger.info("=" * 70)
    logger.info("")
    
    if args.profile == "localhost":
        success = validate_localhost_profile()
    else:
        success = validate_polygon_profile(dry_run=args.dry_run)
    
    logger.info("")
    if success:
        logger.info("🎉 Validation completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Validation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

