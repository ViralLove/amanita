"""
Фабрика валидаторов для создания и управления экземплярами валидаторов.

Этот модуль реализует Factory и Singleton паттерны для централизованного
управления валидаторами в системе валидации.
"""

from typing import Dict, Optional, Type
from .rules import ValidationRule, ValidationResult
from .validators import CIDValidator, ProportionValidator, PriceValidator, ProductValidator


class ValidationFactory:
    """
    Фабрика для создания и управления валидаторами.
    
    Реализует Singleton паттерн для каждого типа валидатора,
    обеспечивая единственный экземпляр на все приложение.
    
    Пример использования:
        factory = ValidationFactory()
        cid_validator = factory.get_cid_validator()
        result = cid_validator.validate("Qm123456789")
    """
    
    # Приватные атрибуты для хранения экземпляров валидаторов
    _cid_validator: Optional[CIDValidator] = None
    _proportion_validator: Optional[ProportionValidator] = None
    _price_validator: Optional[PriceValidator] = None
    _product_validator: Optional[ProductValidator] = None
    
    @classmethod
    def get_cid_validator(cls, min_length: int = 3) -> CIDValidator:
        """
        Возвращает синглтон CIDValidator.
        
        Args:
            min_length: Минимальная длина CID (используется только при первом создании)
            
        Returns:
            CIDValidator: Единственный экземпляр валидатора CID
        """
        if cls._cid_validator is None:
            cls._cid_validator = CIDValidator(min_length=min_length)
        return cls._cid_validator
    
    @classmethod
    def get_proportion_validator(cls) -> ProportionValidator:
        """
        Возвращает синглтон ProportionValidator.
        
        Returns:
            ProportionValidator: Единственный экземпляр валидатора пропорций
        """
        if cls._proportion_validator is None:
            cls._proportion_validator = ProportionValidator()
        return cls._proportion_validator
    
    @classmethod
    def get_price_validator(cls, min_price: float = 0) -> PriceValidator:
        """
        Возвращает синглтон PriceValidator.
        
        Args:
            min_price: Минимальная цена (используется только при первом создании)
            
        Returns:
            PriceValidator: Единственный экземпляр валидатора цен
        """
        if cls._price_validator is None:
            cls._price_validator = PriceValidator(min_price=min_price)
        return cls._price_validator
    
    @classmethod
    def get_product_validator(cls) -> ProductValidator:
        """
        Возвращает синглтон ProductValidator.
        
        Returns:
            ProductValidator: Единственный экземпляр валидатора продуктов
        """
        if cls._product_validator is None:
            cls._product_validator = ProductValidator()
        return cls._product_validator
    
    @classmethod
    def reset_all_validators(cls) -> None:
        """
        Сбрасывает все экземпляры валидаторов.
        
        Этот метод используется в тестах для очистки состояния
        между тестовыми случаями.
        """
        cls._cid_validator = None
        cls._proportion_validator = None
        cls._price_validator = None
        cls._product_validator = None
    
    @classmethod
    def get_all_validators(cls) -> Dict[str, ValidationRule]:
        """
        Возвращает словарь со всеми доступными валидаторами.
        
        Returns:
            Dict[str, ValidationRule]: Словарь с именами и экземплярами валидаторов
        """
        return {
            "cid": cls.get_cid_validator(),
            "proportion": cls.get_proportion_validator(),
            "price": cls.get_price_validator(),
            "product": cls.get_product_validator()
        }
    
    @classmethod
    def get_validator_by_name(cls, name: str) -> Optional[ValidationRule]:
        """
        Возвращает валидатор по имени.
        
        Args:
            name: Имя валидатора ('cid', 'proportion', 'price', 'product')
            
        Returns:
            ValidationRule: Валидатор или None, если не найден
        """
        validators = {
            "cid": cls.get_cid_validator,
            "proportion": cls.get_proportion_validator,
            "price": cls.get_price_validator,
            "product": cls.get_product_validator
        }
        
        if name in validators:
            return validators[name]()
        return None
    
    @classmethod
    def validate_with_all_validators(cls, data: Dict[str, any]) -> Dict[str, ValidationResult]:
        """
        Валидирует данные всеми доступными валидаторами.
        
        Args:
            data: Данные для валидации
            
        Returns:
            Dict[str, ValidationResult]: Результаты валидации для каждого валидатора
        """
        results = {}
        validators = cls.get_all_validators()
        
        for name, validator in validators.items():
            if name in data:
                results[name] = validator.validate(data[name])
            else:
                results[name] = ValidationResult.failure(
                    f"Поле '{name}' отсутствует в данных",
                    field_name=name,
                    error_code="MISSING_FIELD"
                )
        
        return results
    
    @classmethod
    def create_composite_validator(cls, validator_names: list[str]) -> 'CompositeValidationFactory':
        """
        Создает составной валидатор из указанных валидаторов.
        
        Args:
            validator_names: Список имен валидаторов для объединения
            
        Returns:
            CompositeValidationFactory: Составной валидатор
        """
        from .rules import CompositeValidationRule
        
        validators = []
        for name in validator_names:
            validator = cls.get_validator_by_name(name)
            if validator:
                validators.append(validator)
        
        return CompositeValidationFactory(validators)


class CompositeValidationFactory:
    """
    Фабрика для создания составных валидаторов.
    
    Этот класс позволяет создавать сложные валидаторы,
    объединяющие несколько простых валидаторов.
    """
    
    def __init__(self, validators: list[ValidationRule]):
        """
        Инициализирует фабрику составных валидаторов.
        
        Args:
            validators: Список валидаторов для объединения
        """
        from .rules import CompositeValidationRule
        self.composite_validator = CompositeValidationRule(validators)
    
    def validate(self, data: any) -> ValidationResult:
        """
        Валидирует данные составным валидатором.
        
        Args:
            data: Данные для валидации
            
        Returns:
            ValidationResult: Результат валидации
        """
        return self.composite_validator.validate(data)
    
    def add_validator(self, validator: ValidationRule) -> None:
        """
        Добавляет валидатор в составной валидатор.
        
        Args:
            validator: Валидатор для добавления
        """
        self.composite_validator.add_rule(validator)
    
    def remove_validator(self, validator: ValidationRule) -> None:
        """
        Удаляет валидатор из составного валидатора.
        
        Args:
            validator: Валидатор для удаления
        """
        self.composite_validator.remove_rule(validator)
