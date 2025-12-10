# Валидация синхронизации активатора и инвайта

## Обзор

Этот документ описывает систему валидации синхронизации между активатором и инвайтом перед активацией пользователя в SpiralEngine. Система предотвращает ошибки рассинхронизации, которые могут возникать при изменении состояния сети между выбором инвайта и его использованием.

## Проблема

При активации пользователя через SpiralEngine может возникнуть рассинхронизация между активатором и инвайтом:

1. **Рассинхронизация минтера**: Инвайт был создан другим активатором, но используется текущим
2. **Изменение состояния**: Между выбором активатора/инвайта и активацией состояние сети изменилось
3. **Circle limit reached**: Активатор заполнил свой круг (12/12) между выбором и активацией
4. **Инвайт использован**: Инвайт был использован другим пользователем

## Решение

Система проактивной валидации, которая проверяет синхронизацию перед каждой активацией:

- **Предварительная валидация**: Проверка состояния перед активацией
- **Подробное логирование**: Детальные логи для диагностики
- **Понятные ошибки**: Четкие сообщения об ошибках для пользователя

## Архитектура

### BlockchainService.validate_activator_invite_pair()

Метод валидации пары активатор-инвайт в `BlockchainService`.

**Расположение**: `bot/services/core/blockchain.py`

**Сигнатура**:
```python
def validate_activator_invite_pair(self, activator_address: str, invite_code: str) -> dict:
```

**Проверки**:
1. ✅ Инвайт существует (`inviteCodeExists`)
2. ✅ Синхронизация минтера (`inviteMinter == activator`)
3. ✅ Инвайт не использован (`isInviteUsed == false`)
4. ✅ Инвайт не истек (`inviteExpiry > current_time`)
5. ✅ Активатор имеет capacity (`circle_size < 12`)

**Возвращаемое значение**:
```python
{
    'valid': bool,                    # Результат валидации
    'reason': str | None,             # Причина если не valid
    'token_id': int | None,           # Token ID инвайта
    'minter': str | None,             # Адрес минтера
    'is_used': bool,                  # Использован ли инвайт
    'expired': bool,                  # Истек ли инвайт
    'activator_capacity': int,        # Оставшаяся capacity (если valid)
    'circle_size': int,               # Размер круга активатора
    'expected_activator': str | None  # Ожидаемый активатор (если не синхронизирован)
}
```

**Пример использования**:
```python
from bot.services.core.blockchain import BlockchainService

blockchain_service = BlockchainService()

# Валидация перед активацией
validation = blockchain_service.validate_activator_invite_pair(
    activator_address="0x1234...",
    invite_code="AMANITA-XXXX-YYYY"
)

if validation['valid']:
    print(f"✅ Валидно: capacity={validation['activator_capacity']}/12")
    # Можно безопасно активировать
else:
    print(f"❌ Невалидно: {validation['reason']}")
    # Не активировать, обработать ошибку
```

### AccountService.activate_and_mint_invites()

Метод активации с автоматической валидацией в `AccountService`.

**Расположение**: `bot/services/core/account.py`

**Сигнатура**:
```python
async def activate_and_mint_invites(self, invite_code: str, wallet_address: str) -> List[str]:
```

**Процесс**:
1. Получение адреса активатора (seller)
2. **Валидация синхронизации** (новое)
3. Генерация 12 новых инвайт-кодов
4. Активация пользователя через SpiralEngine
5. Возврат новых инвайт-кодов

**Обработка ошибок**:
- Понятные сообщения для каждого типа ошибки
- Подробное логирование для диагностики
- Исключения с детальной информацией

**Пример использования**:
```python
from bot.services.core.blockchain import BlockchainService
from bot.services.core.account import AccountService

blockchain_service = BlockchainService()
account_service = AccountService(blockchain_service)

try:
    # Активация с автоматической валидацией
    new_invite_codes = await account_service.activate_and_mint_invites(
        invite_code="AMANITA-XXXX-YYYY",
        wallet_address="0xabcd..."
    )
    print(f"✅ Активация успешна, создано {len(new_invite_codes)} новых инвайтов")
except Exception as e:
    print(f"❌ Ошибка активации: {e}")
```

