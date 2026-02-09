"""
Механизм симуляции ошибок для Activities API mocks.

Используется в эндпоинтах через ?simulate_error=<code> для тестирования
GPT error handling (api-orchestrator Section 18.2, Error Codes Matrix).
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from api.models.common import RequestId, Timestamp, generate_request_id, get_current_timestamp
from api.models.errors import (
    ErrorDetail,
    AuthenticationErrorResponse,
    AuthorizationErrorResponse,
    NotFoundErrorResponse,
    ValidationErrorResponse,
    InvalidStateTransitionErrorResponse,
    NotActivatedErrorResponse,
    DuplicateDetectedErrorResponse,
    InternalServerErrorResponse,
    ServiceUnavailableErrorResponse,
    RateLimitErrorResponse,
)

_DEFAULT_RETRY_AFTER = 60


def _rid() -> RequestId:
    return RequestId(generate_request_id())


def _ts() -> Timestamp:
    return Timestamp(get_current_timestamp())


def _path(request: Request) -> str:
    return str(request.url.path)


def simulate_error_response(error_code: str, request: Request) -> JSONResponse:
    """
    Симуляция ошибок для тестирования GPT (таск 9.1, 9.3; Error Codes Matrix).

    Принимает error_code и request; возвращает JSONResponse с ErrorResponse и нужным status_code.
    Error responses (9.3): 401 authentication_error, 403 forbidden/not_activated, 404 not_found,
    422 validation_error/missing_required_fields, 400 invalid_state_transition (details: current_state,
    required_state), 409 duplicate_detected, 500 server_error, 503 backend_unavailable,
    429 rate_limit_exceeded (Retry-After header). Дополнительно 400 (bad request, search).
    Неизвестный код → 500, error="unknown_error".
    """
    rid, ts, path = _rid(), _ts(), _path(request)

    error_map: dict[str, tuple[int, AuthenticationErrorResponse | AuthorizationErrorResponse | NotFoundErrorResponse | ValidationErrorResponse | InvalidStateTransitionErrorResponse | NotActivatedErrorResponse | DuplicateDetectedErrorResponse | InternalServerErrorResponse | ServiceUnavailableErrorResponse | RateLimitErrorResponse]] = {
        "401": (
            401,
            AuthenticationErrorResponse(
                message="Token expired or invalid",
                request_id=rid,
                timestamp=ts,
                path=path,
            ),
        ),
        "403": (
            403,
            AuthorizationErrorResponse(
                error="forbidden",
                message="Permission denied",
                request_id=rid,
                timestamp=ts,
                path=path,
            ),
        ),
        "403_not_activated": (
            403,
            NotActivatedErrorResponse(
                message="Account not activated. Activation required to publish activities.",
                request_id=rid,
                timestamp=ts,
                path=path,
            ),
        ),
        "404": (
            404,
            NotFoundErrorResponse(
                error="not_found",
                message="Activity not found",
                request_id=rid,
                timestamp=ts,
                path=path,
            ),
        ),
        "400": (
            400,
            ValidationErrorResponse(
                error="bad_request",
                message="Bad request",
                request_id=rid,
                timestamp=ts,
                path=path,
            ),
        ),
        "422": (
            422,
            ValidationErrorResponse(
                error="validation_error",
                message="Validation failed",
                details=[
                    ErrorDetail(field="title", message="Field is required"),
                    ErrorDetail(field="event_timing.date", message="Invalid date format"),
                ],
                request_id=rid,
                timestamp=ts,
                path=path,
            ),
        ),
        "422_missing_required": (
            422,
            ValidationErrorResponse(
                error="missing_required_fields",
                message="Activity does not meet minimum completeness requirements",
                details=[
                    ErrorDetail(field="event_timing.date", message="Event date is required for review"),
                    ErrorDetail(field="location_info.city", message="Location city is required for review"),
                ],
                request_id=rid,
                timestamp=ts,
                path=path,
            ),
        ),
        "400_invalid_state_transition": (
            400,
            InvalidStateTransitionErrorResponse(
                message="Cannot transition from Draft to Published",
                details=[
                    ErrorDetail(
                        field="status",
                        message="Current state: Draft. Required state: Approved",
                        current_state="Draft",
                        required_state="Approved",
                    ),
                ],
                request_id=rid,
                timestamp=ts,
                path=path,
            ),
        ),
        "409": (
            409,
            DuplicateDetectedErrorResponse(
                message="A similar activity already exists",
                request_id=rid,
                timestamp=ts,
                path=path,
            ),
        ),
        "500": (
            500,
            InternalServerErrorResponse(
                error="server_error",
                message="Internal server error",
                request_id=rid,
                timestamp=ts,
                path=path,
            ),
        ),
        "503": (
            503,
            ServiceUnavailableErrorResponse(
                error="backend_unavailable",
                message="Service unavailable",
                request_id=rid,
                timestamp=ts,
                path=path,
            ),
        ),
        "429": (
            429,
            RateLimitErrorResponse(
                message="Rate limit exceeded",
                retry_after=_DEFAULT_RETRY_AFTER,
                request_id=rid,
                timestamp=ts,
                path=path,
            ),
        ),
    }

    if error_code not in error_map:
        status_code = 500
        body = InternalServerErrorResponse(
            error="unknown_error",
            message=f"Unknown error code: {error_code}",
            request_id=rid,
            timestamp=ts,
            path=path,
        )
    else:
        status_code, body = error_map[error_code]

    content = body.model_dump()
    resp = JSONResponse(status_code=status_code, content=content)

    if status_code == 429 and getattr(body, "retry_after", None) is not None:
        resp.headers["Retry-After"] = str(body.retry_after)

    return resp


def invalid_state_transition_response(
    current_state: str,
    required_state: str,
    request: Request,
) -> JSONResponse:
    """
    Возвращает 400 с invalid_state_transition для реальных недопустимых переходов
    в handlers (не через simulate_error).
    """
    rid, ts, path = _rid(), _ts(), _path(request)
    msg = f"Current state: {current_state}. Required state: {required_state}."
    body = InvalidStateTransitionErrorResponse(
        message=msg,
        details=[
            ErrorDetail(
                field="status",
                message=msg,
                current_state=current_state,
                required_state=required_state,
            ),
        ],
        request_id=rid,
        timestamp=ts,
        path=path,
    )
    return JSONResponse(status_code=400, content=body.model_dump())
