import logging
import dotenv
import os
from typing import Optional, List, Dict, Any, Tuple
from eth_account import Account
from web3 import Web3

dotenv.load_dotenv()
logger = logging.getLogger(__name__)

class AccountService:
    """
    Сервис для работы с аккаунтами и правами доступа.
    Отвечает за управление аккаунтами, проверку прав и аутентификацию пользователей.
    """

    def __init__(self, blockchain_service):
        """
        Инициализирует AccountService.
        
        Args:
            blockchain_service: Экземпляр BlockchainService для работы с блокчейном
        """
        self.blockchain_service = blockchain_service
        logger.info("[AccountService] Сервис инициализирован")

    def get_seller_account(self) -> Account:
        """
        Получает аккаунт продавца.
        
        Returns:
            Account: Объект аккаунта продавца
            
        Raises:
            ValueError: Если SELLER_PRIVATE_KEY не установлен
        """
        seller_private_key = os.getenv("SELLER_PRIVATE_KEY")
        if not seller_private_key:
            raise ValueError("SELLER_PRIVATE_KEY не установлен в .env")
        return Account.from_key(seller_private_key)

    def get_account(self, user_id: str) -> Optional[Account]:
        """
        Получает аккаунт пользователя по ID.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Optional[Account]: Объект аккаунта или None
        """
        # TODO: Реализовать получение аккаунта по user_id
        logger.warning(f"[AccountService] Метод get_account({user_id}) не реализован")
        return None
    
    def is_seller(self, wallet_address: str) -> bool:
        """
        Проверяет, является ли адрес адресом продавца.
        
        Args:
            wallet_address: Адрес кошелька для проверки
            
        Returns:
            bool: True если адрес является продавцом, False иначе
        """
        logger.info(f"[AccountService] Проверка прав продавца для адреса: {wallet_address}")
        try:
            # Получаем SELLER_ROLE хеш из SpiralEngine
            seller_role = self.blockchain_service.get_contract("SpiralEngine").functions.SELLER_ROLE().call()
            
            # Проверяем роль через SpiralEngine
            result = self.blockchain_service._call_contract_read_function(
                "SpiralEngine", "hasRole", False, seller_role, wallet_address
            )
        except Exception as e:
            logger.error(f"[AccountService] Ошибка проверки роли продавца: {e}")
            result = False
        logger.info(f"[AccountService] Результат проверки продавца: {result}")
        return result
    
    def validate_invite_code(self, wallet_address: str) -> bool:
        """
        Проверяет наличие Invite NFT у адреса.
        
        Args:
            wallet_address: Адрес кошелька для проверки
            
        Returns:
            bool: True если адрес владеет Invite NFT, False иначе
        """
        logger.info(f"[AccountService][CHECK] Проверяем наличие Invite NFT у адреса: {wallet_address}")
        
        try:
            # Проверяем активацию пользователя через SpiralEngine
            is_activated = self.blockchain_service.is_user_activated(wallet_address)
            logger.info(f"[AccountService] Пользователь {wallet_address} активирован: {is_activated}")
            return is_activated
        except Exception as e:
            logger.error(f"[AccountService] Ошибка проверки активации пользователя: {e}")
            return False
    
    def is_user_activated(self, user_address: str) -> bool:
        """
        Проверяет, активирован ли пользователь.
        
        Args:
            user_address: Адрес пользователя
            
        Returns:
            bool: True если пользователь активирован, False иначе
        """
        logger.info(f"[AccountService] Проверка активации пользователя: {user_address}")
        try:
            # Используем метод is_user_activated из blockchain_service
            result = self.blockchain_service.is_user_activated(user_address)
        except Exception as e:
            logger.error(f"[AccountService] Ошибка проверки активации пользователя: {e}")
            result = False
        logger.info(f"[AccountService] Пользователь {user_address} активирован: {result}")
        return result
    
    
    async def activate_and_mint_invites(self, invite_code: str, wallet_address: str) -> List[str]:
        """
        Активирует инвайт и минтит новые инвайт-коды.
        
        Включает валидацию синхронизации активатора и инвайта перед активацией
        для предотвращения ошибок рассинхронизации.
        
        Args:
            invite_code: Код для активации
            wallet_address: Адрес кошелька
            
        Returns:
            List[str]: Список новых инвайт-кодов
            
        Raises:
            ValueError: Если SELLER_PRIVATE_KEY не установлен
            Exception: Если валидация не прошла или активация не удалась
        """
        logger.info(f"[AccountService] Активация инвайта {invite_code} для {wallet_address}")
        
        try:
            # Всегда берем приватный ключ напрямую из окружения
            seller_private_key = os.getenv("SELLER_PRIVATE_KEY")
            if not seller_private_key:
                raise ValueError("SELLER_PRIVATE_KEY не установлен в .env")
            
            # Получаем адрес seller'а (активатора)
            seller_account = Account.from_key(seller_private_key)
            activator_address = seller_account.address
            
            # КРИТИЧНО: Валидация синхронизации активатора и инвайта перед активацией
            logger.info(
                f"[AccountService] Валидация синхронизации перед активацией: "
                f"activator={activator_address[:10]}..., invite={invite_code}"
            )
            
            validation = self.blockchain_service.validate_activator_invite_pair(
                activator_address,
                invite_code
            )
            
            if not validation.get('valid'):
                reason = validation.get('reason', 'unknown')
                logger.error(
                    f"[AccountService] ❌ Валидация не прошла: {reason}. "
                    f"Детали: {validation}"
                )
                
                # Понятные сообщения об ошибках для пользователя
                error_messages = {
                    'invite_not_found': f"Инвайт-код {invite_code} не найден",
                    'invite_not_from_activator': (
                        f"Инвайт-код {invite_code} был создан другим активатором. "
                        f"Ожидался: {activator_address[:10]}..., "
                        f"Создан: {validation.get('minter', 'unknown')[:10]}..."
                    ),
                    'invite_already_used': f"Инвайт-код {invite_code} уже использован",
                    'invite_expired': (
                        f"Инвайт-код {invite_code} истек. "
                        f"Expiry: {validation.get('expiry')}, "
                        f"Current: {validation.get('current_time')}"
                    ),
                    'activator_circle_full': (
                        f"Активатор {activator_address[:10]}... заполнил свой круг "
                        f"(circle_size: {validation.get('circle_size', 0)}/12)"
                    )
                }
                
                error_message = error_messages.get(reason, f"Ошибка валидации: {reason}")
                raise Exception(error_message)
            
            logger.info(
                f"[AccountService] ✅ Валидация прошла успешно: "
                f"capacity={validation.get('activator_capacity')}/12, "
                f"circle_size={validation.get('circle_size')}/12"
            )
            
            # Генерируем ровно 12 уникальных инвайт-кодов для спиральной системы
            new_invite_codes = self._generate_spiral_invite_codes(12)
            logger.info(f"[AccountService] Сгенерированы {len(new_invite_codes)} новых спиральных инвайт-кодов")
            
            # Активируем пользователя через SpiralEngine
            result = await self.blockchain_service.activate_invite(
                invite_code, 
                wallet_address, 
                new_invite_codes, 
                0,  # expiry
                seller_private_key
            )
            
            if result.get("success"):
                logger.info(
                    f"[AccountService] ✅ Пользователь {wallet_address} активирован успешно. "
                    f"Создано {len(new_invite_codes)} новых инвайт-кодов. "
                    f"TX: {result.get('tx_hash', 'N/A')[:10]}..."
                )
                return new_invite_codes
            else:
                error_reason = result.get('reason', 'Unknown error')
                logger.error(f"[AccountService] ❌ Ошибка активации: {error_reason}")
                raise Exception(f"Ошибка активации: {error_reason}")
                
        except Exception as e:
            logger.error(
                f"[AccountService] ❌ Ошибка активации пользователя {wallet_address}: {e}",
                exc_info=True
            )
            raise

    def _generate_spiral_invite_codes(self, count: int = 12) -> List[str]:
        """Генерация уникальных инвайт-кодов для спиральной системы"""
        import random
        import string
        
        codes = set()
        chars = string.ascii_uppercase + string.digits
        
        while len(codes) < count:
            # Генерируем код в формате SPIRAL-XXXX-XXXX
            first_part = ''.join(random.choice(chars) for _ in range(4))
            second_part = ''.join(random.choice(chars) for _ in range(4))
            code = f"SPIRAL-{first_part}-{second_part}"
            
            # Проверяем уникальность
            if code not in codes:
                codes.add(code)
        
        result = list(codes)
        logger.info(f"[AccountService] Сгенерировано {count} уникальных инвайт-кодов для спиральной системы")
        return result
