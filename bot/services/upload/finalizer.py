"""
Finalizer job: проверка доступности bundle в gateway, переход published → finalized (task 3.2).
"""

from __future__ import annotations

import logging
import os
import urllib.request
from typing import Any, Callable, Optional

from model.upload import FINALIZED, PUBLISHED

logger = logging.getLogger(__name__)

DEFAULT_GATEWAY_BASE = "https://arweave.net/"
DEFAULT_INTERVAL_SEC = 300
DEFAULT_LIMIT = 50


def _default_fetch(url: str, timeout: int = 10) -> int:
    """HTTP GET url, returns status code. Raises on connection error."""
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status


def run_finalizer(
    supabase_client: Any,
    *,
    gateway_base: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    fetch_url: Optional[Callable[[str], int]] = None,
    timeout: int = 10,
) -> int:
    """
    Выбирает uploads со status=published, для каждого проверяет доступность bundle
    по gateway (GET gateway_base + bundle_tx_id); при 200 обновляет status=finalized.

    Returns:
        Количество переведённых в finalized записей.
    """
    gateway_base = gateway_base or os.environ.get("UPLOAD_FINALIZER_GATEWAY_URL") or DEFAULT_GATEWAY_BASE
    if not gateway_base.endswith("/"):
        gateway_base = gateway_base + "/"
    fetch = fetch_url or _default_fetch
    rows = supabase_client.list_uploads_by_status(PUBLISHED, limit=limit)
    finalized_count = 0
    for row in rows:
        upload_id = row.get("upload_id")
        bundle_tx_id = row.get("bundle_tx_id")
        if not upload_id or not bundle_tx_id:
            continue
        url = f"{gateway_base}{bundle_tx_id}"
        try:
            status = fetch(url)
            if 200 <= status < 300:
                supabase_client.update_upload_status(upload_id, FINALIZED)
                finalized_count += 1
                logger.info("Upload finalized", extra={"upload_id": upload_id, "bundle_tx_id": bundle_tx_id})
        except Exception as e:
            logger.debug(
                "Finalizer: bundle not yet available",
                extra={"upload_id": upload_id, "bundle_tx_id": bundle_tx_id, "error": str(e)},
            )
    return finalized_count
