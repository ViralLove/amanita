// docs/reference/09_commerce_checkout_floous-metamask-map.md

# 09_commerce_checkout_floous — MetaMask reference map

## Что подсматривать
- Approve + send tx UX patterns.
- Swaps/ramps floous как референс “платёжных” pipeline.

## Где искать
- `transaction-controller` + UI confirm screens
- `approval-controller`
- `swaps-controller` (паттерн шагов)
- `transaction-pay-controller` (если релевантно)

## Не копировать
- Их конкретные интеграции ramps/swaps (сервисные зависимости).

## Перевод
- Собственный “checkout orchestrator” поверх твоих Tx/Signing/Approval модулей.
- Сохранение order state локально, независимое от внешних API.