## Типы ошибок валидации

### 1. `invite_not_found`
Инвайт-код не существует в SpiralEngine.

**Причина**: Неверный код или инвайт не был создан.

**Решение**: Проверить корректность кода.

### 2. `invite_not_from_activator`
Инвайт был создан другим активатором.

**Причина**: Рассинхронизация между созданием и использованием инвайта.

**Решение**: Использовать инвайт, созданный текущим активатором.

**Детали в ответе**:
- `minter`: Адрес фактического минтера
- `expected_activator`: Адрес ожидаемого активатора

### 3. `invite_already_used`
Инвайт уже был использован.

**Причина**: Инвайт был использован ранее другим пользователем.

**Решение**: Использовать другой инвайт.

### 4. `invite_expired`
Инвайт истек по сроку действия.

**Причина**: Время истечения инвайта (`inviteExpiry`) меньше текущего времени.

**Решение**: Использовать актуальный инвайт или создать новый.

**Детали в ответе**:
- `expiry`: Время истечения
- `current_time`: Текущее время

### 5. `activator_circle_full`
Активатор заполнил свой круг (12/12).

**Причина**: Активатор уже активировал 12 пользователей.

**Решение**: Использовать другого активатора с доступной capacity.

**Детали в ответе**:
- `capacity`: 0 (нет доступных слотов)
- `circle_size`: 12 (круг заполнен)

## Логирование

Система включает подробное логирование на каждом этапе:

### Уровни логирования

1. **INFO**: Успешные операции
   ```
   [BlockchainService] ✅ Пара валидна: activator=0x1234..., invite=AMANITA-XXXX-YYYY, capacity=5/12
   ```

2. **WARNING**: Проблемы валидации
   ```
   [BlockchainService] Рассинхронизация: инвайт AMANITA-XXXX-YYYY создан 0x5678..., а активирует 0x1234...
   ```

3. **ERROR**: Критические ошибки
   ```
   [BlockchainService] ❌ Ошибка валидации пары активатор-инвайт: ...
   ```

### Пример логов

**Успешная валидация**:
```
[BlockchainService] Валидация пары активатор-инвайт: activator=0x1234..., invite=AMANITA-XXXX-YYYY
[BlockchainService] ✅ Пара валидна: activator=0x1234..., invite=AMANITA-XXXX-YYYY, capacity=8/12
[AccountService] ✅ Валидация прошла успешно: capacity=8/12, circle_size=4/12
[AccountService] ✅ Пользователь 0xabcd... активирован успешно. Создано 12 новых инвайт-кодов. TX: 0xef01...
```

**Ошибка валидации**:
```
[BlockchainService] Валидация пары активатор-инвайт: activator=0x1234..., invite=AMANITA-XXXX-YYYY
[BlockchainService] Рассинхронизация: инвайт AMANITA-XXXX-YYYY создан 0x5678..., а активирует 0x1234...
[AccountService] ❌ Валидация не прошла: invite_not_from_activator. Детали: {...}
```

## Интеграция в production

### Автоматическая валидация

Валидация интегрирована автоматически в `AccountService.activate_and_mint_invites()`. 

**Преимущества**:
- ✅ Прозрачность для пользователя
- ✅ Автоматическая защита от ошибок
- ✅ Подробные логи для диагностики

**Текущее использование**:
```python
# В handlers/webapp_common.py и других местах
new_invite_codes = await account_service.activate_and_mint_invites(
    invite_code, 
    wallet_address
)
```

### Ручная валидация (опционально)

Если нужно проверить валидность перед активацией:

```python
from bot.services.core.blockchain import BlockchainService

blockchain_service = BlockchainService()
seller_address = blockchain_service.seller_account.address

# Предварительная проверка
validation = blockchain_service.validate_activator_invite_pair(
    seller_address,
    invite_code
)

if validation['valid']:
    # Можно безопасно активировать
    print(f"Capacity: {validation['activator_capacity']}/12")
else:
    # Обработать ошибку
    print(f"Ошибка: {validation['reason']}")
```

## Производственные сценарии

