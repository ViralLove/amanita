import pytest
from web3 import Web3
from bot.tests.utils.invite_code_generator import generate_invite_code, validate_invite_code
from bot.tests.utils.error_assertions import assert_revert
from bot.tests.utils.activation_helpers import activate_user_with_retry
from eth_account import Account
import os
import time

# ============================================================================
# Helper функции для работы с SpiralEngine
# ============================================================================

def mint_invites_batch(contract, codes, expiry, sender, web3):
    """Helper для минтинга нескольких инвайтов (SpiralEngine не имеет batch функции)"""
    tx_hashes = []
    for code in codes:
        tx_hash = contract.functions.mintInvite(code, expiry).transact({'from': sender})
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        tx_hashes.append(tx_hash)
    return tx_hashes

def validate_invite_code_helper(contract, code, web3):
    """Helper для валидации инвайт-кода (замена отсутствующей публичной функции)"""
    exists = contract.functions.inviteCodeExists(code).call()
    if not exists:
        return False, "not_found"
    
    token_id = contract.functions.inviteCodeToTokenId(code).call()
    if token_id == 0:
        return False, "not_found"
    
    is_used = contract.functions.isInviteUsed(token_id).call()
    if is_used:
        return False, "already_used"
    
    expiry = contract.functions.inviteExpiry(token_id).call()
    current_time = web3.eth.get_block('latest').timestamp
    if expiry > 0 and expiry <= current_time:
        return False, "expired"
    
    return True, ""

def batch_validate_invite_codes(contract, codes, user, web3):
    """Helper для batch-валидации инвайт-кодов"""
    success = []
    reasons = []
    for code in codes:
        valid, reason = validate_invite_code_helper(contract, code, web3)
        success.append(valid)
        reasons.append(reason)
    return success, reasons

def ensure_activator_role(contract, web3, account, node_admin_key):
    """Helper для назначения ACTIVATOR_ROLE если её нет"""
    ACTIVATOR_ROLE = web3.keccak(text="ACTIVATOR_ROLE")
    has_role = contract.functions.hasRole(ACTIVATOR_ROLE, account.address).call()
    
    if has_role:
        return  # Роль уже есть
    
    # Try DEPLOYER_PRIVATE_KEY first, then NODE_ADMIN
    deployer_key = os.getenv("DEPLOYER_PRIVATE_KEY")
    admin_key = deployer_key or node_admin_key
    
    if not admin_key:
        pytest.skip(f"ACTIVATOR_ROLE required but no admin key available (tried DEPLOYER_PRIVATE_KEY, NODE_ADMIN_PRIVATE_KEY)")
    
    try:
        admin_account = Account.from_key(admin_key)
        tx_hash = contract.functions.grantRole(
            ACTIVATOR_ROLE, account.address
        ).transact({'from': admin_account.address})
        web3.eth.wait_for_transaction_receipt(tx_hash)
    except Exception as e:
        pytest.skip(f"Cannot grant ACTIVATOR_ROLE: {e}. Use account with ACTIVATOR_ROLE.")

def ensure_seller_role(contract, web3, account, node_admin_key):
    """Helper для назначения SELLER_ROLE если её нет"""
    SELLER_ROLE = web3.keccak(text="SELLER_ROLE")
    has_role = contract.functions.hasRole(SELLER_ROLE, account.address).call()
    
    if has_role:
        return  # Роль уже есть
    
    # Try DEPLOYER_PRIVATE_KEY first, then NODE_ADMIN
    deployer_key = os.getenv("DEPLOYER_PRIVATE_KEY")
    admin_key = deployer_key or node_admin_key
    
    key_source = "DEPLOYER_PRIVATE_KEY" if deployer_key else "NODE_ADMIN_PRIVATE_KEY"
    
    if not admin_key:
        pytest.skip(f"SELLER_ROLE required but no admin key available (tried DEPLOYER_PRIVATE_KEY, NODE_ADMIN_PRIVATE_KEY)")
    
    try:
        admin_account = Account.from_key(admin_key)
        print(f"🔐 Granting SELLER_ROLE using {key_source} (admin: {admin_account.address[:10]}...)")
        tx_hash = contract.functions.grantRole(
            SELLER_ROLE, account.address
        ).transact({'from': admin_account.address})
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"✅ SELLER_ROLE granted successfully (tx: {receipt.transactionHash.hex()[:10]}...)")
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed to grant SELLER_ROLE using {key_source}: {error_msg[:100]}")
        pytest.skip(f"Cannot grant SELLER_ROLE with {key_source}: {error_msg[:100]}")

