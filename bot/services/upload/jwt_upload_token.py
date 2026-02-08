"""
Upload token JWT RS256: sign with backend private key for Edge to verify.

Claims: upload_id, user_id, max_bytes, exp.
Key: env UPLOAD_TOKEN_JWT_PRIVATE_KEY (PEM string) or UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE (path).
"""

from __future__ import annotations

import os
import time
from typing import Optional

try:
    import jwt as pyjwt
except ImportError:
    pyjwt = None  # type: ignore

ALGORITHM = "RS256"


class JWTUploadTokenError(Exception):
    """Missing key or signing failure."""
    pass


def _load_private_key() -> str:
    """Load PEM from env. Raises JWTUploadTokenError if missing or invalid."""
    raw = os.environ.get("UPLOAD_TOKEN_JWT_PRIVATE_KEY")
    if raw:
        # Allow literal \n in env
        return raw.replace("\\n", "\n").strip()
    path = os.environ.get("UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE")
    if path and os.path.isfile(path):
        with open(path, "r") as f:
            return f.read().strip()
    raise JWTUploadTokenError(
        "Upload JWT private key not configured: set UPLOAD_TOKEN_JWT_PRIVATE_KEY (PEM string) "
        "or UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE (path to PEM file)."
    )


def sign_upload_token(
    upload_id: str,
    user_id: str,
    max_bytes: int,
    exp_seconds: int,
    private_key_pem: Optional[str] = None,
) -> str:
    """
    Sign a JWT for the upload flow. Edge will verify with the public key.

    Args:
        upload_id: Upload record id (UUID string).
        user_id: User id (UUID string).
        max_bytes: Max payload size allowed.
        exp_seconds: Token validity in seconds from now.
        private_key_pem: Optional PEM string; if None, loaded from env.

    Returns:
        JWT string (RS256).

    Raises:
        JWTUploadTokenError: If PyJWT is not installed, key is missing, or signing fails.
    """
    if pyjwt is None:
        raise JWTUploadTokenError("PyJWT is required for upload_token signing. Install with: pip install PyJWT cryptography.")
    key = private_key_pem or _load_private_key()
    now = int(time.time())
    payload = {
        "upload_id": upload_id,
        "user_id": user_id,
        "max_bytes": max_bytes,
        "exp": now + exp_seconds,
        "iat": now,
    }
    try:
        return pyjwt.encode(payload, key, algorithm=ALGORITHM)
    except Exception as e:
        if isinstance(e, JWTUploadTokenError):
            raise
        raise JWTUploadTokenError(f"Failed to sign upload token: {e}") from e
