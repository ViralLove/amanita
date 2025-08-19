"""
Pydantic модели для продуктов с бизнес-валидацией (новая архитектура с organic_components)

Основные изменения:
- Заменено поле 'description' на 'organic_components'
- Добавлена поддержка многокомпонентных продуктов
- Добавлена валидация для organic_components
- Улучшена валидация для всех обязательных полей
- Синхронизированы типы данных с смарт-контрактом ProductRegistry.sol:
  * id: int (gt=0) вместо Union[str, int]
  * price: int (gt=0) вместо str
  * seller_address: Optional[str] для Ethereum адреса
"""

from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, validator
from bot.model.organic_component import OrganicComponent

from api.exceptions.validation import (
    InvalidCIDError, InvalidProductFormError, EmptyCategoriesError
)
from bot.validation import CIDValidator, ProportionValidator, PriceValidator

# Единые валидаторы для API-уровня
# Для IPFS CID применяем строгую минимальную длину 46 символов (v0 CID: 'Qm' + 44 base58)
_cid_validator_strict = CIDValidator(min_length=46)
_proportion_validator = ProportionValidator()
_price_validator = PriceValidator(min_price=0)

class OrganicComponentAPI(BaseModel):
    """
    Pydantic модель для API схемы органического компонента
    
    Attributes:
        biounit_id (str): Уникальный идентификатор биологической единицы
        description_cid (str): CID описания биоединицы в IPFS
        proportion (str): Пропорция компонента (например, "50%", "100g", "30ml")
    """
    biounit_id: str = Field(..., min_length=1, description="Уникальный идентификатор биологической единицы")
    description_cid: str = Field(..., min_length=1, description="CID описания биоединицы в IPFS")
    proportion: str = Field(..., min_length=1, description="Пропорция компонента (например, '50%', '100g', '30ml')")
    
    @validator('biounit_id')
    def validate_biounit_id(cls, v):
        """Валидация biounit_id"""
        if not v or not v.strip():
            raise ValueError("biounit_id: Поле обязательно для заполнения")
        return v.strip()
    
    @validator('description_cid')
    def validate_description_cid(cls, v):
        """Валидация description_cid"""
        if not v or not v.strip():
            raise ValueError("description_cid: Поле обязательно для заполнения")

        # Сначала проверяем префикс, как требуют тесты
        if not v.startswith('Qm'):
            raise InvalidCIDError("description_cid", v)

        result = _cid_validator_strict.validate(v)
        if not result.is_valid:
            # Если слишком короткий, поднимаем ValueError как в исходной логике
            if result.error_code in {"CID_TOO_SHORT"}:
                raise ValueError("description_cid: Некорректная длина CID")
            # Иначе оставляем InvalidCIDError для формата/символов
            raise InvalidCIDError("description_cid", v)

        return v.strip()
    
    @validator('proportion')
    def validate_proportion(cls, v):
        """Валидация пропорции"""
        if not v or not v.strip():
            raise ValueError("proportion: Поле обязательно для заполнения")

        result = _proportion_validator.validate(v)
        if not result.is_valid:
            raise ValueError(f"proportion: {result.error_message}")

        return v.strip()
    
    class Config:
        """Конфигурация Pydantic модели"""
        json_schema_extra = {
            "example": {
                "biounit_id": "amanita_muscaria",
                "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                "proportion": "100%"
            }
        }

class PriceModel(BaseModel):
    """Модель цены продукта"""
    weight: Optional[str] = Field(None, description="Вес продукта")
    weight_unit: Optional[str] = Field(None, description="Единица измерения веса")
    volume: Optional[str] = Field(None, description="Объем продукта")
    volume_unit: Optional[str] = Field(None, description="Единица измерения объема")
    price: int = Field(..., gt=0, description="Цена продукта (должна быть положительным числом)")
    currency: str = Field(default="EUR", description="Валюта цены")
    form: Optional[str] = Field(None, description="Форма продукта для данной цены")

