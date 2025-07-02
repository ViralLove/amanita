Buyer ──► WebApp (Order View)
            │
            ├─ Generates payment amount (price + otp)
            ├─ Deploys minimal PaymentProcessor contract for order
            └─ Shows QR code for contract address + USDT amount
                         │
                         ▼
          Buyer pays exact amount to contract
                         │
              Blockchain emits Transfer event
                         ▼
      Observer Service (web3.py or webhook infra)
            └─ Match tx.amount with OTP-encoded order
            └─ Parse tx.sender
            └─ Call internal order.confirm(orderId, tx.sender)
                         ▼
            Notifies seller (bot, email, callback)
            Unlocks access or fulfillment
