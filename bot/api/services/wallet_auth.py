from __future__ import annotations

import os
import secrets
import time
from dataclasses import dataclass
from typing import Dict, Optional

from eth_account import Account
from eth_account.messages import encode_defunct


def _normalize_address(address: str) -> str:
    return (address or "").strip().lower()


def _now() -> int:
    return int(time.time())


@dataclass
class ChallengeRecord:
    challenge_id: str
    wallet_address: str
    user_id: str
    auth_scope: str
    nonce: str
    issued_at: int
    expires_at: int
    chain_id: str
    domain: str
    consumed: bool = False


@dataclass
class WalletSession:
    token: str
    wallet_address: str
    user_id: str
    scope: str
    expires_at: int


class WalletAuthService:
    """In-memory wallet auth service for challenge/signature flow."""

    def __init__(self):
        self._challenges: Dict[str, ChallengeRecord] = {}
        self._sessions: Dict[str, WalletSession] = {}

    def _challenge_ttl_sec(self) -> int:
        return int(os.environ.get("WALLET_AUTH_CHALLENGE_TTL_SEC", "120"))

    def _session_ttl_sec(self) -> int:
        return int(os.environ.get("WALLET_AUTH_SESSION_TTL_SEC", "300"))

    def _clock_skew_sec(self) -> int:
        return int(os.environ.get("WALLET_AUTH_CLOCK_SKEW_SEC", "30"))

    def _domain(self) -> str:
        return os.environ.get("WALLET_AUTH_DOMAIN", "localhost")

    def _chain_id(self) -> str:
        return os.environ.get("CHAIN_ID", "137")

    def issue_challenge(self, wallet_address: str, user_id: str, auth_scope: str) -> ChallengeRecord:
        now_ts = _now()
        challenge_id = f"ch_{secrets.token_urlsafe(18)}"
        nonce = f"n_{secrets.token_urlsafe(12)}"
        rec = ChallengeRecord(
            challenge_id=challenge_id,
            wallet_address=_normalize_address(wallet_address),
            user_id=user_id,
            auth_scope=auth_scope,
            nonce=nonce,
            issued_at=now_ts,
            expires_at=now_ts + self._challenge_ttl_sec(),
            chain_id=self._chain_id(),
            domain=self._domain(),
        )
        self._challenges[challenge_id] = rec
        return rec

    def build_canonical_message(self, rec: ChallengeRecord) -> str:
        return (
            "Amanita Wallet Auth\n"
            f"Domain: {rec.domain}\n"
            f"Wallet: {rec.wallet_address}\n"
            f"User: {rec.user_id}\n"
            f"Scope: {rec.auth_scope}\n"
            f"Challenge ID: {rec.challenge_id}\n"
            f"Nonce: {rec.nonce}\n"
            f"Issued At: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(rec.issued_at))}\n"
            f"Expires At: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(rec.expires_at))}\n"
            f"Chain ID: {rec.chain_id}\n"
        )

    def verify_signature(
        self,
        challenge_id: str,
        wallet_address: str,
        user_id: str,
        signature: str,
    ) -> WalletSession:
        rec = self._challenges.get(challenge_id)
        if not rec:
            raise ValueError("auth_challenge_not_found")
        if rec.consumed:
            raise ValueError("auth_challenge_reused")
        now_ts = _now()
        if now_ts > rec.expires_at + self._clock_skew_sec():
            raise ValueError("auth_challenge_expired")
        if _normalize_address(wallet_address) != rec.wallet_address:
            raise ValueError("auth_wallet_mismatch")
        if user_id != rec.user_id:
            raise ValueError("auth_user_mismatch")
        message = self.build_canonical_message(rec)
        recovered = Account.recover_message(encode_defunct(text=message), signature=signature)
        if _normalize_address(recovered) != rec.wallet_address:
            raise ValueError("auth_signature_invalid")
        rec.consumed = True
        token = f"wa_{secrets.token_urlsafe(24)}"
        session = WalletSession(
            token=token,
            wallet_address=rec.wallet_address,
            user_id=rec.user_id,
            scope=rec.auth_scope,
            expires_at=now_ts + self._session_ttl_sec(),
        )
        self._sessions[token] = session
        return session

    def validate_session(self, token: str) -> WalletSession:
        session = self._sessions.get(token)
        if not session:
            raise ValueError("auth_token_invalid")
        if _now() > session.expires_at + self._clock_skew_sec():
            raise ValueError("auth_session_expired")
        return session

