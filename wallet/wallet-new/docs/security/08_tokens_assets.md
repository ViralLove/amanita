// docs/spec/08_tokens_assets.md

# 08_tokens_assets — Tokens & assets

## Цель
Показывать балансы и ассеты, поддерживать добавление токенов, кэш, фильтрацию спама.

## Инварианты
- Не доверять metadata от RPC без валидации.
- Кэшируем осторожно, обновляем по блокам.
- Отдельный слой “token registry”.

## MVP
- ERC20 balanceOf, decimals, symbol/name.
- Token list per chain (ручное добавление + импорт).
- NFT опционально позже.

## API
- `getTokenBalance(account, token): Balance`
- `refreshBalances(chainId): void`
- `addCustomToken(tokenMeta): void`

## Тесты
- Mock ERC20 contract calls.
- Caching correctness.