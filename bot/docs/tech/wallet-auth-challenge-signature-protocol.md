# Wallet Auth Challenge-Signature Protocol

Статус: draft  
Контекст: wallet -> bot signing flow  
Связанный task: `bot/docs/analysis/tasks/task-implement-wallet-bot-auth-server-shared/subtask-a-auth-protocol-contract/task-implement-wallet-auth-challenge-signature-contract.md`

---

## 1. Purpose and Scope

Этот документ фиксирует protocol SSOT для авторизации wallet-клиента в signing flow:
- `GET /v1/pending-sign-requests`
- `GET /v1/uploads/{upload_id}/sign-payload`
- `GET /v1/sign-requests/{id}`
- `POST /v1/sign-requests/{id}/submit`

Цель: заменить trust-by-header (`X-User-Id`) на криптографически подтвержденную схему `challenge + EVM signature`.

---

## 2. Handshake Endpoints

### 2.1 Issue challenge

`POST /v1/wallet-auth/challenge`

Request:
```json
{
  "wallet_address": "0xabc...",
  "user_id": "user-123",
  "auth_scope": "signing_flow"
}
```

Response:
```json
{
  "challenge_id": "ch_01...",
  "nonce": "n_01...",
  "issued_at": "2026-03-26T12:00:00Z",
  "expires_at": "2026-03-26T12:02:00Z",
  "canonical_message": "Amanita Wallet Auth\nDomain: ...\n..."
}
```

### 2.2 Verify signature

`POST /v1/wallet-auth/verify`

Request:
```json
{
  "challenge_id": "ch_01...",
  "wallet_address": "0xabc...",
  "user_id": "user-123",
  "signature": "0x..."
}
```

Response:
```json
{
  "token_type": "bearer",
  "wallet_auth_token": "wa_eyJ...",
  "expires_at": "2026-03-26T12:05:00Z"
}
```

---

## 3. Canonical Message Format

Подписываемая строка (строгий порядок строк):

```text
Amanita Wallet Auth
Domain: {domain}
Wallet: {wallet_address}
User: {user_id}
Scope: {auth_scope}
Challenge ID: {challenge_id}
Nonce: {nonce}
Issued At: {issued_at}
Expires At: {expires_at}
Chain ID: {chain_id}
```

Обязательные требования:
- `domain` должен соответствовать bot API домену/host.
- `wallet_address` и `user_id` должны совпадать между challenge и verify.
- `auth_scope` для этого контекста: `signing_flow`.
- `chain_id` включается для domain separation и защиты от cross-chain reuse.

---

## 4. Auth Contract for Signing Endpoints

После успешного verify клиент передает:
- `Authorization: Bearer <wallet_auth_token>`
- `X-Wallet-Address: <0x...>`
- `X-User-Id: <user_id>` (transitional compatibility)

Server-side проверки (ожидаемое поведение Subtask B):
1) токен валиден и не истек;
2) адрес в токене совпадает с `X-Wallet-Address`;
3) user в токене/контексте совпадает с ресурсом endpoint;
4) для fallback-path проверяется env-политика.

---

## 5. Replay and TTL Policy

- Challenge TTL: 120 seconds.
- Wallet auth token TTL: 300 seconds.
- Challenge one-time usage: после успешного verify challenge переходит в `consumed`.
- Повторное использование consumed challenge запрещено.
- Clock skew tolerance: +-30 seconds.

Challenge states:
- `issued`
- `consumed`
- `expired`

Session states:
- `active`
- `expired`
- `revoked` (резерв для будущего hardening)

---

## 6. Error Contract

Auth-ошибки должны возвращать machine-readable `error_code`.

Минимальный набор:
- `auth_header_missing` -> 401
- `auth_token_invalid` -> 401
- `auth_session_expired` -> 401
- `auth_challenge_expired` -> 401
- `auth_challenge_reused` -> 409
- `auth_signature_invalid` -> 401
- `auth_wallet_mismatch` -> 403
- `auth_user_mismatch` -> 403
- `auth_fallback_disabled` -> 403

Рекомендуемый response shape:
```json
{
  "error": "authentication_error",
  "error_code": "auth_signature_invalid",
  "message": "Wallet signature validation failed"
}
```

---

## 7. Localhost Compatibility Policy

Env contract:
- `WALLET_AUTH_MODE=challenge_signature`
- `ALLOW_X_USER_ID_FALLBACK=true|false`

Правила:
- production: `ALLOW_X_USER_ID_FALLBACK=false`;
- localhost/dev: допускается `true` для мягкой миграции;
- каждый fallback-case должен логироваться как `degraded_auth_mode`.

---

## 8. Security Notes and Limitations

- In-memory challenge/session store допустим для single-instance localhost.
- Для multi-instance нужен shared store (например Redis).
- Transitional зависимость от `X-User-Id` должна быть удалена на финальном hardening этапе.