# ============================================================================
# Тесты
# ============================================================================

@pytest.mark.integration
def test_onboarding_success(web3, spiral_engine_contract, seller_account):
    """Тест успешного онбординга (baseline + isolated account)"""
    # Настраиваем роли
    node_admin_key = os.getenv("NODE_ADMIN_PRIVATE_KEY")
    if node_admin_key:
        ensure_seller_role(spiral_engine_contract, web3, seller_account, node_admin_key)
    
    # Генерируем 12 уникальных инвайт-кодов с timestamp
    timestamp = int(time.time() * 1000)
    invite_codes = [generate_invite_code(prefix=f"test_{timestamp}_{i}") for i in range(12)]
    for code in invite_codes:
        assert validate_invite_code(code), "Сгенерированный код невалидный"
    
    # Минтим 12 инвайтов (SpiralEngine: по одному)
    mint_invites_batch(spiral_engine_contract, invite_codes, 0, seller_account.address, web3)
    
    # Проверяем что код уникальный (попытка минтить дубликат должна revert)
    with pytest.raises(Exception) as exc_info:
        spiral_engine_contract.functions.mintInvite(invite_codes[0], 0).transact({'from': seller_account.address})
    
    # Universal revert assertion (works with Anvil, testnet, mainnet)
    assert_revert(exc_info, "Ожидали revert при попытке минтить дубликат кода")

@pytest.mark.integration
def test_seller_can_mint_any_batch_size(web3, spiral_engine_contract, seller_account):
    """
    Селлер может минтить себе batch любого размера (1, 12, 100), сколько угодно раз.
    Проверяем, что owner всех инвайтов — seller_account.
    """
    # Обеспечиваем SELLER_ROLE
    ensure_seller_role(spiral_engine_contract, web3, seller_account, os.getenv("NODE_ADMIN_PRIVATE_KEY"))
    
    timestamp = int(time.time() * 1000)
    
    # Минтим 1 инвайт
    codes1 = [generate_invite_code(prefix=f"one_{timestamp}")] 
    mint_invites_batch(spiral_engine_contract, codes1, 0, seller_account.address, web3)
    token_id1 = spiral_engine_contract.functions.inviteCodeToTokenId(codes1[0]).call()
    assert spiral_engine_contract.functions.ownerOf(token_id1).call() == seller_account.address

    # Минтим 12 инвайтов
    codes12 = [generate_invite_code(prefix=f"dozen_{timestamp}_{i}") for i in range(12)]
    mint_invites_batch(spiral_engine_contract, codes12, 0, seller_account.address, web3)
    for code in codes12:
        token_id = spiral_engine_contract.functions.inviteCodeToTokenId(code).call()
        assert spiral_engine_contract.functions.ownerOf(token_id).call() == seller_account.address

    # Минтим 100 инвайтов
    codes100 = [generate_invite_code(prefix=f"hundred_{timestamp}_{i}") for i in range(100)]
    mint_invites_batch(spiral_engine_contract, codes100, 0, seller_account.address, web3)
    for code in codes100:
        token_id = spiral_engine_contract.functions.inviteCodeToTokenId(code).call()
        assert spiral_engine_contract.functions.ownerOf(token_id).call() == seller_account.address

@pytest.mark.integration
def test_invite_code_uniqueness_new(web3, spiral_engine_contract, seller_account):
    """
    Нельзя минтить один и тот же inviteCode дважды, даже в разных batch-ах.
    """
    # Обеспечиваем SELLER_ROLE
    ensure_seller_role(spiral_engine_contract, web3, seller_account, os.getenv("NODE_ADMIN_PRIVATE_KEY"))
    
    timestamp = int(time.time() * 1000)
    code = generate_invite_code(prefix=f"uniq_{timestamp}")
    mint_invites_batch(spiral_engine_contract, [code], 0, seller_account.address, web3)
    
    # Попытка минтить тот же код должна revert
    with pytest.raises(Exception) as exc_info:
        spiral_engine_contract.functions.mintInvite(code, 0).transact({'from': seller_account.address})
    
    # Universal revert assertion (works with Anvil, testnet, mainnet)
    assert_revert(exc_info, "Ожидали revert при попытке минтить дубликат кода")

