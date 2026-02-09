"""
Парсинг и валидация параметра sort (field, order) для search.

Поддерживаемые поля: date, title, created_at. Порядок: asc, desc.
Формат: "field" или "field:order"; при отсутствии order — asc.
"""

from __future__ import annotations

ALLOWED_SORT_FIELDS = frozenset({"date", "title", "created_at"})
ALLOWED_SORT_ORDERS = frozenset({"asc", "desc"})


def parse_sort(sort: str) -> tuple[str, str]:
    """
    Парсит "field" или "field:order" в (field, order).

    Raises:
        ValueError: неизвестное поле или порядок.
    """
    sort = (sort or "").strip()
    if not sort:
        raise ValueError("sort is empty")
    parts = sort.split(":", 1)
    field = (parts[0] or "").strip().lower()
    order = (parts[1] or "asc").strip().lower() if len(parts) > 1 else "asc"
    if field not in ALLOWED_SORT_FIELDS:
        raise ValueError(f"sort field must be one of {sorted(ALLOWED_SORT_FIELDS)}")
    if order not in ALLOWED_SORT_ORDERS:
        raise ValueError(f"sort order must be one of {sorted(ALLOWED_SORT_ORDERS)}")
    return field, order


def validate_sort_field_order(field: str | None, order: str | None) -> None:
    """
    Проверяет field и order. Если оба None — ок.
    Если задан хотя бы один — оба должны быть валидны; при отсутствии order используется asc.

    Raises:
        ValueError: невалидное поле или порядок.
    """
    if field is None and order is None:
        return
    f = (field or "").strip().lower()
    o = (order or "asc").strip().lower()
    if not f:
        raise ValueError("sort_field is required when sort_order is provided")
    if f not in ALLOWED_SORT_FIELDS:
        raise ValueError(f"sort_field must be one of {sorted(ALLOWED_SORT_FIELDS)}")
    if o not in ALLOWED_SORT_ORDERS:
        raise ValueError(f"sort_order must be one of {sorted(ALLOWED_SORT_ORDERS)}")
