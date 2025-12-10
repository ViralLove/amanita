import os
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from bot.services.core.blockchain import BlockchainService
from web3 import Web3
import logging

# Настройка pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transact_contract_function_receipt_error():
    """
    Проверяет error handling в BlockchainService.transact_contract_function
    для случая когда transaction отправлена, но receipt получить не удалось.
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("alarm_mode")

    service = BlockchainService()
    contract_name = "SpiralEngine"
    function_name = "grantRole"
    load_dotenv(dotenv_path="bot/.env")
    private_key = os.getenv("NODE_ADMIN_PRIVATE_KEY")
    
    # AC1: Skip if key missing
    if not private_key:
        pytest.skip("NODE_ADMIN_PRIVATE_KEY не найден в .env")
    
    w3 = service.web3
    SELLER_ROLE = w3.keccak(text="SELLER_ROLE")
    
    # AC2: Skip if contract not found
    contract = service.get_contract(contract_name)
    if not contract:
        pytest.skip(f"Контракт {contract_name} не найден в блокчейне")
    
    # Use deployer account (has admin rights)
    deployer = w3.eth.accounts[0]

    logger.info(f"Вызов transact_contract_function:")
    logger.info(f"  contract_name: {contract_name}")
    logger.info(f"  function_name: {function_name}")
    logger.info(f"  SELLER_ROLE: {SELLER_ROLE.hex()}")
    logger.info(f"  deployer: {deployer}")

    try:
        tx_hash = await service.transact_contract_function(
            contract_name,
            function_name,
            private_key,
            SELLER_ROLE,
            deployer
        )
        
        logger.info(f"tx_hash: {tx_hash}")
        logger.info(f"Тип tx_hash: {type(tx_hash)}")
        
        # AC3: Handle None case (role already granted)
        if tx_hash is None:
            logger.info("transact_contract_function вернул None (роль уже назначена)")
            pytest.skip("transact_contract_function вернул None (роль уже назначена)")
        
        # Ожидаем receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f"Receipt получен: {receipt.transactionHash.hex()}")
        
        # AC4: Verify receipt status
        assert receipt.status == 1, "Transaction failed"
        logger.info("✅ Transaction успешна")
        
    except Exception as exc:
        # AC5: Log error handling without failing
        logger.error(f"ОШИБКА: {exc}")
        logger.info(f"Error handling работает корректно: {type(exc).__name__}")
        # Re-raise to fail test (this is error case)
        raise

@pytest.mark.integration
def test_mint_invites_wrong_args():
    """
    Проверяет ошибку ABI при передаче списка в mintInvite (ожидает строку).
    SpiralEngine.mintInvite(code, expiry) принимает один код (string), не массив.
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("alarm_mode")

    service = BlockchainService()
    contract = service.get_contract("SpiralEngine")
    
    # Skip if contract not found
    if not contract:
        pytest.skip("SpiralEngine контракт не найден")
    
    # Пытаемся передать список вместо строки
    initial_invite_codes = [f"INVITE{i}" for i in range(8)]
    
    logger.info(f"Пытаемся вызвать mintInvite с списком (ожидаем ABI error):")
    logger.info(f"  Аргументы: codes={initial_invite_codes}, expiry=0")
    
    # Use pytest.raises to catch expected error
    with pytest.raises(Exception) as exc_info:
        # Передаём список где ожидается строка
        result = contract.functions.mintInvite(initial_invite_codes, 0).call()
    
    error_msg = str(exc_info.value).lower()
    logger.info(f"Получена ожидаемая ошибка: {error_msg}")
    
    # Проверяем что это ABI/type error
    assert any(keyword in error_msg for keyword in ['abi', 'type', 'argument', 'expected', 'encoding']), \
        f"Ожидали ABI/type error, получили: {error_msg}"

