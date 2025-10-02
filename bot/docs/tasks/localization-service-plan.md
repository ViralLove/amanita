# План реализации LocalizationService

## Цель
Создать универсальный сервис локализации, который расширяет существующий Localization для поддержки переводов продуктов и компонентов.

## Стратегия
1. **Расширение существующего класса** - наследование от Localization
2. **Сохранение обратной совместимости** - все существующие вызовы работают
3. **Добавление новой функциональности** - поддержка продуктов и компонентов
4. **Поэтапная реализация** - сначала базовая структура, потом интеграция

## Детальный план изменений

### 1. Создание LocalizationService (bot/services/common/localization_service.py)
```python
class LocalizationService(Localization):
    def __init__(self, lang='ru'):
        super().__init__(lang)
        self.product_localization = ProductLocalizationService()
        self.component_localization = ComponentLocalizationService()
    
    def t(self, key, default=None, **kwargs):
        # Универсальный метод для всех типов переводов
        if key.startswith('product.'):
            return self.product_localization.get_translation(key, default, **kwargs)
        elif key.startswith('component.'):
            return self.component_localization.get_translation(key, default, **kwargs)
        else:
            return super().t(key, default, **kwargs)
```

### 2. Создание ProductLocalizationService (bot/services/common/product_localization.py)
```python
class ProductLocalizationService:
    def __init__(self):
        self.cache = {}
        self.fallback_data = {}
    
    def get_translation(self, key, default=None, **kwargs):
        # Логика получения переводов продуктов
        pass
```

### 3. Создание ComponentLocalizationService (bot/services/common/component_localization.py)
```python
class ComponentLocalizationService:
    def __init__(self):
        self.cache = {}
        self.fallback_data = {}
    
    def get_translation(self, key, default=None, **kwargs):
        # Логика получения переводов компонентов
        pass
```

### 4. Обновление импортов в существующих файлах
- Обновить импорты в handlers для использования LocalizationService
- Обновить ProductFormatterService для работы с новым API
- Обновить тесты для проверки новой функциональности

## Риски и митигация

### Риск 1: Нарушение обратной совместимости
- **Митигация**: Наследование от Localization, сохранение всех методов
- **Тестирование**: Запуск всех существующих тестов

### Риск 2: Снижение производительности
- **Митигация**: Ленивая загрузка, кэширование, оптимизация
- **Тестирование**: Бенчмарки производительности

### Риск 3: Сложность интеграции
- **Митигация**: Поэтапная реализация, тестирование на каждом этапе
- **Тестирование**: Интеграционные тесты

## Критерии успеха
- ✅ Все существующие тесты проходят
- ✅ Новый API работает для продуктов и компонентов
- ✅ Производительность не хуже существующей
- ✅ Код готов к интеграции с кэшированием
