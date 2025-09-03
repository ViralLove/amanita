"""
Менеджер HTTP сессий для оптимизации соединений.
Централизованное управление aiohttp сессиями с connection pooling.
"""

import asyncio
import aiohttp
import logging
from typing import Optional
from .image_service_config import ImageServiceConfig


class SessionManager:
    """
    Менеджер HTTP сессий с использованием Singleton pattern.
    
    Обеспечивает:
    - Единую сессию для всех ImageService
    - Connection pooling
    - Keep-alive соединения
    - Автоматическую очистку ресурсов
    """
    
    _instance: Optional['SessionManager'] = None
    _session: Optional[aiohttp.ClientSession] = None
    _lock = asyncio.Lock()
    
    def __new__(cls) -> 'SessionManager':
        """Singleton pattern - возвращает единственный экземпляр."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Инициализация менеджера сессий."""
        if not hasattr(self, '_initialized'):
            self.logger = logging.getLogger(__name__)
            self._initialized = True
            self.logger.info("[SessionManager] Инициализирован")
    
    async def get_session(self, config: Optional[ImageServiceConfig] = None) -> aiohttp.ClientSession:
        """
        Получает или создает HTTP сессию с оптимальными настройками.
        
        Args:
            config: Конфигурация для настройки сессии
            
        Returns:
            aiohttp.ClientSession: Оптимизированная HTTP сессия
        """
        async with self._lock:
            if self._session is None or self._session.closed:
                self._session = await self._create_session(config)
                self.logger.info("[SessionManager] Создана новая HTTP сессия")
            return self._session
    
    async def _create_session(self, config: Optional[ImageServiceConfig] = None) -> aiohttp.ClientSession:
        """
        Создает новую HTTP сессию с оптимальными настройками.
        
        Args:
            config: Конфигурация для настройки сессии
            
        Returns:
            aiohttp.ClientSession: Новая HTTP сессия
        """
        # Настройки по умолчанию
        timeout = aiohttp.ClientTimeout(
            total=30,
            connect=10,
            sock_read=20
        )
        
        # Настройки connector для connection pooling
        connector = aiohttp.TCPConnector(
            limit=100,  # Общий лимит соединений
            limit_per_host=30,  # Лимит соединений на хост
            keepalive_timeout=30,  # Keep-alive timeout
            enable_cleanup_closed=True,  # Автоматическая очистка закрытых соединений
            use_dns_cache=True,  # Кэширование DNS
            ttl_dns_cache=300,  # TTL для DNS кэша
            family=0,  # IPv4 и IPv6
            ssl=False  # SSL будет настроен автоматически
        )
        
        # Общие заголовки для всех запросов
        headers = {
            'User-Agent': 'AmanitaBot/1.0 (ImageService)',
            'Accept': 'image/jpeg,image/png,image/webp,*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        # Если передана конфигурация, используем её настройки
        if config:
            timeout = aiohttp.ClientTimeout(
                total=config.download_timeout,
                connect=min(config.download_timeout // 3, 10),
                sock_read=min(config.download_timeout // 2, 20)
            )
            
            # Настройки connector на основе конфигурации
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                keepalive_timeout=config.download_timeout,
                enable_cleanup_closed=True,
                use_dns_cache=True,
                ttl_dns_cache=300,
                family=0,
                ssl=False
            )
        
        # Создаем сессию с оптимизированными настройками
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers,
            raise_for_status=False,  # Обрабатываем статусы вручную
            auto_decompress=True  # Автоматическая декомпрессия
        )
        
        self.logger.info(f"[SessionManager] Создана сессия с настройками: "
                        f"timeout={timeout.total}s, "
                        f"connector_limit={connector.limit}, "
                        f"keepalive={connector._keepalive_timeout}s")
        
        return session
    
    async def close_session(self) -> None:
        """Закрывает текущую HTTP сессию."""
        async with self._lock:
            if self._session and not self._session.closed:
                await self._session.close()
                self.logger.info("[SessionManager] HTTP сессия закрыта")
    
    async def cleanup(self) -> None:
        """Полная очистка ресурсов менеджера сессий."""
        await self.close_session()
        self._session = None
        self.logger.info("[SessionManager] Ресурсы очищены")
    
    def get_session_info(self) -> dict:
        """
        Возвращает информацию о текущей сессии.
        
        Returns:
            dict: Информация о сессии
        """
        if self._session is None or self._session.closed:
            return {'status': 'closed', 'session': None}
        
        connector = self._session.connector
        return {
            'status': 'active',
            'session': str(self._session),
            'connector_limit': connector.limit if connector else None,
            'connector_limit_per_host': connector.limit_per_host if connector else None,
            'keepalive_timeout': connector._keepalive_timeout if connector else None,
            'closed': self._session.closed
        }
    
    @classmethod
    async def get_instance(cls) -> 'SessionManager':
        """
        Получает экземпляр SessionManager (async версия).
        
        Returns:
            SessionManager: Экземпляр менеджера сессий
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Сбрасывает singleton instance (для тестирования)."""
        cls._instance = None
        cls._session = None
