# Точки решений: task-activities-deploy-2 (деплой ActivityRegistry)

**Дата:** 2026-01-29  
**Контекст:** как реализовать деплой ActivityRegistry в scripts.

---

## Решение: интеграция в deploy_full (action 5 + action 1)

| Вопрос | Варианты | Выбор |
|--------|----------|--------|
| Отдельный скрипт vs интеграция в deploy_full | (a) Создать `deploy_activity_registry.js` с CLI/env для SpiralEngine. (b) Добавить ActivityRegistry в существующий механизм deploy_full: action 5 (универсальный UUPS) и action 1 (старт проекта). | **(b)** — добавить новый сегмент про Activity в action 5 и action 1; использовать готовый механизм UUPS и регистрации через MagicRegistry. |
| Источник адреса SpiralEngine | При интеграции в action 1/5 SpiralEngine уже есть: в action 1 — из порядка деплоя, в action 5 — из ContractManager.getContract('SpiralEngine') (env/конфиг/MagicRegistry). | Отдельный источник не задаём; тот же механизм, что для ProductRegistry. |
| Запись адресов в файл (deployments/localhost/...) | Опционально по таску. При интеграции в deploy_full адреса выводятся в stdout (printContractAddresses); при необходимости чтения из файла — по образцу существующих скриптов позже. | На первом шаге — вывод в stdout; опционально добавить запись в файл по образцу других контрактов. |

---

**Итог:** Реализация — добавление ActivityRegistry в ContractManager (getInitializeArgs, список UUPS, getLogicConstructorArgs), в DeployActions.action5 (uupsContracts), в DeployActions.action1 (деплой + printContractAddresses); при необходимости — constants.js. Проверка на localhost — через DEPLOY_ACTION=1 или DEPLOY_ACTION=5 DEPLOY_CONTRACT=ActivityRegistry.
