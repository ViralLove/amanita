# wallet_push — отправка запроса на подпись в Wallet

Абстракция **PushSender**: отправка запроса на подпись в приложение пользователя (Wallet). Реальная реализация — FCM/APNs; в тестах и в wallet-mock runner используется **StubPushSender**.

## Подмена в тестах

Инжектируйте `StubPushSender` вместо реального клиента пуша. После вызовов сервиса проверяйте вызовы через:

```python
stub = StubPushSender()
# ... вызов кода, который вызывает push_sender.send_sign_request(...)
events = stub.get_pending_events()
assert len(events) == 1
assert events[0]["user_id"] == "user-1"
assert events[0]["request_type"] == "sign_arweave"
assert events[0]["request_id"] == "upload-uuid-1"
```

## Как runner читает события

Wallet-mock runner получает тот же экземпляр `StubPushSender`. После того как бэкенд вызвал `send_sign_request`, runner вызывает `get_pending_events()`, забирает новые события и эмулирует «приложение получило пуш». Между сценариями можно вызывать `clear_pending()`.
