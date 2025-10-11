# 🧬 Organic Components: Структура данных и процесс загрузки

**Версия:** 2.0.0  
**Дата:** 2025-10-09  
**Статус:** ✅ Production Ready (Arweave + State Management)

---

## 📋 Содержание

1. [🚀 Quick Start Guide](#-quick-start-guide)
2. [Обзор и архитектура](#обзор-и-архитектура)
3. [Структура файлов](#структура-файлов)
4. [Типы данных](#типы-данных)
5. [Интеграция с контрактами](#интеграция-с-контрактами)
6. [Процесс загрузки в Arweave](#процесс-загрузки-в-arweave)
7. [Скрипт загрузки](#скрипт-загрузки)
8. [Примеры использования](#примеры-использования)

---

## 🚀 Quick Start Guide

### **Шаг 1: Подготовка файлов компонента**

#### 1.1 Создание структуры директорий

```bash
# Создайте директорию для вашего компонента
cd scripts/organic_components
mkdir your_component_name
cd your_component_name

# Создайте поддиректории
mkdir simple_fields
mkdir complex_fields
```

#### 1.2 Создание корневого файла: `your_component_name.json`

Скопируйте структуру из `amanita_muscaria.json` и заполните:

```bash
cp ../amanita_muscaria/amanita_muscaria.json ./your_component_name.json
```

**Обязательные поля для редактирования:**
- `biounit_id`: Уникальный идентификатор (латиница, snake_case)
- `scientific_title`: Научное название на латыни
- `created_by`: Ваш Ethereum адрес (0x...)
- `forms`: Массив форм продукта (ключи из `bot/catalog/component_forms.json`)
- `features.common`: Общие характеристики (ключи из `bot/catalog/features.json`)
- `features.forms`: Специфичные характеристики для каждой формы

**⚠️ Важно:** `localizations` будет заполнен автоматически скриптом!

#### 1.3 Подготовка Simple Fields (многоязычные строки)

Создайте 2 файла в `simple_fields/`:

**Файл 1: `your_component_name.ComponentDescription.title.json`**
```json
{
  "ru": "Ваше название на русском",
  "et": "Teie pealkiri eesti keeles",
  "en": "Your title in English",
  "es": "Tu título en español",
  "fr": "Votre titre en français",
  "de": "Ihr Titel auf Deutsch",
  "nl": "Uw titel in het Nederlands"
}
```

**Файл 2: `your_component_name.DosageInstruction.description.json`**
```json
{
  "dried": {
    "ru": "Инструкция для сушеного (на русском)",
    "et": "Juhised kuivatatud jaoks (eesti keeles)",
    "en": "Instructions for dried (in English)",
    "es": "Instrucciones para seco (en español)",
    "fr": "Instructions pour séché (en français)",
    "de": "Anweisungen für getrocknet (auf Deutsch)",
    "nl": "Instructies voor gedroogd (in het Nederlands)"
  },
  "tincture": {
    "ru": "Инструкция для настойки...",
    // ... аналогично для всех языков
  }
  // ... для всех форм из вашего корневого файла
}
```

#### 1.4 Подготовка Complex Fields (многоязычные описания)

Создайте 7 файлов в `complex_fields/` (по одному на язык):

**Шаблон имени:** `your_component_name.ComponentDescription.{lang}.json`

Где `{lang}` = `ru`, `et`, `en`, `es`, `fr`, `de`, `nl`

**Структура каждого файла:**
```json
{
  "generic_description": "🔬 Подробное описание компонента на данном языке...",
  "effects": "🌿 Целительное действие и эффекты...",
  "shamanic": "🌀 Шаманская/духовная перспектива (опционально)...",
  "warnings": "⚠️ Предостережения и противопоказания..."
}
```

**Пример для русского (`your_component_name.ComponentDescription.ru.json`):**
```json
{
  "generic_description": "🔬 Активные компоненты:\n🔹Компонент А — описание\n🔹Компонент Б — описание",
  "effects": "🌿 Целительное действие:\n🔹Эффект 1: описание\n🔹Эффект 2: описание",
  "shamanic": "🌀 Шаманская перспектива:\nОписание традиционного использования...",
  "warnings": "⚠️ Предостережения:\n🔹Предостережение 1\n🔹Предостережение 2"
}
```

**⚠️ Важно:** 
- Используйте эмодзи для визуальной структуры (🔬, 🌿, 🌀, ⚠️)
- Форматируйте текст с `\n` для переносов строк
- Все 7 языков должны иметь одинаковую структуру полей

---

### **Шаг 2: Тестовая загрузка (Dry-run)**

Перед реальной загрузкой протестируйте все в **dry-run режиме**:

```bash
# 1. Убедитесь, что .env настроен
# DEPLOYER_PRIVATE_KEY=ваш_приватный_ключ
# AMANITA_INTERNATIONAL_PROXY_ADDRESS=0x...
# ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS=0x...
# ARWEAVE_PRIVATE_KEY=ваш_arweave_ключ

# 2. Запустите dry-run
cd /Users/eslinko/Development/Amanita
DRY_RUN=true COMPONENT_ID=your_component_name \
npx hardhat run scripts/upload_organic_component.js --network localhost
```

**Что происходит в dry-run:**
- ✅ Все файлы проверяются на существование
- ✅ JSON валидируется
- ✅ Создаются mock Arweave TX IDs (DRYRUN_...)
- ✅ Симулируется загрузка без реальных транзакций
- ✅ Создается файл state: `_upload_state_localhost.json`

**Проверьте вывод:**
```
🔹 ШАГ 1: Загрузка Simple Fields
📝 1.1. ComponentDescription.title
📤 Загрузка your_component_name_ComponentDescription_title.json в Arweave...
🔷 [DRY-RUN] Mock TX ID: DRYRUN_1728500000_abc123
✅ your_component_name_ComponentDescription_title.json загружен: DRYRUN_...
🔷 [DRY-RUN] Пропускаем сохранение в контракт

🔹 ШАГ 2: Загрузка Complex Fields
📝 2.1. ComponentDescription.ru
...

✅ ШАГ 6 завершен (DRY-RUN)
🎉 ЗАГРУЗКА ЗАВЕРШЕНА УСПЕШНО!
📦 Component ID: your_component_name
🔢 Blockchain Component ID: 999
📄 Root Metadata CID: DRYRUN_...
```

---

### **Шаг 3: Проверка файла с маппингами**

После dry-run проверьте созданный файл состояния:

```bash
# Файл находится в директории вашего компонента
cat scripts/organic_components/your_component_name/_upload_state_localhost.json
```

**Структура state файла:**
```json
{
  "component_id": "your_component_name",
  "network": "localhost",
  "created_at": "2025-10-09T12:00:00.000Z",
  "updated_at": "2025-10-09T12:05:00.000Z",
  "steps_completed": [
    "simple_fields_uploaded",
    "complex_fields_uploaded",
    "shareable_data_uploaded",
    "root_metadata_uploaded",
    "component_registered"
  ],
  "simple_fields": {
    "title": {
      "cid": "DRYRUN_1728500000_abc123",
      "label": "ComponentDescription.title",
      "file_path": "simple_fields/your_component_name.ComponentDescription.title.json"
    },
    "dosage_types": {
      "cid": "DRYRUN_1728500001_def456",
      "label": "DosageInstruction.description",
      "file_path": "simple_fields/your_component_name.DosageInstruction.description.json"
    }
  },
  "complex_fields": {
    "ru": {
      "cid": "DRYRUN_1728500002_ghi789",
      "label": "ComponentDescription",
      "file_path": "complex_fields/your_component_name.ComponentDescription.ru.json"
    },
    "en": {
      "cid": "DRYRUN_1728500003_jkl012",
      "label": "ComponentDescription",
      "file_path": "complex_fields/your_component_name.ComponentDescription.en.json"
    }
    // ... остальные языки
  },
  "shareable_data": {
    "featuresCID": "DRYRUN_1728500010_mno345",
    "formsCID": "DRYRUN_1728500011_pqr678"
  },
  "root_metadata": {
    "path": "your_component_name_final_localhost.json",
    "cid": "DRYRUN_1728500012_stu901",
    "data": {
      // ... финальный root metadata с CID ссылками
    }
  },
  "contract_registration": {
    "componentId": 999,
    "txHash": "DRYRUN_TX_HASH",
    "dry_run": true
  }
}
```

**Этот файл:**
- 📝 Сохраняет все CID для каждого загруженного файла
- 🔄 Позволяет продолжить загрузку с любого шага
- ✅ Отслеживает выполненные шаги
- 🌐 Специфичен для каждой сети (localhost, polygon, etc.)

---

### **Шаг 4: Production загрузка в контракты**

После успешного dry-run можно загружать в production:

#### 4.1 Первая загрузка (с shareable data)

**Только для самого первого компонента в системе:**

```bash
# Загружаем глобальные словари (features.json, component_forms.json)
COMPONENT_ID=your_component_name UPLOAD_SHAREABLE=true \
npx hardhat run scripts/upload_organic_component.js --network polygon
```

#### 4.2 Обычная загрузка компонента

**Для всех последующих компонентов:**

```bash
# Загружаем только данные компонента
COMPONENT_ID=your_component_name \
npx hardhat run scripts/upload_organic_component.js --network polygon
```

**Процесс:**
1. **ШАГ 1:** Загрузка `ComponentDescription.title` и `DosageInstruction.description` в Arweave
2. **ШАГ 2:** Загрузка `ComponentDescription.{lang}` для 7 языков в Arweave
3. **ШАГ 3:** Загрузка глобальных словарей (если `UPLOAD_SHAREABLE=true`)
4. **ШАГ 4:** Создание финального root metadata с CID ссылками
5. **ШАГ 5:** Загрузка root metadata в Arweave
6. **ШАГ 6:** Регистрация в `OrganicComponentRegistry.createComponent()`

**После загрузки проверьте state файл:**
```bash
cat scripts/organic_components/your_component_name/_upload_state_polygon.json
```

Теперь вместо mock CID будут реальные Arweave TX IDs!

---

### **Шаг 5: Продолжение с середины процесса**

Если загрузка прервалась, скрипт автоматически продолжит с последнего шага:

```bash
# Просто запустите снова - state загрузится автоматически
COMPONENT_ID=your_component_name \
npx hardhat run scripts/upload_organic_component.js --network polygon
```

**Вывод:**
```
💾 Загрузка state...
✅ State загружен из _upload_state_polygon.json
📊 Выполнено шагов: 3

🔹 ШАГ 1: Загрузка Simple Fields
✅ Шаг уже выполнен, используем сохраненные данные

🔹 ШАГ 2: Загрузка Complex Fields
✅ Шаг уже выполнен, используем сохраненные данные

🔹 ШАГ 3: Загрузка глобальных словарей
✅ Шаг уже выполнен, используем сохраненные данные

🔹 ШАГ 4: Создание финального Root Metadata
📖 Чтение оригинального файла: your_component_name.json
...
```

---

### **Шаг 6: Проверка результатов**

#### 6.1 Проверка в Arweave

```bash
# Получите Root CID из вывода скрипта
# https://arweave.net/{root_cid}

# Пример
curl https://arweave.net/TX_ID_HERE
```

#### 6.2 Проверка в контрактах

**AmanitaInternational:**
```javascript
const titleCID = await amanitaInternational.methods.getSimpleFieldCID(
  "ComponentDescription.title"
).call();

const descRuCID = await amanitaInternational.methods.getComplexFieldCID(
  "ComponentDescription",
  "ru"
).call();

console.log("Title CID:", titleCID);
console.log("Description RU CID:", descRuCID);
```

**OrganicComponentRegistry:**
```javascript
const component = await organicComponentRegistry.methods.getComponent(
  componentId
).call();

console.log("Component:", component);
console.log("Root Metadata CID:", component.rootMetadataCID);
console.log("Status:", component.status);
```

---

### **📋 Checklist перед загрузкой**

**Подготовка файлов:**
- [ ] Корневой файл `{component_id}.json` создан и заполнен
- [ ] `biounit_id` уникален (проверьте в контракте)
- [ ] Все `forms` и `features` используют корректные ключи из глобальных словарей
- [ ] `simple_fields/` содержит 2 файла с переводами на 7 языков
- [ ] `complex_fields/` содержит 7 файлов (по одному на язык)
- [ ] Все JSON файлы валидны (проверьте через `jq` или онлайн валидатор)

**Конфигурация:**
- [ ] `.env` содержит `DEPLOYER_PRIVATE_KEY`
- [ ] `.env` содержит `AMANITA_INTERNATIONAL_PROXY_ADDRESS`
- [ ] `.env` содержит `ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS`
- [ ] `.env` содержит `ARWEAVE_PRIVATE_KEY`
- [ ] Deployer имеет роли `ADMIN_ROLE` в обоих контрактах
- [ ] Баланс достаточен для gas (~0.1 MATIC на Polygon)

**Тестирование:**
- [ ] Dry-run выполнен успешно (`DRY_RUN=true`)
- [ ] State файл создан и содержит корректные данные
- [ ] Финальный root metadata файл создан локально
- [ ] Нет ошибок валидации

**Production:**
- [ ] Первый компонент: `UPLOAD_SHAREABLE=true` установлен
- [ ] Последующие компоненты: `UPLOAD_SHAREABLE` не установлен
- [ ] Network указана правильно (--network polygon)

---

### **🚨 Troubleshooting**

**Проблема:** "Файл не найден"
```
❌ Ошибка: Файл не найден: scripts/organic_components/your_component_name/simple_fields/...
```
**Решение:** Проверьте правильность имени файла. Имя должно быть: `{component_id}.{ClassName}.{fieldName}.json`

---

**Проблема:** "Mock TX ID в production"
```
⚠️ В production обнаружены DRYRUN CID
```
**Решение:** Удалите state файл и запустите снова без `DRY_RUN=true`

---

**Проблема:** "Баланс равен 0"
```
⚠️ ВНИМАНИЕ: Баланс равен 0! Контрактные операции не выполнятся.
```
**Решение:** Пополните баланс deployer адреса (минимум 0.1 MATIC)

---

**Проблема:** "Компонент уже существует"
```
❌ Ошибка в ШАГ 6: Component with this businessId already exists
```
**Решение:** Используйте уникальный `biounit_id` или удалите существующий компонент

---

## 📦 Batch Upload: Загрузка всех компонентов

### **Когда использовать Batch Upload?**

Если у вас есть **несколько компонентов** (например, 11 готовых компонентов), используйте систему batch upload для автоматической загрузки всех компонентов за один запуск.

**Преимущества:**
- ✅ Автоматическая обработка всех компонентов из директории
- ✅ Детальный JSON отчет с метриками
- ✅ Resume capability (продолжение с любого компонента)
- ✅ Error isolation (один сбойный компонент не блокирует остальные)
- ✅ Progress tracking в реальном времени

---

### **🔄 Двухэтапный процесс загрузки**

Система разделена на 2 этапа для гибкости и безопасности:

```
ЭТАП 1: Arweave Upload         ЭТАП 2: Blockchain Upload
     (получение CID)               (регистрация в контрактах)
           ↓                                ↓
┌──────────────────────┐         ┌──────────────────────┐
│ upload_all_components│         │ upload_all_components│
│                      │         │                      │
│ • Все компоненты     │         │ • Используем CID     │
│ • Все языки          │         │ • Все контракты      │
│ • Глобальные словари │         │ • Все транзакции     │
│                      │         │                      │
│ Output:              │         │ Output:              │
│ _upload_report.json  │────────▶│ Blockchain IDs       │
│ (CID для всех файлов)│         │ (componentId)        │
└──────────────────────┘         └──────────────────────┘
```

**⚠️ Важно:** Этапы можно запускать **отдельно** или **вместе**. Для тестирования рекомендуется сначала только Arweave, затем контракты.

---

### **📋 Предварительные требования**

#### Arweave Баланс ⚠️

**Для загрузки в Arweave требуются AR токены** (оплата постоянного хранения данных):

- **Минимум требуется:** ~0.065 AR для 11 компонентов (110 файлов)
- **Рекомендуется:** 0.1-0.2 AR (с запасом на тестирование)
- **Стоимость 1 файла:** ~0.0006 AR (~280 bytes)

**Проверка баланса:**

```bash
# Быстрый тест Arweave подключения и баланса
node scripts/test_arweave_upload.js

# Ожидаемый результат:
# ✅ Arweave ключ загружен
# ✅ Адрес кошелька: ycF5nnTP0NSkb2MymMXxitbpUlbHNgIkC8IqrSzQaO8
# ✅ Баланс: 0.123 AR  <-- должно быть > 0
```

**Если баланс = 0:**

1. **Получить адрес для пополнения:**
   - Запустите `node scripts/test_arweave_upload.js`
   - Скопируйте адрес из вывода
   
2. **Пополнить баланс:**
   - Купить AR на бирже (Binance, KuCoin, etc.)
   - Использовать testnet faucet (только для тестирования)
   - Сайт Arweave: https://www.arweave.org/

3. **Проверить пополнение:**
   - Подождите ~2-5 минут после отправки
   - Запустите тест снова: `node scripts/test_arweave_upload.js`

**⚠️ ВАЖНО:** Без AR токенов загрузка вернет ошибку `400 Bad Request`

#### Ethereum/Polygon Контракты

- Контракты должны быть задеплоены на целевой сети
- Адреса контрактов прописаны в `.env` или `hardhat.config.js`
- Deployer account должен иметь достаточно ETH/MATIC для gas

---

### **Шаг 1: Подготовка всех компонентов**

#### 1.1 Проверка структуры директории

```bash
cd scripts/organic_components
ls -la

# Ожидаемая структура:
# amanita_muscaria/
# amanita_pantherina/
# blue_lotus/
# cantharellus_cibarius/
# cordyceps_militaris/
# inonotus_obliquus/
# lions_mane/
# mint/
# nettle/
# passionflower/
# populus_tremula/
```

#### 1.2 Валидация всех компонентов

Каждый компонент должен содержать:
- ✅ `{component_id}.json` - корневой файл
- ✅ `simple_fields/` - 2 файла (title, dosage)
- ✅ `complex_fields/` - 7 файлов (по языку)

**Быстрая проверка:**
```bash
# Проверка структуры всех компонентов
for dir in */; do
  echo "Проверка $dir"
  ls -1 "$dir" | grep -E "\.json$" | wc -l  # должно быть >= 1
  ls -1 "$dir/simple_fields/" | wc -l      # должно быть 2
  ls -1 "$dir/complex_fields/" | wc -l     # должно быть 7
done
```

---

### **Шаг 2: Dry-run тестирование всех компонентов**

Перед реальной загрузкой протестируйте всю систему в dry-run режиме:

```bash
cd /Users/eslinko/Development/Amanita

# Dry-run: Симуляция загрузки всех компонентов
DRY_RUN=true npx hardhat run scripts/upload_all_components.js --network localhost
```

**Что происходит:**
- ✅ Автоматическое обнаружение всех компонентов в `scripts/organic_components/`
- ✅ Проверка структуры файлов для каждого компонента
- ✅ Генерация mock Arweave TX IDs (DRYRUN_...)
- ✅ Симуляция всех 6 шагов для каждого компонента
- ✅ Создание batch state: `_batch_state_localhost.json`
- ✅ Создание report: `_upload_report_localhost_{timestamp}.json`

**Вывод в консоли:**
```
🔷 Batch Upload: Organic Components
📊 Network: LOCALHOST
🔷 Dry-run режим: ВСЕ транзакции симулируются

🔍 Обнаружено компонентов: 11
✅ Все компоненты валидны

🌍 Загрузка глобальных словарей (shareable data)
📤 Загрузка bot/catalog/features.json в Arweave...
🔷 [DRY-RUN] Mock TX ID: DRYRUN_1760005001000_abc123
✅ Глобальные словари загружены

======================================================================
📦 КОМПОНЕНТ 1/11: amanita_muscaria
======================================================================
🔹 ШАГ 1: Загрузка Simple Fields
📝 1.1. ComponentDescription.title
🔷 [DRY-RUN] Mock TX ID: DRYRUN_...
...

📊 Общий прогресс: 1/11 (9%)
======================================================================
📦 КОМПОНЕНТ 2/11: amanita_pantherina
======================================================================
...

✅ Все компоненты обработаны

======================================================================
📊 ИТОГОВАЯ СТАТИСТИКА
======================================================================
✅ Успешно: 11
❌ Ошибки: 0
⏭️ Пропущено: 0
📝 Всего: 11
======================================================================

✅ Финальный отчет сохранен: _upload_report_localhost_20251009T123456789Z.json
```

---

### **Шаг 3: Просмотр отчета**

После dry-run проверьте созданный отчет:

```bash
# Автоматический просмотр последнего отчета
node scripts/view_upload_report.js

# Детальный просмотр с информацией по каждому компоненту
node scripts/view_upload_report.js --details

# Экспорт отчета в новый файл
node scripts/view_upload_report.js --export my_test_report.json
```

**Формат отчета:**
```json
{
  "upload_session": {
    "session_id": "upload_2025-10-09T12-34-56-789Z",
    "network": "localhost",
    "started_at": "2025-10-09T12:34:56.789Z",
    "completed_at": "2025-10-09T12:35:07.789Z",
    "duration_seconds": 11,
    "deployer": "0x...",
    "dry_run": true,
    "upload_shareable": true
  },
  "global_dictionaries": {
    "uploaded": true,
    "features_cid": "DRYRUN_...",
    "forms_cid": "DRYRUN_...",
    "features_version": 1,
    "forms_version": 1
  },
  "components": [
    {
      "component_id": "amanita_muscaria",
      "status": "completed",
      "duration_seconds": 1,
      "arweave": {
        "files_uploaded": 10,
        "total_size_bytes": 12345,
        "simple_fields": {
          "ComponentDescription.title": "DRYRUN_...",
          "DosageInstruction.description": "DRYRUN_..."
        },
        "complex_fields": {
          "ru": "DRYRUN_...",
          "en": "DRYRUN_...",
          // ... остальные языки
        },
        "root_metadata_cid": "DRYRUN_..."
      },
      "blockchain": {
        "component_id": 999,
        "tx_hash": "DRYRUN_TX",
        "gas_used": 0,
        "cost_matic": "0"
      },
      "metadata": {
        "biounit_id": "amanita_muscaria",
        "scientific_title": "Amanita muscaria",
        "forms_count": 5,
        "features_count": 15
      },
      "validation": {
        "files_valid": true,
        "structure_valid": true,
        "translations_complete": true
      }
    }
    // ... остальные 10 компонентов
  ],
  "summary": {
    "total_components": 11,
    "successful": 11,
    "failed": 0,
    "skipped": 0,
    "total_files": 110,
    "total_arweave_size_bytes": 135690,
    "total_gas_used": 0,
    "total_cost_matic": "0",
    "average_component_duration": 1
  },
  "errors": []
}
```

**Этот отчет содержит ВСЕ CID для всех файлов всех компонентов!**

---

### **Шаг 4: Production загрузка в Arweave (без контрактов)**

После успешного dry-run можно загружать в реальный Arweave:

#### 4.1 Тестирование на localhost Hardhat

**Первый запуск: Arweave upload + localhost контракты**

```bash
# 1. Запустите локальную Hardhat сеть в отдельном терминале
npx hardhat node

# 2. В другом терминале: Deploy контрактов на localhost
npx hardhat run scripts/deploy_full.js --network localhost

# 3. Запустите batch upload на localhost
UPLOAD_SHAREABLE=true \
npx hardhat run scripts/upload_all_components.js --network localhost
```

**Что происходит:**
- ✅ Реальная загрузка в Arweave (используется ARWEAVE_PRIVATE_KEY из .env)
- ✅ Реальные Arweave TX IDs (ar://...)
- ✅ Реальные транзакции в localhost контракты
- ✅ Реальные blockchain component IDs (1, 2, 3, ...)
- ✅ Финальный отчет с реальными данными

**Время выполнения:** ~5-10 минут (зависит от размера данных и Arweave сети)

**Вывод:**
```
🌐 Network: LOCALHOST
🔑 Deployer: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
💰 Баланс: 10000 ETH

🌍 Загрузка глобальных словарей (shareable data)
📤 Загрузка bot/catalog/features.json в Arweave...
✅ Features загружены: ar://abc123def456...
📤 Загрузка bot/catalog/component_forms.json в Arweave...
✅ Forms загружены: ar://789ghi012jkl...
📝 Сохранение в OrganicComponentRegistry...
✅ Глобальные словари зарегистрированы

======================================================================
📦 КОМПОНЕНТ 1/11: amanita_muscaria
======================================================================

🔹 ШАГ 1: Загрузка Simple Fields
📤 Загрузка amanita_muscaria_ComponentDescription_title.json в Arweave...
✅ Загружено: ar://real_tx_id_1
📝 Сохранение в AmanitaInternational...
✅ TX: 0xabcdef...

🔹 ШАГ 2: Загрузка Complex Fields
📤 Загрузка amanita_muscaria_ComponentDescription_ru.json в Arweave...
✅ Загружено: ar://real_tx_id_2
...

🔹 ШАГ 5: Загрузка Root Metadata
📤 Загрузка root metadata в Arweave...
✅ Root Metadata CID: ar://real_tx_id_root

🔹 ШАГ 6: Регистрация в OrganicComponentRegistry
📝 createComponent("amanita_muscaria", "ar://real_tx_id_root")
✅ Компонент зарегистрирован! Component ID: 1
✅ TX Hash: 0x123456...

✅ Компонент amanita_muscaria загружен успешно!
   → Duration: 30s
   → Root CID: ar://real_tx_id_root
   → Blockchain ID: 1

📊 Общий прогресс: 1/11 (9%)
...

======================================================================
📊 ИТОГОВАЯ СТАТИСТИКА
======================================================================
✅ Успешно: 11
❌ Ошибки: 0
⏭️ Пропущено: 0
📝 Всего: 11
⏱️ Время: 5 минут 23 секунды
======================================================================

✅ Финальный отчет сохранен: _upload_report_localhost_20251009T150000Z.json
```

---

### **Шаг 5: Проверка результатов на localhost**

#### 5.1 Просмотр детального отчета

```bash
node scripts/view_upload_report.js --details
```

**Вывод:**
```
======================================================================
📊 UPLOAD REPORT SUMMARY
======================================================================

🎯 Session Info:
   → Session ID: upload_2025-10-09T15-00-00-000Z
   → Network: LOCALHOST
   → Started: 10/9/2025, 3:00:00 PM
   → Completed: 10/9/2025, 3:05:23 PM
   → Duration: 5m 23s
   → Dry Run: NO

📦 Components:
   → Total: 11
   → ✅ Successful: 11
   → ❌ Failed: 0

📊 Arweave Metrics:
   → Total Files: 110
   → Total Size: 132.4 KB

💰 Blockchain Costs:
   → Total Gas Used: 2,456,789
   → Total Cost: 0.0024 MATIC (~$0.002)

⏱️ Performance:
   → Average Component Duration: 29s

======================================================================
📋 ТАБЛИЦА КОМПОНЕНТОВ
======================================================================
№   Component ID             Status      Duration  Files   B-chain ID
----------------------------------------------------------------------
1   amanita_muscaria         ✅ OK        30s       10      1
2   amanita_pantherina       ✅ OK        28s       10      2
3   blue_lotus               ✅ OK        29s       10      3
4   cantharellus_cibarius    ✅ OK        31s       10      4
5   cordyceps_militaris      ✅ OK        27s       10      5
6   inonotus_obliquus        ✅ OK        30s       10      6
7   lions_mane               ✅ OK        29s       10      7
8   mint                     ✅ OK        28s       10      8
9   nettle                   ✅ OK        29s       10      9
10  passionflower            ✅ OK        30s       10      10
11  populus_tremula          ✅ OK        28s       10      11
======================================================================
```

#### 5.2 Проверка в Arweave

```bash
# Получите Root CID любого компонента из отчета
# Проверьте доступность через Arweave gateway:
curl https://arweave.net/ar://real_tx_id_root | jq
```

#### 5.3 Проверка в контрактах (localhost)

```bash
# Создайте скрипт для проверки
cat > scripts/check_components.js << 'EOF'
const hre = require("hardhat");

async function main() {
  const registry = await hre.ethers.getContractAt(
    "OrganicComponentRegistryLogicV1",
    process.env.ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS
  );

  console.log("\n🔍 Проверка загруженных компонентов:\n");

  for (let i = 1; i <= 11; i++) {
    const [component] = await registry.getComponent(i);
    console.log(`${i}. ${component.businessId}`);
    console.log(`   Status: ${component.status}`);
    console.log(`   Root CID: ${component.rootMetadataCID}`);
    console.log(`   Creator: ${component.creator}`);
    console.log("");
  }
}

main().catch(console.error);
EOF

# Запустите проверку
npx hardhat run scripts/check_components.js --network localhost
```

---

### **Шаг 6: Resume capability (продолжение с середины)**

Если процесс прервался, система автоматически продолжит с последнего успешного компонента:

```bash
# Просто запустите снова - state загрузится автоматически
UPLOAD_SHAREABLE=true \
npx hardhat run scripts/upload_all_components.js --network localhost
```

**Вывод:**
```
💾 Загрузка batch state...
✅ Batch state загружен из _batch_state_localhost.json
📊 Прогресс: 5/11 компонентов завершено

⏭️ Пропускаем уже завершенные компоненты:
   1. amanita_muscaria - ✅ completed
   2. amanita_pantherina - ✅ completed
   3. blue_lotus - ✅ completed
   4. cantharellus_cibarius - ✅ completed
   5. cordyceps_militaris - ✅ completed

======================================================================
📦 КОМПОНЕНТ 6/11: inonotus_obliquus
======================================================================
🔹 ШАГ 1: Загрузка Simple Fields
...
```

---

### **Шаг 7: Production deployment на Polygon**

После успешного тестирования на localhost можно загружать в Polygon mainnet:

#### 7.1 Проверка конфигурации

```bash
# Убедитесь, что в .env настроено:
grep -E "POLYGON_RPC_URL|DEPLOYER_PRIVATE_KEY|ARWEAVE_PRIVATE_KEY" .env

# Проверьте адреса контрактов на Polygon
grep -E "PROXY_ADDRESS" .env
```

#### 7.2 Проверка баланса

```bash
# Создайте скрипт для проверки баланса
cat > scripts/check_balance.js << 'EOF'
const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const balance = await hre.ethers.provider.getBalance(deployer.address);
  
  console.log(`\n💰 Deployer: ${deployer.address}`);
  console.log(`💰 Баланс: ${hre.ethers.formatEther(balance)} MATIC`);
  
  // Оценка стоимости для 11 компонентов
  const estimatedCost = 0.1; // ~0.1 MATIC для всех компонентов
  console.log(`\n📊 Оценка стоимости загрузки 11 компонентов:`);
  console.log(`   ~${estimatedCost} MATIC (+ запас)`);
  console.log(`\n${balance > estimatedCost * 1.5 ? "✅" : "❌"} Баланса ${balance > estimatedCost * 1.5 ? "достаточно" : "НЕ достаточно"}`);
}

main().catch(console.error);
EOF

npx hardhat run scripts/check_balance.js --network polygon
```

#### 7.3 Запуск production upload

```bash
# ВАЖНО: Первый раз с UPLOAD_SHAREABLE=true
UPLOAD_SHAREABLE=true \
npx hardhat run scripts/upload_all_components.js --network polygon

# Если загрузка прервалась - просто запустите снова
UPLOAD_SHAREABLE=true \
npx hardhat run scripts/upload_all_components.js --network polygon
```

**Время выполнения на Polygon:** ~30-40 минут для 11 компонентов

---

### **📊 Сравнение подходов**

| Параметр | Single Upload | Batch Upload |
|----------|---------------|--------------|
| **Скрипт** | `upload_organic_component.js` | `upload_all_components.js` |
| **Компонентов** | 1 | Все (автообнаружение) |
| **Время (11 комп.)** | ~5 мин × 11 = 55 мин | ~30-40 мин |
| **State файлы** | 1 per component | 1 batch + 1 per component |
| **Report** | Консоль | Детальный JSON |
| **Resume** | Per step | Per component |
| **Error handling** | Stops on error | Continues on error |
| **Use case** | Тестирование, обновление | Production массовая загрузка |

---

### **🚨 Troubleshooting Batch Upload**

**Проблема:** "No components found"
```
❌ Ошибка: Не найдено компонентов в scripts/organic_components/
```
**Решение:** Убедитесь, что директории компонентов находятся в `scripts/organic_components/` и содержат `.json` файл

---

**Проблема:** "Component X failed, continuing..."
```
❌ Ошибка обработки cordyceps_militaris: File not found
⚠️ Пропускаем cordyceps_militaris, продолжаем со следующим
```
**Решение:** Batch upload продолжит работу. Проверьте детали ошибки в report, исправьте компонент и запустите снова - failed компоненты будут обработаны повторно

---

**Проблема:** "Network timeout"
```
❌ Ошибка: Network timeout во время загрузки в Arweave
```
**Решение:** Просто запустите скрипт снова - resume capability загрузит state и продолжит с последнего успешного компонента

---

**Проблема:** "Insufficient balance"
```
⚠️ ВНИМАНИЕ: Баланс 0.05 MATIC может быть недостаточен
```
**Решение:** Пополните баланс deployer адреса (рекомендуется минимум 0.15 MATIC для 11 компонентов)

---

### **✅ Checklist для Batch Upload**

**Перед запуском:**
- [ ] Все 11 компонентов в `scripts/organic_components/` готовы
- [ ] Dry-run пройден успешно (11/11 OK)
- [ ] Report проверен (`view_upload_report.js`)
- [ ] `.env` настроен (ARWEAVE_PRIVATE_KEY, contract addresses)
- [ ] Deployer баланс >= 0.15 MATIC (для Polygon)
- [ ] Контракты задеплоены на целевой сети

**После localhost тестирования:**
- [ ] Все компоненты загружены (11/11)
- [ ] Report показывает 0 errors
- [ ] Все Arweave CID доступны
- [ ] Все blockchain IDs получены (1-11)
- [ ] Проверены несколько компонентов в контрактах

**Перед Polygon production:**
- [ ] Localhost тестирование завершено успешно
- [ ] Backup `.env` файла сделан
- [ ] Deployer адрес имеет ADMIN_ROLE в контрактах
- [ ] Баланс проверен и достаточен
- [ ] Готовы ждать ~30-40 минут

---

## 🎯 Обзор и архитектура

### **Что такое Organic Components?**

**Organic Components** - это система описания органических компонентов (грибы, растения, травы) в экосистеме Amanita с поддержкой:
- **Мультиязычности** (7 языков: ru, et, en, es, fr, de, nl)
- **Децентрализованного хранения** (Arweave через TX IDs как CID)
- **On-chain валидации** через смарт-контракт `OrganicComponentRegistry`
- **Глобальных словарей** для `forms` (формы продукта) и `features` (характеристики)
- **State Management** для возобновления загрузки с любого шага
- **Dry-run режима** для тестирования без реальных транзакций

### **Архитектурная схема**

```
┌────────────────────────────────────────────────────────────────┐
│                   СЛОЙ 1: Файловая структура                    │
│  scripts/organic_components/amanita_muscaria/                  │
│  ├─ amanita_muscaria.json          ← ОСНОВНОЙ ФАЙЛ             │
│  ├─ simple_fields/                 ← ПРОСТЫЕ ПОЛЯ (title, etc.)│
│  │  ├─ ComponentDescription.title.json                          │
│  │  └─ DosageInstruction.description.json                       │
│  └─ complex_fields/                ← СЛОЖНЫЕ ПОЛЯ (descriptions)│
│     ├─ ComponentDescription.ru.json                             │
│     ├─ ComponentDescription.en.json                             │
│     ├─ ComponentDescription.de.json                             │
│     └─ ... (7 языков)                                           │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────────┐
│                   СЛОЙ 2: Глобальные словари                    │
│  bot/catalog/                                                   │
│  ├─ features.json              ← 48 характеристик × 7 языков   │
│  └─ component_forms.json       ← 9 форм продукта × 7 языков    │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────────┐
│                   СЛОЙ 3: Arweave Storage                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. Upload simple_fields → TX_ID1 (title)                 │  │
│  │ 2. Upload simple_fields → TX_ID2 (dosage)                │  │
│  │ 3. Upload complex_fields → TX_ID3 (ru), TX_ID4 (en), ... │  │
│  │ 4. Upload features.json → TX_ID_FEATURES                  │  │
│  │ 5. Upload component_forms.json → TX_ID_FORMS             │  │
│  │ 6. State Management: _upload_state_{network}.json        │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────────┐
│              СЛОЙ 4: AmanitaInternational (UUPS Proxy)          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ setSimpleFieldCID("ComponentDescription.title", CID1)    │  │
│  │ setSimpleFieldCID("DosageInstruction.description", CID2) │  │
│  │ setComplexFieldCID("ComponentDescription", "ru", CID3)   │  │
│  │ setComplexFieldCID("ComponentDescription", "en", CID4)   │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────────┐
│         СЛОЙ 5: OrganicComponentRegistry (3-contract)           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ createComponent({                                         │  │
│  │   businessId: "amanita_muscaria",                         │  │
│  │   rootMetadata: {                                         │  │
│  │     scientific_name: "Amanita muscaria",                  │  │
│  │     forms: ["dried", "tincture", ...],                    │  │
│  │     features: { common: [...], forms: {...} },            │  │
│  │     localizations: {                                      │  │
│  │       simple_fields: { title: CID1, dosage: CID2 },       │  │
│  │       complex_fields: { ru: CID3, en: CID4, ... }         │  │
│  │     }                                                      │  │
│  │   }                                                       │  │
│  │ })                                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

---

## 📁 Структура файлов

### **Реальная структура директории**

```
scripts/organic_components/amanita_muscaria/
├── amanita_muscaria.json                    ← КОРНЕВОЙ ФАЙЛ
├── simple_fields/                           ← ПРОСТЫЕ ПОЛЯ (переводы)
│   ├── amanita_muscaria.ComponentDescription.title.json
│   └── amanita_muscaria.DosageInstruction.description.json
└── complex_fields/                          ← СЛОЖНЫЕ ПОЛЯ (описания)
    ├── amanita_muscaria.ComponentDescription.ru.json
    ├── amanita_muscaria.ComponentDescription.et.json
    ├── amanita_muscaria.ComponentDescription.en.json
    ├── amanita_muscaria.ComponentDescription.es.json
    ├── amanita_muscaria.ComponentDescription.fr.json
    ├── amanita_muscaria.ComponentDescription.de.json
    └── amanita_muscaria.ComponentDescription.nl.json
```

### **Файл: `amanita_muscaria.json` (КОРНЕВОЙ)**

**Назначение:** Основной файл с метаданными компонента, ссылками на CID и неизменяемыми данными.

**Структура:**

```json
{
  "biounit_id": "amanita_muscaria",
  "scientific_title": "Amanita muscaria",
  "created_at": "2024-01-15T00:00:00Z",
  "last_updated": "2024-01-15T00:00:00Z",
  "created_by": "0x1234567890abcdef1234567890abcdef12345678",
  
  "contributors": [
    {
      "address": "0x1234567890abcdef1234567890abcdef12345678",
      "role": "creator",
      "added_at": "2024-01-15T00:00:00Z"
    }
  ],
  
  "localizations": {
    "simple_fields": {
      "title": {
        "cid": "QmTitleCID123...",
        "label": "ComponentDescription.title"
      },
      "dosage_types": {
        "cid": "QmDosageTypesCID012...",
        "label": "DosageInstruction.description"
      }
    },
    "complex_fields": {
      "ru": {
        "cid": "QmComponentDescriptionRuCID345...",
        "label": "ComponentDescription"
      },
      "en": {
        "cid": "QmComponentDescriptionEnCID901...",
        "label": "ComponentDescription"
      }
      // ... остальные языки (et, es, fr, de, nl)
    }
  },
  
  "forms": [
    "dried",
    "tincture",
    "powder_extract",
    "oil_extract",
    "water_extract"
  ],
  
  "features": {
    "common": [
      "stress_relief",
      "tension_relief",
      "vitality_boost",
      "focus_enhancement",
      "presence_enhancement",
      "sleep_improvement",
      "sensitivity_restoration",
      "muscle_relaxation",
      "antioxidant_protection",
      "nervous_system_support",
      "intuition_enhancement",
      "consciousness_expansion",
      "spiritual_development",
      "meditation_practice",
      "emotional_balance"
    ],
    "forms": {
      "dried": [
        "long_term_effect",
        "gradual_reveal",
        "cumulative_effect",
        "microdosing",
        "personal_tuning"
      ],
      "tincture": [
        "fast_absorption",
        "precise_dosing",
        "external_application",
        "face_masks",
        "compresses",
        "with_camphor_oil",
        "body_therapy",
        "local_effect",
        "skin_absorption",
        "muscle_relaxation_therapy"
      ],
      "powder_extract": [
        "high_concentration",
        "fast_action",
        "precise_dosage",
        "convenience",
        "long_storage"
      ],
      "oil_extract": [
        "fat_soluble_compounds",
        "external_application",
        "skin_care",
        "penetrating_action",
        "moisturizing"
      ],
      "water_extract": [
        "water_soluble_compounds",
        "mild_effect",
        "fast_absorption_oral"
      ]
    }
  },
  
  "metadata": {
    "version": "1.0",
    "schema_version": "1.0",
    "status": "active",
    "validation": {
      "last_validated": "2024-01-15T00:00:00Z",
      "validator": "0x1234567890abcdef1234567890abcdef12345678",
      "checksum": "sha256:abc123...",
      "integrity": "verified"
    },
    "permissions": {
      "read": ["public"],
      "write": ["contributors"],
      "moderate": ["moderators"]
    }
  },
  
  "change_history": [
    {
      "timestamp": "2024-01-15T00:00:00Z",
      "address": "0x1234567890abcdef1234567890abcdef12345678",
      "action": "create",
      "changes": ["initial_creation"],
      "transaction_hash": "0xabcdef...",
      "block_number": 12345678
    }
  ],
  
  "moderation": {
    "status": "approved",
    "moderated_by": "0x1234567890abcdef1234567890abcdef12345678",
    "moderated_at": "2024-01-15T00:00:00Z",
    "moderation_reason": "initial_approval",
    "moderation_notes": "Component created and approved by system"
  },
  
  "sharing": {
    "is_shared": true,
    "shared_with": ["all_sellers"],
    "shared_at": "2024-01-15T00:00:00Z",
    "shared_by": "0x1234567890abcdef1234567890abcdef12345678",
    "license": "creative_commons",
    "attribution_required": true
  },
  
  "usage_stats": {
    "views": 0,
    "downloads": 0,
    "last_accessed": null,
    "popularity_score": 0
  }
}
```

---

### **Файл: `simple_fields/ComponentDescription.title.json`**

**Назначение:** Переводы названия компонента на 7 языков.

**Структура:**

```json
{
  "ru": "Мухомор красный",
  "et": "Punane kärbseseen",
  "en": "Red Fly Agaric",
  "es": "Amanita Muscaria",
  "fr": "Amanite Tue-mouches",
  "de": "Roter Fliegenpilz",
  "nl": "Vliegenzwam"
}
```

**Процесс:**
1. Загружается в IPFS → получаем `CID_TITLE`
2. Сохраняется в `AmanitaInternational`:
   ```solidity
   setSimpleFieldCID("ComponentDescription.title", CID_TITLE)
   ```

---

### **Файл: `simple_fields/DosageInstruction.description.json`**

**Назначение:** Инструкции по дозировке для каждой формы продукта на 7 языках.

**Структура:**

```json
{
  "dried": {
    "ru": "⚖️ Дозировка и настрой\nМухомор — это не препарат с универсальной нормой, а персональный союзник...",
    "et": "[Kuivatatud - Eesti tõlge tuleb]",
    "en": "[Dried - English translation needed]",
    "es": "[Seco - Traducción al español necesaria]",
    "fr": "[Séché - Traduction française nécessaire]",
    "de": "[Getrocknet - Deutsche Übersetzung erforderlich]",
    "nl": "[Gedroogd - Nederlandse vertaling nodig]"
  },
  "tincture": {
    "ru": "В зависимости от вида мухомора и его концентрации, дозировка может варьироваться от 1 до 5 мл...",
    "et": "[Tinktuur - Eesti tõlge tuleb]",
    "en": "[Tincture - English translation needed]",
    // ... остальные языки
  },
  "powder_extract": {
    "ru": "Экстракт в порошке. В зависимости от вида мухомора и его концентрации...",
    // ... остальные языки
  },
  "oil_extract": {
    "ru": "Экстракт в масле. В зависимости от вида мухомора и его концентрации...",
    // ... остальные языки
  },
  "water_extract": {
    "ru": "Экстракт в воде. В зависимости от вида мухомора и его концентрации...",
    // ... остальные языки
  }
}
```

**Процесс:**
1. Загружается в IPFS → получаем `CID_DOSAGE`
2. Сохраняется в `AmanitaInternational`:
   ```solidity
   setSimpleFieldCID("DosageInstruction.description", CID_DOSAGE)
   ```

---

### **Файл: `complex_fields/ComponentDescription.ru.json`**

**Назначение:** Полное описание компонента на русском языке.

**Структура:**

```json
{
  "generic_description": "🔬 Активные компоненты:\n🔹Мусцимол — седатив, диссоциатив, открывает доступ к \"второму телу\"...",
  "effects": "🌿 Целительное действие:\n🔹Нейромодуляция: балансирует возбуждение и торможение...",
  "shamanic": "🌀 Шаманская перспектива:\nМухомор не \"даёт приход\" — он отключает автоматизм...",
  "warnings": "⚠️ Предостережения:\n🔹Нельзя употреблять в сыром виде — иботеновая кислота активна..."
}
```

**Процесс:**
1. Загружается в IPFS → получаем `CID_RU`
2. Сохраняется в `AmanitaInternational`:
   ```solidity
   setComplexFieldCID("ComponentDescription", "ru", CID_RU)
   ```

**Аналогично для всех 7 языков:** ru, et, en, es, fr, de, nl

---

## 📊 Типы данных

### **1. Неизменяемые данные (Non-Localizable)**

**Хранятся в корневом `amanita_muscaria.json`:**

```typescript
interface NonLocalizableData {
  biounit_id: string;              // "amanita_muscaria"
  scientific_title: string;        // "Amanita muscaria"
  created_at: string;              // ISO 8601 timestamp
  last_updated: string;            // ISO 8601 timestamp
  created_by: string;              // Ethereum address
  contributors: Contributor[];
  
  // КРИТИЧНО: Ссылки на форму (indices из component_forms.json)
  forms: string[];                 // ["dried", "tincture", ...]
  
  // КРИТИЧНО: Характеристики (indices из features.json)
  features: {
    common: string[];              // Общие для всех форм
    forms: {
      [formKey: string]: string[]; // Специфичные для каждой формы
    };
  };
  
  // Метаданные
  metadata: ComponentMetadata;
  change_history: ChangeRecord[];
  moderation: ModerationInfo;
  sharing: SharingInfo;
  usage_stats: UsageStats;
}
```

**Важно:**
- `forms` и `features` - это **индексы** из глобальных словарей
- Сами переводы хранятся в `bot/catalog/features.json` и `bot/catalog/component_forms.json`
- В контракте хранятся только индексы, переводы берутся динамически

---

### **2. Локализуемые данные (Localizable)**

#### **2.1 Simple Fields - Простые поля (мультиязычные строки)**

```typescript
interface SimpleFieldData {
  [language: string]: string;
}

// Пример: ComponentDescription.title
{
  "ru": "Мухомор красный",
  "en": "Red Fly Agaric",
  "de": "Roter Fliegenpilz"
  // ... остальные языки
}
```

**Процесс хранения:**
1. Файл → IPFS → CID
2. CID → `AmanitaInternational.setSimpleFieldCID(label, cid)`
3. Ссылка на CID в корневом файле: `localizations.simple_fields[field].cid`

---

#### **2.2 Complex Fields - Сложные поля (мультиязычные объекты)**

```typescript
interface ComplexFieldData {
  generic_description: string;
  effects: string;
  shamanic: string;
  warnings: string;
}

// Пример: ComponentDescription.ru
{
  "generic_description": "🔬 Активные компоненты...",
  "effects": "🌿 Целительное действие...",
  "shamanic": "🌀 Шаманская перспектива...",
  "warnings": "⚠️ Предостережения..."
}
```

**Процесс хранения:**
1. Файл (для каждого языка) → IPFS → CID_RU, CID_EN, ...
2. Каждый CID → `AmanitaInternational.setComplexFieldCID(className, lang, cid)`
3. Ссылка на CID в корневом файле: `localizations.complex_fields[lang].cid`

---

### **3. Глобальные словари**

#### **3.1 Features Dictionary (`bot/catalog/features.json`)**

```json
{
  "features": {
    "stress_relief": {
      "ru": "снятие стресса",
      "et": "stressi vähendamine",
      "en": "stress relief",
      "es": "alivio del estrés",
      "fr": "soulagement du stress",
      "de": "Stressabbau",
      "nl": "stressverlichting"
    },
    "tension_relief": {
      "ru": "снятие напряжения",
      "et": "pinge vähendamine",
      "en": "tension relief"
      // ... остальные языки
    }
    // ... всего 48 характеристик
  }
}
```

**Использование:**
- В `amanita_muscaria.json` хранятся только **ключи**: `"stress_relief"`, `"tension_relief"`
- Переводы берутся динамически из глобального словаря по текущему языку пользователя

---

#### **3.2 Component Forms Dictionary (`bot/catalog/component_forms.json`)**

```json
{
  "forms": {
    "dried": {
      "ru": "Сушёный",
      "et": "Kuivatatud",
      "en": "Dried",
      "es": "Seco",
      "fr": "Séché",
      "de": "Getrocknet",
      "nl": "Gedroogd"
    },
    "tincture": {
      "ru": "Настойка",
      "et": "Tinktuur",
      "en": "Tincture"
      // ... остальные языки
    }
    // ... всего 9 форм
  }
}
```

**Использование:**
- В `amanita_muscaria.json` хранятся только **ключи**: `"dried"`, `"tincture"`
- Переводы берутся динамически из глобального словаря по текущему языку пользователя

---

## 🔗 Интеграция с контрактами

### **Контракт: AmanitaInternational (UUPS Proxy)**

**Назначение:** Хранение маппингов между лейблами полей и IPFS CID для локализованных данных.

**Функции:**

```solidity
// Простые поля (мультиязычные строки)
function setSimpleFieldCID(string calldata fieldKey, string calldata cid) 
    external 
    onlyRole(ADMIN_ROLE) 
    whenNotPaused;

function getSimpleFieldCID(string calldata fieldKey) 
    external 
    view 
    returns (string memory);

// Сложные поля (мультиязычные объекты)
function setComplexFieldCID(
    string calldata className, 
    string calldata language, 
    string calldata cid
) external onlyRole(ADMIN_ROLE) whenNotPaused;

function getComplexFieldCID(
    string calldata className, 
    string calldata language
) external view returns (string memory);
```

**Пример использования:**

```javascript
// 1. Загрузка simple field (title)
const titleCID = await uploadToIPFS(titleData); // "QmTitle123..."
await amanitaInternational.setSimpleFieldCID(
  "ComponentDescription.title",
  titleCID
);

// 2. Загрузка complex field (русское описание)
const descRuCID = await uploadToIPFS(descRuData); // "QmDescRu456..."
await amanitaInternational.setComplexFieldCID(
  "ComponentDescription",
  "ru",
  descRuCID
);

// 3. Чтение данных
const titleCID = await amanitaInternational.getSimpleFieldCID(
  "ComponentDescription.title"
);
const descRuCID = await amanitaInternational.getComplexFieldCID(
  "ComponentDescription",
  "ru"
);
```

---

### **Контракт: OrganicComponentRegistry (3-contract: Proxy + Logic + Storage)**

**Назначение:** Регистрация и управление органическими компонентами с валидацией.

**Функции:**

```solidity
function createComponent(
    string memory businessId,
    string memory rootMetadataCID
) external onlyActivatedUser returns (uint256);

function getComponent(uint256 componentId) 
    external 
    view 
    returns (
        Component memory component,
        ComponentUpdate[] memory updates,
        ComponentValidator[] memory validators
    );
```

**Пример использования:**

```javascript
// 1. Подготовка rootMetadata
const rootMetadata = {
  scientific_name: "Amanita muscaria",
  forms: ["dried", "tincture", "powder_extract", "oil_extract", "water_extract"],
  features: {
    common: ["stress_relief", "tension_relief", "vitality_boost", ...],
    forms: {
      dried: ["long_term_effect", "gradual_reveal", ...],
      tincture: ["fast_absorption", "precise_dosing", ...],
      // ... остальные формы
    }
  },
  localizations: {
    simple_fields: {
      title: { cid: "QmTitle123...", label: "ComponentDescription.title" },
      dosage_types: { cid: "QmDosage456...", label: "DosageInstruction.description" }
    },
    complex_fields: {
      ru: { cid: "QmDescRu789...", label: "ComponentDescription" },
      en: { cid: "QmDescEn012...", label: "ComponentDescription" },
      // ... остальные языки
    }
  },
  metadata: { version: "1.0", schema_version: "1.0", status: "active" },
  // ... остальные метаданные
};

// 2. Загрузка rootMetadata в IPFS
const rootMetadataCID = await uploadToIPFS(rootMetadata); // "QmRoot345..."

// 3. Создание компонента в контракте
const tx = await organicComponentRegistry.createComponent(
  "amanita_muscaria",
  rootMetadataCID
);

// 4. Получение componentId из события
const receipt = await tx.wait();
const event = receipt.logs.find(log => {
  const parsed = organicComponentRegistry.interface.parseLog(log);
  return parsed.name === "ComponentCreated";
});
const componentId = event.args.componentId;

console.log(`Component created with ID: ${componentId}`);
console.log(`Root Metadata CID: ${rootMetadataCID}`);
```

---

## 📤 Процесс загрузки в Arweave

### **Последовательность действий**

**⚠️ Важно:** Все действия выполняются автоматически скриптом `upload_organic_component.js` с поддержкой:
- ✅ State Management (продолжение с любого шага)
- ✅ Dry-run режим (тестирование без реальных транзакций)
- ✅ Automatic retry при ошибках сети

```
┌─────────────────────────────────────────────────────────────┐
│ ШАГ 1: Загрузка Simple Fields                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 1.1. Проверка isStepCompleted('simple_fields_uploaded')│ │
│ │ 1.2. Читаем ComponentDescription.title.json             │ │
│ │ 1.3. Загружаем в Arweave → TX_ID_TITLE                  │ │
│ │ 1.4. Сохраняем в AmanitaInternational:                  │ │
│ │      setSimpleFieldCID("ComponentDescription.title",    │ │
│ │                        TX_ID_TITLE)                      │ │
│ │ 1.5. Читаем DosageInstruction.description.json          │ │
│ │ 1.6. Загружаем в Arweave → TX_ID_DOSAGE                 │ │
│ │ 1.7. Сохраняем в AmanitaInternational:                  │ │
│ │      setSimpleFieldCID("DosageInstruction.description", │ │
│ │                        TX_ID_DOSAGE)                     │ │
│ │ 1.8. markStepCompleted + saveState                      │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ ШАГ 2: Загрузка Complex Fields                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 2.1. Проверка isStepCompleted('complex_fields_uploaded')│ │
│ │ 2.2. Для каждого языка (ru, et, en, es, fr, de, nl):   │ │
│ │      - Читаем ComponentDescription.{lang}.json          │ │
│ │      - Загружаем в Arweave → TX_ID_{LANG}               │ │
│ │      - Сохраняем в AmanitaInternational:                │ │
│ │        setComplexFieldCID("ComponentDescription",       │ │
│ │                           lang, TX_ID_{LANG})           │ │
│ │ 2.3. markStepCompleted + saveState                      │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ ШАГ 3: Загрузка глобальных словарей (опционально!)         │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 3.1. Проверка isStepCompleted('shareable_data_uploaded')│ │
│ │ 3.2. Если UPLOAD_SHAREABLE !== true → пропустить шаг   │ │
│ │ 3.3. Читаем bot/catalog/features.json                   │ │
│ │ 3.4. Загружаем в Arweave → TX_ID_FEATURES               │ │
│ │ 3.5. Читаем bot/catalog/component_forms.json            │ │
│ │ 3.6. Загружаем в Arweave → TX_ID_FORMS                  │ │
│ │ 3.7. Сохраняем в OrganicComponentRegistry:              │ │
│ │      updateShareableData(TX_ID_FEATURES, TX_ID_FORMS, ...)│ │
│ │ 3.8. markStepCompleted + saveState                      │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ ШАГ 4: Обновление корневого файла с TX IDs                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 4.1. Читаем {component_id}.json                         │ │
│ │ 4.2. Обновляем localizations.simple_fields:             │ │
│ │      { title: { cid: TX_ID_TITLE, label: "...", ... },  │ │
│ │        dosage: { cid: TX_ID_DOSAGE, label: "...", ... }}│ │
│ │ 4.3. Обновляем localizations.complex_fields:            │ │
│ │      { ru: { cid: TX_ID_RU, label: "..." },             │ │
│ │        en: { cid: TX_ID_EN, label: "..." }, ... }       │ │
│ │ 4.4. Добавляем timestamp + network                      │ │
│ │ 4.5. Сохраняем {component_id}_final_{network}.json      │ │
│ │ 4.6. saveState (без markStepCompleted)                  │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ ШАГ 5: Загрузка Root Metadata в Arweave                    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 5.1. Проверка isStepCompleted('root_metadata_uploaded')│ │
│ │ 5.2. Загружаем финальный JSON в Arweave → TX_ID_ROOT   │ │
│ │ 5.3. markStepCompleted + saveState                      │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ ШАГ 6: Регистрация в OrganicComponentRegistry              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 6.1. Проверка isStepCompleted('component_registered')  │ │
│ │ 6.2. Вызываем createComponent(component_id, TX_ID_ROOT)│ │
│ │ 6.3. Получаем componentId из события ComponentCreated   │ │
│ │ 6.4. Сохраняем txHash + componentId в state             │ │
│ │ 6.5. markStepCompleted + saveState                      │ │
│ │ 6.6. Логируем успех с Arweave gateway link             │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Время выполнения:** ~5-10 минут (зависит от размера данных и сети)

---

## 🛠️ Скрипт загрузки

### **Файл: `scripts/upload_organic_component.js`**

**Версия:** 1.0.0 (Production Ready)  
**Технологии:** Web3.js + Arweave SDK + Hardhat  
**Особенности:**
- ✅ State Management система
- ✅ Dry-run режим для тестирования
- ✅ Автоматическое возобновление с любого шага
- ✅ Поддержка 7 языков
- ✅ Газ-оптимизированные транзакции
- ✅ Детальное логирование

### **Использование:**

```bash
# 1. Dry-run (тестирование без реальных транзакций)
DRY_RUN=true COMPONENT_ID=amanita_muscaria \
npx hardhat run scripts/upload_organic_component.js --network localhost

# 2. Production (первый компонент с shareable data)
COMPONENT_ID=amanita_muscaria UPLOAD_SHAREABLE=true \
npx hardhat run scripts/upload_organic_component.js --network polygon

# 3. Production (обычный компонент)
COMPONENT_ID=amanita_muscaria \
npx hardhat run scripts/upload_organic_component.js --network polygon
```

### **Структура скрипта:**

**📂 Основные компоненты:**

1. **Infrastructure Setup (строки 1-110)**
   - Web3.js инициализация
   - Arweave SDK инициализация  
   - Network configuration
   - Contract addresses загрузка

2. **Utility Functions (строки 111-369)**
   - `loadContractArtifact()` - загрузка ABI
   - `loadUUPSContract()` - подключение к UUPS контрактам
   - `readJSON()` / `saveJSON()` - работа с файлами
   - `getGasPrice()` / `getGasLimit()` - gas оптимизация
   - `uploadToArweave()` - загрузка в Arweave

3. **State Management (строки 203-369)**
   - `loadState()` - загрузка прогресса
   - `saveState()` - сохранение прогресса
   - `isStepCompleted()` - проверка выполнения шага
   - `markStepCompleted()` - отметка шага как выполненного

4. **Upload Steps (строки 370-842)**
   - Step 1: `uploadSimpleFields()` - title + dosage
   - Step 2: `uploadComplexFields()` - 7 языковых версий
   - Step 3: `uploadShareableData()` - глобальные словари
   - Step 4: `updateRootMetadata()` - финальный JSON
   - Step 5: `uploadRootMetadata()` - загрузка в Arweave
   - Step 6: `registerComponent()` - регистрация в контракте

5. **Main Function (строки 851-934)**
   - Orchestration всех шагов
   - Error handling
   - Финальный отчет

**📄 Детали реализации:** См. `scripts/upload_organic_component.js` (947 строк, production-ready)

**📖 Подробная документация:** См. `scripts/docs/AIJournal.md`

---

## 🚀 Примеры использования

### **Пример 1: Базовая загрузка компонента**

```bash
# 1. Установка переменных окружения
export COMPONENT_ID=amanita_muscaria
export UPLOAD_SHAREABLE=false

# 2. Запуск скрипта (testnet)
npx hardhat run scripts/upload_organic_component.js --network mumbai

# 3. Запуск скрипта (mainnet)
npx hardhat run scripts/upload_organic_component.js --network polygon
```

**Результат:**
```
🚀 Начало загрузки органического компонента
📦 Component ID: amanita_muscaria
📁 Component Directory: /scripts/organic_components/amanita_muscaria
👤 Signer: 0x1234...
✅ AmanitaInternational подключен: 0xAAAA...
✅ OrganicComponentRegistry подключен: 0xBBBB...

🔹 ШАГ 1: Загрузка Simple Fields
📤 Загрузка amanita_muscaria_ComponentDescription_title.json в IPFS...
✅ amanita_muscaria_ComponentDescription_title.json загружен: QmTitle123...
✅ Сохранено в AmanitaInternational: ComponentDescription.title
...

============================================================
🎉 ЗАГРУЗКА ЗАВЕРШЕНА УСПЕШНО!
============================================================
📦 Component ID: amanita_muscaria
🔢 Blockchain Component ID: 1
📄 Root Metadata CID: QmRoot345...
🔗 IPFS Gateway: https://ipfs.io/ipfs/QmRoot345...
============================================================
```

---

### **Пример 2: Первая загрузка с глобальными словарями**

```bash
# Загрузка глобальных словарей (только первый раз!)
export UPLOAD_SHAREABLE=true
npx hardhat run scripts/upload_organic_component.js --network polygon
```

---

### **Пример 3: Загрузка нового компонента**

```bash
# 1. Создать директорию для нового компонента
mkdir scripts/organic_components/amanita_pantherina

# 2. Скопировать структуру из amanita_muscaria
cp -r scripts/organic_components/amanita_muscaria/* \
      scripts/organic_components/amanita_pantherina/

# 3. Отредактировать JSON файлы

# 4. Загрузить
export COMPONENT_ID=amanita_pantherina
npx hardhat run scripts/upload_organic_component.js --network polygon
```

---

## 📊 Проверка результатов

### **1. Проверка CID в AmanitaInternational**

```javascript
const amanitaInternational = await ethers.getContractAt(
    "AmanitaInternationalLogic",
    PROXY_ADDRESS
);

// Simple Field
const titleCID = await amanitaInternational.getSimpleFieldCID(
    "ComponentDescription.title"
);
console.log(`Title CID: ${titleCID}`);

// Complex Field
const descRuCID = await amanitaInternational.getComplexFieldCID(
    "ComponentDescription",
    "ru"
);
console.log(`Description (RU) CID: ${descRuCID}`);
```

---

### **2. Проверка компонента в OrganicComponentRegistry**

```javascript
const organicComponentRegistry = await ethers.getContractAt(
    "OrganicComponentRegistryLogicV1",
    PROXY_ADDRESS
);

// Получение компонента по ID
const component = await organicComponentRegistry.getComponent(1);
console.log(`Component:`, component);

// Получение по business_id
const componentByBusinessId = await organicComponentRegistry.getComponentByBusinessId(
    "amanita_muscaria"
);
console.log(`Component by business_id:`, componentByBusinessId);

// Проверка статуса
const status = await organicComponentRegistry.getComponentStatus(1);
console.log(`Status:`, status); // "active"
```

---

### **3. Проверка данных в IPFS**

```bash
# Через IPFS gateway
curl https://ipfs.io/ipfs/QmRoot345...

# Или через Pinata gateway
curl https://gateway.pinata.cloud/ipfs/QmRoot345...
```

---

## ✅ Checklist перед загрузкой

### **Подготовка данных:**
- [ ] Все JSON файлы валидны (проверить через `jq`)
- [ ] Все переводы заполнены (минимум ru, en)
- [ ] `forms` и `features` используют корректные индексы из глобальных словарей
- [ ] `biounit_id` уникален в системе

### **Конфигурация:**
- [ ] `.env` содержит адреса контрактов
- [ ] IPFS/Arweave credentials настроены
- [ ] Deployer имеет роли ADMIN_ROLE в обоих контрактах
- [ ] Баланс достаточен для gas (~0.05 MATIC)

### **После загрузки:**
- [ ] Все CID сохранены в корневом файле
- [ ] Компонент создан в OrganicComponentRegistry
- [ ] Данные доступны через IPFS gateway
- [ ] Root Metadata CID добавлен в документацию

---

## 🎯 Заключение

**Organic Components** - это полноценная система для децентрализованного хранения и управления данными о органических компонентах с:
- ✅ **Мультиязычной поддержкой** (7 языков)
- ✅ **Arweave хранением** через TX IDs
- ✅ **On-chain валидацией** через смарт-контракты
- ✅ **Глобальными словарями** для переиспользования данных
- ✅ **State Management** для резюме загрузки
- ✅ **Dry-run режимом** для безопасного тестирования
- ✅ **Версионированием** и историей изменений

**Скрипт загрузки** автоматизирует весь процесс от загрузки в Arweave до регистрации в контрактах!

**📚 Документация:**
- Реализация: `scripts/upload_organic_component.js` (947 строк)
- Детальный журнал: `scripts/docs/AIJournal.md` (1000+ строк)
- Quick Start Guide: см. начало этого документа

---

**Версия документа:** 2.0.0  
**Последнее обновление:** 2025-10-09  
**Статус:** ✅ Production Ready (Arweave + State Management)  
**Совместимость:** Web3.js + Arweave SDK + Hardhat

