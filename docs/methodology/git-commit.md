# Группировка изменений и создание коммитов (методика)

**Методология анализа:** Используйте `@.cursor/commands/run-analysis.md` (и мышление analysis) — только факты из кода, без предположений.

**Процесс и план на согласование:** Полная методика работы с коммитами (план коммита на согласование с оператором, push только по разрешению) — в **docs/methodology/git-commit-prompt.md**. Этот документ задаёт алгоритм группировки, фильтрации и формата сообщений; обязательный шаг «план коммита на согласование» и ограничения по push описаны в git-commit-prompt.md.

## Назначение
Этот документ содержит алгоритм для анализа изменений в коде, группировки их по функциональным категориям и создания структурированных коммитов с английскими сообщениями.

**Применение:** Используйте вместе с **docs/methodology/git-commit-prompt.md** при завершении тасков (контракты, тесты, документация); перед выполнением коммитов — план на согласование оператору.

---

## Алгоритм работы

### Шаг 1: Анализ измененных файлов

**Команды:**
```bash
# Проверить текущую ветку
git branch --show-current

# Получить список всех измененных файлов (исключая служебные)
git diff --name-only --diff-filter=ACDMRT <target_directory>/ 2>/dev/null | \
  sort

# Получить статистику изменений
git diff --stat <target_directory>/
```

**Примечание:** Конкретные фильтры для исключения файлов применяются на шаге 2 (Фильтрация файлов).

**Что делать:**
1. Замените `<target_directory>` на нужную директорию (например, `bot`, `wp_plugin`, и т.д.)
2. Изучите список измененных файлов
3. Исключите служебные файлы из анализа (см. фильтр ниже)

---

### Шаг 2: Фильтрация файлов (что НЕ коммитить)

**Логические категории файлов, которые НЕ должны попадать в коммиты:**

#### 1. Сгенерированные/компилированные файлы
**Логика:** Автоматически генерируемые файлы, которые могут быть воссозданы из исходников.

**Примеры:**
- **Python:** `__pycache__/`, `*.pyc`, `*.pyo`, `*.py[cod]`, `*$py.class`
- **JavaScript/TypeScript:** `node_modules/`, `dist/`, `build/`, `*.js.map`, `.next/`, `.nuxt/`
- **Java:** `target/`, `*.class`, `*.jar` (кроме исходных), `*.war`
- **C/C++:** `*.o`, `*.obj`, `*.exe`, `*.dll`, `*.so`, `*.dylib`
- **Go:** `*.exe`, `*.test`, `*.out`
- **Rust:** `target/`, `Cargo.lock` (зависит от проекта)
- **Solidity:** `artifacts/`, `cache/`, `typechain/`, `typechain-types/`
- **Общие build артефакты:** `coverage/`, `.nyc_output/`, `*.egg-info/`

#### 2. Временные файлы и документы
**Логика:** Файлы, созданные для временного использования, черновики, промежуточные результаты.

**Паттерны:**
- `temp-*` - любые файлы/директории, начинающиеся с `temp-`
- `**/temp-*` - во всех поддиректориях
- `*.tmp`, `*.temp.*` - временные файлы с расширениями
- `*.bak`, `*.backup` - резервные копии
- `*.swp`, `*.swo`, `*~` - файлы редакторов (Vim, Emacs)
- `*.orig` - файлы конфликтов слияния

**Документы:**
- `**/AIJournal.md`, `**/Bridge.md`, `**/bridge-prompt.md` - временные рабочие документы
- Файлы с префиксом `temp-` в названии документации

#### 3. Логи и результаты выполнения
**Логика:** Файлы с результатами выполнения программ, логирование, отчеты о тестах.

**Паттерны:**
- `*.log` - любые логи
- `logs/`, `**/logs/` - директории с логами
- `test_results.log`, `test_output.*` - результаты тестов
- `*.log.*` - ротированные логи

#### 4. Приватные данные и секреты
**Логика:** Файлы, содержащие конфиденциальную информацию, ключи, токены, персональные данные.

