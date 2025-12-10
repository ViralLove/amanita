"""
Integration tests for InviteStateTracker.

Tests validation of activator-invite synchronization and invite state tracking.
"""

import pytest
from web3 import Web3
from bot.tests.utils.invite_state_tracker import InviteStateTracker
from bot.tests.utils.invite_code_generator import generate_invite_code
from bot.tests.integration.test_spiral_engine import ensure_seller_role, ensure_activator_role
import os
import time


@pytest.mark.integration
def test_validate_valid_activator_invite_pair(web3, spiral_engine_contract, seller_account, network_growth_context):
    """
    Тест валидации валидной пары активатор-инвайт.
    
    ⚠️ ТРЕБУЕТ CAPACITY: Тест проверяет, что активатор имеет capacity > 0.
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
    
    tracker = InviteStateTracker(spiral_engine_contract, web3)
    
    # Get activator + invite from network growth pool
    activator = network_growth_context['activator']
    invite_code = network_growth_context['invite_code']
    
    # Validate pair
    validation = tracker.validate_activator_invite_pair(activator.address, invite_code)
    
    # Should be valid
    assert validation['valid'] is True, f"Expected valid pair, got reason: {validation.get('reason')}"
    assert validation['reason'] is None
    assert validation['token_id'] is not None
    assert validation['minter'] == activator.address
    assert validation['is_used'] is False
    assert validation['expired'] is False
    assert validation['activator_capacity'] > 0
    assert validation['circle_size'] < 12


@pytest.mark.integration
def test_validate_nonexistent_invite(web3, spiral_engine_contract, seller_account, network_growth_context):
    """
    Тест валидации несуществующего инвайта.
    """
    tracker = InviteStateTracker(spiral_engine_contract, web3)
    
    # Get activator from network growth pool
    activator = network_growth_context['activator']
    
    # Use non-existent invite code
    fake_invite_code = "AMANITA-FAKE-CODE"
    
    # Validate pair
    validation = tracker.validate_activator_invite_pair(activator.address, fake_invite_code)
    
    # Should be invalid
    assert validation['valid'] is False
    assert validation['reason'] == 'invite_not_found'
    assert validation['token_id'] is None
    assert validation['minter'] is None


@pytest.mark.integration
def test_validate_invite_from_different_activator(web3, spiral_engine_contract, seller_account, network_growth_context):
    """
    Тест валидации инвайта от другого активатора (рассинхронизация).
    
    ⚠️ ТРЕБУЕТ CAPACITY: Тест требует 2 активатора, нужны активаторы с capacity > 0.
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
    
    tracker = InviteStateTracker(spiral_engine_contract, web3)
    
    # Get two different activator-invite pairs
    activator1 = network_growth_context['activator']
    invite_code1 = network_growth_context['invite_code']
    
    # Get another pair (need to get next from pool)
    activator2, invite_code2 = pool.get_next()
    
    # Try to validate invite1 with activator2 (should fail)
    validation = tracker.validate_activator_invite_pair(activator2.address, invite_code1)
    
    # Should be invalid due to mismatch
    assert validation['valid'] is False
    assert validation['reason'] == 'invite_not_from_activator'
    assert validation['token_id'] is not None
    assert validation['minter'] == activator1.address
    assert validation['expected_activator'] == activator2.address


