"""
Pydantic модели для продуктов с бизнес-валидацией
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from bot.api.exceptions.validation import (
    InvalidCIDError, 
    InvalidProductFormError, 
    EmptyCategoriesError,
    InvalidBusinessIdError
)

class PriceModel(BaseModel):
    """Модель цены продукта"""
    weight: Optional[str] = Field(None, description="Вес продукта")
    weight_unit: Optional[str] = Field(None, description="Единица измерения веса")
    volume: Optional[str] = Field(None, description="Объем продукта")
    volume_unit: Optional[str] = Field(None, description="Единица измерения объема")
    price: str = Field(..., description="Цена продукта")
    currency: str = Field(default="EUR", description="Валюта цены")
    form: Optional[str] = Field(None, description="Форма продукта для данной цены")

class ProductUploadIn(BaseModel):
    """Модель для входящего продукта с валидацией"""
    id: Union[str, int] = Field(..., description="Уникальный идентификатор продукта (business_id)")
    business_id: Optional[str] = Field(None, description="Бизнес-идентификатор продукта (если отличается от id)")
    title: str = Field(..., min_length=1, description="Название продукта")
    description: Dict[str, Any] = Field(..., description="Структурированное описание продукта")
    description_cid: str = Field(..., description="CID расширенного описания")
    cover_image: str = Field(..., description="CID обложки")
    gallery: List[str] = Field(default_factory=list, description="Массив дополнительных изображений (CID)")
    categories: List[str] = Field(..., description="Список категорий")
    forms: List[str] = Field(..., description="Список форм продукта")
    species: str = Field(..., min_length=1, description="Вид продукта")
    prices: List[PriceModel] = Field(..., min_items=1, description="Массив цен")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные поля")

    @validator('description_cid', 'cover_image')
    def validate_cid_format(cls, v):
        if not v.startswith('Qm'):
            raise InvalidCIDError("CID field", v)
        return v

    @validator('gallery')
    def validate_gallery_cids(cls, v):
        for cid in v:
            if not cid.startswith('Qm'):
                raise InvalidCIDError("gallery", cid)
        return v

    @validator('forms')
    def validate_product_forms(cls, v):
        if not v or len(v) == 0:
            raise InvalidProductFormError("Список форм не может быть пустым")
        valid_forms = ["powder", "tincture", "capsules", "extract", "tea", "oil", "mixed slices", "whole caps", "broken caps", "premium caps", "flower", "chunks", "dried whole", "dried powder", "dried strips"]
        for form in v:
            if form not in valid_forms:
                raise InvalidProductFormError(form)
        return v

    @validator('categories')
    def validate_categories(cls, v):
        if not v or len(v) == 0:
            raise EmptyCategoriesError()
        return v

    @validator('business_id')
    def validate_business_id(cls, v):
        if v is not None and (not isinstance(v, str) or not v.strip()):
            raise InvalidBusinessIdError("Business ID должен быть непустой строкой")
        return v

    def get_business_id(self) -> str:
        """Возвращает business_id или id как fallback"""
        return self.business_id or str(self.id)

    def get_forms_list(self) -> List[str]:
        """Возвращает список форм"""
        return self.forms if self.forms else []

class ProductUploadRequest(BaseModel):
    """Модель для запроса загрузки продуктов"""
    products: List[ProductUploadIn] = Field(..., min_items=1, description="Список продуктов для загрузки")

class ProductUpdateIn(BaseModel):
    """Модель для обновления продукта"""
    title: Optional[str] = Field(None, min_length=1, description="Название продукта")
    description: Optional[Dict[str, Any]] = Field(None, description="Структурированное описание продукта")
    description_cid: Optional[str] = Field(None, description="CID расширенного описания")
    cover_image: Optional[str] = Field(None, description="CID обложки")
    gallery: Optional[List[str]] = Field(None, description="Массив дополнительных изображений (CID)")
    categories: Optional[List[str]] = Field(None, description="Список категорий")
    forms: Optional[List[str]] = Field(None, description="Список форм продукта")
    species: Optional[str] = Field(None, min_length=1, description="Вид продукта")
    prices: Optional[List[PriceModel]] = Field(None, min_items=1, description="Массив цен")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Дополнительные поля")

    @validator('description_cid', 'cover_image')
    def validate_cid_format(cls, v):
        if v is not None and not v.startswith('Qm'):
            raise InvalidCIDError("CID field", v)
        return v

    @validator('gallery')
    def validate_gallery_cids(cls, v):
        if v is not None:
            for cid in v:
                if not cid.startswith('Qm'):
                    raise InvalidCIDError("gallery", cid)
        return v

    @validator('forms')
    def validate_product_forms(cls, v):
        if v is not None:
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

class ProductStatusUpdate(BaseModel):
    """Модель для обновления статуса продукта"""
    status: int = Field(..., ge=0, le=1, description="Статус продукта (0 - неактивен, 1 - активен)")

class ProductResponse(BaseModel):
    """Модель ответа для продукта"""
    id: str = Field(..., description="Бизнес-идентификатор продукта")
    blockchain_id: Optional[int] = Field(None, description="ID продукта в блокчейне")
    tx_hash: Optional[str] = Field(None, description="Хеш транзакции создания")
    metadata_cid: Optional[str] = Field(None, description="CID метаданных в IPFS")
    status: str = Field(..., description="Статус операции")
    error: Optional[str] = Field(None, description="Описание ошибки, если есть")

class ProductsUploadResponse(BaseModel):
    """Модель ответа для загрузки продуктов"""
    results: List[ProductResponse] = Field(..., description="Результаты загрузки продуктов")
