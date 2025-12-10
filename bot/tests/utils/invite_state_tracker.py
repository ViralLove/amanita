"""
Invite State Tracker for validating activator-invite synchronization.

Tracks the relationship between activators and invites, validates their synchronization
before use, and provides comprehensive invite state information.

Works with all blockchain networks:
- localhost (Anvil/Foundry)
- testnet (amoy)
- mainnet (polygon)

Usage:
    from bot.tests.utils.invite_state_tracker import InviteStateTracker
    
    tracker = InviteStateTracker(spiral_engine_contract, web3)
    
    # Validate activator-invite pair
    validation = tracker.validate_activator_invite_pair(activator_address, invite_code)
    if validation['valid']:
        # Proceed with activation
        pass
    
    # Get full invite state
    state = tracker.get_invite_state(invite_code)
"""

from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from web3 import Web3


class InviteStateTracker:
    """
    Отслеживает состояние инвайта и его связь с активатором.
    Валидирует синхронизацию перед использованием.
    
    Provides validation for:
    - Invite existence
    - Activator-invite synchronization (inviteMinter == activator)
    - Invite usage status
    - Invite expiration
    - Activator capacity
    """
    
    def __init__(self, contract, web3: "Web3"):
        """
        Initialize InviteStateTracker.
        
        Args:
            contract: SpiralEngine contract instance (web3.eth.contract)
            web3: Web3 instance for blockchain queries
        """
        self.contract = contract
        self.web3 = web3
    
    def validate_activator_invite_pair(
        self, 
        activator_address: str, 
        invite_code: str
    ) -> Dict:
        """
        Валидирует связь между активатором и инвайтом.
        
        Проверки:
        1. Инвайт существует
        2. inviteMinter[tokenId] == activator
        3. Инвайт не использован
        4. Инвайт не истек
        5. Активатор имеет capacity (circle < 12)
        
        Args:
            activator_address: Адрес активатора (checksummed или lowercase)
            invite_code: Код инвайта для проверки
            
        Returns:
            dict: {
                'valid': bool,
                'reason': str (если не valid),
                'token_id': int (если найден),
                'minter': str (если найден),
                'is_used': bool,
                'expired': bool,
                'activator_capacity': int (если valid),
                'circle_size': int (если valid),
                'expected_activator': str (если не синхронизирован)
            }
        """
        try:
            # 1. Проверка существования инвайта
            exists = self.contract.functions.inviteCodeExists(invite_code).call()
            if not exists:
                return {
                    'valid': False,
                    'reason': 'invite_not_found',
                    'token_id': None,
                    'minter': None,
                    'is_used': False,
                    'expired': False
                }
            
            # 2. Получение token_id
            token_id = self.contract.functions.inviteCodeToTokenId(invite_code).call()
            
            # 3. Проверка минтера
            minter = self.contract.functions.inviteMinter(token_id).call()
            # Normalize addresses for comparison (lowercase)
            if minter.lower() != activator_address.lower():
                return {
                    'valid': False,
                    'reason': 'invite_not_from_activator',
                    'token_id': token_id,
                    'minter': minter,
                    'expected_activator': activator_address,
                    'is_used': False,
                    'expired': False
                }
            
            # 4. Проверка использования
            is_used = self.contract.functions.isInviteUsed(token_id).call()
            if is_used:
                return {
                    'valid': False,
                    'reason': 'invite_already_used',
                    'token_id': token_id,
                    'minter': minter,
                    'is_used': True,
                    'expired': False
                }
            
            # 5. Проверка срока действия
            expiry = self.contract.functions.inviteExpiry(token_id).call()
            current_time = self.web3.eth.get_block('latest').timestamp
            expired = expiry > 0 and expiry <= current_time
            if expired:
                return {
                    'valid': False,
                    'reason': 'invite_expired',
                    'token_id': token_id,
                    'minter': minter,
                    'is_used': False,
                    'expired': True,
                    'expiry': expiry,
                    'current_time': current_time
                }
            
            # 6. Проверка capacity активатора
            circle = self.contract.functions.getCircleMembers(activator_address).call()
            capacity = 12 - len(circle)
            
            if capacity <= 0:
                return {
                    'valid': False,
                    'reason': 'activator_circle_full',
                    'token_id': token_id,
                    'minter': minter,
                    'is_used': False,
                    'expired': False,
                    'capacity': capacity,
                    'circle_size': len(circle)
                }
            
            # Все проверки пройдены
            return {
                'valid': True,
                'reason': None,
                'token_id': token_id,
                'minter': minter,
                'is_used': False,
                'expired': False,
                'activator_capacity': capacity,
                'circle_size': len(circle)
            }
            
        except Exception as e:
            return {
                'valid': False,
                'reason': f'validation_error: {str(e)}',
                'token_id': None,
                'minter': None,
                'is_used': False,
                'expired': False
            }
    
    def get_invite_state(self, invite_code: str) -> Dict:
        """
        Получает полное состояние инвайта.
        
        Args:
            invite_code: Код инвайта для проверки
            
        Returns:
            dict: {
                'exists': bool,
                'token_id': int (если существует),
                'minter': str (если существует),
                'is_used': bool,
                'used_by': Optional[str] (если использован, может быть None),
                'expiry': int,
                'expired': bool,
                'created_at': int,
                'error': Optional[str] (если ошибка)
            }
        """
        try:
            exists = self.contract.functions.inviteCodeExists(invite_code).call()
            if not exists:
                return {'exists': False}
            
            token_id = self.contract.functions.inviteCodeToTokenId(invite_code).call()
            minter = self.contract.functions.inviteMinter(token_id).call()
            is_used = self.contract.functions.isInviteUsed(token_id).call()
            expiry = self.contract.functions.inviteExpiry(token_id).call()
            created_at = self.contract.functions.inviteCreatedAt(token_id).call()
            
            current_time = self.web3.eth.get_block('latest').timestamp
            expired = expiry > 0 and expiry <= current_time
            
            # Try to find who used the invite (if used)
            # Note: This requires checking all activated users, which may be expensive
            # For now, we'll leave it as None if used
            used_by = None
            if is_used:
                # Could iterate through activatedUsers, but that's expensive
                # For now, we'll just mark it as used
                pass
            
            return {
                'exists': True,
                'token_id': token_id,
                'minter': minter,
                'is_used': is_used,
                'used_by': used_by,
                'expiry': expiry,
                'expired': expired,
                'created_at': created_at
            }
        except Exception as e:
            return {
                'exists': False,
                'error': str(e)
            }


__all__ = ['InviteStateTracker']

