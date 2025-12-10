"""
Environment Requirements Validator for E2E tests.

Provides unified API for checking environment requirements:
- Hardhat node availability
- Environment variables
- External services (Arweave, IPFS)

Based on: @temp-test-fixes-architecture.md (Section 3.1)
"""

import os
import pytest
import logging
from typing import Tuple, List, Dict, Callable, Optional

logger = logging.getLogger(__name__)


class EnvironmentValidator:
    """
    Валидатор требований к окружению для E2E тестов.
    
    Обеспечивает:
    - Проверку наличия необходимых переменных окружения
    - Проверку доступности внешних сервисов (Hardhat node, Arweave)
    - Унифицированный API для всех типов тестов
    """
    
    @staticmethod
    def validate_hardhat_node() -> Tuple[bool, str]:
        """
        Проверяет доступность Hardhat node.
        
        Returns:
            Tuple[bool, str]: (доступен, сообщение)
        """
        try:
            # Lazy import to avoid singleton initialization issues
            from bot.services.core.blockchain import BlockchainService
            
            blockchain = BlockchainService()
            if blockchain.web3.is_connected():
                chain_id = blockchain.web3.eth.chain_id
                block_number = blockchain.web3.eth.block_number
                return True, f"Hardhat node доступен (Chain ID: {chain_id}, Block: {block_number})"
            else:
                return False, "Hardhat node не подключен"
        except Exception as e:
            return False, f"Ошибка подключения к Hardhat node: {e}"
    
    @staticmethod
    def validate_environment_variables(required_vars: List[str]) -> Tuple[bool, List[str]]:
        """
        Проверяет наличие переменных окружения.
        
        Args:
            required_vars: Список обязательных переменных
        
        Returns:
            Tuple[bool, List[str]]: (все присутствуют, список отсутствующих)
        """
        missing = [var for var in required_vars if not os.getenv(var)]
        return len(missing) == 0, missing
    
    @staticmethod
    def skip_if_requirements_not_met(requirements: Dict[str, Callable]) -> None:
        """
        Пропускает тест, если требования не выполнены.
        
        Args:
            requirements: Dict[название_требования, функция_проверки]
        
        Raises:
            pytest.skip: Если хотя бы одно требование не выполнено
        """
        for name, check_func in requirements.items():
            result, message = check_func()
            if not result:
                pytest.skip(f"⚠️ {name}: {message}")
    
    @staticmethod
    def should_use_stubs() -> bool:
        """
        Проверяет, должен ли использоваться stub режим.
        
        Returns:
            bool: True если E2E_USE_STUBS=true
        """
        return os.getenv("E2E_USE_STUBS") == "true"
    
    @staticmethod
    def validate_e2e_environment() -> Tuple[bool, Optional[str]]:
        """
        Валидирует окружение для E2E тестов.
        
        Если E2E_USE_STUBS=true, пропускает проверку Hardhat node.
        Если E2E_USE_STUBS=false, проверяет доступность Hardhat node.
        
        Returns:
            Tuple[bool, Optional[str]]: (валидно, сообщение об ошибке или None)
        """
        use_stubs = EnvironmentValidator.should_use_stubs()
        
        if use_stubs:
            logger.info("✅ E2E_USE_STUBS=true: stub режим активирован, проверка Hardhat node пропущена")
            return True, None
        
        # Проверяем Hardhat node только если не stub режим
        node_available, message = EnvironmentValidator.validate_hardhat_node()
        
        if not node_available:
            return False, f"Hardhat node недоступен: {message}. Установите E2E_USE_STUBS=true для stub режима или запустите Hardhat node."
        
        logger.info(f"✅ Hardhat node доступен: {message}")
        return True, None

