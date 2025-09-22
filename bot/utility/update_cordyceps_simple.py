#!/usr/bin/env python3
"""
Простой скрипт для обновления продуктов кордицепса.
Загружает исправленные JSON файлы в IPFS и обновляет контракт.
"""

import sys
import os
import json
import logging
from pathlib import Path
from web3 import Web3

# Добавляем корневую директорию в путь
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.core.ipfs_factory import IPFSFactory

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Конфигурация
PRODUCT_IDS = {
    "cordyceps_militaris_powder": 41,
    "cordyceps_militaris_dried_bodies": 42
}

# Адреса контрактов (из .env)
PRODUCT_REGISTRY_ADDRESS = "0x8059081F8F668e14AD35E21674DCdbe0Aa3A80dC"
SELLER_ADDRESS = "0xF0ad0a870d83D83fcaD2158C8d0315033B74c82A"

# ABI для ProductRegistry (только нужные методы)
PRODUCT_REGISTRY_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "productId", "type": "uint256"},
            {"internalType": "string", "name": "newIpfsCID", "type": "string"},
            {"internalType": "uint256", "name": "newPrice", "type": "uint256"}
        ],
        "name": "updateProduct",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

def load_json_file(file_path):
    """Загружает JSON файл"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

async def upload_json_to_ipfs(json_data):
    """Загружает JSON данные в IPFS"""
    logger.info("📤 Загружаем JSON в IPFS...")
    
    storage_service = IPFSFactory().get_storage()
    # Загружаем как объект, а не как строку
    cid = await storage_service.upload_json(json_data)
    
    logger.info(f"✅ JSON загружен в IPFS: {cid}")
    return cid

def connect_to_contract():
    """Подключается к контракту ProductRegistry"""
    logger.info("🔗 Подключаемся к блокчейну...")
    
    # Используем Polygon RPC из переменных окружения
    polygon_rpc = os.getenv('POLYGON_MAINNET_RPC', 'https://polygon-rpc.com')
    w3 = Web3(Web3.HTTPProvider(polygon_rpc))
    
    if not w3.is_connected():
        raise Exception("Не удалось подключиться к блокчейну")
    
    logger.info("✅ Подключение к блокчейну установлено")
    
    # Загружаем приватный ключ продавца из переменных окружения
    private_key = os.getenv('SELLER_PRIVATE_KEY')
    if not private_key:
        raise Exception("SELLER_PRIVATE_KEY не найден в переменных окружения")
    
    account = w3.eth.account.from_key(private_key)
    logger.info(f"👤 Аккаунт: {account.address}")
    
    # Подключаемся к контракту
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(PRODUCT_REGISTRY_ADDRESS),
        abi=PRODUCT_REGISTRY_ABI
    )
    
    return w3, contract, account

def update_product_in_contract(w3, contract, account, product_id, new_cid, price=888):
    """Обновляет продукт в контракте"""
    logger.info(f"🔄 Обновляем продукт {product_id} с CID {new_cid}")
    
    # Строим транзакцию
    transaction = contract.functions.updateProduct(
        product_id,
        new_cid,
        price
    ).build_transaction({
        'from': account.address,
        'gas': 500000,
        'gasPrice': w3.to_wei('50', 'gwei'),
        'nonce': w3.eth.get_transaction_count(account.address)
    })
    
    # Подписываем и отправляем транзакцию
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=account.key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    
    logger.info(f"📤 Транзакция отправлена: {tx_hash.hex()}")
    
    # Ждем подтверждения
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt.status == 1:
        logger.info(f"✅ Продукт {product_id} успешно обновлен!")
        logger.info(f"🔗 Транзакция: https://polygonscan.com/tx/{tx_hash.hex()}")
    else:
        raise Exception(f"Транзакция не удалась: {receipt}")
    
    return receipt

def main():
    """Основная функция"""
    try:
        logger.info("🚀 Начинаем обновление продуктов кордицепса...")
        
        # 1. Загружаем исправленные JSON файлы
        # Относительные пути к исправленным JSON файлам
        json_files = {
            "cordyceps_militaris_powder": "catalog/product_jsons/cordyceps_militaris_powder.json",
            "cordyceps_militaris_dried_bodies": "catalog/product_jsons/cordyceps_militaris_dried_bodies.json"
        }
        
        products_data = {}
        for business_id, product_id in PRODUCT_IDS.items():
            json_file_path = json_files[business_id]
            json_file = Path(json_file_path)
            
            if not json_file.exists():
                raise FileNotFoundError(f"Файл {json_file} не найден")
            
            products_data[business_id] = {
                'id': product_id,
                'data': load_json_file(json_file)
            }
            logger.info(f"📋 Загружен {business_id}: {json_file}")
        
        # 2. Загружаем JSON файлы в IPFS
        import asyncio
        uploaded_cids = {}
        for business_id, product_info in products_data.items():
            cid = asyncio.run(upload_json_to_ipfs(product_info['data']))
            uploaded_cids[business_id] = cid
        
        # 3. Подключаемся к контракту
        w3, contract, account = connect_to_contract()
        
        # 4. Обновляем продукты в контракте
        for business_id, product_info in products_data.items():
            product_id = product_info['id']
            new_cid = uploaded_cids[business_id]
            
            update_product_in_contract(w3, contract, account, product_id, new_cid)
        
        logger.info("🎉 Все продукты кордицепса успешно обновлены!")
        
        # Выводим результаты
        print("\n" + "="*60)
        print("📋 РЕЗУЛЬТАТЫ ОБНОВЛЕНИЯ КОРДИЦЕПСА")
        print("="*60)
        for business_id, product_info in products_data.items():
            print(f"✅ {business_id}:")
            print(f"   ID: {product_info['id']}")
            print(f"   Новый CID: {uploaded_cids[business_id]}")
        print("="*60)
        
    except Exception as e:
        logger.error(f"❌ Ошибка выполнения: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
