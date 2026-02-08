# Абстракция вызова Edge Function (вариант B: ООП, тесты дергают реальную Edge с секретом мока).
# См. bot/docs/analysis/tasks/task-implement-upload-flow-core-phase3/edge-mock-integration-variant-b.md

import os
import logging
from typing import Dict, Any, Optional, Protocol

import requests

logger = logging.getLogger(__name__)

# --- Хелпер заголовков мока (env) ---

def get_edge_mock_headers() -> Dict[str, str]:
    """
    Читает EDGE_USE_MOCK и EDGE_MOCK_TEST_SECRET (и опционально override).
    Возвращает заголовки для мок-режима Edge или пустой словарь.
    """
    use_mock = os.getenv("EDGE_USE_MOCK", "").strip().lower() in ("true", "1")
    secret = (os.getenv("EDGE_MOCK_TEST_SECRET") or "").strip()
    if not use_mock or not secret:
        return {}
    headers = {"X-Backend-Mock-Secret": secret}
    put_status = (os.getenv("EDGE_MOCK_PUT_STATUS") or "").strip()
    if put_status in ("200", "404", "409"):
        headers["X-Backend-Mock-Put-Status"] = put_status
    callback = (os.getenv("EDGE_MOCK_CALLBACK") or "").strip()
    if callback in ("200", "404", "409"):
        headers["X-Backend-Mock-Callback"] = callback
    return headers


# --- Абстракция (шаг 1) ---

class EdgeClientProtocol(Protocol):
    """Контракт: клиент вызова Edge (POST к Edge с телом/файлом)."""

    def post(
        self,
        endpoint: str,
        data: Dict[str, Any],
        is_file: bool = False,
        timeout: int = 30,
    ) -> Optional[requests.Response]:
        """
        Выполнить POST к Edge (base_url + endpoint).
        data: для JSON — тело; для is_file — словарь с file_path и content_type.
        Возвращает ответ или None при ошибке до ответа.
        """
        ...


# --- Реализация «Supabase» без мок-заголовков (шаг 2) ---

class SupabaseEdgeClient:
    """
    Реальный HTTP-клиент к Supabase Edge Function.
    Только Authorization и Content-Type; мок-заголовков нет.
    """

    def __init__(self, base_url: str, anon_key: str):
        self.base_url = base_url.rstrip("/")
        self.anon_key = anon_key
        self._base_headers = {
            "Authorization": f"Bearer {anon_key}",
            "Content-Type": "application/json",
        }

    def post(
        self,
        endpoint: str,
        data: Dict[str, Any],
        is_file: bool = False,
        timeout: int = 30,
    ) -> Optional[requests.Response]:
        url = f"{self.base_url}{endpoint}"
        try:
            if is_file:
                file_path = data.get("file_path")
                content_type = data.get("content_type", "application/octet-stream")
                if not file_path:
                    logger.error("[EdgeClient] file_path отсутствует для is_file=True")
                    return None
                with open(file_path, "rb") as f:
                    files = {
                        "file": (
                            os.path.basename(file_path),
                            f,
                            content_type,
                        )
                    }
                resp = requests.post(
                    url,
                    files=files,
                    headers={"Authorization": f"Bearer {self.anon_key}"},
                    timeout=timeout,
                )
            else:
                resp = requests.post(
                    url,
                    json=data,
                    headers=self._base_headers,
                    timeout=timeout,
                )
            return resp
        except requests.exceptions.RequestException as e:
            logger.error(f"[EdgeClient] Ошибка запроса к Edge: {e}")
            return None
        except OSError as e:
            logger.error(f"[EdgeClient] Ошибка чтения файла: {e}")
            return None


# --- Реализация с мок-заголовками (шаг 3) ---

class SupabaseEdgeClientWithMockHeaders(SupabaseEdgeClient):
    """
    Тот же HTTP к Edge, но к каждому запросу добавляются заголовки мока
    (X-Backend-Mock-Secret из EDGE_MOCK_TEST_SECRET и при необходимости override).
    """

    def __init__(self, base_url: str, anon_key: str, extra_headers: Optional[Dict[str, str]] = None):
        super().__init__(base_url, anon_key)
        self._extra_headers = extra_headers if extra_headers is not None else get_edge_mock_headers()

    def post(
        self,
        endpoint: str,
        data: Dict[str, Any],
        is_file: bool = False,
        timeout: int = 30,
    ) -> Optional[requests.Response]:
        url = f"{self.base_url}{endpoint}"
        try:
            if is_file:
                file_path = data.get("file_path")
                content_type = data.get("content_type", "application/octet-stream")
                if not file_path:
                    logger.error("[EdgeClient] file_path отсутствует для is_file=True")
                    return None
                headers = {"Authorization": f"Bearer {self.anon_key}"}
                headers.update(self._extra_headers)
                with open(file_path, "rb") as f:
                    files = {
                        "file": (
                            os.path.basename(file_path),
                            f,
                            content_type,
                        )
                    }
                resp = requests.post(url, files=files, headers=headers, timeout=timeout)
            else:
                headers = {**self._base_headers, **self._extra_headers}
                resp = requests.post(url, json=data, headers=headers, timeout=timeout)
            return resp
        except requests.exceptions.RequestException as e:
            logger.error(f"[EdgeClient] Ошибка запроса к Edge: {e}")
            return None
        except OSError as e:
            logger.error(f"[EdgeClient] Ошибка чтения файла: {e}")
            return None