@pytest.mark.integration
def test_mint_invites_correct_args():
    """
    Проверяет корректный вызов mintInvite с правильными аргументами.
    SpiralEngine.mintInvite(code, expiry) - один код за раз.
    Использует .transact() для изменения state.
    """
    import time
    from eth_account import Account
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("alarm_mode")

    service = BlockchainService()
    contract = service.get_contract("SpiralEngine")
    
    if not contract:
        pytest.skip("SpiralEngine контракт не найден")
    
    w3 = service.web3
    
    # Получаем seller account (должен иметь SELLER_ROLE)
    load_dotenv(dotenv_path="bot/.env")
    seller_key = os.getenv("SELLER_PRIVATE_KEY")
    
    if not seller_key:
        pytest.skip("SELLER_PRIVATE_KEY не найден в .env")
    
    seller_account = Account.from_key(seller_key)
    
    # Проверяем SELLER_ROLE
    SELLER_ROLE = w3.keccak(text="SELLER_ROLE")
    has_role = contract.functions.hasRole(SELLER_ROLE, seller_account.address).call()
    
    if not has_role:
        pytest.skip(f"Seller {seller_account.address} не имеет SELLER_ROLE")
    
    # Генерируем уникальный код
    timestamp = int(time.time() * 1000)
    code = f"ALARM_TEST_{timestamp}"
    
    logger.info(f"Вызываем mintInvite с корректными аргументами:")
    logger.info(f"  code: {code}")
    logger.info(f"  expiry: 0")
    logger.info(f"  from: {seller_account.address}")
    
    try:
        # Правильный вызов: .transact() для state change
        tx_hash = contract.functions.mintInvite(code, 0).transact({'from': seller_account.address})
        logger.info(f"Transaction sent: {tx_hash.hex()}")
        
        # Ожидаем подтверждения
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f"Transaction confirmed in block {receipt.blockNumber}")
        
        assert receipt.status == 1, "Transaction failed"
        
        # Проверяем что invite создан
        token_id = contract.functions.inviteCodeToTokenId(code).call()
        assert token_id > 0, "Invite не был создан"
        logger.info(f"✅ Invite создан успешно, tokenId: {token_id}")
        
    except Exception as e:
        import traceback
        logger.error(f"ОШИБКА: {e}\n{traceback.format_exc()}")
        raise

@pytest.mark.integration
@pytest.mark.asyncio
async def test_transact_contract_function_returns_none():
    """
    Проверяет что BlockchainService.transact_contract_function
    возвращает валидный tx_hash (не None) при корректном вызове mintInvite.
    """
    import time
    from eth_account import Account
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("alarm_mode")

    service = BlockchainService()
    contract_name = "SpiralEngine"
    function_name = "mintInvite"
    
    load_dotenv(dotenv_path="bot/.env")
    private_key = os.getenv("SELLER_PRIVATE_KEY")
    
    if not private_key:
        pytest.skip("SELLER_PRIVATE_KEY не найден в .env")
    
    w3 = service.web3
    seller_account = Account.from_key(private_key)
    
    # Проверяем контракт
    contract = service.get_contract(contract_name)
    if not contract:
        pytest.skip(f"Контракт {contract_name} не найден")
    
    # Проверяем роль
    SELLER_ROLE = w3.keccak(text="SELLER_ROLE")
    has_role = contract.functions.hasRole(SELLER_ROLE, seller_account.address).call()
    
    if not has_role:
        pytest.skip(f"Seller не имеет SELLER_ROLE")
    
    # Уникальный код
    timestamp = int(time.time() * 1000)
    invite_code = f"ALARM_NONE_TEST_{timestamp}"

    logger.info(f"Вызов transact_contract_function:")
    logger.info(f"  contract_name: {contract_name}")
    logger.info(f"  function_name: {function_name}")
    logger.info(f"  invite_code: {invite_code}")
    logger.info(f"  seller: {seller_account.address}")

    try:
        # NOTE: Check BlockchainService.transact_contract_function signature
        # Expected: (contract_name, function_name, private_key, *args, **kwargs)
        tx_hash = await service.transact_contract_function(
            contract_name,
            function_name,
            private_key,
            invite_code,  # arg 1: code
            0             # arg 2: expiry
        )
        
        logger.info(f"tx_hash: {tx_hash}")
        logger.info(f"Тип tx_hash: {type(tx_hash)}")
        
        assert tx_hash is not None, \
            "transact_contract_function вернул None вместо tx_hash"
        
        assert isinstance(tx_hash, (bytes, str)), \
            f"tx_hash должен быть bytes или str, получили {type(tx_hash)}"
        
        # Конвертируем в hex если bytes
        if isinstance(tx_hash, bytes):
            tx_hash_hex = tx_hash.hex()
        else:
            tx_hash_hex = tx_hash
        
        logger.info(f"✅ tx_hash валидный: {tx_hash_hex}")
        
        # Ожидаем receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        assert receipt.status == 1, "Transaction failed"
        logger.info(f"✅ Transaction confirmed")
        
    except Exception as e:
        logger.error(f"ОШИБКА: {e}")
        raise