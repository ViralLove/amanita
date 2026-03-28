// docs/spec/06_transactions_lifecycle.md

# 06_transactions_lifecycle — Tx lifecycle

## Цель
Сделать полный цикл транзакций: build → fee → sign → send → track → speedup/cancel.

## Инварианты
- Nonce management консистентен.
- Газ/fee считаются и отображаются прозрачно.
- Возможность replace-by-fee (EIP-1559).

## MVP
- EIP-1559 tx.
- Send + local tracking (pending/confirmed/failed).
- Speedup/Cancel через replacement tx.

## API
- `buildTx(intent): TxRequest`
- `estimateFees(tx): FeeQuote`
- `submitTx(accountId, tx): TxId`
- `getTxStatus(txId): Status`

## Тесты
- Deterministic tx building.
- Replace tx tests.