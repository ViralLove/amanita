// docs/reference/05_signing_messages-metamask-map.md

# 05_signing_messages — MetaMask reference map

## Что подсматривать
- eth-sig-util usage.
- SignatureController patterns.
- Anti-phishing formatting/preview.

## Где искать
- `eth-sig-util`
- `SignatureController`
- `signTypedData` / `personal_sign`
- `approval-controller` связка с подписью

## Не копировать
- UI-компоненты предпросмотра 1-в-1.
- Любые “seedless” ветки.

## Перевод
- Свой “SigningService” + “ApprovalService” интерфейсы.
- Typed data preview как отдельный модуль formatter.