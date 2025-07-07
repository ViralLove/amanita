# Анализ каталога и заполнение словарей

## Цель
Проанализировать файл `bot/catalog/active_catalog.json` и создать INSERT запросы для всех словарей системы локализации на основе реально используемых значений.

## Анализ каталога

### Исходные данные
- **Файл**: `bot/catalog/active_catalog.json`
- **Количество продуктов**: 16
- **Язык каталога**: Английский
- **Структура**: JSON массив с объектами продуктов

### Извлеченные уникальные значения

#### 1. Категории продуктов (categories)
```
mushroom          - Грибы
plant             - Растения  
mental health     - Психическое здоровье
focus             - Концентрация
ADHD support      - Поддержка при СДВГ
mental force      - Ментальная сила
immune system     - Иммунная система
vital force       - Жизненная сила
antiparasite      - Антипаразитарные
```

#### 2. Формы продуктов (form)
```
mixed slices      - Смешанные ломтики
whole caps        - Целые шляпки
broken caps       - Сломанные шляпки
premium caps      - Премиум шляпки
unknown           - Неизвестно
powder            - Порошок
tincture          - Настойка
flower            - Цветы
chunks            - Кусочки
dried whole       - Цельные сушеные
dried powder      - Сушеный порошок
dried strips      - Сушеные полоски
whole dried       - Цельные сушеные
```

#### 3. Единицы измерения
```
g  - грамм (вес)
ml - миллилитр (объем)
```

#### 4. Валюты
```
EUR - Евро (€)
```

#### 5. Статусы (стандартные)
**Заказы:**
```
pending    - Ожидает
confirmed  - Подтвержден
shipped    - Отправлен
delivered  - Доставлен
cancelled  - Отменен
```

**Платежи:**
```
pending    - Ожидает
confirmed  - Подтвержден
failed     - Ошибка
```

## Реализация в базе данных

### 1. Вставка базовых данных словарей

```sql
-- Категории продуктов
insert into category_dictionary (code) values ('mushroom');
insert into category_dictionary (code) values ('plant');
insert into category_dictionary (code) values ('mental health');
insert into category_dictionary (code) values ('focus');
insert into category_dictionary (code) values ('ADHD support');
insert into category_dictionary (code) values ('mental force');
insert into category_dictionary (code) values ('immune system');
insert into category_dictionary (code) values ('vital force');
insert into category_dictionary (code) values ('antiparasite');

-- Формы продуктов
insert into form_dictionary (code) values ('mixed slices');
insert into form_dictionary (code) values ('whole caps');
insert into form_dictionary (code) values ('broken caps');
insert into form_dictionary (code) values ('premium caps');
insert into form_dictionary (code) values ('unknown');
insert into form_dictionary (code) values ('powder');
insert into form_dictionary (code) values ('tincture');
insert into form_dictionary (code) values ('flower');
insert into form_dictionary (code) values ('chunks');
insert into form_dictionary (code) values ('dried whole');
insert into form_dictionary (code) values ('dried powder');
insert into form_dictionary (code) values ('dried strips');
insert into form_dictionary (code) values ('whole dried');

-- Единицы измерения
insert into measurement_units (code, unit_type) values ('g', 'weight');
insert into measurement_units (code, unit_type) values ('ml', 'volume');

-- Валюты
insert into currencies (code, symbol) values ('EUR', '€');

-- Статусы заказов
insert into order_statuses (code) values ('pending');
insert into order_statuses (code) values ('confirmed');
insert into order_statuses (code) values ('shipped');
insert into order_statuses (code) values ('delivered');
insert into order_statuses (code) values ('cancelled');

-- Статусы платежей
insert into payment_statuses (code) values ('pending');
insert into payment_statuses (code) values ('confirmed');
insert into payment_statuses (code) values ('failed');
```

### 2. Переводы на русский язык (дефолтный)

#### Категории
```sql
insert into category_translations (category_id, language_code, name, description) 
select cd.id, 'ru', 
  case cd.code
    when 'mushroom' then 'Грибы'
    when 'plant' then 'Растения'
    when 'mental health' then 'Психическое здоровье'
    when 'focus' then 'Концентрация'
    when 'ADHD support' then 'Поддержка при СДВГ'
    when 'mental force' then 'Ментальная сила'
    when 'immune system' then 'Иммунная система'
    when 'vital force' then 'Жизненная сила'
    when 'antiparasite' then 'Антипаразитарные'
    else cd.code
  end,
  case cd.code
    when 'mushroom' then 'Натуральные грибы для здоровья'
    when 'plant' then 'Лекарственные растения'
    when 'mental health' then 'Продукты для психического здоровья'
    when 'focus' then 'Средства для улучшения концентрации'
    when 'ADHD support' then 'Поддержка при синдроме дефицита внимания'
    when 'mental force' then 'Усиление ментальных способностей'
    when 'immune system' then 'Укрепление иммунной системы'
    when 'vital force' then 'Повышение жизненной энергии'
    when 'antiparasite' then 'Средства против паразитов'
    else null
  end
from category_dictionary cd;
```

