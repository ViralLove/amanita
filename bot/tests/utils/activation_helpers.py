"""
Helper functions for activation operations with retry mechanism.

Provides automatic retry when CircleLimitReached error occurs due to race conditions
between capacity validation and actual activation.

Works with all blockchain networks:
- localhost (Anvil/Foundry): ContractCustomError with error codes
- testnet (amoy): web3.py exceptions via RPC
- mainnet (polygon): web3.py exceptions via RPC

Usage:
    from bot.tests.utils.activation_helpers import activate_user_with_retry, activate_user_with_adaptation
    
    # Simple retry (only CircleLimitReached)
    tx_hash, activator, invite_code = activate_user_with_retry(
        contract,
        invite_code,
        user_address,
        new_codes,
        expiry,
        activator,
        pool,
        web3
    )
    
    # Adaptive activation (full validation + retry for all errors)
    from bot.tests.utils.invite_state_tracker import InviteStateTracker
    tracker = InviteStateTracker(contract, web3)
    
    tx_hash, activator, invite_code = activate_user_with_adaptation(
        contract,
        invite_code,
        user_address,
        new_codes,
        expiry,
        activator,
        pool,
        tracker,
        web3
    )
"""

from web3.exceptions import ContractCustomError, ContractLogicError
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eth_account import Account
    from web3 import Web3


def is_circle_limit_reached(error: Exception) -> bool:
    """
    Проверяет, является ли ошибка CircleLimitReached.
    
    CircleLimitReached имеет error selector: 0xb6c7d551
    (keccak256("CircleLimitReached()")[:4])
    
    Args:
        error: Exception из вызова транзакции
        
    Returns:
        bool: True если это CircleLimitReached ошибка
        
    Supported formats:
    - Anvil: ContractCustomError с error code '0xb6c7d551'
    - Testnet/Mainnet: ContractLogicError с сообщением 'CircleLimitReached'
    """
    error_str = str(error)
    error_code = '0xb6c7d551'  # CircleLimitReached error selector
    
    # Check 1: ContractCustomError (Anvil) с нужным error code
    if isinstance(error, ContractCustomError):
        # ContractCustomError format: ('0xb6c7d551', '0xb6c7d551')
        # Проверяем через args (если доступен) или через строковое представление
        if hasattr(error, 'args') and error.args:
            # args может быть tuple: ('0xb6c7d551', '0xb6c7d551')
            if any(error_code in str(arg) for arg in error.args):
                return True
        # Fallback: проверка через строку
        if error_code in error_str:
            return True
    
    # Check 2: ContractLogicError (testnet/mainnet) с именем ошибки
    if isinstance(error, ContractLogicError):
        if 'CircleLimitReached' in error_str:
            return True
    
    # Check 3: Error message contains CircleLimitReached (fallback)
    if 'CircleLimitReached' in error_str:
        return True
    
    # Check 4: Error selector в строке ошибки (fallback)
    if '0xb6c7d551' in error_str:
        return True
    
    return False


