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
        
        Args:
            invite_code: Код для активации
            wallet_address: Адрес кошелька
            
        Returns:
            List[str]: Список новых инвайт-кодов
        """
        logger.info(f"[AccountService] Активация инвайта {invite_code} для {wallet_address}")
        
        try:
            # Генерируем ровно 12 уникальных инвайт-кодов для спиральной системы
            new_invite_codes = self._generate_spiral_invite_codes(12)
            logger.info(f"[AccountService] Сгенерированы {len(new_invite_codes)} новых спиральных инвайт-кодов")

            # Всегда берем приватный ключ напрямую из окружения
            seller_private_key = os.getenv("SELLER_PRIVATE_KEY")
            if not seller_private_key:
                raise ValueError("SELLER_PRIVATE_KEY не установлен в .env")
            
            # Активируем пользователя через SpiralEngine
            result = await self.blockchain_service.activate_invite(
                invite_code, 
                wallet_address, 
                new_invite_codes, 
                0,  # expiry
                seller_private_key
            )
            
            if result.get("success"):
                logger.info(f"[AccountService] Пользователь {wallet_address} активирован с {len(new_invite_codes)} новыми кодами")
                return new_invite_codes
            else:
                raise Exception(f"Ошибка активации: {result.get('reason', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"[AccountService] Ошибка активации пользователя: {e}")
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