@pytest.mark.integration
def test_unauthorized_mint_new(web3, spiral_engine_contract, user_account):
    """
    Не-seller не может минтить инвайты (mintInvite без SELLER_ROLE).
    """
    timestamp = int(time.time() * 1000)
    code = generate_invite_code(prefix=f"unauth_{timestamp}")
    
    # Проверяем что user_account НЕ имеет SELLER_ROLE
    SELLER_ROLE = web3.keccak(text="SELLER_ROLE")
    has_role = spiral_engine_contract.functions.hasRole(SELLER_ROLE, user_account.address).call()
    if has_role:
        pytest.skip("user_account имеет SELLER_ROLE, тест не применим")
    
    # Попытка минтить должна revert
    with pytest.raises(Exception) as exc_info:
        spiral_engine_contract.functions.mintInvite(code, 0).transact({'from': user_account.address})
    
    # Universal revert assertion (works with Anvil, testnet, mainnet)
    assert_revert(exc_info, "Ожидали revert для unauthorized mint")

@pytest.mark.integration
def test_activation_and_new_invites(web3, spiral_engine_contract, seller_account, network_growth_context):
    """
    Activator активирует пользователя используя динамически созданный invite.
    Uses network_growth_context для state-agnostic testing + exponential growth.
    
    ⚠️ ТРЕБУЕТ CAPACITY: Тест активирует пользователя, нужен активатор с capacity > 0.
    При насыщении сети тест скипается.
    См: bot/docs/analysis/doc-network-bridge-mechanism-architecture.md#режим-гибернации
    """
    # Проверка наличия capacity перед тестом
    pool = network_growth_context['pool']
    gaps = pool.tracker.find_bridge_gaps(min_gap_size=1, max_gaps=2)
    if len(gaps) < 2:
        pytest.skip(
            f"Insufficient capacity in network: found {len(gaps)} gaps, need at least 2. "
            f"Network may be fully saturated. "
            f"See: bot/docs/analysis/doc-network-bridge-mechanism-architecture.md#режим-гибернации "
            f"for details on restoring network state."
        )
    
    # Get activator + invite from network growth pool
    activator = network_growth_context['activator']
    invite_code = network_growth_context['invite_code']
    
    # Новый изолированный пользователь
    fresh_user = web3.eth.account.create()
    
    # Генерируем 12 новых инвайтов для user
    timestamp = int(time.time() * 1000)
    new_codes = [generate_invite_code(prefix=f"user12_{timestamp}_{i}") for i in range(12)]
    
    # Активация через activateUser с retry механизмом (activator == minter)
    tx_hash, activator, invite_code = activate_user_with_retry(
        spiral_engine_contract,
        invite_code,
        fresh_user.address,
        new_codes,
        0,
        activator,
        pool,
        web3,
        max_retries=3
    )
    
    # Проверяем, что все новые инвайты принадлежат user
    for c in new_codes:
        token_id = spiral_engine_contract.functions.inviteCodeToTokenId(c).call()
        assert spiral_engine_contract.functions.ownerOf(token_id).call() == fresh_user.address
    
    # Повторная активация — ошибка (user уже активирован)
    # Get another invite from pool
    duplicate_activator, duplicate_invite = pool.get_next()
    duplicate_codes = [generate_invite_code(prefix=f"dup_{timestamp}_{i}") for i in range(12)]
    with pytest.raises(Exception) as exc_info:
        spiral_engine_contract.functions.activateUser(
            duplicate_invite, fresh_user.address, duplicate_codes, 0
        ).transact({'from': duplicate_activator.address})
    
    # Universal revert assertion (works with Anvil, testnet, mainnet)
    assert_revert(exc_info, "Ожидали revert при повторной активации")

@pytest.mark.integration
def test_batch_invites_minted_event(web3, spiral_engine_contract, seller_account):
    """
    Проверяем событие InviteMinted для каждого минтинга.
    SpiralEngine emits InviteMinted (single) per invite, not BatchInvitesMinted.
    """
    # Обеспечиваем SELLER_ROLE
    ensure_seller_role(spiral_engine_contract, web3, seller_account, os.getenv("NODE_ADMIN_PRIVATE_KEY"))
    
    timestamp = int(time.time() * 1000)
    codes = [generate_invite_code(prefix=f"event_{timestamp}_{i}") for i in range(5)]
    
    # Минтим по одному и собираем receipts
    receipts = []
    for code in codes:
        tx_hash = spiral_engine_contract.functions.mintInvite(code, 0).transact({'from': seller_account.address})
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        receipts.append(receipt)
    
    # Проверяем события InviteMinted для каждого минтинга
    for i, receipt in enumerate(receipts):
        events = spiral_engine_contract.events.InviteMinted().process_receipt(receipt)
        assert len(events) == 1, f"Должно быть ровно 1 событие InviteMinted для кода {codes[i]}"
        event = events[0]['args']
        # SpiralEngine event: InviteMinted(address indexed minter, uint256 indexed tokenId, string inviteCode, uint256 expiry)
        assert event['minter'] == seller_account.address, f"Minter должен быть seller_account"
        assert event['inviteCode'] == codes[i], f"InviteCode должен соответствовать {codes[i]}"
        assert 'tokenId' in event, "TokenId должен присутствовать в событии"
        assert event['tokenId'] > 0, "TokenId должен быть положительным"

