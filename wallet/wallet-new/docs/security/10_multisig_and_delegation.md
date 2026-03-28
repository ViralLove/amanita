// docs/spec/10_multisig_and_delegation.md

# 10_multisig_and_delegation — Multisig & Delegation

## Цель
Добавить слой, позволяющий работать с мультисигом и делегированием прав без привязки к одному протоколу.

## Инварианты
- Базовый кошелёк остаётся минимальным; multisig/AA — модули сверху.
- Подписанты абстрагированы.
- UI чётко показывает “кто подписывает” и “какой порог”.

## MVP
- Read-only поддержка Safe: просмотр owners/threshold, создание tx hash (без исполнения) — опционально.
- Делегирование прав на подпись/действия — через onchain модуль (позже).

## API
- `getAccountCapability(accountId): CapabilitySet`
- `createMultisigTx(intent): MultisigTxDraft`
- `signMultisigTx(draft, signer): Signature`

## Тесты
- Deterministic safeTxHash (если Safe).