**Паттерны:**
- `.env`, `.env.*`, `*.env` (кроме `.env.example`, `.env.template`)
- `*.key`, `*.pem`, `*_key.json`, `*_wallet.json` - приватные ключи
- `api_keys.json`, `secrets.json` - файлы с ключами API
- `*_invites*.txt`, `*_invites*.json` - сгенерированные инвайты с приватными данными
- `SECURITY_INCIDENT_*` - файлы инцидентов безопасности
- `sensitive-files.txt` - списки чувствительных файлов

#### 5. Тестовые данные и фикстуры с реальными данными
**Логика:** Файлы с тестовыми данными, которые содержат реальные или чувствительные данные, или слишком большие для git.

**Паттерны:**
- `fixtures/temp/` - временные тестовые фикстуры
- `test_data/`, `test_data_*/` - директории с тестовыми данными
- Большие файлы с реальными данными (>1MB обычно)
- `*.csv`, `*.json` в test directories, если содержат приватные данные

#### 6. Кэш и промежуточные данные
**Логика:** Файлы кэша, которые могут быть пересозданы.

**Паттерны:**
- `.cache/`, `cache/`, `**/cache/`
- `*.cache`, `*.cache.*`
- `pinata_cache.json`, `.cleanup_timestamp` - специфичные кэши

#### 7. Системные и IDE файлы
**Логика:** Файлы, созданные операционной системой или IDE, не относящиеся к коду проекта.

**Паттерны:**
- `.DS_Store` (macOS), `Thumbs.db` (Windows)
- `.vscode/`, `.idea/`, `.vs/` - настройки IDE (если не нужны для команды)
- `.cursor/` (может быть исключен в некоторых проектах)

#### 8. Зависимости и vendor директории
**Логика:** Внешние зависимости, которые управляются пакетными менеджерами.

**Паттерны:**
- `node_modules/`, `vendor/`, `venv/`, `env/`, `.venv/`
- `bower_components/`, `jspm_packages/`

#### 9. Данные и каталоги (проект-специфичные)
**Логика:** Директории с данными, которые не являются частью исходного кода.

**Примеры для этого проекта:**
- `data/`, `bot/catalog`, `bot/catalog_data/`
- `scripts/organic_components/`, `metrics/`
- `bot/flowers/` - служебные директории с данными

---

**Правило для новых файлов (untracked):**
- ✅ **МОЖНО коммитить:** Новые файлы, которые являются частью задачи и функционально связаны с другими измененными файлами
- ✅ **МОЖНО коммитить:** Новые файлы, чей функциональный смысл понятен из контекста изменений
- ❌ **НЕ коммитить:** Новые файлы, которые являются временными, логи, сгенерированные данные
- ❌ **НЕ коммитить:** Новые файлы, чье назначение неясно или они не связаны с текущими изменениями

**Рекомендация:** Если сомневаетесь, включите новый файл в группу документации или создайте отдельный коммит после уточнения.

---

### Шаг 3: Группировка файлов по функциональным категориям

**Принципы группировки:**
1. **Логическое объединение** - файлы, решающие одну задачу/фичу
2. **Зависимости** - файлы, которые должны быть вместе для работоспособности
3. **Разделение по слоям** - код, тесты, конфигурация, документация

**Типичные группы:**
1. **Core Feature / Main Implementation** - основная реализация фичи
2. **Models and Services** - модели данных и сервисы
3. **Localization / i18n** - локализация и многоязычность
4. **Unit Tests** - unit тесты
5. **Integration / E2E Tests** - интеграционные и E2E тесты
6. **Configuration** - конфигурационные файлы, conftest, валидаторы
7. **Documentation** - документация, cleanup файлов

**Алгоритм группировки:**
1. Определить основную функциональность изменений
2. Сгруппировать файлы по роли (независимо от языка программирования):
   - Runtime код (сервисы, модели, handlers, контроллеры, компоненты)
   - Тесты (unit, integration, e2e)
   - Конфигурация (config files, test setup files, validators)
   - Документация
3. Проверить зависимости между группами (какие группы должны идти в каком порядке)
4. Для новых файлов: убедиться что они контекстно связаны с другими файлами в группе и их функциональный смысл понятен

