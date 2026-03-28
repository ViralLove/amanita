// docs/reference/04_provider_rpc_layer-metamask-map.md

# 04_provider_rpc_layer — MetaMask reference map

## Что подсматривать
- JSON-RPC engine + middleware pipeline.
- Network controller patterns.

## Где искать
- `json-rpc-engine`
- `eth-json-rpc-middleware`
- `network-controller`
- `selected-network-controller`
- `rpc-errors`

## Не копировать
- Сложные feature flags и backend сервисы.
- Их “multichain api client” если ты хочешь независимость.

## Перевод
- Минимальный middleware chain (2–4 middleware).
- Явный модуль `rpc/engine.ts` вместо размазанной логики.