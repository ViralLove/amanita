from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.dependencies import get_wallet_auth_service

router = APIRouter(prefix="/v1/wallet-auth", tags=["wallet-auth"])


class ChallengeBody(BaseModel):
    wallet_address: str
    user_id: str
    auth_scope: str = "signing_flow"


class VerifyBody(BaseModel):
    challenge_id: str
    wallet_address: str
    user_id: str
    signature: str


@router.post("/challenge")
async def issue_wallet_challenge(
    body: ChallengeBody,
    auth_service=Depends(get_wallet_auth_service),
):
    rec = auth_service.issue_challenge(body.wallet_address, body.user_id, body.auth_scope)
    return JSONResponse(
        status_code=200,
        content={
            "challenge_id": rec.challenge_id,
            "nonce": rec.nonce,
            "issued_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(rec.issued_at)),
            "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(rec.expires_at)),
            "canonical_message": auth_service.build_canonical_message(rec),
        },
    )


@router.post("/verify")
async def verify_wallet_challenge(
    body: VerifyBody,
    auth_service=Depends(get_wallet_auth_service),
):
    try:
        session = auth_service.verify_signature(
            challenge_id=body.challenge_id,
            wallet_address=body.wallet_address,
            user_id=body.user_id,
            signature=body.signature,
        )
    except ValueError as e:
        code = str(e)
        if code in ("auth_challenge_expired", "auth_signature_invalid", "auth_token_invalid"):
            status = 401
        elif code in ("auth_wallet_mismatch", "auth_user_mismatch"):
            status = 403
        elif code == "auth_challenge_reused":
            status = 409
        else:
            status = 401
        raise HTTPException(status_code=status, detail={"error_code": code})
    return JSONResponse(
        status_code=200,
        content={
            "token_type": "bearer",
            "wallet_auth_token": session.token,
            "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(session.expires_at)),
        },
    )

