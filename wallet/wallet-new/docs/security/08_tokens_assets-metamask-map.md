// docs/reference/08_tokens_assets-metamask-map.md

# 08_tokens_assets — MetaMask reference map

## Что подсматривать
- Assets controllers architecture.
- Token detection patterns.

## Где искать
- `assets-controller` / `assets-controllers`
- `token` / `balance`
- `contract-metadata` (в целом в их экосистеме)
- `preferences-controller` (custom tokens)

## Не копировать
- Их сервисные источники токен-листов, если хочешь автономность.

## Перевод
- Слой `TokenService` с источниками: onchain + локальная база.
- Тогглы “trusted token lists” vs “user-added”.