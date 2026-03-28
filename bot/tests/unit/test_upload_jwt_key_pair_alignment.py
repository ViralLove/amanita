"""
Временный unit-тест: проверка, что пара ключей JWT (bot private и uploader public) совпадает.
Эталон — конфигурация smoke crystalize (200). Запуск: см. bot/docs/tests/data-upload-integration-tests.md.
Маркер: key_alignment. После стабилизации окружения тест можно удалить.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

# Unit-тесты по умолчанию не загружают bot/.env; этот тест читает из env пути к ключам — подгружаем .env
try:
    from dotenv import load_dotenv
    # __file__ = bot/tests/unit/this_file.py → parent.parent.parent = bot/
    _bot_dir = Path(__file__).resolve().parent.parent.parent
    _env_file = _bot_dir / ".env"
    if _env_file.is_file():
        load_dotenv(_env_file)
except ImportError:
    pass

logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
    from cryptography.hazmat.backends import default_backend
except ImportError:
    serialization = None
    load_pem_private_key = None
    load_pem_public_key = None
    default_backend = None


def _normalize_pem(pem: str) -> str:
    return pem.strip().replace("\r\n", "\n")


def _load_bot_private_pem() -> str | None:
    raw = os.environ.get("UPLOAD_TOKEN_JWT_PRIVATE_KEY")
    if raw:
        logger.info("key_alignment: bot private from UPLOAD_TOKEN_JWT_PRIVATE_KEY (inline)")
        return raw.replace("\\n", "\n").strip()
    path = os.environ.get("UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE")
    if path:
        p = Path(path)
        if not p.is_absolute():
            p = Path.cwd() / path
        if p.is_file():
            logger.info("key_alignment: bot private from UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE=%s (resolved %s)", path, p)
            return p.read_text().strip()
        logger.info("key_alignment: UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE=%s not a file (resolved %s)", path, p)
    return None


def _load_public_pem() -> str | None:
    raw = os.environ.get("UPLOAD_TOKEN_JWT_PUBLIC_KEY")
    if raw:
        logger.info("key_alignment: public key from UPLOAD_TOKEN_JWT_PUBLIC_KEY (inline)")
        return raw.replace("\\n", "\n").strip()
    path = os.environ.get("UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE")
    if path:
        p = Path(path)
        if not p.is_absolute():
            p = Path.cwd() / path
        if p.is_file():
            logger.info("key_alignment: public key from UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE=%s (resolved %s)", path, p)
            return p.read_text().strip()
        logger.info("key_alignment: UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE=%s not a file (resolved %s)", path, p)
    return None


def _load_reference_private_pem() -> str | None:
    path = os.environ.get("REFERENCE_JWT_PRIVATE_KEY_FILE")
    if not path:
        return None
    p = Path(path)
    if not p.is_absolute():
        p = Path.cwd() / path
    if not p.is_file():
        logger.info("key_alignment: REFERENCE_JWT_PRIVATE_KEY_FILE=%s not a file (resolved %s)", path, p)
        return None
    logger.info("key_alignment: reference private from REFERENCE_JWT_PRIVATE_KEY_FILE=%s (resolved %s)", path, p)
    return p.read_text().strip()


def _public_pem_from_private_pem(private_pem: str) -> str:
    key = load_pem_private_key(
        private_pem.encode(),
        password=None,
        backend=default_backend(),
    )
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return pub.decode("utf-8")


@pytest.mark.unit
@pytest.mark.key_alignment
class TestUploadJwtKeyPairAlignment:
    """Проверка совпадения пары ключей JWT (bot = эталон smoke). Временный тест."""

    def test_jwt_key_pair_bot_private_matches_uploader_public(self):
        """Bot private (UPLOAD_TOKEN_JWT_*) и публичный (UPLOAD_TOKEN_JWT_PUBLIC_KEY) — одна пара."""
        if load_pem_private_key is None:
            logger.info("key_alignment: skip — cryptography not installed")
            pytest.skip("cryptography required for key pair check")

        bot_private = _load_bot_private_pem()
        if not bot_private:
            logger.info("key_alignment: skip — no bot private key (set UPLOAD_TOKEN_JWT_PRIVATE_KEY or _FILE)")
            pytest.skip(
                "UPLOAD_TOKEN_JWT_PRIVATE_KEY or UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE not set; "
                "set one to run key alignment test"
            )

        public_pem = _load_public_pem()
        ref_private_pem = _load_reference_private_pem()

        if public_pem:
            logger.info("key_alignment: mode=bot_private_vs_public — comparing derived public vs UPLOAD_TOKEN_JWT_PUBLIC_KEY")
            derived = _public_pem_from_private_pem(bot_private)
            if _normalize_pem(derived) != _normalize_pem(public_pem):
                logger.error("key_alignment: mismatch — bot private and UPLOAD_TOKEN_JWT_PUBLIC_KEY are not a pair")
                pytest.fail(
                    "Bot private key and UPLOAD_TOKEN_JWT_PUBLIC_KEY are not a pair. "
                    "Use the same key pair as smoke (REFERENCE_JWT_PRIVATE_KEY_FILE / uploader public)."
                )
            logger.info("key_alignment: OK — bot private and public key are a pair")
            return

        if ref_private_pem:
            logger.info("key_alignment: mode=bot_vs_reference — comparing public keys from bot private and REFERENCE_JWT_PRIVATE_KEY_FILE")
            bot_public = _public_pem_from_private_pem(bot_private)
            ref_public = _public_pem_from_private_pem(ref_private_pem)
            if _normalize_pem(bot_public) != _normalize_pem(ref_public):
                logger.error("key_alignment: mismatch — bot private and REFERENCE_JWT_PRIVATE_KEY_FILE are not the same pair")
                pytest.fail(
                    "Bot private and REFERENCE_JWT_PRIVATE_KEY_FILE are not the same pair. "
                    "Point UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE to the same file as smoke (e.g. keys/..._private.pem)."
                )
            logger.info("key_alignment: OK — bot private and reference private are the same pair")
            return

        logger.info(
            "key_alignment: skip — no public or reference; set UPLOAD_TOKEN_JWT_PUBLIC_KEY (or _FILE) or REFERENCE_JWT_PRIVATE_KEY_FILE"
        )
        pytest.skip(
            "Set UPLOAD_TOKEN_JWT_PUBLIC_KEY (or _FILE) or REFERENCE_JWT_PRIVATE_KEY_FILE to verify key pair; "
            "reference = smoke crystalize config."
        )