### Сценарий 1: Нормальная активация

**Условия**:
- Инвайт существует и не использован
- Инвайт создан текущим активатором
- Активатор имеет capacity (circle < 12)

**Результат**: ✅ Успешная активация

### Сценарий 2: Рассинхронизация

**Условия**:
- Инвайт существует, но создан другим активатором

**Результат**: ❌ Ошибка `invite_not_from_activator` с деталями

**Логи**:
```
[BlockchainService] Рассинхронизация: инвайт AMANITA-XXXX-YYYY создан 0x5678..., а активирует 0x1234...
```

### Сценарий 3: Circle Full

**Условия**:
- Активатор заполнил свой круг (12/12)

**Результат**: ❌ Ошибка `activator_circle_full`

**Логи**:
```
[BlockchainService] Активатор 0x1234... заполнен: circle_size=12/12, capacity=0
```

### Сценарий 4: Одновременные активации

**Условия**:
- Два пользователя пытаются активироваться одновременно
- Один успевает, второй получает ошибку

**Результат**: 
- ✅ Первая активация успешна
- ❌ Вторая получает `invite_already_used` или `activator_circle_full`

## Мониторинг и метрики

### Метрики для отслеживания

1. **Успешные валидации**: Количество успешных проверок
2. **Ошибки валидации**: Количество и типы ошибок
3. **Рассинхронизации**: Количество ошибок `invite_not_from_activator`
4. **Circle full**: Количество ошибок из-за заполненного круга

### Рекомендуемые логи

Все события логируются автоматически. Рекомендуется настроить мониторинг:
- Уровень ERROR для критических ошибок
- Уровень WARNING для проблем валидации
- Уровень INFO для успешных операций

## Тестирование

### Unit тесты

Валидация покрыта unit тестами:
- `bot/tests/unit/test_blockchain_service.py`
- `bot/tests/unit/test_account_service.py`

### Integration тесты

Валидация покрыта integration тестами:
- `bot/tests/integration/test_invite_state_tracker.py`
- `bot/tests/integration/test_spiral_engine.py`

### Ручное тестирование

```python
# Пример ручного тестирования
from bot.services.core.blockchain import BlockchainService

bs = BlockchainService()

# Тест 1: Валидная пара
validation = bs.validate_activator_invite_pair(
    activator_address="0x...",
    invite_code="AMANITA-XXXX-YYYY"
)
assert validation['valid'] is True

# Тест 2: Несуществующий инвайт
validation = bs.validate_activator_invite_pair(
    activator_address="0x...",
    invite_code="NONEXISTENT"
)
assert validation['valid'] is False
assert validation['reason'] == 'invite_not_found'
```

## Часто задаваемые вопросы

### Q: Нужно ли вызывать валидацию вручную?

**A**: Нет, валидация вызывается автоматически в `AccountService.activate_and_mint_invites()`. Ручной вызов нужен только для предварительной проверки.

### Q: Что происходит, если валидация не прошла?

**A**: Метод `activate_and_mint_invites()` выбросит исключение с понятным сообщением об ошибке. Нужно обработать исключение и показать пользователю понятное сообщение.

### Q: Как часто возникает рассинхронизация?

**A**: В production рассинхронизация может возникать при:
- Долгой задержке между выбором инвайта и активацией
- Одновременных попытках активации
- Смене активатора между выбором и активацией

Система валидации предотвращает эти проблемы.

### Q: Влияет ли валидация на производительность?

**A**: Валидация добавляет ~3-5 read-only вызовов к контракту, что занимает ~100-200ms. Это приемлемо для production, так как предотвращает ошибки активации.

## Связанные документы

- [`active3-race-condition-explanation-2025-12-06.md`](../analysis/active3-race-condition-explanation-2025-12-06.md) - Подробное описание проблемы и решения
- [`doc-spiral-engine-invite-activation-flow-2025-12-06.md`](../analysis/doc-spiral-engine-invite-activation-flow-2025-12-06.md) - Описание флоу активации

## Версия

**Версия документа**: 1.0  
**Дата создания**: 2025-12-06  
**Последнее обновление**: 2025-12-06

