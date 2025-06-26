"""
Сервис для управления пользовательскими настройками
"""
import logging
from typing import Dict, Any, Optional, NamedTuple
from datetime import datetime

class Web3Credentials(NamedTuple):
    """Структура для хранения Web3 данных пользователя"""
    address: str
    private_key: str
    created_at: datetime

class UserSettings:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UserSettings, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._settings: Dict[int, Dict[str, Any]] = {}
        self._default_settings = {
            'language': 'ru',
            'notifications_enabled': True,
            'created_at': None,
            'last_activity': None,
            'onboarding_completed': False,
            'telegram_username': None,
            'web3_credentials': None,
            'wallet_connected': False
        }
        logging.info("[USER_SETTINGS] Initialized UserSettings service (Singleton)")
        self._initialized = True

    def _ensure_user_exists(self, user_id: int) -> None:
        """Создает запись для пользователя, если она не существует"""
        if user_id not in self._settings:
            self._settings[user_id] = self._default_settings.copy()
            self._settings[user_id]['created_at'] = datetime.now()
            logging.info(f"[USER_SETTINGS] Created new user settings: user_id={user_id}")

    def _update_activity(self, user_id: int) -> None:
        """Обновляет время последней активности пользователя"""
        self._settings[user_id]['last_activity'] = datetime.now()

    def set_telegram_username(self, user_id: int, username: str) -> None:
        """Устанавливает username пользователя из Telegram"""
        self._ensure_user_exists(user_id)
        self._settings[user_id]['telegram_username'] = username
        self._update_activity(user_id)
        logging.info(f"[USER_SETTINGS] Telegram username set: user_id={user_id}, username={username}")

    def get_telegram_username(self, user_id: int) -> Optional[str]:
        """Получает username пользователя из Telegram"""
        if user_id in self._settings:
            return self._settings[user_id].get('telegram_username')
        return None

    def set_web3_credentials(self, user_id: int, address: str, private_key: str) -> None:
        """Устанавливает Web3 данные пользователя"""
        self._ensure_user_exists(user_id)
        credentials = Web3Credentials(
            address=address,
            private_key=private_key,
            created_at=datetime.now()
        )
        self._settings[user_id]['web3_credentials'] = credentials
        self._settings[user_id]['wallet_connected'] = True
        self._update_activity(user_id)
        logging.info(f"[USER_SETTINGS] Web3 credentials set: user_id={user_id}, address={address}")

    def get_web3_credentials(self, user_id: int) -> Optional[Web3Credentials]:
        """Получает Web3 данные пользователя"""
        if user_id in self._settings:
            return self._settings[user_id].get('web3_credentials')
        return None

    def get_wallet_address(self, user_id: int) -> Optional[str]:
        """Получает только адрес кошелька пользователя"""
        credentials = self.get_web3_credentials(user_id)
        return credentials.address if credentials else None

    def is_wallet_connected(self, user_id: int) -> bool:
        """Проверяет, подключен ли кошелек пользователя"""
        if user_id in self._settings:
            return self._settings[user_id].get('wallet_connected', False)
        return False

    def disconnect_wallet(self, user_id: int) -> None:
        """Отключает кошелек пользователя"""
        if user_id in self._settings:
            self._settings[user_id]['web3_credentials'] = None
            self._settings[user_id]['wallet_connected'] = False
            self._update_activity(user_id)
            logging.info(f"[USER_SETTINGS] Wallet disconnected: user_id={user_id}")

    def set_language(self, user_id: int, language: str) -> None:
        """Устанавливает язык пользователя"""
        self._ensure_user_exists(user_id)
        self._settings[user_id]['language'] = language
        self._update_activity(user_id)
        logging.info(f"[USER_SETTINGS] Language set: user_id={user_id}, language={language}")

    def get_language(self, user_id: int, default: str = 'ru') -> str:
        """Получает язык пользователя"""
        if user_id in self._settings:
            return self._settings[user_id].get('language', default)
        return default

    def set_setting(self, user_id: int, key: str, value: Any) -> None:
        """Устанавливает произвольную настройку пользователя"""
        self._ensure_user_exists(user_id)
        self._settings[user_id][key] = value
        self._update_activity(user_id)
        logging.info(f"[USER_SETTINGS] Setting updated: user_id={user_id}, key={key}, value={value}")

    def get_setting(self, user_id: int, key: str, default: Any = None) -> Any:
        """Получает произвольную настройку пользователя"""
        if user_id in self._settings:
            return self._settings[user_id].get(key, default)
        return default

    def get_all_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает все настройки пользователя"""
        return self._settings.get(user_id)

    def set_onboarding_completed(self, user_id: int, completed: bool = True) -> None:
        """Отмечает завершение онбординга"""
        self._ensure_user_exists(user_id)
        self._settings[user_id]['onboarding_completed'] = completed
        self._update_activity(user_id)
        logging.info(f"[USER_SETTINGS] Onboarding completion set: user_id={user_id}, completed={completed}")

    def is_onboarding_completed(self, user_id: int) -> bool:
        """Проверяет, завершил ли пользователь онбординг"""
        if user_id in self._settings:
            return self._settings[user_id].get('onboarding_completed', False)
        return False

    def set_notifications_enabled(self, user_id: int, enabled: bool) -> None:
        """Включает/выключает уведомления"""
        self._ensure_user_exists(user_id)
        self._settings[user_id]['notifications_enabled'] = enabled
        self._update_activity(user_id)
        logging.info(f"[USER_SETTINGS] Notifications setting updated: user_id={user_id}, enabled={enabled}")

    def are_notifications_enabled(self, user_id: int) -> bool:
        """Проверяет, включены ли уведомления"""
        if user_id in self._settings:
            return self._settings[user_id].get('notifications_enabled', True)
        return True

    def get_user_creation_date(self, user_id: int) -> Optional[datetime]:
        """Получает дату создания настроек пользователя"""
        if user_id in self._settings:
            return self._settings[user_id].get('created_at')
        return None

    def get_last_activity(self, user_id: int) -> Optional[datetime]:
        """Получает время последней активности пользователя"""
        if user_id in self._settings:
            return self._settings[user_id].get('last_activity')
        return None

    def delete_user(self, user_id: int) -> bool:
        """Удаляет все настройки пользователя"""
        if user_id in self._settings:
            del self._settings[user_id]
            logging.info(f"[USER_SETTINGS] User settings deleted: user_id={user_id}")
            return True
        return False