@pytest.mark.integration
def test_batch_with_duplicates_reverts(web3, spiral_engine_contract, seller_account):
    """
    Минтинг с дублирующимся inviteCode — revert.
    SpiralEngine: mintInvite single, поэтому проверяем что второй вызов с тем же кодом revert'ит.
    """
    # Обеспечиваем SELLER_ROLE
    ensure_seller_role(spiral_engine_contract, web3, seller_account, os.getenv("NODE_ADMIN_PRIVATE_KEY"))
    
    timestamp = int(time.time() * 1000)
    code = generate_invite_code(prefix=f"dup_{timestamp}")
    
    # Первый минт должен пройти
    tx_hash = spiral_engine_contract.functions.mintInvite(code, 0).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Второй минт с тем же кодом должен revert
    with pytest.raises(Exception) as exc_info:
        spiral_engine_contract.functions.mintInvite(code, 0).transact({'from': seller_account.address})
    
    # Universal revert assertion (works with Anvil, testnet, mainnet)
    assert_revert(exc_info, "Ожидали revert при повторном минте")

@pytest.mark.integration
def test_activate_and_mint_requires_12_invites(web3, spiral_engine_contract, seller_account, network_growth_context):
    """
    activateUser должен минтить ровно 12 новых инвайтов, иначе revert.
    Uses network_growth_context для dynamic activator selection.
    
    ⚠️ ТРЕБУЕТ CAPACITY: Тест активирует пользователя, нужны активаторы с capacity > 0.
    При насыщении сети тест скипается.
    См: bot/docs/analysis/doc-network-bridge-mechanism-architecture.md#режим-гибернации
    """
    # Проверка наличия capacity перед тестом
    pool = network_growth_context['pool']
    gaps = pool.tracker.find_bridge_gaps(min_gap_size=1, max_gaps=3)
    if len(gaps) < 3:
        pytest.skip(
            f"Insufficient capacity in network: found {len(gaps)} gaps, need at least 3. "
            f"Network may be fully saturated. "
            f"See: bot/docs/analysis/doc-network-bridge-mechanism-architecture.md#режим-гибернации "
            f"for details on restoring network state."
        )
    
    # Get 3 invites from pool для тестирования (< 12, > 12, == 12)
    
    act1, invite_code_11 = pool.get_next()
    act2, invite_code_13 = pool.get_next()
    act3, invite_code_12 = pool.get_next()
    
    fresh_user = web3.eth.account.create()
    timestamp = int(time.time() * 1000)
    
    # Меньше 12 — ошибка
    codes11 = [generate_invite_code(prefix=f"less_{timestamp}_{i}") for i in range(11)]
    with pytest.raises(Exception) as exc_info:
        spiral_engine_contract.functions.activateUser(
            invite_code_11, fresh_user.address, codes11, 0
        ).transact({'from': act1.address})
    
    # Universal revert assertion (works with Anvil, testnet, mainnet)
    assert_revert(exc_info, "Ожидали revert при передаче <12 кодов")
    
    # Больше 12 — ошибка
    codes13 = [generate_invite_code(prefix=f"more_{timestamp}_{i}") for i in range(13)]
    with pytest.raises(Exception) as exc_info:
        spiral_engine_contract.functions.activateUser(
            invite_code_13, fresh_user.address, codes13, 0
        ).transact({'from': act2.address})
    
    # Universal revert assertion (works with Anvil, testnet, mainnet)
    assert_revert(exc_info, "Ожидали revert при передаче >12 кодов")
    
    # Ровно 12 — проходит (с retry механизмом)
    codes12 = [generate_invite_code(prefix=f"ok12_{timestamp}_{i}") for i in range(12)]
    tx_hash, act3, invite_code_12 = activate_user_with_retry(
        spiral_engine_contract,
        invite_code_12,
        fresh_user.address,
        codes12,
        0,
        act3,
        pool,
        web3,
        max_retries=3
    )
    for c in codes12:
        token_id = spiral_engine_contract.functions.inviteCodeToTokenId(c).call()
        assert spiral_engine_contract.functions.ownerOf(token_id).call() == fresh_user.address

