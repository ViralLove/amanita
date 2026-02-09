"""
Модели для Activities API (моки).

Минимальный набор для lifecycle endpoints; полная схема — по Activity Data Model.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ActivityCreateRequest(BaseModel):
    """Тело POST /activities/draft. Минимум для Draft: activity_type, title, short_summary или full_description."""

    activity_type: Literal["event", "service"] = Field(..., description="Тип активности")
    title: str = Field(..., min_length=1, description="Название")
    short_summary: Optional[str] = Field(None, description="Краткое описание")
    full_description: Optional[str] = Field(None, description="Полное описание")

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def at_least_one_description(self) -> "ActivityCreateRequest":
        if not self.short_summary and not self.full_description:
            raise ValueError("At least one of short_summary or full_description is required")
        return self


class ActivitySearchRequest(BaseModel):
    """Тело POST /activities/search. query, filters, pagination, sort."""

    query: Optional[str] = Field(None, description="Текст поиска (title, description)")
    filters: Optional[dict[str, Any]] = Field(None, description="Фильтры, напр. activity_type")
    page: int = Field(1, ge=1, description="Страница")
    per_page: int = Field(20, ge=1, le=100, description="Размер страницы")
    sort_field: Optional[str] = Field(None, description="Поле сортировки (напр. title)")
    sort_order: Optional[str] = Field(None, description="Порядок: asc, desc")

    model_config = ConfigDict(extra="allow")