def activate_user_with_retry(
    contract,
    invite_code: str,
    user_address: str,
    new_codes: list,
    expiry: int,
    activator_account: "Account",
    pool,
    web3: "Web3",
    max_retries: int = 3
):
    """
    Активирует пользователя с автоматическим retry при CircleLimitReached.
    
    Если активатор потерял capacity между выбором и использованием (race condition),
    автоматически получает нового активатора и повторяет попытку.
    
    Args:
        contract: SpiralEngine контракт instance
        invite_code: Код инвайта для активации
        user_address: Адрес пользователя для активации
        new_codes: Список из 12 новых инвайт кодов для пользователя
        expiry: Срок действия новых инвайтов (обычно 0 = бессрочный)
        activator_account: Аккаунт активатора (eth_account.Account)
        pool: ExponentialActivatorPool для получения нового активатора
        web3: Web3 instance
        max_retries: Максимальное количество попыток (default: 3)
        
    Returns:
        tuple: (tx_hash, activator_account, invite_code) - успешная активация
        
    Raises:
        RuntimeError: Если все попытки исчерпаны
        Exception: Другие ошибки (не CircleLimitReached) поднимаются сразу
        
    Example:
        >>> from bot.tests.utils.activation_helpers import activate_user_with_retry
        >>> tx_hash, activator, invite = activate_user_with_retry(
        ...     spiral_engine_contract,
        ...     invite_code,
        ...     fresh_user.address,
        ...     new_codes,
        ...     0,
        ...     activator,
        ...     pool,
        ...     web3
        ... )
    """
    current_activator = activator_account
    current_invite = invite_code
    
    for attempt in range(max_retries):
        try:
            # Build transaction
            nonce = web3.eth.get_transaction_count(current_activator.address)
            gas_price = web3.eth.gas_price
            
            transaction = contract.functions.activateUser(
                current_invite,
                user_address,
                new_codes,
                expiry
            ).build_transaction({
                'from': current_activator.address,
                'nonce': nonce,
                'gasPrice': gas_price,
                'chainId': web3.eth.chain_id
            })
            
            # Sign locally (supports both Anvil pre-funded and deterministic accounts)
            signed_txn = current_activator.sign_transaction(transaction)
            
            # Send raw transaction
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            web3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Успех!
            return tx_hash, current_activator, current_invite
            
        except Exception as e:
            # Проверяем, это ли CircleLimitReached
            if is_circle_limit_reached(e):
                if attempt < max_retries - 1:
                    # Получаем нового активатора и инвайт
                    print(f"⚠️  Attempt {attempt+1}/{max_retries}: CircleLimitReached, "
                          f"getting new activator...")
                    current_activator, current_invite = pool.get_next()
                    continue
                else:
                    raise RuntimeError(
                        f"Failed to activate user after {max_retries} attempts. "
                        f"All activators may be full or network may be saturated."
                    ) from e
            else:
                # Другая ошибка - не retry, сразу поднимаем
                raise
    
    # Не должно сюда дойти (все попытки должны обработаться в try/except)
    raise RuntimeError(f"Unexpected error in activate_user_with_retry: all retries exhausted")


def is_invite_not_from_activator(error: Exception) -> bool:
    """
    Проверяет, является ли ошибка InviteNotFromActivator.
    
    InviteNotFromActivator имеет error selector: 0xe15c6068
    (keccak256("InviteNotFromActivator()")[:4])
    
    Args:
        error: Exception из вызова транзакции
        
    Returns:
        bool: True если это InviteNotFromActivator ошибка
        
    Supported formats:
    - Anvil: ContractCustomError с error code '0xe15c6068'
    - Testnet/Mainnet: ContractLogicError с сообщением 'InviteNotFromActivator'
    """
    error_str = str(error)
    error_code = '0xe15c6068'  # InviteNotFromActivator error selector
    
    # Check 1: ContractCustomError (Anvil) с нужным error code
    if isinstance(error, ContractCustomError):
        # ContractCustomError format: ('0xe15c6068', '0xe15c6068')
        # Проверяем через args (если доступен) или через строковое представление
        if hasattr(error, 'args') and error.args:
            # args может быть tuple: ('0xe15c6068', '0xe15c6068')
            if any(error_code in str(arg) for arg in error.args):
                return True
        # Fallback: проверка через строку
        if error_code in error_str:
            return True
    
    # Check 2: ContractLogicError (testnet/mainnet) с именем ошибки
    if isinstance(error, ContractLogicError):
        if 'InviteNotFromActivator' in error_str:
            return True
    
    # Check 3: Error message contains InviteNotFromActivator (fallback)
    if 'InviteNotFromActivator' in error_str:
        return True
    
    # Check 4: Error selector в строке ошибки (fallback)
    if '0xe15c6068' in error_str:
        return True
    
    return False