@pytest.mark.integration
def test_activation_of_nonexistent_code_reverts_new(web3, spiral_engine_contract, seller_account):
    """
    Попытка активировать несуществующий inviteCode — revert.
    """
    # Обеспечиваем ACTIVATOR_ROLE
    ensure_activator_role(spiral_engine_contract, web3, seller_account, os.getenv("NODE_ADMIN_PRIVATE_KEY"))
    
    fresh_user = web3.eth.account.create()
    timestamp = int(time.time() * 1000)
    fake_code = f"not_exist_{timestamp}_{os.urandom(4).hex()}"
    codes = [generate_invite_code(prefix=f"new_{timestamp}_{i}") for i in range(12)]
    
    with pytest.raises(Exception) as exc_info:
        spiral_engine_contract.functions.activateUser(
            fake_code, fresh_user.address, codes, 0
        ).transact({'from': seller_account.address})
    
    # Universal revert assertion (works with Anvil, testnet, mainnet)
    assert_revert(exc_info, "Ожидали revert при активации несуществующим кодом")

@pytest.mark.integration
def test_contract_metadata(web3, spiral_engine_contract):
    """Проверка базовых метаданных контракта"""
    assert spiral_engine_contract.functions.name().call() == "SpiralInvite"
    assert spiral_engine_contract.functions.symbol().call() == "SPIRAL"

@pytest.mark.integration
def test_soulbound_mechanism(web3, spiral_engine_contract, seller_account):
    """
    Тест механизма Soulbound Token:
    - Можно минтить (from == address(0))
    - Можно сжигать (to == address(0))
    - Нельзя передавать между адресами
    """
    # Обеспечиваем SELLER_ROLE
    ensure_seller_role(spiral_engine_contract, web3, seller_account, os.getenv("NODE_ADMIN_PRIVATE_KEY"))
    
    # Минтим инвайт с уникальным префиксом
    timestamp = int(time.time() * 1000)
    code = generate_invite_code(prefix=f"soul_{timestamp}")
    tx_hash = spiral_engine_contract.functions.mintInvite(code, 0).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    token_id = spiral_engine_contract.functions.inviteCodeToTokenId(code).call()
    
    # Проверяем что токен принадлежит seller_account
    assert spiral_engine_contract.functions.ownerOf(token_id).call() == seller_account.address
    
    # Создаём изолированный account для попытки передачи
    fresh_user = web3.eth.account.create()
    
    # Пытаемся передать токен - должно быть отклонено
    with pytest.raises(Exception) as exc_info:
        spiral_engine_contract.functions.transferFrom(
            seller_account.address,
            fresh_user.address,
            token_id
        ).transact({'from': seller_account.address})
    
    # Universal revert assertion (works with Anvil, testnet, mainnet)
    assert_revert(exc_info, "Expected revert for soulbound transfer")
    
    # Проверяем safeTransferFrom - тоже должно быть отклонено
    with pytest.raises(Exception) as exc_info:
        spiral_engine_contract.functions.safeTransferFrom(
            seller_account.address,
            fresh_user.address,
            token_id
        ).transact({'from': seller_account.address})
    
    # Universal revert assertion (works with Anvil, testnet, mainnet)
    assert_revert(exc_info, "Expected revert for soulbound transfer")

@pytest.mark.integration
def test_registry_integration(web3, spiral_engine_contract, registry_contract):
    """Проверка интеграции с реестром (исправлен метод get вместо getAddress)"""
    # Проверяем что контракт зарегистрирован (MagicRegistry.get, не getAddress)
    invite_address = registry_contract.functions.get("SpiralEngine").call()
    assert invite_address == spiral_engine_contract.address, "Адрес в реестре не соответствует адресу контракта"
    
    # Проверяем что это действительно тот же контракт
    registered_contract = web3.eth.contract(
        address=invite_address,
        abi=spiral_engine_contract.abi
    )
    assert registered_contract.functions.name().call() == "SpiralInvite"
    assert registered_contract.functions.symbol().call() == "SPIRAL"

