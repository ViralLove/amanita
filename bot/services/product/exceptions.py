"""
Типизированные исключения для product сервисов
Создано для правильной обработки ошибок в интеграционных тестах
"""

class ProductError(Exception):
    """Базовое исключение для product сервисов"""
    def __init__(self, message: str, product_id: str = None):
        self.message = message
        self.product_id = product_id
        super().__init__(self.message)

class InvalidProductIdError(ProductError):
    """Исключение для невалидного ID продукта"""
    def __init__(self, product_id: str, message: str = None):
        if message is None:
            message = f"Невалидный ID продукта: {product_id}"
        super().__init__(message, product_id)

class ProductNotFoundError(ProductError):
    """Исключение для продукта, который не найден"""
    def __init__(self, product_id: str, message: str = None):
        if message is None:
            message = f"Продукт не найден: {product_id}"
        super().__init__(message, product_id)

class ProductValidationError(ProductError):
    """Исключение для ошибок валидации продукта"""
    def __init__(self, message: str, product_id: str = None, field: str = None):
        self.field = field
        super().__init__(message, product_id)

class ProductRegistryError(ProductError):
    """Исключение для ошибок реестра продуктов"""
    def __init__(self, message: str, product_id: str = None):
        super().__init__(message, product_id)
