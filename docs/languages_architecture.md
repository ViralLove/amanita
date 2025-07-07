# Архитектура локализации в системе Amanita

## Обзор

Система локализации Amanita представляет собой многоуровневую архитектуру, обеспечивающую поддержку 15 языков для Telegram-бота и веб-приложений. Архитектура построена на принципах модульности, расширяемости и централизованного управления переводами.

## Структура системы

### 1. Уровень хранения переводов

#### 1.1 JSON файлы переводов (`bot/templates/`)
```
bot/templates/
├── __init__.py          # Утилита для загрузки переводов
├── ru.json             # Русский (112 строк)
├── en.json             # Английский (34 строки)
├── es.json             # Испанский (30 строк)
├── de.json             # Немецкий (54 строки)
├── fr.json             # Французский (54 строки)
├── no.json             # Норвежский (26 строк)
├── da.json             # Датский (26 строк)
├── sv.json             # Шведский (26 строк)
├── fi.json             # Финский (26 строк)
├── et.json             # Эстонский (26 строк)
├── lv.json             # Латышский (26 строк)
├── lt.json             # Литовский (26 строк)
├── pl.json             # Польский (26 строк)
├── nl.json             # Голландский (26 строк)
└── pt.json             # Португальский (26 строк)
```

#### 1.2 Структура JSON файлов
```json
{
  "welcome": "Добро пожаловать в AMANITA!",
  "onboarding": {
    "welcome_title": "🍄 Добро пожаловать в экосистему AMANITA.",
    "welcome_description": "Ты попал туда, где натуральная медицина встречает заботу...",
    "btn_have_invite": "🌱 У меня есть приглашение",
    "success": "✅ Успешно",
    "invite_prompt": "Пожалуйста, введите ваш инвайт-код"
  },
  "menu": {
    "title": "Главное меню",
    "catalog": "🛍 Каталог",
    "cart": "🛒 Корзина"
  },
  "catalog": {
    "loading": "🔄 Загружаем каталог...",
    "empty": "🤷‍♂️ Каталог пуст"
  }
}
```

### 2. Уровень сервисов локализации

#### 2.1 Класс Localization (`bot/services/common/localization.py`)
```python
class Localization:
    def __init__(self, lang='ru'):
        self.lang = lang
        self.labels = self.load_labels(lang)
    
    def load_labels(self, lang):
        # Загрузка JSON файла по языку
        path = f"bot/templates/{lang}.json"
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    
    def t(self, key):
        # Рекурсивный поиск по вложенным ключам
        # Пример: t('onboarding.welcome_title')
        parts = key.split('.')
        value = self.labels
        for part in parts:
            value = value.get(part, key)
        return value
```

#### 2.2 Утилита get_text (`bot/templates/__init__.py`)
```python
def get_text(key: str, lang: str = 'en') -> str:
    """
    Получает текст по ключу из соответствующего языкового файла.
    Поддерживает рекурсивный поиск по вложенным ключам.
    """
    try:
        file_path = f"bot/templates/{lang}.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        
        def find_nested(d, k):
            if k in d:
                return d[k]
            for v in d.values():
                if isinstance(v, dict):
                    result = find_nested(v, k)
                    if result and result != k:
                        return result
            return k
        
        return find_nested(translations, key)
    except Exception:
        return key
```

### 3. Уровень управления пользовательскими настройками

#### 3.1 Класс UserSettings (`bot/model/user_settings.py`)
```python
class UserSettings:
    def set_language(self, user_id: int, language: str) -> None:
        """Устанавливает язык пользователя"""
        self._ensure_user_exists(user_id)
        self._settings[user_id]['language'] = language
    
    def get_language(self, user_id: int, default: str = 'ru') -> str:
        """Получает язык пользователя"""
        if user_id in self._settings:
            return self._settings[user_id].get('language', default)
        return default
```

### 4. Уровень базы данных

#### 4.1 Таблица languages (`bot/db.sql`)
```sql
create table languages (
    code varchar(5) primary key,           -- 'en', 'ru', 'es', 'fr', 'de', etc.
    name text not null,                    -- English, Русский, Español, Français, Deutsch
    native_name text not null,             -- English, Русский, Español, Français, Deutsch
    is_active boolean default true,
    created_at timestamptz default now()
);

-- Базовые данные: языки из bot/templates
insert into languages (code, name, native_name) values ('ru', 'Russian', 'Русский');
insert into languages (code, name, native_name) values ('en', 'English', 'English');
insert into languages (code, name, native_name) values ('es', 'Spanish', 'Español');
-- ... и так далее для всех 15 языков
```

#### 4.2 Таблицы переводов для словарей
```sql
-- Словарь категорий продуктов
create table category_dictionary (
    id uuid primary key default gen_random_uuid(),
    code varchar(50) unique not null,      -- 'mushrooms', 'herbs', 'supplements'
    created_at timestamptz default now()
);

-- Переводы категорий
create table category_translations (
    category_id uuid references category_dictionary(id) on delete cascade,
    language_code varchar(5) references languages(code),
    name text not null,
    description text,
    primary key (category_id, language_code)
);

-- Аналогично для форм, единиц измерения, статусов заказов и платежей
```

## Принципы работы

### 1. Выбор языка пользователем

#### 1.1 Клавиатура выбора языка
```python
LANG_KEYBOARD = [
    ["🇷🇺 ru", "🇪🇸 es", "🇬🇧 en", "🇫🇷 fr"],
    ["🇪🇪 et", "🇮🇹 it", "🇵🇹 pt", "🇩🇪 de"],
    ["🇵🇱 pl", "🇫🇮 fi", "🇳🇴 no", "🇸🇪 sv"]
]

lang_map = {
    "🇷🇺 ru": "ru",
    "🇪🇸 es": "es",
    "🇬🇧 en": "en",
    # ... и так далее
}
```