---

### Шаг 4: Создание описания изменений (опционально, для валидации)

**Структура описания:**
```markdown
# Описание изменений: <Краткое описание>

## Дата изменений
YYYY-MM-DD

## Общая статистика
- **Изменено файлов:** N файлов
- **Основные изменения:** ~X добавлений, ~Y удалений
- **Группы изменений:** N функциональных групп

---

## Группа 1: <Название группы>

### Файлы
- `path/to/file1.py`
- `path/to/file2.py`

### Что изменено
- Краткое описание изменений в файле 1
- Краткое описание изменений в файле 2

### Цель изменений
Зачем эти изменения были сделаны.

---
```

**Создать файл:** `<target_directory>/docs/analysis/CHANGELOG-<feature-name>.md`

**Описание коммитов и CHANGELOG:** В описании групп и в сообщениях коммитов **не перечислять файлы из папок тасков** (например `tasks/task-*/`) — указывать канонические документы, зеркала, CHANGELOG, группы изменений (Core, Tests, Documentation).

---

### Шаг 4.5: План коммита на согласование (обязательно)

**Перед выполнением коммитов** агент формирует **план коммита** и представляет его оператору:

- Список групп (какие файлы в какую группу).
- Количество коммитов и сообщения для каждого (type(scope): subject; при необходимости body).
- Кратко: что входит в каждый коммит.

Оператор согласовывает план («подходит», «исправить …», «разбить иначе»). Коммиты выполняются **только после явного согласования**. Подробнее — в **docs/methodology/git-commit-prompt.md**, шаг 4.

---

### Шаг 5: Создание коммитов по группам

**Формат commit message:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Типы коммитов (conventional commits):**
- `feat` - новая функциональность
- `fix` - исправление бага
- `refactor` - рефакторинг без изменения функциональности
- `test` - добавление/изменение тестов
- `chore` - изменения в конфигурации, документации, cleanup
- `docs` - только изменения в документации
- `style` - форматирование, отсутствующие точки с запятой и т.д.
- `perf` - улучшение производительности

**Scope:** модуль/компонент (например, `woocommerce`, `localization`, `services`)

**Subject:** краткое описание (до 50 символов, без точки в конце)

**Body:** подробное описание (опционально, разделяется пустой строкой от subject)
- Что изменено
- Почему изменено
- Как это влияет на существующий код

**Примеры commit messages:**

```bash
# Группа 1: Core Feature
feat(woocommerce): implement component descriptions aggregation for HTML export

- Add _aggregate_component_descriptions() method to HTMLFormatAdapter
- Aggregate descriptions from all product components
- Lazy aggregation at render time (does not modify Product model)
- Support 1-N components with component titles
- Add new HTML sections: Description, Effects, Warnings, Dosage
- Improve HTML escaping for security (XSS prevention)

This enables WooCommerce product cards to include full marketing content from component descriptions.

# Группа 2: Models and Services
refactor(services): update models and services for component descriptions support

- Update ComponentDescription model (documentation improvements)
- Enhance ProductAssembler for ComponentDescription enrichment
- Update ComponentService for component descriptions handling
- Update ServiceFactory for HTMLFormatAdapter dependencies

These changes ensure the complete chain works correctly: Blockchain → Assembler → HTMLFormatAdapter.

# Группа 3: Localization
feat(localization): enhance component descriptions localization support

- Improve ComponentLocalizationService for component descriptions
- Enhance ProductLocalizationService for multilingual descriptions
- Update MultilingualIPFSService for ComponentDescription payload handling

These changes ensure correct localization of component descriptions when exporting to WooCommerce.

# Группа 4: Unit Tests
test(unit): add comprehensive test coverage for component descriptions aggregation

- Add unit tests for HTMLFormatAdapter._aggregate_component_descriptions()
- Add integration tests for format_product_html() with descriptions
- Update existing unit tests for compatibility

Test coverage follows @test-qualification.mdc principles.

# Группа 5: Integration Tests
test(integration): add integration tests for WooCommerce export pipeline

- Add new integration test file: test_woocommerce_export_pipeline.py
- Update integration tests for compatibility with component descriptions
- Update integration stubs and fixtures

These tests validate the complete pipeline: Blockchain → Assembler → HTMLFormatAdapter → CSV Export.

# Группа 6: Configuration
chore(config): update test infrastructure and configuration for component descriptions

- Update pytest.ini: Add new test markers or update test configuration
- Update conftest.py files: Add fixtures for testing
- Update validators.py: Improve validation for ComponentDescription

These changes ensure correct test infrastructure and validation support.

# Группа 7: Documentation
chore(docs): remove temporary test qualification report files

- Remove test-qualification-*.md (temporary reports)

These were temporary qualification reports that are no longer needed.
```

