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
        self.blockchain = blockchain_service
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
        result = self.blockchain._call_contract_read_function("InviteNFT", "isSeller", False, wallet_address)
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
        
        # Проверяем количество инвайтов у пользователя
        invite_count = self.blockchain._call_contract_read_function("InviteNFT", "userInviteCount", 0, wallet_address)
        logger.info(f"[AccountService] Количество инвайтов у {wallet_address}: {invite_count}")
        
        if invite_count > 0:
            logger.info(f"[AccountService] Адрес {wallet_address} владеет {invite_count} инвайтами")
            return True
        else:
            logger.warning(f"[AccountService] Адрес {wallet_address} не владеет Invite NFT")
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
        result = self.blockchain._call_contract_read_function("InviteNFT", "isUserActivated", False, user_address)
        logger.info(f"[AccountService] Пользователь {user_address} активирован: {result}")
        return result
    
    def get_all_activated_users(self) -> List[str]:
        """
        Получает список всех активированных пользователей.
        
        Returns:
            List[str]: Список адресов активированных пользователей
        """
        logger.info("[AccountService] Получение списка активированных пользователей")
        users = self.blockchain._call_contract_read_function("InviteNFT", "getAllActivatedUsers", [])
        logger.info(f"[AccountService] Найдено активированных пользователей: {len(users)}")
        return users
    
    def batch_validate_invite_codes(self, invite_codes: List[str], user_address: str) -> Tuple[List[str], List[str]]:
        """
        Пакетная валидация инвайт-кодов для пользователя.
        
        Args:
            invite_codes: Список инвайт-кодов для проверки
            user_address: Адрес пользователя
            
        Returns:
            Tuple[List[str], List[str]]: Кортеж (валидные_коды, невалидные_коды)
        """
        logger.info(f"[AccountService] Пакетная валидация {len(invite_codes)} кодов для {user_address}")
        result = self.blockchain._call_contract_read_function("InviteNFT", "batchValidateInviteCodes", ([], []), invite_codes, user_address)
        success_array, reasons_array = result
        
        # Преобразуем результат в нужный формат
        valid_codes = []
        invalid_codes = []
        
        for i, (code, is_valid) in enumerate(zip(invite_codes, success_array)):
            if is_valid:
                valid_codes.append(code)
            else:
                invalid_codes.append(code)
        
        logger.info(f"[AccountService] Валидных кодов: {len(valid_codes)}, невалидных: {len(invalid_codes)}")
        return valid_codes, invalid_codes
    
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
        
        # Генерируем 12 новых кодов в формате AMANITA-XXXX-YYYY
        def generate_random_code():
            import random
            chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            first_part = ''.join(random.choice(chars) for _ in range(4))
            second_part = ''.join(random.choice(chars) for _ in range(4))
            return f"AMANITA-{first_part}-{second_part}"

        new_invite_codes = [generate_random_code() for _ in range(12)]
        logger.info(f"[AccountService] Сгенерированы новые инвайт-коды: {new_invite_codes}")

        # Всегда берем приватный ключ напрямую из окружения
        seller_private_key = os.getenv("SELLER_PRIVATE_KEY")
        if not seller_private_key:
            raise ValueError("SELLER_PRIVATE_KEY не установлен в .env")
        
        # Получаем контракт и функцию для оценки газа
        contract = self.blockchain.get_contract("InviteNFT")
        contract_function = getattr(contract.functions, "activateAndMintInvites")
        
        estimate_gas = await self.blockchain.estimate_gas_with_multiplier(
            contract_function,
            invite_code,
            wallet_address,
            new_invite_codes,
            0  # expiry - добавляем 4-й аргумент
        )

        logger.info(f"[AccountService] Оценка газа: {estimate_gas}")
        
        # Увеличиваем лимит газа для сложных транзакций
        gas_limit = max(estimate_gas, 10000000)  # 10M газа
        logger.info(f"[AccountService] Используемый лимит газа: {gas_limit}")
            
        tx_hash = await self.blockchain.transact_contract_function(
            "InviteNFT",
            "activateAndMintInvites",
            seller_private_key,
            invite_code,
            wallet_address,
            new_invite_codes,
            0,
            gas=gas_limit
        )
        logger.info(f"[AccountService] Транзакция отправлена: {tx_hash}")
        
        # Проверяем результат транзакции
        if not tx_hash:
            raise Exception("Транзакция не была отправлена или завершилась с ошибкой")
        
        # Ждем подтверждения транзакции
        receipt = self.blockchain.web3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f"[AccountService] Транзакция выполнена: gasUsed={receipt['gasUsed']}, status={receipt['status']}")
        
        # Проверяем статус транзакции
        if receipt['status'] != 1:
            raise Exception(f"Транзакция завершилась с ошибкой. Status: {receipt['status']}")
            
        logger.info(f"[AccountService][INVITE] Успешно активирован инвайт и выданы новые для {wallet_address}")

        return new_invite_codes