class ProductUploadIn(BaseModel):
    """Модель для входящего продукта с валидацией (новая архитектура с organic_components)"""
    id: int = Field(..., gt=0, description="Уникальный идентификатор продукта (должен быть положительным числом)")
    title: str = Field(..., min_length=1, description="Название продукта")
    organic_components: List[OrganicComponentAPI] = Field(..., min_items=1, description="Список органических компонентов продукта")
    cover_image: str = Field(..., description="CID обложки")
    categories: List[str] = Field(..., description="Список категорий")
    forms: List[str] = Field(..., description="Список форм продукта")
    species: str = Field(..., min_length=1, description="Вид продукта")
    prices: List[PriceModel] = Field(..., min_items=1, description="Массив цен")
    seller_address: Optional[str] = Field(None, description="Адрес продавца (Ethereum адрес)")

    @validator('cover_image')
    def validate_cid_format(cls, v):
        """Строгая валидация CID обложки"""
        if not v or not v.strip():
            raise ValueError("cover_image: Поле обязательно для заполнения")

        # Сначала проверяем префикс, как требуют тесты
        if not v.startswith('Qm'):
            raise InvalidCIDError("cover_image", v)

        result = _cid_validator_strict.validate(v)
        if not result.is_valid:
            if result.error_code in {"CID_TOO_SHORT"}:
                raise ValueError("cover_image: Некорректная длина CID")
            raise InvalidCIDError("cover_image", v)

        return v

    @validator('organic_components')
    def validate_organic_components(cls, v):
        """Строгая валидация списка органических компонентов"""
        if not v or len(v) == 0:
            raise ValueError("organic_components: Поле обязательно для заполнения")
        
        # Проверяем, что все компоненты являются экземплярами OrganicComponentAPI
        for i, component in enumerate(v):
            if not isinstance(component, OrganicComponentAPI):
                raise ValueError(f"organic_components[{i}]: Должен быть экземпляром OrganicComponentAPI, получен: {type(component)}")
        
        # Проверяем уникальность biounit_id
        biounit_ids = [comp.biounit_id for comp in v]
        if len(biounit_ids) != len(set(biounit_ids)):
            duplicate_ids = [bid for bid in set(biounit_ids) if biounit_ids.count(bid) > 1]
            raise ValueError(f"organic_components: biounit_id должен быть уникальным. Дублирующиеся ID: {duplicate_ids}")
        
        return v

    @validator('forms')
    def validate_product_forms(cls, v):
        """Строгая валидация списка форм продукта"""
        if not v or len(v) == 0:
            raise InvalidProductFormError("forms: Список форм не может быть пустым")
        
        valid_forms = ["powder", "tincture", "capsules", "extract", "tea", "oil", "mixed slices", "whole caps", "broken caps", "premium caps", "flower", "chunks", "dried whole", "dried powder", "dried strips"]
        
        for i, form in enumerate(v):
            if not form or not form.strip():
                raise InvalidProductFormError(f"forms[{i}]: Форма не может быть пустой")
            
            if form not in valid_forms:
                raise InvalidProductFormError(f"forms[{i}]: Недопустимая форма '{form}'. Допустимые: {', '.join(valid_forms)}")
        
        return v

    @validator('categories')
    def validate_categories(cls, v):
        """Строгая валидация списка категорий"""
        if not v or len(v) == 0:
            raise EmptyCategoriesError()
        
        for i, category in enumerate(v):
            if not category or not category.strip():
                raise EmptyCategoriesError()
        
        return v

    @validator('seller_address')
    def validate_seller_address(cls, v):
        """Валидация адреса продавца (Ethereum адрес)"""
        if v is None:
            return v  # Поле опциональное
        
        # Проверяем формат Ethereum адреса (0x + 40 hex символов)
        import re
        address_pattern = r'^0x[a-fA-F0-9]{40}$'
        
        if not re.match(address_pattern, v):
            raise ValueError(
                f"seller_address: Некорректный формат Ethereum адреса '{v}'. "
                f"Ожидается формат: 0x + 40 hex символов"
            )
        
        return v

    def get_business_id(self) -> str:
        """Возвращает id как business_id (для обратной совместимости)"""
        return str(self.id)

    def get_forms_list(self) -> List[str]:
        """Возвращает список форм"""
        return self.forms if self.forms else []
    
    def get_organic_components_summary(self) -> str:
        """Возвращает краткое описание органических компонентов"""
        if not self.organic_components:
            return "Нет компонентов"
        
        component_summaries = []
        for comp in self.organic_components:
            component_summaries.append(f"{comp.biounit_id} ({comp.proportion})")
        
        return ", ".join(component_summaries)
    
    class Config:
        """Конфигурация Pydantic модели"""
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "Amanita Muscaria — Powder",
                "organic_components": [
                    {
                        "biounit_id": "amanita_muscaria",
                        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                        "proportion": "100%"
                    }
                ],
                "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                "categories": ["mushroom", "medicinal"],
                "forms": ["powder"],
                "species": "Amanita Muscaria",
                "prices": [
                    {
                        "weight": "100",
                        "weight_unit": "g",
                        "price": 80,
                        "currency": "EUR"
                    }
                ],
                "seller_address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
            }
        }