#### Формы
```sql
insert into form_translations (form_id, language_code, name, description)
select fd.id, 'ru',
  case fd.code
    when 'mixed slices' then 'Смешанные ломтики'
    when 'whole caps' then 'Целые шляпки'
    when 'broken caps' then 'Сломанные шляпки'
    when 'premium caps' then 'Премиум шляпки'
    when 'unknown' then 'Неизвестно'
    when 'powder' then 'Порошок'
    when 'tincture' then 'Настойка'
    when 'flower' then 'Цветы'
    when 'chunks' then 'Кусочки'
    when 'dried whole' then 'Цельные сушеные'
    when 'dried powder' then 'Сушеный порошок'
    when 'dried strips' then 'Сушеные полоски'
    when 'whole dried' then 'Цельные сушеные'
    else fd.code
  end,
  case fd.code
    when 'mixed slices' then 'Смешанные ломтики грибов'
    when 'whole caps' then 'Целые шляпки грибов'
    when 'broken caps' then 'Сломанные шляпки грибов'
    when 'premium caps' then 'Премиум качество шляпок'
    when 'powder' then 'Измельченный в порошок'
    when 'tincture' then 'Спиртовая настойка'
    when 'flower' then 'Цветочные части растений'
    when 'chunks' then 'Крупные кусочки'
    when 'dried whole' then 'Цельные сушеные части'
    when 'dried powder' then 'Сушеный и измельченный'
    when 'dried strips' then 'Сушеные полоски коры'
    when 'whole dried' then 'Цельные сушеные части'
    else null
  end
from form_dictionary fd;
```

#### Единицы измерения
```sql
insert into measurement_unit_translations (unit_id, language_code, name, short_name)
select mu.id, 'ru',
  case mu.code
    when 'g' then 'грамм'
    when 'ml' then 'миллилитр'
    else mu.code
  end,
  case mu.code
    when 'g' then 'г'
    when 'ml' then 'мл'
    else mu.code
  end
from measurement_units mu;
```

#### Валюты
```sql
insert into currency_translations (currency_id, language_code, name)
select c.id, 'ru',
  case c.code
    when 'EUR' then 'Евро'
    else c.code
  end
from currencies c;
```

#### Статусы заказов
```sql
insert into order_status_translations (status_id, language_code, name, description)
select os.id, 'ru',
  case os.code
    when 'pending' then 'Ожидает'
    when 'confirmed' then 'Подтвержден'
    when 'shipped' then 'Отправлен'
    when 'delivered' then 'Доставлен'
    when 'cancelled' then 'Отменен'
    else os.code
  end,
  case os.code
    when 'pending' then 'Заказ ожидает подтверждения'
    when 'confirmed' then 'Заказ подтвержден продавцом'
    when 'shipped' then 'Заказ отправлен покупателю'
    when 'delivered' then 'Заказ доставлен покупателю'
    when 'cancelled' then 'Заказ отменен'
    else null
  end
from order_statuses os;
```

#### Статусы платежей
```sql
insert into payment_status_translations (status_id, language_code, name, description)
select ps.id, 'ru',
  case ps.code
    when 'pending' then 'Ожидает'
    when 'confirmed' then 'Подтвержден'
    when 'failed' then 'Ошибка'
    else ps.code
  end,
  case ps.code
    when 'pending' then 'Платеж ожидает подтверждения'
    when 'confirmed' then 'Платеж подтвержден'
    when 'failed' then 'Ошибка при обработке платежа'
    else null
  end
from payment_statuses ps;
```

## Особенности реализации

### 1. Дефолтный язык
- **Русский язык** уже установлен как дефолтный в системе
- В `UserSettings.get_language()` используется `default: str = 'ru'`
- Все переводы созданы для языка `'ru'`

### 2. Структура переводов
- **Категории**: 9 уникальных значений с описаниями
- **Формы**: 13 уникальных значений с описаниями
- **Единицы**: 2 типа (вес и объем)
- **Валюты**: 1 валюта (EUR)
- **Статусы**: 5 статусов заказов + 3 статуса платежей

### 3. Использование CASE выражений
- Все переводы реализованы через `CASE` выражения
- Автоматическое связывание с базовыми записями через `SELECT`
- Поддержка fallback (возврат исходного кода при отсутствии перевода)

### 4. Описания для категорий
- Добавлены подробные описания для каждой категории
- Описания объясняют назначение и свойства категории
- Помогают пользователям понять назначение продуктов

## Результаты

### Выполненные задачи
- [x] Анализ каталога `active_catalog.json`
- [x] Извлечение всех уникальных значений
- [x] Создание INSERT запросов для словарей
- [x] Создание переводов на русский язык
- [x] Добавление описаний для категорий
- [x] Интеграция с существующей системой локализации

### Статистика
- **Категорий**: 9
- **Форм**: 13
- **Единиц измерения**: 2
- **Валют**: 1
- **Статусов заказов**: 5
- **Статусов платежей**: 3
- **Всего переводов**: 33 записи

### Следующие шаги
1. Добавить переводы для других языков (en, es, de, fr, etc.)
2. Создать систему автоматического обновления переводов
3. Добавить валидацию полноты переводов
4. Интегрировать с веб-интерфейсом управления

## Заключение

Система словарей полностью заполнена на основе реальных данных каталога. Все значения из `active_catalog.json` корректно отражены в базе данных с переводами на русский язык. Система готова к использованию в production среде и может быть легко расширена для поддержки дополнительных языков. 