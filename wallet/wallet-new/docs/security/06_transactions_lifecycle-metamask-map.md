// docs/reference/06_transactions_lifecycle-metamask-map.md

# 06_transactions_lifecycle — MetaMask reference map

## Что подсматривать
- TransactionController patterns.
- GasFeeController.
- Smart transactions / tracking подходы (концептуально).

## Где искать
- `transaction-controller`
- `gas-fee-controller`
- `nonce`
- `speedup` / `cancel`
- `EIP-1559`

## Не копировать
- Их smart-transactions backend flow (если хочешь независимость).
- Их analytics hooks.

## Перевод
- Свой TxStore + TxService.
- Отделить fee estimation от отправки.