class ProductUploadRequest(BaseModel):
    """Модель для запроса загрузки продуктов"""
    products: List[ProductUploadIn] = Field(..., min_items=1, description="Список продуктов для загрузки")

class ProductUpdateIn(BaseModel):
    """Модель для обновления продукта (новая архитектура с organic_components)"""
    title: Optional[str] = Field(None, min_length=1, description="Название продукта")
    organic_components: Optional[List[OrganicComponentAPI]] = Field(None, min_items=1, description="Список органических компонентов продукта")
    cover_image: Optional[str] = Field(None, description="CID обложки")
    categories: Optional[List[str]] = Field(None, description="Список категорий")
    forms: Optional[List[str]] = Field(None, min_items=1, description="Список форм продукта")
    species: Optional[str] = Field(None, min_length=1, description="Вид продукта")
    prices: Optional[List[PriceModel]] = Field(None, min_items=1, description="Массив цен")
    seller_address: Optional[str] = Field(None, description="Адрес продавца (Ethereum адрес)")

    @validator('cover_image')
    def validate_cid_format(cls, v):
        """Строгая валидация CID обложки для обновления"""
        if v is not None:
            if not v.strip():
                raise ValueError("cover_image: Поле не может быть пустым")

            # Сначала проверяем префикс, как требуют тесты
            if not v.startswith('Qm'):
                raise InvalidCIDError("cover_image", v)

            result = _cid_validator_strict.validate(v)
            if not result.is_valid:
                if result.error_code in {"CID_TOO_SHORT"}:
                    raise ValueError("cover_image: Некорректная длина CID")
                raise InvalidCIDError("cover_image", v)
        
        return v

    @validator('organic_components')
    def validate_organic_components(cls, v):
        """Валидация списка органических компонентов для обновления"""
        if v is not None:
            if not v or len(v) == 0:
                raise ValueError("organic_components: Список не может быть пустым")
            
            # Проверяем, что все компоненты являются экземплярами OrganicComponentAPI
            for i, component in enumerate(v):
                if not isinstance(component, OrganicComponentAPI):
                    raise ValueError(f"organic_components[{i}]: Должен быть экземпляром OrganicComponentAPI, получен: {type(component)}")
            
            # Проверяем уникальность biounit_id
            biounit_ids = [comp.biounit_id for comp in v]
            if len(biounit_ids) != len(set(biounit_ids)):
                duplicate_ids = [bid for bid in set(biounit_ids) if biounit_ids.count(bid) > 1]
                raise ValueError(f"organic_components: biounit_id должен быть уникальным. Дублирующиеся ID: {duplicate_ids}")
        
        return v

    @validator('forms')
    def validate_product_forms(cls, v):
        if v is not None:
            if not v or len(v) == 0:
                raise InvalidProductFormError("Список форм не может быть пустым")
            valid_forms = ["powder", "tincture", "capsules", "extract", "tea", "oil", "mixed slices", "whole caps", "broken caps", "premium caps", "flower", "chunks", "dried whole", "dried powder", "dried strips"]
            for form in v:
                if form not in valid_forms:
                    raise InvalidProductFormError(form)
        return v

    @validator('categories')
    def validate_categories(cls, v):
        if v is not None and (not v or len(v) == 0):
            raise EmptyCategoriesError()
        return v
    
    class Config:
        """Конфигурация Pydantic модели"""
        json_schema_extra = {
            "example": {
                "title": "Amanita Muscaria — Premium Powder",
                "organic_components": [
                    {
                        "biounit_id": "amanita_muscaria",
                        "description_cid": "QmdoqBWBZoupjQWFfBxMJD5N9dJSFTyjVEV1AVL8oNEVSG",
                        "proportion": "100%"
                    }
                ],
                "cover_image": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                "categories": ["mushroom", "medicinal", "premium"],
                "forms": ["powder", "capsules"],
                "species": "Amanita Muscaria",
                "seller_address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
            }
        }

