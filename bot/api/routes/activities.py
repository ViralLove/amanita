"""
Activities API — lifecycle, retrieval и search моки для тестирования GPT.

Эндпоинты: draft, update, submit-review, publish, unpublish; GET /me, GET /{id}; GET/POST /search.
Во всех: ?simulate_error=<code> (Query) → simulate_error_response() вместо нормального flow (таск 9.2).
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from api.dependencies import get_activity_storage, get_payload_cache, get_prepare_resolve_service, get_push_sender
from api.models.activity import ActivityCreateRequest, ActivitySearchRequest
from api.services import ActivityStorage
from api.utils.error_simulation import invalid_state_transition_response, simulate_error_response
from api.utils.sort_params import parse_sort, validate_sort_field_order
from api.utils.success_response import build_pagination, build_success_response

router = APIRouter(prefix="/activities", tags=["activities"])

# ---- Lifecycle (4.1) ----

_ALLOWED_DRAFT = ("401", "422", "403")
_ALLOWED_ME = ("401",)
_ALLOWED_GET_SEARCH = ("400", "422")
_ALLOWED_POST_SEARCH = ("400", "422")
_ALLOWED_GET_ID = ("404", "403")
_ALLOWED_PUT = ("401", "404", "400_invalid_state_transition", "403", "422")
_ALLOWED_SUBMIT = ("401", "404", "400_invalid_state_transition", "422_missing_required", "403")
_ALLOWED_PUBLISH = ("401", "403_not_activated", "404", "400_invalid_state_transition", "403")
_ALLOWED_UNPUBLISH = ("401", "404", "400_invalid_state_transition", "403")


def _ensure_simulate(
    simulate_error: Optional[str],
    request: Request,
    allowed: tuple[str, ...],
) -> Optional[JSONResponse]:
    if not simulate_error:
        return None
    if simulate_error not in allowed:
        return simulate_error_response("500", request)
    return simulate_error_response(simulate_error, request)


@router.post("/draft")
async def create_draft(
    request: Request,
    body: ActivityCreateRequest,
    simulate_error: Optional[str] = Query(None, description="Simulate error (Error Codes Matrix); 401, 422, 403"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="User ID for wallet push (mock: X-User-Id)"),
    storage: ActivityStorage = Depends(get_activity_storage),
    prepare_svc=Depends(get_prepare_resolve_service),
    push_sender=Depends(get_push_sender),
    payload_cache=Depends(get_payload_cache),
):
    """Создать Draft Activity; prepare для wallet, кэш payload, пуш sign_arweave. ?simulate_error=401|422|403 → simulate_error_response()."""
    r = _ensure_simulate(simulate_error, request, _ALLOWED_DRAFT)
    if r is not None:
        return r
    user_id = x_user_id or "mock_user"
    payload = body.model_dump(exclude_none=True)
    activity = storage.create(payload)
    draft_id = activity["activity_id"]
    prepare_result = prepare_svc.prepare_upload_for_draft(draft_id, user_id, payload)
    payload_cache.put(
        prepare_result.upload_id,
        prepare_result.payload_bytes,
        prepare_result.upload_token,
        prepare_result.tags_for_item,
        prepare_result.anchor,
        prepare_result.expires_at,
    )
    push_sender.send_sign_request(user_id, "sign_arweave", prepare_result.upload_id)
    response_data = build_success_response(
        activity=activity,
        upload_id=prepare_result.upload_id,
        upload_token=prepare_result.upload_token,
        expires_at=prepare_result.expires_at.isoformat() if prepare_result.expires_at else None,
    )
    return JSONResponse(status_code=201, content=response_data)


# ---- Retrieval (5.1) ----

@router.get("/me")
async def list_my_activities(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    activity_type: Optional[str] = Query(None),
    owner_id: str = Query("owner_mock", description="Mock owner (auth skipped)"),
    simulate_error: Optional[str] = Query(None, description="Simulate error (Error Codes Matrix); 401"),
    storage: ActivityStorage = Depends(get_activity_storage),
):
    """Список своих Activities. Pagination: page, per_page. Фильтры: status, activity_type. ?simulate_error=401 → simulate_error_response()."""
    r = _ensure_simulate(simulate_error, request, _ALLOWED_ME)
    if r is not None:
        return r
    items, total = storage.list(owner_id=owner_id, status=status, activity_type=activity_type, page=page, per_page=per_page)
    pagination = build_pagination(page, per_page, total)
    return JSONResponse(status_code=200, content=build_success_response(activities=items, pagination=pagination))


# ---- Search (6.1) ----

@router.get("/search")
async def search_activities_get(
    request: Request,
    text: Optional[str] = Query(None, description="Поиск по title, description"),
    activity_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort: Optional[str] = Query(None, description="Сортировка: field или field:order (date, title, created_at; asc, desc)"),
    simulate_error: Optional[str] = Query(None, description="Simulate error (Error Codes Matrix); 400, 422"),
    storage: ActivityStorage = Depends(get_activity_storage),
):
    """Простой поиск. Только Published. sort: field или field:order. ?simulate_error=400|422 → simulate_error_response()."""
    r = _ensure_simulate(simulate_error, request, _ALLOWED_GET_SEARCH)
    if r is not None:
        return r
    sort_field: Optional[str] = None
    sort_order: Optional[str] = None
    if sort:
        try:
            sort_field, sort_order = parse_sort(sort)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    items, total = storage.search(
        text=text,
        activity_type=activity_type,
        page=page,
        per_page=per_page,
        sort_field=sort_field,
        sort_order=sort_order,
    )
    pagination = build_pagination(page, per_page, total)
    return JSONResponse(status_code=200, content=build_success_response(activities=items, pagination=pagination))


@router.post("/search")
async def search_activities_post(
    request: Request,
    body: ActivitySearchRequest,
    simulate_error: Optional[str] = Query(None, description="Simulate error (Error Codes Matrix); 400, 422"),
    storage: ActivityStorage = Depends(get_activity_storage),
):
    """Сложный поиск (JSON body: query, filters, pagination, sort). Только Published. ?simulate_error=400|422 → simulate_error_response()."""
    r = _ensure_simulate(simulate_error, request, _ALLOWED_POST_SEARCH)
    if r is not None:
        return r
    try:
        validate_sort_field_order(body.sort_field, body.sort_order)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    filters = body.filters or {}
    activity_type = filters.get("activity_type") if isinstance(filters.get("activity_type"), str) else None
    order = (body.sort_order or "asc").strip().lower() if body.sort_field else None
    items, total = storage.search(
        text=body.query,
        activity_type=activity_type,
        filters=body.filters,
        page=body.page,
        per_page=body.per_page,
        sort_field=body.sort_field,
        sort_order=order,
    )
    pagination = build_pagination(body.page, body.per_page, total)
    return JSONResponse(status_code=200, content=build_success_response(activities=items, pagination=pagination))


@router.put("/{activity_id}")
async def update_draft(
    request: Request,
    activity_id: str,
    body: dict[str, Any] = Body(...),
    simulate_error: Optional[str] = Query(None, description="Simulate error (Error Codes Matrix); 401,404,400_invalid_state_transition,403,422"),
    storage: ActivityStorage = Depends(get_activity_storage),
):
    """Обновить Draft Activity. Только status == Draft. ?simulate_error=... → simulate_error_response()."""
    r = _ensure_simulate(simulate_error, request, _ALLOWED_PUT)
    if r is not None:
        return r
    existing = storage.get(activity_id)
    if not existing:
        return simulate_error_response("404", request)
    current = existing.get("status", "Draft")
    if current != "Draft":
        return invalid_state_transition_response(current, "Draft", request)
    activity = storage.update(activity_id, body)
    return JSONResponse(status_code=200, content=build_success_response(activity=activity))


@router.post("/{activity_id}/submit-review")
async def submit_review(
    request: Request,
    activity_id: str,
    simulate_error: Optional[str] = Query(None, description="Simulate error (Error Codes Matrix); 401, 404, 400_invalid_state_transition, 422_missing_required, 403"),
    storage: ActivityStorage = Depends(get_activity_storage),
):
    """Draft → SentToReview. ?simulate_error=... → simulate_error_response()."""
    r = _ensure_simulate(simulate_error, request, _ALLOWED_SUBMIT)
    if r is not None:
        return r
    existing = storage.get(activity_id)
    if not existing:
        return simulate_error_response("404", request)
    current = existing.get("status", "Draft")
    if current != "Draft":
        return invalid_state_transition_response(current, "Draft", request)
    try:
        activity = storage.update_status(activity_id, "SentToReview")
    except ValueError:
        return invalid_state_transition_response(current, "Draft", request)
    return JSONResponse(status_code=200, content=build_success_response(activity=activity))


@router.post("/{activity_id}/publish")
async def publish(
    request: Request,
    activity_id: str,
    simulate_error: Optional[str] = Query(None, description="Simulate error (Error Codes Matrix); 401, 403_not_activated, 404, 400_invalid_state_transition, 403"),
    storage: ActivityStorage = Depends(get_activity_storage),
):
    """Approved → Published. ?simulate_error=... → simulate_error_response()."""
    r = _ensure_simulate(simulate_error, request, _ALLOWED_PUBLISH)
    if r is not None:
        return r
    existing = storage.get(activity_id)
    if not existing:
        return simulate_error_response("404", request)
    current = existing.get("status", "Draft")
    if current != "Approved":
        return invalid_state_transition_response(current, "Approved", request)
    try:
        activity = storage.update_status(activity_id, "Published")
    except ValueError:
        return invalid_state_transition_response(current, "Approved", request)
    return JSONResponse(status_code=200, content=build_success_response(activity=activity))


@router.delete("/{activity_id}/unpublish")
async def unpublish(
    request: Request,
    activity_id: str,
    simulate_error: Optional[str] = Query(None, description="Simulate error (Error Codes Matrix); 401, 404, 400_invalid_state_transition, 403"),
    storage: ActivityStorage = Depends(get_activity_storage),
):
    """Published → Draft. ?simulate_error=... → simulate_error_response()."""
    r = _ensure_simulate(simulate_error, request, _ALLOWED_UNPUBLISH)
    if r is not None:
        return r
    existing = storage.get(activity_id)
    if not existing:
        return simulate_error_response("404", request)
    current = existing.get("status", "Draft")
    if current != "Published":
        return invalid_state_transition_response(current, "Published", request)
    try:
        activity = storage.update_status(activity_id, "Draft")
    except ValueError:
        return invalid_state_transition_response(current, "Published", request)
    return JSONResponse(status_code=200, content=build_success_response(activity=activity))


@router.get("/{activity_id}")
async def get_activity(
    request: Request,
    activity_id: str,
    simulate_error: Optional[str] = Query(None, description="Simulate error (Error Codes Matrix); 404, 403"),
    storage: ActivityStorage = Depends(get_activity_storage),
):
    """Получить Activity по ID. Published — public; для моков все «свои». ?simulate_error=404|403 → simulate_error_response()."""
    r = _ensure_simulate(simulate_error, request, _ALLOWED_GET_ID)
    if r is not None:
        return r
    activity = storage.get(activity_id)
    if not activity:
        return simulate_error_response("404", request)
    return JSONResponse(status_code=200, content=build_success_response(activity=activity))