@pytest.mark.integration
def test_invite_expiry(web3, spiral_engine_contract, seller_account):
    """
    Проверка механизма истечения срока действия инвайтов:
    - Создание с expiry
    - Проверка валидности до истечения
    - Проверка невалидности после истечения
    """
    # Обеспечиваем SELLER_ROLE
    ensure_seller_role(spiral_engine_contract, web3, seller_account, os.getenv("NODE_ADMIN_PRIVATE_KEY"))
    
    # Текущий timestamp
    current_time = web3.eth.get_block('latest').timestamp
    expiry_time = current_time + 3600  # +1 час
    
    # Минтим инвайт с expiry и уникальным префиксом
    timestamp = int(time.time() * 1000)
    code = generate_invite_code(prefix=f"exp_{timestamp}")
    tx_hash = spiral_engine_contract.functions.mintInvite(code, expiry_time).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    token_id = spiral_engine_contract.functions.inviteCodeToTokenId(code).call()
    
    # Проверяем что expiry установлен правильно
    # SpiralEngine: public mapping inviteExpiry(uint256 => uint256)
    actual_expiry = spiral_engine_contract.functions.inviteExpiry(token_id).call()
    assert actual_expiry == expiry_time, f"Expiry должен быть {expiry_time}, получен {actual_expiry}"
    
    # Проверяем что инвайт валидный до истечения срока
    is_used = spiral_engine_contract.functions.isInviteUsed(token_id).call()
    assert not is_used, "Инвайт не должен быть использован"
    current_block_time = web3.eth.get_block('latest').timestamp
    assert current_block_time < expiry_time, "Текущее время должно быть раньше expiry"
    
    # Увеличиваем время в блокчейне на 2 часа (чтобы инвайт истек)
    web3.provider.make_request("evm_increaseTime", [7200])  # +2 часа
    web3.provider.make_request("evm_mine", [])  # Майним новый блок
    
    # Проверяем что инвайт истек
    new_block_time = web3.eth.get_block('latest').timestamp
    assert new_block_time > expiry_time, "Текущее время должно быть после expiry"
    
    # Попытка активации с истекшим инвайтом должна revert
    fresh_user = web3.eth.account.create()
    new_codes = [generate_invite_code(prefix=f"exp_new_{timestamp}_{i}") for i in range(12)]
    
    with pytest.raises(Exception) as exc_info:
        spiral_engine_contract.functions.activateUser(
            code, fresh_user.address, new_codes, 0
        ).transact({'from': seller_account.address})
    
    # Universal revert assertion (works with Anvil, testnet, mainnet)
    assert_revert(exc_info, "Expected revert for expired invite")

@pytest.mark.integration
def test_batch_validate_invite_codes(web3, spiral_engine_contract, seller_account):
    """
    Проверка batch-валидации инвайт-кодов:
    - Валидные коды
    - Невалидные коды
    - Смешанный набор
    """
    # Обеспечиваем SELLER_ROLE
    ensure_seller_role(spiral_engine_contract, web3, seller_account, os.getenv("NODE_ADMIN_PRIVATE_KEY"))
    
    # Создаем набор инвайтов с уникальными префиксами
    timestamp = int(time.time() * 1000)
    valid_codes = [generate_invite_code(prefix=f"batch_valid_{timestamp}_{i}") for i in range(3)]
    invalid_codes = [generate_invite_code(prefix=f"batch_invalid_{timestamp}_{i}") for i in range(2)]
    
    # Минтим валидные инвайты: часть без expiry, часть с будущим expiry
    current_time = web3.eth.get_block('latest').timestamp
    future_time = current_time + 3600
    
    # Минтим инвайты без expiry (по одному)
    for code in valid_codes[:2]:
        tx_hash = spiral_engine_contract.functions.mintInvite(code, 0).transact({'from': seller_account.address})
        web3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Минтим инвайт с будущим expiry
    tx_hash = spiral_engine_contract.functions.mintInvite(valid_codes[2], future_time).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Увеличиваем время в блокчейне на 2 часа
    web3.provider.make_request("evm_increaseTime", [7200])
    web3.provider.make_request("evm_mine", [])
    
    # Проверяем batch-валидацию
    all_codes = valid_codes[:2] + invalid_codes + [valid_codes[2]]
    fresh_test_user = web3.eth.account.create()
    success, reasons = batch_validate_invite_codes(spiral_engine_contract, all_codes, fresh_test_user.address, web3)
    
    assert len(success) == len(all_codes), "Количество результатов не соответствует количеству кодов"
    assert len(reasons) == len(all_codes), "Количество причин не соответствует количеству кодов"
    
    # Проверяем результаты для валидных кодов без expiry
    for i in range(2):
        assert success[i], f"Валидный код {valid_codes[i]} помечен как невалидный"
        assert reasons[i] == "", f"Для валидного кода указана причина: {reasons[i]}"
    
    # Проверяем результаты для невалидных кодов
    for i in range(2, 4):
        assert not success[i], f"Невалидный код {invalid_codes[i-2]} должен быть невалидным"
    
    # Проверяем результат для истекшего кода
    assert not success[-1], "Истекший код должен быть невалидным"

