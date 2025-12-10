# Test: Simple Fields Restoration After Node Reset

## Цель

Проверить, что рефакторинг `uploadSimpleFields()` корректно обрабатывает сценарий перезапуска ноды:
- State файл содержит `simple_fields_uploaded = true`
- Контракт пуст (нода перезапущена, blockchain state сброшен)
- `uploadSimpleFields()` должен автоматически восстановить данные из state в контракт

## Предварительные условия

1. Hardhat node запущен:
   ```bash
   npx hardhat node
   ```

2. Контракты развернуты (Action 1):
   ```bash
   DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost
   ```

3. State файл существует с `simple_fields_uploaded`:
   ```bash
   # Проверить наличие state файла
   ls data/components/amanita_muscaria/_upload_state_localhost.json
   ```

## Сценарий тестирования

### Вариант A: Контракт пуст (симуляция перезапуска ноды)

1. **Очистить контракт** (опционально, если нужно симулировать пустой контракт):
   - Перезапустить Hardhat node
   - Передеплоить контракты (Action 1)

2. **Запустить тест**:
   ```bash
   node scripts/tests/test-simple-fields-restoration.js
   ```

3. **Ожидаемый результат**:
   - ✅ Обнаружено несоответствие: state говорит "загружено", контракт пуст
   - ✅ `uploadSimpleFields()` вызван
   - ✅ Данные восстановлены из state в контракт
   - ✅ CIDs в контракте совпадают с CIDs в state файле

### Вариант B: Контракт уже содержит данные

1. **Запустить тест** (без очистки контракта):
   ```bash
   node scripts/tests/test-simple-fields-restoration.js
   ```

2. **Ожидаемый результат**:
   - ✅ Обнаружено соответствие: state и контракт согласованы
   - ✅ `uploadSimpleFields()` пропускает загрузку
   - ✅ Возвращает данные из state без изменений

## Проверка результатов

### Успешный тест должен показать:

```
🧪 Test: Simple Fields Restoration After Node Reset
======================================================================

✅ State file loaded: .../amanita_muscaria/_upload_state_localhost.json
   Component: amanita_muscaria
   Steps completed: simple_fields_uploaded, complex_fields_uploaded, ...
   Simple fields CIDs:
     - title: S9DqZ4nTiYh4mEuyT95qszmEdFAOXJmXhBfUNtZbpts
     - dosage: dnA2n37-LOcO67slOTK3cSGyNVfNX2X6aPtzS5SNHZU

✅ Precondition: simple_fields_uploaded is marked in state

📦 Loading contracts...
   Seller: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
   AmanitaInternational: 0x...

🔍 Checking contract state...
   Contract check result:
     - All present: false
     - Missing: title, dosage
     - Present: none

🔍 Running verifyStepCompletion...
   Verification result:
     - isComplete: true
     - isConsistent: false
     - missingItems: title, dosage

⚠️  Inconsistency detected: State says "uploaded", but contract is empty
   This simulates a node reset scenario
   Testing restoration...

🔧 Calling uploadSimpleFields (should restore from state)...
🔹 ШАГ 1: Загрузка Simple Fields
❌ НЕСООТВЕТСТВИЕ: State file говорит "загружено", но данных нет в контракте
   Отсутствующие поля: title, dosage
   💡 Вероятная причина: Node был перезапущен, blockchain state сброшен
   🔧 Восстанавливаем из state в контракт...
🔧 Восстанавливаем ComponentDescription.title из state в контракт...
✅ ComponentDescription.title восстановлен (CID: S9DqZ4nTiYh4mEuyT95...)
🔧 Восстанавливаем DosageInstruction.description из state в контракт...
✅ DosageInstruction.description восстановлен (CID: dnA2n37-LOcO67slO...)

✅ uploadSimpleFields completed
   Result keys: title, dosage_types

🔍 Verifying contract state after restoration...
   Contract check after restoration:
     - All present: true
     - Missing: none
     - Present: title, dosage

✅ SUCCESS: All fields restored to contract
   Title CID: S9DqZ4nTiYh4mEuyT95qszmEdFAOXJmXhBfUNtZbpts
   Dosage CID: dnA2n37-LOcO67slOTK3cSGyNVfNX2X6aPtzS5SNHZU

✅ CID verification: CIDs match state file

======================================================================
✅ Test completed
======================================================================
```

## Интеграция с валидатором

После успешного теста можно проверить валидатором:

```bash
node scripts/validators/validate_component_upload.js amanita_muscaria localhost
```

Ожидаемый результат:
- ✅ Simple Fields: 2/2 keys found
- ✅ Contract validation: passed

## Troubleshooting

### Ошибка: "State file not found"
- Убедитесь, что компонент был загружен ранее (Action 555)
- Проверьте путь: `data/components/{component_id}/_upload_state_localhost.json`

### Ошибка: "Contract not deployed"
- Запустите Action 1 для деплоя контрактов
- Проверьте, что Hardhat node запущен

### Ошибка: "Seller not activated"
- Запустите Action 777 для генерации инвайтов
- Запустите Action 555 для активации seller

### Тест не обнаруживает несоответствие
- Убедитесь, что контракт действительно пуст (перезапустите ноду и передеплойте)
- Проверьте, что state файл содержит `simple_fields_uploaded` в `steps_completed`

