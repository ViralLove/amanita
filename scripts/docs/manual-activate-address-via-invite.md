# Простой мануал: как сделать любой адрес активатором через инвайт

Этот мануал показывает самый простой путь: взять любой EVM-адрес и подготовить его для работы как `ACTIVATOR_ROLE` через `deploy_full.js`.

## Что нужно заранее

- Запущенная сеть (`localhost` или другая из `hardhat.config.js`)
- Уже задеплоенный `SpiralEngine`
- В `.env` заполнены:
  - `DEPLOYER_PRIVATE_KEY`
  - `ACTIVITY_CREATOR_ADDRESS`
  - `DEPLOYER_INVITE`

## 1) Проверь `.env`

```bash
DEPLOYER_PRIVATE_KEY=0x...
ACTIVITY_CREATOR_ADDRESS=0x...
DEPLOYER_INVITE=AMANITA-XXXX-YYYY
```

## 2) Запусти действие подготовки

```bash
DEPLOY_ACTION=846 npx hardhat run scripts/deploy_full.js --network localhost
```

Что сделает скрипт:
- активирует адрес через `activateUser(...)` (если еще не активирован);
- проверит `ACTIVATOR_ROLE`;
- выдаст `ACTIVATOR_ROLE`, если его нет;
- проверит итоговое состояние.

## 3) Проверка результата

Минимально: посмотреть успешный лог Action 846.

Опционально on-chain:
- `usedInviteByUser(ACTIVITY_CREATOR_ADDRESS) != 0`
- `hasRole(ACTIVATOR_ROLE, ACTIVITY_CREATOR_ADDRESS) == true`

## Частые проблемы

- `ACTIVITY_CREATOR_ADDRESS is required...`  
  Проверь, что адрес задан и валидный.

- `DEPLOYER_INVITE is required...`  
  Добавь валидный инвайт в `.env`.

- Ошибка прав при `grantRole`  
  Проверь, что `DEPLOYER_PRIVATE_KEY` соответствует администратору в `SpiralEngine`.

