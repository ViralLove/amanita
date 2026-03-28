// docs/spec/07_permissions_approvals.md

# 07_permissions_approvals — Approvals & Permissions

## Цель
Единый механизм запросов на подтверждение: подписи, транзакции, подключения dapp, разрешения.

## Инварианты
- Ничего опасного без явного approval.
- Все approvals логируются локально (audit trail) без секретов.
- Политики разрешений ограничены по доменам/адресам.

## MVP
- Approval types: SIGN_MESSAGE, SIGN_TYPED_DATA, SEND_TX, CONNECT_DAPP.
- UI prompts + cancellable flow.
- Permission store per origin.

## API
- `requestApproval(type, payload): Promise<Decision>`
- `getPermissions(origin): Permissions`
- `grant/revokePermissions(origin, ...)`

## Тесты
- Approval state machine.
- Permission revocation.