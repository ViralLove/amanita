import os
import pytest
from dotenv import load_dotenv
from bot.services.core.blockchain import BlockchainService
from web3 import Web3
import logging


def test_transact_contract_function_receipt_error():
    """
    Воспроизводит ошибку, если transact_contract_function возвращает не строку-хэш,
    а объект (например, SignedTransaction), как в тесте onboarding.
    Добавлено подробное логирование для диагностики.
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("alarm_mode")

    service = BlockchainService()
    contract_name = "InviteNFT"
    function_name = "grantRole"
    load_dotenv(dotenv_path="bot/.env")
    private_key = os.getenv("NODE_ADMIN_PRIVATE_KEY")
    assert private_key, "NODE_ADMIN_PRIVATE_KEY не найден в .env"
    w3 = service.web3
    SELLER_ROLE = w3.keccak(text="SELLER_ROLE")
    seller_account = w3.eth.accounts[0]

    logger.info(f"Вызов transact_contract_function с аргументами:")
    logger.info(f"  contract_name: {contract_name}")
    logger.info(f"  function_name: {function_name}")
    logger.info(f"  private_key: {'***' if private_key else None}")
    logger.info(f"  SELLER_ROLE: {SELLER_ROLE}")
    logger.info(f"  seller_account: {seller_account}")

    tx_hash = service.transact_contract_function(
        contract_name,
        function_name,
        private_key,
        SELLER_ROLE,
        seller_account
    )
    logger.info(f"Результат transact_contract_function (tx_hash): {tx_hash}")
    logger.info(f"Тип результата: {type(tx_hash)}")
    if hasattr(tx_hash, '__dict__'):
        logger.info(f"Атрибуты объекта tx_hash: {tx_hash.__dict__}")
    else:
        logger.info(f"tx_hash не имеет __dict__ (скорее всего это строка или bytes)")

    logger.info("Вызов w3.eth.wait_for_transaction_receipt(tx_hash)...")
    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f"Транзакция успешно подтверждена, receipt: {receipt}")
    except Exception as exc:
        logger.error(f"ОШИБКА при ожидании receipt: {exc}")
        raise

def test_mint_invites_wrong_args():
    """
    Воспроизводит ошибку ABI при неверной упаковке аргументов mintInvites,
    с подробным логированием для диагностики.
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("alarm_mode")

    service = BlockchainService()
    contract = service.get_contract("InviteNFT")
    initial_invite_codes = [f"INVITE{i}" for i in range(8)]
    args = [initial_invite_codes, 0]
    logger.info(f"Пробуем вызвать mintInvites с аргументами: {args} (type: {type(args)})")
    try:
        # Передаём [initial_invite_codes, 0] как один аргумент, а не два отдельных
        result = contract.functions.mintInvites([initial_invite_codes, 0]).call()
        logger.info(f"mintInvites вернул: {result}")
    except Exception as e:
        import traceback
        logger.error(f"ОШИБКА при вызове mintInvites: {e}\n{traceback.format_exc()}")
        raise

def test_mint_invites_correct_args():
    """
    Проверяет корректный вызов mintInvites с правильной упаковкой аргументов.
    Подробное логирование результата.
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("alarm_mode")

    service = BlockchainService()
    contract = service.get_contract("InviteNFT")
    initial_invite_codes = [f"INVITE{i}" for i in range(8)]
    logger.info(f"Пробуем вызвать mintInvites с аргументами: {initial_invite_codes}, 0")
    try:
        # Передаём два отдельных аргумента, как требует ABI
        result = contract.functions.mintInvites(initial_invite_codes, 0).call()
        logger.info(f"mintInvites вернул: {result}")
    except Exception as e:
        import traceback
        logger.error(f"ОШИБКА при вызове mintInvites: {e}\n{traceback.format_exc()}")
        raise

def test_transact_contract_function_returns_none():
    """
    Изолирует технический контекст бага: вызов transact_contract_function возвращает None вместо строки-хэша.
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("alarm_mode")

    service = BlockchainService()
    contract_name = "InviteNFT"
    function_name = "mintInvites"
    load_dotenv(dotenv_path="bot/.env")
    private_key = os.getenv("NODE_ADMIN_PRIVATE_KEY")
    assert private_key, "NODE_ADMIN_PRIVATE_KEY не найден в .env"
    w3 = service.web3
    seller_account = w3.eth.accounts[0]
    initial_invite_codes = [f"INVITE{i}" for i in range(8)]

    logger.info(f"Вызов transact_contract_function с аргументами:")
    logger.info(f"  contract_name: {contract_name}")
    logger.info(f"  function_name: {function_name}")
    logger.info(f"  private_key: {'***' if private_key else None}")
    logger.info(f"  initial_invite_codes: {initial_invite_codes}")
    logger.info(f"  seller_account: {seller_account}")

    tx_hash = service.transact_contract_function(
        contract_name,
        function_name,
        private_key,
        initial_invite_codes, 0,  # передаём два отдельных аргумента
        sender=seller_account
    )
    logger.info(f"Результат transact_contract_function (tx_hash): {tx_hash}")
    logger.info(f"Тип результата: {type(tx_hash)}")
    if hasattr(tx_hash, '__dict__'):
        logger.info(f"Атрибуты объекта tx_hash: {tx_hash.__dict__}")
    else:
        logger.info(f"tx_hash не имеет __dict__ (скорее всего это строка или bytes)")

    assert tx_hash is not None, "transact_contract_function вернул None вместо строки-хэша"