def activate_user_with_adaptation(
    contract,
    invite_code: str,
    user_address: str,
    new_codes: list,
    expiry: int,
    activator_account: "Account",
    pool,
    tracker,
    web3: "Web3",
    max_retries: int = 3
):
    """
    Активирует пользователя с автоматической адаптацией при рассинхронизациях.
    
    Автоматически:
    1. Валидирует синхронизацию активатор/инвайт перед каждой попыткой
    2. При обнаружении рассинхронизации получает новый активатор и инвайт
    3. Обрабатывает все типы ошибок (CircleLimitReached, InviteNotFromActivator)
    
    Args:
        contract: SpiralEngine контракт instance
        invite_code: Код инвайта для активации
        user_address: Адрес пользователя для активации
        new_codes: Список из 12 новых инвайт кодов для пользователя
        expiry: Срок действия новых инвайтов
        activator_account: Аккаунт активатора (eth_account.Account)
        pool: ExponentialActivatorPool для получения нового активатора
        tracker: InviteStateTracker для валидации синхронизации
        web3: Web3 instance
        max_retries: Максимальное количество попыток (default: 3)
        
    Returns:
        tuple: (tx_hash, activator_account, invite_code) - успешная активация
        
    Raises:
        RuntimeError: Если все попытки исчерпаны
        
    Example:
        >>> from bot.tests.utils.activation_helpers import activate_user_with_adaptation
        >>> from bot.tests.utils.invite_state_tracker import InviteStateTracker
        >>> tracker = InviteStateTracker(contract, web3)
        >>> tx_hash, activator, invite = activate_user_with_adaptation(
        ...     spiral_engine_contract,
        ...     invite_code,
        ...     fresh_user.address,
        ...     new_codes,
        ...     0,
        ...     activator,
        ...     pool,
        ...     tracker,
        ...     web3
        ... )
    """
    current_activator = activator_account
    current_invite = invite_code
    
    for attempt in range(max_retries):
        # КРИТИЧНО: Валидация синхронизации перед каждой попыткой
        validation = tracker.validate_activator_invite_pair(
            current_activator.address,
            current_invite
        )
        
        if not validation['valid']:
            print(f"⚠️  Attempt {attempt+1}/{max_retries}: Validation failed: {validation['reason']}")
            
            # Адаптация: получаем новый активатор и инвайт
            if attempt < max_retries - 1:
                print(f"   Getting new activator/invite pair...")
                current_activator, current_invite = pool.get_next()
                
                # Повторная валидация новой пары
                new_validation = tracker.validate_activator_invite_pair(
                    current_activator.address,
                    current_invite
                )
                
                if not new_validation['valid']:
                    print(f"   ⚠️  New pair also invalid: {new_validation['reason']}, continuing anyway...")
                
                continue  # Retry с новой парой
            else:
                raise RuntimeError(
                    f"Failed to activate user after {max_retries} attempts. "
                    f"Last validation error: {validation['reason']}"
                )
        
        # Валидация прошла, пытаемся активировать
        try:
            # Build transaction
            nonce = web3.eth.get_transaction_count(current_activator.address)
            gas_price = web3.eth.gas_price
            
            transaction = contract.functions.activateUser(
                current_invite,
                user_address,
                new_codes,
                expiry
            ).build_transaction({
                'from': current_activator.address,
                'nonce': nonce,
                'gasPrice': gas_price,
                'chainId': web3.eth.chain_id
            })
            
            # Sign locally (supports both Anvil pre-funded and deterministic accounts)
            signed_txn = current_activator.sign_transaction(transaction)
            
            # Send raw transaction
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            web3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Успех!
            print(f"✅ Activation successful: {current_activator.address[:10]}... / {current_invite}")
            return tx_hash, current_activator, current_invite
            
        except Exception as e:
            # Проверяем тип ошибки
            if is_circle_limit_reached(e):
                print(f"⚠️  Attempt {attempt+1}/{max_retries}: CircleLimitReached")
                if attempt < max_retries - 1:
                    current_activator, current_invite = pool.get_next()
                    continue
                else:
                    raise RuntimeError(
                        f"Failed to activate user after {max_retries} attempts. "
                        f"All activators may be full."
                    ) from e
            
            elif is_invite_not_from_activator(e):
                print(f"⚠️  Attempt {attempt+1}/{max_retries}: InviteNotFromActivator")
                if attempt < max_retries - 1:
                    # Критично: получаем новую пару
                    current_activator, current_invite = pool.get_next()
                    continue
                else:
                    raise RuntimeError(
                        f"Failed to activate user after {max_retries} attempts. "
                        f"Invite/activator mismatch."
                    ) from e
            
            else:
                # Другая ошибка - не retry, сразу поднимаем
                raise
    
    # Не должно сюда дойти (все попытки должны обработаться в try/except)
    raise RuntimeError(f"Unexpected error in activate_user_with_adaptation: all retries exhausted")


__all__ = [
    'activate_user_with_retry', 
    'is_circle_limit_reached',
    'activate_user_with_adaptation',
    'is_invite_not_from_activator'
]