@pytest.mark.integration
def test_invite_counters(web3, spiral_engine_contract, seller_account, network_growth_context):
    """
    Проверка счетчиков инвайтов: прирост при активации.
    Работает с любым baseline state (не требует counters = 0).
    Uses network_growth_context для dynamic activator selection.
    
    ⚠️ ТРЕБУЕТ CAPACITY: Тест активирует пользователя, нужен активатор с capacity > 0.
    При насыщении сети тест скипается.
    См: bot/docs/analysis/doc-network-bridge-mechanism-architecture.md#режим-гибернации
    """
    # Проверка наличия capacity перед тестом
    pool = network_growth_context['pool']
    gaps = pool.tracker.find_bridge_gaps(min_gap_size=1, max_gaps=1)
    if not gaps:
        pytest.skip(
            f"Insufficient capacity in network: no gaps available. "
            f"Network may be fully saturated. "
            f"See: bot/docs/analysis/doc-network-bridge-mechanism-architecture.md#режим-гибернации "
            f"for details on restoring network state."
        )
    
    # Фиксируем baseline (может быть > 0!)
    baseline_minted = spiral_engine_contract.functions.totalInvitesMinted().call()
    baseline_used = spiral_engine_contract.functions.totalInvitesUsed().call()
    
    # Get activator + invite from network growth pool
    activator = network_growth_context['activator']
    invite_code = network_growth_context['invite_code']
    
    # Создаём изолированный пользовательский account
    fresh_user = web3.eth.account.create()
    
    # Активируем инвайт для fresh_user с retry механизмом (activator == minter)
    timestamp = int(time.time() * 1000)
    new_codes = [generate_invite_code(prefix=f"counter_new_{timestamp}_{i}") for i in range(12)]
    
    tx_hash, activator, invite_code = activate_user_with_retry(
        spiral_engine_contract,
        invite_code,
        fresh_user.address,
        new_codes,
        0,
        activator,
        pool,
        web3,
        max_retries=3
    )
    
    # Проверяем прирост обоих счетчиков
    # +12 minted (новые инвайты для fresh_user), +1 used (invite_code использован)
    assert spiral_engine_contract.functions.totalInvitesMinted().call() == baseline_minted + 12, \
        "totalInvitesMinted не увеличился после активации"
    assert spiral_engine_contract.functions.totalInvitesUsed().call() == baseline_used + 1, \
        "totalInvitesUsed не увеличился после активации"

