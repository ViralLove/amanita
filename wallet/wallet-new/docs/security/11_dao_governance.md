// docs/spec/11_dao_governance.md

# 11_dao_governance — DAO & governance

## Цель
Дать пользователю инструменты DAO: просмотр предложений, голосование, делегирование, подписи.

## Инварианты
- Голосование должно быть воспроизводимо: показываем данные proposal.
- Подписи EIP-712 для offchain voting где применимо.
- Никаких “автоголосований” без подтверждения.

## MVP
- Read-only: proposals + текущие результаты (через RPC/indexer по выбору).
- Onchain vote (Governor) — 1 протокол в MVP.
- Delegation (ERC20Votes) — позже.

## API
- `listProposals(daoId): Proposal[]`
- `castVote(proposalId, choice): TxId`
- `signVoteOffchain(typedData): Signature`

## Тесты
- Typed data domain fixtures.
- Vote tx building.