@pytest.mark.integration
def test_validate_used_invite(web3, spiral_engine_contract, seller_account, network_growth_context):
    """
    Тест валидации уже использованного инвайта.
    
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
    
    tracker = InviteStateTracker(spiral_engine_contract, web3)
    
    # Get activator + invite from network growth pool
    activator = network_growth_context['activator']
    invite_code = network_growth_context['invite_code']
    
    # Use the invite (activate a user)
    from bot.tests.utils.activation_helpers import activate_user_with_retry
    fresh_user = web3.eth.account.create()
    timestamp = int(time.time() * 1000)
    new_codes = [generate_invite_code(prefix=f"used_test_{timestamp}_{i}") for i in range(12)]
    
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
    
    # Now validate the used invite
    validation = tracker.validate_activator_invite_pair(activator.address, invite_code)
    
    # Should be invalid (used)
    assert validation['valid'] is False
    assert validation['reason'] == 'invite_already_used'
    assert validation['is_used'] is True


@pytest.mark.integration
def test_validate_expired_invite(web3, spiral_engine_contract, seller_account):
    """
    Тест валидации истекшего инвайта.
    """
    tracker = InviteStateTracker(spiral_engine_contract, web3)
    
    # Ensure seller has role
    ensure_seller_role(spiral_engine_contract, web3, seller_account, os.getenv("NODE_ADMIN_PRIVATE_KEY"))
    
    # Create invite with expiry in the past
    current_time = web3.eth.get_block('latest').timestamp
    past_expiry = current_time - 3600  # 1 hour ago
    
    timestamp = int(time.time() * 1000)
    invite_code = generate_invite_code(prefix=f"expired_{timestamp}")
    
    # Mint invite with past expiry
    tx_hash = spiral_engine_contract.functions.mintInvite(invite_code, past_expiry).transact({
        'from': seller_account.address
    })
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Grant ACTIVATOR_ROLE to seller for validation
    from bot.tests.integration.test_spiral_engine import ensure_activator_role
    ensure_activator_role(spiral_engine_contract, web3, seller_account, os.getenv("NODE_ADMIN_PRIVATE_KEY"))
    
    # Validate expired invite
    validation = tracker.validate_activator_invite_pair(seller_account.address, invite_code)
    
    # Should be invalid (expired)
    assert validation['valid'] is False
    assert validation['reason'] == 'invite_expired'
    assert validation['expired'] is True


@pytest.mark.integration
def test_validate_full_activator_circle(web3, spiral_engine_contract, seller_account, network_growth_context):
    """
    Тест валидации инвайта от активатора с заполненным кругом.
    
    Задача: Проверить, что validate_activator_invite_pair правильно определяет
    ситуацию, когда активатор заполнил свой круг (12/12) и возвращает
    activator_circle_full до попытки транзакции.
    
    Реализация: Тест самостоятельно заполняет круг активатора до 12,
    затем проверяет валидацию заполненного круга.
    
    ⚠️ ТРЕБУЕТ CAPACITY: Тест заполняет круг активатора, нужен активатор с capacity > 0.
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
    
    from bot.tests.utils.activation_helpers import activate_user_with_retry
    
    tracker = InviteStateTracker(spiral_engine_contract, web3)
    
    # 1. Получить активатора с capacity > 0 из network growth pool
    activator = network_growth_context['activator']
    
    # 2. Проверить текущее состояние круга
    circle_before = spiral_engine_contract.functions.getCircleMembers(activator.address).call()
    current_circle_size = len(circle_before)
    capacity_before = 12 - current_circle_size
    
    # Убедиться, что у активатора есть capacity (иначе тест не может заполнить круг)
    assert capacity_before > 0, f"Activator {activator.address[:10]}... already has full circle (size: {current_circle_size}/12)"
    
    # 3. Самостоятельно заполнить круг активатора до 12
    # Активируем пользователей до тех пор, пока круг не заполнится
    print(f"📊 Начальное состояние: circle_size={current_circle_size}/12, capacity={capacity_before}")
    
    activations_needed = capacity_before  # Сколько активаций нужно для заполнения круга
    print(f"🔄 Нужно активировать {activations_needed} пользователей для заполнения круга")
    
    # Убедимся, что активатор имеет необходимые роли
    ensure_seller_role(spiral_engine_contract, web3, activator, os.getenv("NODE_ADMIN_PRIVATE_KEY"))
    ensure_activator_role(spiral_engine_contract, web3, activator, os.getenv("NODE_ADMIN_PRIVATE_KEY"))
    
    timestamp = int(time.time() * 1000)  # Генерируем timestamp один раз для всех активаций
    
    for i in range(activations_needed):
        # Проверим, что активатор еще не заполнен
        circle_current = spiral_engine_contract.functions.getCircleMembers(activator.address).call()
        if len(circle_current) >= 12:
            print(f"✅ Круг заполнен после {i} активаций")
            break
        
        # Минтим инвайт напрямую через контракт от нашего активатора
        # Используем local signing (как в conftest.py)
        invite_code = generate_invite_code(prefix=f"full_circle_{timestamp}_{i}")
        
        # Build transaction
        nonce = web3.eth.get_transaction_count(activator.address)
        gas_price = web3.eth.gas_price
        
        transaction = spiral_engine_contract.functions.mintInvite(invite_code, 0).build_transaction({
            'from': activator.address,
            'nonce': nonce,
            'gasPrice': gas_price,
            'chainId': web3.eth.chain_id
        })
        
        # Sign locally
        signed_txn = activator.sign_transaction(transaction)
        
        # Send raw transaction
        tx_hash_mint = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        web3.eth.wait_for_transaction_receipt(tx_hash_mint)
        
        # Создать нового пользователя для активации
        fresh_user = web3.eth.account.create()
        new_codes = [generate_invite_code(prefix=f"full_circle_{timestamp}_{i}_{j}") for j in range(12)]
        
        # Активировать пользователя
        tx_hash, activator_after, invite_code_after = activate_user_with_retry(
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
        
        # Проверить, что активатор не изменился (pool может вернуть нового при retry)
        if activator_after.address.lower() != activator.address.lower():
            print(f"⚠️  Activator changed from {activator.address[:10]}... to {activator_after.address[:10]}... (retry)")
            activator = activator_after
        
        circle_after = spiral_engine_contract.functions.getCircleMembers(activator.address).call()
        print(f"  ✅ Активация {i+1}/{activations_needed}: circle_size={len(circle_after)}/12")
    
    # 4. Проверить, что круг действительно заполнен
    final_circle = spiral_engine_contract.functions.getCircleMembers(activator.address).call()
    final_circle_size = len(final_circle)
    final_capacity = 12 - final_circle_size
    
    assert final_circle_size == 12, f"Expected circle size 12, got {final_circle_size}"
    assert final_capacity == 0, f"Expected capacity 0, got {final_capacity}"
    print(f"✅ Круг заполнен: circle_size={final_circle_size}/12, capacity={final_capacity}")
    
    # 5. Создать новый инвайт от заполненного активатора
    # (это возможно, так как минтить инвайты может любой с SELLER_ROLE, даже если круг заполнен)
    ensure_seller_role(spiral_engine_contract, web3, activator, os.getenv("NODE_ADMIN_PRIVATE_KEY"))
    
    # Минтим инвайт напрямую через контракт (local signing)
    invite_code_for_full = generate_invite_code(prefix=f"full_circle_final")
    
    # Build transaction
    nonce_final = web3.eth.get_transaction_count(activator.address)
    gas_price_final = web3.eth.gas_price
    
    transaction_final = spiral_engine_contract.functions.mintInvite(invite_code_for_full, 0).build_transaction({
        'from': activator.address,
        'nonce': nonce_final,
        'gasPrice': gas_price_final,
        'chainId': web3.eth.chain_id
    })
    
    # Sign locally
    signed_txn_final = activator.sign_transaction(transaction_final)
    
    # Send raw transaction
    tx_hash_final_mint = web3.eth.send_raw_transaction(signed_txn_final.raw_transaction)
    web3.eth.wait_for_transaction_receipt(tx_hash_final_mint)
    
    # 6. Проверить валидацию заполненного круга
    validation = tracker.validate_activator_invite_pair(activator.address, invite_code_for_full)
    
    # 7. Убедиться, что валидация правильно определила заполненный круг
    assert validation['valid'] is False, "Validation should fail for full circle"
    assert validation['reason'] == 'activator_circle_full', f"Expected reason 'activator_circle_full', got '{validation.get('reason')}'"
    assert validation['circle_size'] == 12, f"Expected circle_size 12, got {validation.get('circle_size')}"
    assert validation['capacity'] == 0, f"Expected capacity 0, got {validation.get('capacity')}"
    
    print(f"✅ Валидация правильно определила заполненный круг: reason={validation['reason']}")


@pytest.mark.integration
def test_get_invite_state_existing(web3, spiral_engine_contract, seller_account, network_growth_context):
    """
    Тест получения состояния существующего инвайта.
    
    ℹ️ НЕ ТРЕБУЕТ CAPACITY: Тест только читает состояние инвайта, не активирует пользователей.
    """
    tracker = InviteStateTracker(spiral_engine_contract, web3)
    
    # Get invite from network growth pool
    invite_code = network_growth_context['invite_code']
    
    # Get invite state
    state = tracker.get_invite_state(invite_code)
    
    # Should exist and have all fields
    assert state['exists'] is True
    assert state['token_id'] is not None
    assert state['minter'] is not None
    assert 'is_used' in state
    assert 'expiry' in state
    assert 'expired' in state
    assert 'created_at' in state


@pytest.mark.integration
def test_get_invite_state_nonexistent(web3, spiral_engine_contract):
    """
    Тест получения состояния несуществующего инвайта.
    """
    tracker = InviteStateTracker(spiral_engine_contract, web3)
    
    # Use non-existent invite code
    fake_invite_code = "AMANITA-FAKE-9999"
    
    # Get invite state
    state = tracker.get_invite_state(fake_invite_code)
    
    # Should not exist
    assert state['exists'] is False


@pytest.mark.integration
def test_get_invite_state_used(web3, spiral_engine_contract, seller_account, network_growth_context):
    """
    Тест получения состояния использованного инвайта.
    
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
    
    tracker = InviteStateTracker(spiral_engine_contract, web3)
    
    # Get activator + invite from network growth pool
    activator = network_growth_context['activator']
    invite_code = network_growth_context['invite_code']
    
    # Use the invite (activate a user)
    from bot.tests.utils.activation_helpers import activate_user_with_retry
    fresh_user = web3.eth.account.create()
    timestamp = int(time.time() * 1000)
    new_codes = [generate_invite_code(prefix=f"state_test_{timestamp}_{i}") for i in range(12)]
    
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
    
    # Get state of used invite
    state = tracker.get_invite_state(invite_code)
    
    # Should exist and be marked as used
    assert state['exists'] is True
    assert state['is_used'] is True

