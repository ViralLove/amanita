// docs/spec/05_signing_messages.md

# 05_signing_messages — Message signing (EIP-191 / EIP-712)

## Цель
Безопасно подписывать сообщения и typed data, с анти-фишинг UX.

## Инварианты
- Подпись только после явного approval.
- Typed data валидируется/нормализуется.
- Отображение “что подписываем” человекочитаемо.

## MVP
- `personal_sign`
- `eth_signTypedData_v4` (EIP-712)
- domain separation

## API
- `signPersonalMessage(accountId, message): Signature`
- `signTypedData(accountId, typedData): Signature`

## Тесты
- EIP-712 fixtures.
- Regression on domain hashing.