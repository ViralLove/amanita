"""
Кастомные исключения для валидации продуктов
"""

class ProductValidationError(Exception):
    """Базовое исключение для ошибок валидации продуктов"""
    def __init__(self, message: str, field: str = None, value: any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)

class InvalidCIDError(ProductValidationError):
    """Ошибка валидации CID"""
    def __init__(self, field: str, value: str):
        super().__init__(
            f"Неверный формат CID для поля '{field}': {value}. CID должен начинаться с 'Qm'",
            field=field,
            value=value
        )

class InvalidProductFormError(ProductValidationError):
    """Ошибка валидации формы продукта"""
    def __init__(self, value: str):
        valid_forms = ["powder", "tincture", "capsules", "extract", "tea", "oil", "mixed slices", "whole caps", "broken caps", "premium caps", "flower", "chunks", "dried whole", "dried powder", "dried strips"]
        super().__init__(
            f"Неверная форма продукта: {value}. Допустимые значения: {', '.join(valid_forms)}",
            field="forms",
            value=value
        )

class InvalidBusinessIdError(ProductValidationError):
    """Ошибка валидации business_id"""
    def __init__(self, message: str):
        super().__init__(
            f"Ошибка валидации business_id: {message}",
            field="business_id",
            value=None
        )

class InvalidCurrencyError(ProductValidationError):
    """Ошибка валидации валюты"""
    def __init__(self, value: str):
        valid_currencies = ["EUR", "USD", "GBP"]
        super().__init__(
            f"Неверная валюта: {value}. Допустимые значения: {', '.join(valid_currencies)}",
            field="currency",
            value=value
        )

class EmptyCategoriesError(ProductValidationError):
    """Ошибка валидации пустых категорий"""
    def __init__(self):
        super().__init__(
            "Категории продукта не могут быть пустыми",
            field="categories",
            value=[]
        )

class InvalidPriceFormatError(ProductValidationError):
    """Ошибка валидации формата цены"""
    def __init__(self, field: str, value: any):
        super().__init__(
            f"Неверный формат для поля '{field}': {value}",
            field=field,
            value=value
        )
