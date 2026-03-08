"""
Success response builder для Activities API mocks.

Единообразный формат {success, request_id, timestamp, activity?, activities?, pagination?}.
Pagination по таску 5.2: page, per_page, total, total_pages.
"""

from __future__ import annotations

import math
from typing import Any, Optional

from api.models.common import RequestId, Timestamp, generate_request_id, get_current_timestamp


def build_pagination(page: int, per_page: int, total: int) -> dict[str, Any]:
    """
    Объект pagination по контракту 5.2: {page, per_page, total, total_pages}.
    Для list/search ответов.
    """
    total_pages = max(1, math.ceil(total / per_page)) if per_page > 0 else 1
    return {"page": page, "per_page": per_page, "total": total, "total_pages": total_pages}


def build_success_response(
    *,
    activity: Optional[dict[str, Any]] = None,
    activities: Optional[list[dict[str, Any]]] = None,
    pagination: Optional[dict[str, Any]] = None,
    formats: Optional[list[dict[str, Any]]] = None,
    taxonomy: Optional[dict[str, Any]] = None,
    age_groups: Optional[list[dict[str, Any]]] = None,
    languages: Optional[list[dict[str, Any]]] = None,
    upload_id: Optional[str] = None,
    upload_token: Optional[str] = None,
    expires_at: Optional[str] = None,
) -> dict[str, Any]:
    """
    Собирает success-ответ по контракту API Reference.

    activity/activities/pagination — для activities; formats/taxonomy/age_groups/languages — для reference.
    upload_id/upload_token/expires_at — для draft (W2, поток подписи в wallet).
    """
    out: dict[str, Any] = {
        "success": True,
        "request_id": RequestId(generate_request_id()),
        "timestamp": Timestamp(get_current_timestamp()),
    }
    if activity is not None:
        out["activity"] = activity
    if activities is not None:
        out["activities"] = activities
    if pagination is not None:
        out["pagination"] = pagination
    if formats is not None:
        out["formats"] = formats
    if taxonomy is not None:
        out["taxonomy"] = taxonomy
    if age_groups is not None:
        out["age_groups"] = age_groups
    if languages is not None:
        out["languages"] = languages
    if upload_id is not None:
        out["upload_id"] = upload_id
    if upload_token is not None:
        out["upload_token"] = upload_token
    if expires_at is not None:
        out["expires_at"] = expires_at
    return out