class ProductCreateFromDict(BaseModel):
    """Модель для создания продукта из словаря (для совместимости с тестами)"""
    id: int = Field(..., gt=0, description="Уникальный идентификатор продукта (должен быть положительным числом)")
    title: str = Field(..., min_length=1, description="Название продукта")
    organic_components: List[Dict[str, Any]] = Field(..., min_items=1, description="Список органических компонентов как словари")
    cover_image: str = Field(..., description="CID обложки")
    categories: List[str] = Field(..., description="Список категорий")
    forms: List[str] = Field(..., description="Список форм продукта")
    species: str = Field(..., min_length=1, description="Вид продукта")
    prices: List[Dict[str, Any]] = Field(..., min_items=1, description="Массив цен как словари")
    seller_address: Optional[str] = Field(None, description="Адрес продавца (Ethereum адрес)")

    @validator('cover_image')
    def validate_cid_format(cls, v):
        """Строгая валидация CID обложки"""
        if not v or not v.strip():
            raise ValueError("cover_image: Поле обязательно для заполнения")
        
        if not v.startswith('Qm'):
            raise InvalidCIDError("cover_image", v)
        
        # Проверяем минимальную длину CID
        if len(v) < 46:  # Qm + 44 символа хеша
            raise ValueError("cover_image: Некорректная длина CID")
        
        return v

    @validator('organic_components')
    def validate_organic_components_dict(cls, v):
        """Строгая валидация списка органических компонентов из словарей"""
        if not v or len(v) == 0:
            raise ValueError("organic_components: Поле обязательно для заполнения")
        
        # Проверяем структуру каждого компонента
        for i, component in enumerate(v):
            if not isinstance(component, dict):
                raise ValueError(f"organic_components[{i}]: Должен быть словарем, получен: {type(component)}")
            
            required_fields = ['biounit_id', 'description_cid', 'proportion']
            for field in required_fields:
                if field not in component:
                    raise ValueError(f"organic_components[{i}]: Отсутствует обязательное поле '{field}'")
            
            if not component['biounit_id'] or not str(component['biounit_id']).strip():
                raise ValueError(f"organic_components[{i}].biounit_id: Поле обязательно для заполнения")
            
            if not component['description_cid'] or not str(component['description_cid']).strip():
                raise ValueError(f"organic_components[{i}].description_cid: Поле обязательно для заполнения")
            
            if not component['proportion'] or not str(component['proportion']).strip():
                raise ValueError(f"organic_components[{i}].proportion: Поле обязательно для заполнения")
        
        # Проверяем уникальность biounit_id
        biounit_ids = [comp['biounit_id'] for comp in v]
        if len(biounit_ids) != len(set(biounit_ids)):
            duplicate_ids = [bid for bid in set(biounit_ids) if biounit_ids.count(bid) > 1]
            raise ValueError(f"organic_components: biounit_id должен быть уникальным. Дублирующиеся ID: {duplicate_ids}")
        
        return v

    @validator('forms')
    def validate_product_forms(cls, v):
        """Строгая валидация списка форм продукта"""
        if not v or len(v) == 0:
            raise InvalidProductFormError("forms: Список форм не может быть пустым")
        
        valid_forms = ["powder", "tincture", "capsules", "extract", "tea", "oil", "mixed slices", "whole caps", "broken caps", "premium caps", "flower", "chunks", "dried whole", "dried powder", "dried strips"]
        
        for i, form in enumerate(v):
            if not form or not str(form).strip():
                raise InvalidProductFormError(f"forms[{i}]: Форма не может быть пустой")
            
            if form not in valid_forms:
                raise InvalidProductFormError(f"forms[{i}]: Недопустимая форма '{form}'. Допустимые: {', '.join(valid_forms)}")
        
        return v

    @validator('categories')
    def validate_categories(cls, v):
        """Строгая валидация списка категорий"""
        if not v or len(v) == 0:
            raise EmptyCategoriesError()
        
        for i, category in enumerate(v):
            if not category or not str(category).strip():
                raise EmptyCategoriesError()
        
        return v

    def to_organic_components(self) -> List[OrganicComponent]:
        """Преобразует словари компонентов в объекты OrganicComponent"""
        return [OrganicComponent.from_dict(comp) for comp in self.organic_components]

    def to_price_models(self) -> List[PriceModel]:
        """Преобразует словари цен в объекты PriceModel"""
        return [PriceModel(**price) for price in self.prices]
    
    def get_organic_components_summary(self) -> str:
        """Возвращает краткое описание органических компонентов"""
        if not self.organic_components:
            return "Нет компонентов"
        
        component_summaries = []
        for comp in self.organic_components:
            component_summaries.append(f"{comp['biounit_id']} ({comp['proportion']})")
        
        return ", ".join(component_summaries)
    
    class Config:
        """Конфигурация Pydantic модели"""
        json_schema_extra = {
            "example": {
                "id": "test_product_001",
                "title": "Test Product",
                "organic_components": [
                    {
                        "biounit_id": "test_component",
                        "description_cid": "QmTestCID0011234567890123456789012345678901234567890",
                        "proportion": "100%"
                    }
                ],
                "cover_image": "QmTestCoverCID1234567890123456789012345678901234567890",
                "categories": ["test_category"],
                "forms": ["powder"],
                "species": "Test Species",
                "prices": [
                    {
                        "weight": "100",
                        "weight_unit": "g",
                        "price": "50",
                        "currency": "EUR"
                    }
                ]
            }
        }


