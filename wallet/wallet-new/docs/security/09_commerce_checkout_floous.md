// docs/spec/09_commerce_checkout_floous.md

# 09_commerce_checkout_floous — Commerce floous

## Цель
Сценарии e-commerce: оплата, подтверждения, receipts, статусы.

## Инварианты
- Чёткое разделение: “подпись заказа” (оффчейн) vs “оплата” (ончейн).
- Не делать approve “на бесконечность” по умолчанию.
- Поддержать Permit (EIP-2612/Permit2) там, где возможно.

## MVP
- Floou: cart → quote → approve/permit → pay tx → receipt.
- Сохранение orderId и маппинг tx → order status.
- UI статусы: pending/paid/failed/refunded (последнее позже).

## API
- `createOrderIntent(cart): OrderIntent`
- `preparePayment(orderIntent): PaymentPlan`
- `executePayment(plan): { txId, orderId }`
- `trackOrder(orderId): Status`

## Тесты
- Permit signing fixtures.
- Approve amount logic.