#### 1.2 Процесс установки языка
```python
@router.message(OnboardingStates.LanguageSelection, F.text.in_(lang_map.keys()))
async def set_language(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = lang_map[message.text]
    user_settings.set_language(user_id, lang)
    
    await state.set_state(OnboardingStates.OnboardingPathChoice)
    loc = Localization(lang)
    welcome_message = f"{loc.t('onboarding.welcome_title')}\n\n{loc.t('onboarding.welcome_description')}"
    # ...
```

### 2. Использование переводов в обработчиках

#### 2.1 Типичный паттерн использования
```python
@router.callback_query(F.data == "onboarding:have_invite")
async def process_invite_choice(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = user_settings.get_language(user_id)
    loc = Localization(lang)
    
    await callback.message.answer(loc.t("onboarding.input_invite_label"))
    await state.set_state(OnboardingStates.InviteInput)
```

#### 2.2 Рекурсивный поиск по ключам
```python
# Поддерживаются вложенные ключи через точку
loc.t('onboarding.welcome_title')           # -> "🍄 Добро пожаловать в экосистему AMANITA."
loc.t('menu.catalog')                       # -> "🛍 Каталог"
loc.t('catalog.product.species')            # -> "🌿 Вид"
```

### 3. Интеграция с базой данных

#### 3.1 Связь JSON файлов с БД
- **JSON файлы**: Для интерфейса бота (быстрый доступ)
- **База данных**: Для словарей продуктов, категорий, статусов (структурированные данные)

#### 3.2 Представление с переводами
```sql
create view products_with_translations as
select 
    p.id,
    p.title,
    array_agg(DISTINCT ct.name) as category_names,
    array_agg(DISTINCT ft.name) as form_names
from products p
left join product_categories pc on p.id = pc.product_id
left join category_dictionary cd on pc.category = cd.code
left join category_translations ct on cd.id = ct.category_id
left join product_forms pf on p.id = pf.product_id
left join form_dictionary fd on pf.form = fd.code
left join form_translations ft on fd.id = ft.form_id
group by p.id, p.title;
```

## Особенности архитектуры

### 1. Двойная система переводов

#### 1.1 JSON файлы для интерфейса
- **Назначение**: Переводы интерфейса бота
- **Структура**: Вложенные объекты с ключами
- **Доступ**: Через класс Localization
- **Производительность**: Быстрая загрузка в память

#### 1.2 База данных для словарей
- **Назначение**: Структурированные данные (категории, формы, статусы)
- **Структура**: Нормализованные таблицы с переводами
- **Доступ**: Через SQL запросы
- **Производительность**: Индексированные запросы

### 2. Гибкость ключей

#### 2.1 Поддержка вложенности
```json
{
  "onboarding": {
    "welcome": {
      "title": "Добро пожаловать",
      "description": "Описание"
    }
  }
}
```

#### 2.2 Fallback механизм
- Если ключ не найден, возвращается сам ключ
- Поддержка рекурсивного поиска
- Логирование ошибок для отладки

### 3. Масштабируемость

#### 3.1 Добавление новых языков
1. Создать JSON файл `{lang}.json` в `bot/templates/`
2. Добавить INSERT в таблицу `languages`
3. Добавить в `lang_map` и `LANG_KEYBOARD`

#### 3.2 Добавление новых переводов
1. Добавить ключи во все JSON файлы
2. При необходимости добавить в таблицы переводов БД

## Интеграция с другими компонентами

### 1. Telegram Bot
- Использование в обработчиках сообщений
- Динамическое переключение языков
- Локализованные клавиатуры

### 2. WebApp
- Передача языка через URL параметры
- Синхронизация с настройками пользователя
- Локализованные интерфейсы

### 3. База данных
- Связь с таблицами переводов
- Представления с агрегированными переводами
- Индексы для производительности

## Мониторинг и отладка

### 1. Логирование
```python
logger.debug(f"[LOCALIZATION] Запрошен перевод для ключа: '{key}', язык: {self.lang}")
logger.error(f"[LOCALIZATION] Часть '{part}' не найдена. Доступные ключи: {list(value.keys())}")
```

### 2. Валидация критических ключей
```python
def _verify_critical_keys(self):
    invite_prompt = self.t("onboarding.invite_prompt")
    success = self.t("onboarding.success")
```

### 3. Проверка целостности
- Автоматическая проверка наличия ключей
- Сравнение структуры между языками
- Валидация соответствия ISO 639-1

## Планы развития

### 1. Краткосрочные улучшения
- [ ] Добавить кэширование переводов в Redis
- [ ] Создать систему валидации полноты переводов
- [ ] Добавить автоматическую синхронизацию JSON ↔ БД

### 2. Долгосрочные планы
- [ ] Реализовать полную ИИ автоматизацию для обновления переводов
- [ ] Добавить поддержку плюральных форм

### 3. Оптимизация производительности
- [ ] Предзагрузка всех переводов в память
- [ ] Индексы для быстрого поиска в БД
- [ ] Кэширование часто используемых переводов

## Заключение

Архитектура локализации Amanita представляет собой хорошо структурированную систему, обеспечивающую:

- **Гибкость**: Поддержка 15 языков с возможностью легкого расширения
- **Производительность**: Быстрый доступ к переводам через JSON файлы
- **Структурированность**: Нормализованные данные в БД для словарей
- **Масштабируемость**: Модульная архитектура для добавления новых языков
- **Надежность**: Fallback механизмы и валидация данных

Система готова к использованию в production среде и может быть легко расширена для поддержки дополнительных языков и функций. 