class ProductStatusUpdate(BaseModel):
    """Модель для обновления статуса продукта"""
    status: int = Field(..., ge=0, le=1, description="Статус продукта (0 - неактивен, 1 - активен)")
    
    class Config:
        """Конфигурация Pydantic модели"""
        json_schema_extra = {
            "example": {
                "status": 1
            }
        }

class ProductResponse(BaseModel):
    """Модель ответа для продукта"""
    id: str = Field(..., description="Бизнес-идентификатор продукта")
    blockchain_id: Optional[int] = Field(None, description="ID продукта в блокчейне")
    tx_hash: Optional[str] = Field(None, description="Хеш транзакции создания")
    metadata_cid: Optional[str] = Field(None, description="CID метаданных в IPFS")
    status: str = Field(..., description="Статус операции")
    error: Optional[str] = Field(None, description="Описание ошибки, если есть")
    
    class Config:
        """Конфигурация Pydantic модели"""
        json_schema_extra = {
            "example": {
                "id": "amanita_muscaria_powder_001",
                "blockchain_id": 12345,
                "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                "metadata_cid": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                "status": "success",
                "error": None
            }
        }

class ProductsUploadResponse(BaseModel):
    """Модель ответа для загрузки продуктов"""
    results: List[ProductResponse] = Field(..., description="Результаты загрузки продуктов")
    
    class Config:
        """Конфигурация Pydantic модели"""
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "id": "amanita_muscaria_powder_001",
                        "blockchain_id": 12345,
                        "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                        "metadata_cid": "QmYrs5gAMeZEmiFAJnmRcD19rpCpXF52ssMJ6X2oWrxWWj",
                        "status": "success",
                        "error": None
                    },
                    {
                        "id": "blue_lotus_tincture_001",
                        "blockchain_id": 12346,
                        "tx_hash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                        "error": None
                    }
                ]
            }
        }