---

### Шаг 6: Выполнение коммитов

**Алгоритм:**
1. Для каждой группы файлов:
   ```bash
   # Добавить файлы группы
   git add <file1> <file2> ... <fileN>
   
   # Создать коммит с описательным сообщением
   git commit -m "<type>(<scope>): <subject>

   <body>

   <footer>"
   ```

2. Проверить что все файлы закоммичены:
   ```bash
   git status --short <target_directory>/
   ```

3. Проверить список созданных коммитов:
   ```bash
   git log --oneline -N  # где N - количество коммитов
   ```

---

### Шаг 7: Push в удаленный репозиторий

**Важно:** Push выполняется **только после явного разрешения оператора**. Агент не выполняет `git push` по умолчанию после коммитов; оператор проверяет коммиты и пушит вручную или явно просит выполнить push. См. **docs/methodology/git-commit-prompt.md**, шаг 6.

**Команда (когда оператор разрешил):**
```bash
# Убедиться что находимся в правильной ветке
git branch --show-current

# Push всех коммитов
git push origin <branch-name>
```

**Проверка после push:**
```bash
# Проверить что все коммиты запушены
git log --oneline origin/<branch-name>..HEAD

# Если команда не выводит ничего - все коммиты запушены
```

---

## Шаблон для использования в диалоге

```
Изучи все измененные файлы в <target_directory>, сгруппируй их по функциональным категориям и создай структурированные коммиты с английскими сообщениями для каждой группы.

Алгоритм:
1. Проанализируй измененные файлы, исключив файлы которые НЕ должны попадать в git:
   - Сгенерированные/компилированные файлы (__pycache__, *.pyc, node_modules, dist, artifacts, cache)
   - Временные файлы (temp-*, *.tmp, *.bak, *.backup)
   - Логи (*.log, logs/)
   - Приватные данные (.env*, *keys.json, *wallet.json, *_invites*.txt)
   - Тестовые данные с реальными/приватными данными
   - Системные и IDE файлы
2. Для новых файлов (untracked): проверь что они контекстно связаны с другими изменениями и их функциональный смысл понятен
3. Сгруппируй файлы по функциональным категориям (Core Feature, Models/Services, Localization, Unit Tests, Integration Tests, Configuration, Documentation)
4. Создай коммит для каждой группы с описательным commit message на английском (conventional commits format)
5. Выполни push всех коммитов в <branch-name> ветку

Используй методологию @.cursor/commands/run-analysis.md для анализа — только факты из кода, без предположений. Для процесса коммитов (план на согласование, push по разрешению) — @docs/methodology/git-commit-prompt.md и @docs/methodology/git-commit.md.

Коммить файлы по группам:
- Группа 1: Core Feature (основная реализация)
- Группа 2: Models and Services (модели и сервисы)
- Группа 3: Localization (локализация)
- Группа 4: Unit Tests (unit тесты)
- Группа 5: Integration/E2E Tests (интеграционные тесты)
- Группа 6: Configuration (конфигурация)
- Группа 7: Documentation (документация, cleanup)

Каждый коммит должен иметь:
- Тип: feat/fix/refactor/test/chore/docs
- Scope: модуль/компонент
- Subject: краткое описание (до 50 символов)
- Body: подробное описание изменений (что, почему, как влияет)

ВАЖНО: Не коммитить файлы из категорий "НЕ коммитить" (см. Шаг 2 в docs/git-commit.md).
```

