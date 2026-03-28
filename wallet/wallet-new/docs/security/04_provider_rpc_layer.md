// docs/spec/04_provider_rpc_layer.md

# 04_provider_rpc_layer — Provider & RPC layer (EIP-1193)

## Цель
Дать приложению единый интерфейс общения с EVM сетями: provider, сети, middleware, ретраи.

## Инварианты
- Не доверять RPC: валидация ответов.
- Возможность смены RPC.
- Fallback providers.

## MVP
- EIP-1193 provider для внутренних модулей.
- Chain config: chainId, rpcUrls, blockExplorer.
- Basic middleware: logging (без секретов), error mapping.

## API
- `getProvider(chainId): Provider`
- `switchChain(chainId): void`
- `call(method, params): Promise<any>`

## Тесты
- Mock provider calls.
- Retry/backoff policy.