@pytest.mark.integration
def test_activated_users_tracking(web3, spiral_engine_contract, seller_account, network_growth_context):
    """
    Проверка отслеживания активированных пользователей (baseline + delta).
    Uses network_growth_context для dynamic activator selection.
    
    ⚠️ ТРЕБУЕТ CAPACITY: Тест активирует 3 пользователей, нужны активаторы с capacity > 0.
    При насыщении сети тест скипается.
    См: bot/docs/analysis/doc-network-bridge-mechanism-architecture.md#режим-гибернации
    """
    # Проверка наличия capacity перед тестом
    pool = network_growth_context['pool']
    gaps = pool.tracker.find_bridge_gaps(min_gap_size=1, max_gaps=3)
    if len(gaps) < 3:
        pytest.skip(
            f"Insufficient capacity in network: found {len(gaps)} gaps, need at least 3. "
            f"Network may be fully saturated. "
            f"See: bot/docs/analysis/doc-network-bridge-mechanism-architecture.md#режим-гибернации "
            f"for details on restoring network state."
        )
    
    # Фиксируем baseline активированных пользователей
    # Получаем массив через итерацию по индексам (activatedUsers - публичный массив)
    # Для публичных массивов итерируем до ошибки или используем известную длину
    baseline_activated = []
    i = 0
    while True:
        try:
            user = spiral_engine_contract.functions.activatedUsers(i).call()
            baseline_activated.append(user)
            i += 1
        except Exception:
            break
    baseline_count = len(baseline_activated)
    
    # Создаём 3 изолированных accounts
    fresh_accounts = [web3.eth.account.create() for _ in range(3)]
    
    # Берём 3 invites from pool (динамически)
    invites_and_activators = [pool.get_next() for _ in range(3)]
    
    # Активируем инвайты для разных пользователей
    activated_users = []
    timestamp = int(time.time() * 1000)
    for i in range(3):
        user = fresh_accounts[i]
        activator, invite_code = invites_and_activators[i]
        
        new_codes = [generate_invite_code(prefix=f"new_user_{timestamp}_{i}_{j}") for j in range(12)]
        tx_hash, activator, invite_code = activate_user_with_retry(
            spiral_engine_contract,
            invite_code,
            user.address,
            new_codes,
            0,
            activator,
            pool,
            web3,
            max_retries=3
        )
        activated_users.append(user.address)
        
        # Проверяем что пользователь активирован (usedInviteByUser > 0 означает активацию)
        used_invite = spiral_engine_contract.functions.usedInviteByUser(user.address).call()
        assert used_invite > 0, \
            f"Пользователь {user.address} не отмечен как активированный (usedInviteByUser = {used_invite})"
    
    # Проверяем прирост списка активированных
    all_activated_after = []
    i = 0
    while True:
        try:
            user = spiral_engine_contract.functions.activatedUsers(i).call()
            all_activated_after.append(user)
            i += 1
        except Exception:
            break
    assert len(all_activated_after) == baseline_count + 3, \
        f"Количество активированных должно увеличиться на 3 (было {baseline_count}, стало {len(all_activated_after)})"
    
    # Проверяем что все наши пользователи есть в списке
    for user_address in activated_users:
        assert user_address in all_activated_after, \
            f"Пользователь {user_address} отсутствует в списке активированных"

@pytest.mark.integration
def test_user_invite_count(web3, spiral_engine_contract, seller_account, network_growth_context):
    """
    Проверка подсчета инвайтов пользователя (isolated fresh account).
    Uses network_growth_context для dynamic activator selection.
    
    ⚠️ ТРЕБУЕТ CAPACITY: Тест активирует пользователя, нужен активатор с capacity > 0.
    При насыщении сети тест скипается.
    См: bot/docs/analysis/doc-network-bridge-mechanism-architecture.md#режим-гибернации
    """
    # Проверка наличия capacity перед тестом
    pool = network_growth_context['pool']
    gaps = pool.tracker.find_bridge_gaps(min_gap_size=1, max_gaps=1)
    if not gaps:
        pytest.skip(
            f"Insufficient capacity in network: no gaps available. "
            f"Network may be fully saturated. "
            f"See: bot/docs/analysis/doc-network-bridge-mechanism-architecture.md#режим-гибернации "
            f"for details on restoring network state."
        )
    
    # Создаём изолированный account (гарантированно 0 invites)
    fresh_user = web3.eth.account.create()
    
    # Проверяем начальное значение для fresh account
    initial_count = spiral_engine_contract.functions.userInviteCount(fresh_user.address).call()
    assert initial_count == 0, "Fresh account должен иметь 0 invites"
    
    # Get activator + invite from network growth pool
    activator = network_growth_context['activator']
    invite_code = network_growth_context['invite_code']
    
    # Активируем инвайт для пользователя с retry механизмом (получает 12 новых)
    timestamp = int(time.time() * 1000)
    new_codes = [generate_invite_code(prefix=f"count_new_{timestamp}_{i}") for i in range(12)]
    tx_hash, activator, invite_code = activate_user_with_retry(
        spiral_engine_contract,
        invite_code,
        fresh_user.address,
        new_codes,
        0,
        activator,
        pool,
        web3,
        max_retries=3
    )
    
    # Проверяем количество инвайтов пользователя через getUserInvites
    # Вызываем от имени самого пользователя (требуется по контракту: msg.sender == user)
    user_invites = spiral_engine_contract.functions.getUserInvites(fresh_user.address).call({'from': fresh_user.address})
    assert len(user_invites) == 12, "Пользователь должен иметь 12 инвайтов"
    
    # Проверяем счетчик
    final_count = spiral_engine_contract.functions.userInviteCount(fresh_user.address).call()
    assert final_count == 12, "userInviteCount должен показывать 12 инвайтов"
    
    # Проверяем что все инвайты принадлежат пользователю
    for token_id in user_invites:
        owner = spiral_engine_contract.functions.ownerOf(token_id).call()
        assert owner == fresh_user.address, f"Инвайт {token_id} не принадлежит пользователю"
 