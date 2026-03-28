// docs/reference/10_multisig_and_delegation-metamask-map.md

# 10_multisig_and_delegation — MetaMask reference map

## Что подсматривать
- Их delegation-controller и permission modules.
- Подход “policy/permission first”, а не “всё через один multisig SDK”.

## Где искать
- `delegation-controller`
- `gator-permissions-controller`
- `eip-5792-middleware`
- `keyring` types (hardware, qr) как модель “разных подписантов”

## Не копировать
- Их internal deployment refs без понимания.
- Любые зависимости на backend “smart transactions”.

## Перевод
- Ввести интерфейс `Signer` (EOA signer, hardware signer, multisig signer).
- Делегирование/политики как отдельный модуль, который можно отключать.