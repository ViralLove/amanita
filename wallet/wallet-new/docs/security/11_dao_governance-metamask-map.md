// docs/reference/11_dao_governance-metamask-map.md

# 11_dao_governance — MetaMask reference map

## Что подсматривать
- Permission/approval flows для governance действий.
- Snaps как модульность (идея), если ты хочешь расширяемость.

## Где искать
- `snaps-*` (модульность)
- `approval-controller` / `signature-controller`
- `typed data` / `signTypedData`

## Не копировать
- Их снап-окружения полностью.
- Их конкретные внешние интеграции.

## Перевод
- DAO actions = обычные tx/signing flows + DAO-specific UI.
- Держать DAO слой над базовыми модулями.