---

## Примеры фильтров для разных директорий

**Универсальный фильтр (рекомендуется использовать .gitignore через git):**
```bash
# Использовать git status для автоматического применения .gitignore
git status --short <target_directory>/ | grep -E "^[MAD]" | awk '{print $2}'

# Или использовать git diff с игнорированием (если нужно увидеть untracked)
git diff --name-only --diff-filter=ACDMRT <target_directory>/ 2>/dev/null | \
  grep -v -E "(temp-|\.log$|\.tmp$|\.bak$|__pycache__|node_modules|\.cache)" | \
  sort
```

**Примеры специфичных фильтров (только если нужно явное исключение):**

**Для Python проектов (`bot/`):**
```bash
git diff --name-only --diff-filter=ACDMRT bot/ 2>/dev/null | \
  grep -vE "(__pycache__|\.pyc$|\.pyo$|temp-|\.log$|^bot/flowers/|^bot/cache/)" | \
  sort
```

**Для JavaScript/TypeScript проектов:**
```bash
git diff --name-only --diff-filter=ACDMRT <target_directory>/ 2>/dev/null | \
  grep -vE "(node_modules|dist/|build/|\.log$|temp-|\.cache)" | \
  sort
```

**Для Solidity/Hardhat проектов:**
```bash
git diff --name-only --diff-filter=ACDMRT contracts/ 2>/dev/null | \
  grep -vE "(artifacts/|cache/|typechain/|\.log$|temp-)" | \
  sort
```

**Важно:** Лучше полагаться на `.gitignore` файл проекта, который уже содержит правильные правила исключения для вашего стека технологий.

---

## Чеклист перед коммитами

- [ ] Все файлы из категорий "НЕ коммитить" исключены:
  - [ ] Сгенерированные/компилированные файлы (cache, artifacts, build)
  - [ ] Временные файлы (temp-*, *.tmp, *.bak)
  - [ ] Логи (*.log, logs/)
  - [ ] Приватные данные (.env*, *keys.json, *wallet.json, *_invites*.txt)
  - [ ] Тестовые данные с реальными/приватными данными
  - [ ] Кэш и системные файлы
- [ ] Новые файлы контекстно связаны с другими изменениями и их функциональный смысл понятен
- [ ] Файлы сгруппированы логически (независимо от языка программирования)
- [ ] Зависимости между группами учтены (правильный порядок коммитов)
- [ ] Commit messages на английском языке
- [ ] Commit messages следуют conventional commits format
- [ ] Каждый коммит логически целостный (можно откатить отдельно)
- [ ] Проверено что все нужные файлы закоммичены (git status показывает только исключенные файлы)
- [ ] Коммиты запушены в правильную ветку

---

## Типичные ошибки

1. **Коммит файлов из разных групп вместе** - нарушает логическую целостность
2. **Коммит файлов, которые не должны быть в git:**
   - Сгенерированные/компилированные файлы (cache, artifacts) - засоряют историю
   - Временные файлы (temp-*, *.tmp, *.bak) - не несут ценности
   - Логи (*.log) - могут содержать чувствительные данные
   - Приватные данные (.env*, ключи, инвайты) - **критическая ошибка безопасности**
3. **Коммит новых файлов без понимания их назначения** - могут быть временными/служебными
4. **Русский язык в commit messages** - должен быть английский
5. **Слишком длинные commit messages** - subject до 50 символов, body до 72 символов на строку
6. **Отсутствие scope в commit message** - усложняет навигацию по истории
7. **Коммит без описания (body)** - для сложных изменений нужен body

---

## Дополнительные ресурсы

- [Conventional Commits](https://www.conventionalcommits.org/)
- [How to Write a Git Commit Message](https://chris.beams.io/posts/git-commit/)
- **Методика процесса и план на согласование:** `docs/methodology/git-commit-prompt.md`
- Методология анализа: `@.cursor/commands/run-analysis.md`
- Стандарт задач: `docs/task-standard.md`

