// docs/reference/07_permissions_approvals-metamask-map.md

# 07_permissions_approvals — MetaMask reference map

## Что подсматривать
- ApprovalController / PermissionController patterns.
- Как они строят “request → UI → resolve”.

## Где искать
- `approval-controller`
- `permission-controller`
- `eip1193-permission-middleware`
- `gator-permissions-controller`

## Не копировать
- Их полный permission model (сложный).
- Их снап-специфичные разрешения.

## Перевод
- Минимальная state machine approvals.
- permissions как простой map origin → capabilities.