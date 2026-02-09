"""
Reference Data API — моки для GPT (formats, taxonomy, age-groups, languages).

Во всех: ?simulate_error=<code> (Query) → simulate_error_response() вместо нормального flow (таск 9.2).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from api.utils.error_simulation import simulate_error_response
from api.utils.reference_data import AGE_GROUPS, FORMATS, LANGUAGES, TAXONOMY
from api.utils.success_response import build_success_response

router = APIRouter(prefix="/reference", tags=["reference"])

_ALLOWED_REFERENCE = ("500", "503")


def _ensure_simulate(
    simulate_error: Optional[str],
    request: Request,
) -> Optional[JSONResponse]:
    if not simulate_error:
        return None
    if simulate_error not in _ALLOWED_REFERENCE:
        return simulate_error_response("500", request)
    return simulate_error_response(simulate_error, request)


@router.get("/formats")
async def get_formats(
    request: Request,
    simulate_error: Optional[str] = Query(None, description="Simulate error (Error Codes Matrix); 500, 503"),
):
    """Список форматов (Activity Data Model). ?simulate_error=500|503 → simulate_error_response()."""
    r = _ensure_simulate(simulate_error, request)
    if r is not None:
        return r
    return JSONResponse(
        status_code=200,
        content=build_success_response(formats=FORMATS),
    )


@router.get("/taxonomy")
async def get_taxonomy(
    request: Request,
    simulate_error: Optional[str] = Query(None, description="Simulate error (Error Codes Matrix); 500, 503"),
):
    """Таксономия категорий (двухуровневая). ?simulate_error=500|503 → simulate_error_response()."""
    r = _ensure_simulate(simulate_error, request)
    if r is not None:
        return r
    return JSONResponse(
        status_code=200,
        content=build_success_response(taxonomy=TAXONOMY),
    )


@router.get("/age-groups")
async def get_age_groups(
    request: Request,
    simulate_error: Optional[str] = Query(None, description="Simulate error (Error Codes Matrix); 500, 503"),
):
    """Список возрастных групп. ?simulate_error=500|503 → simulate_error_response()."""
    r = _ensure_simulate(simulate_error, request)
    if r is not None:
        return r
    return JSONResponse(
        status_code=200,
        content=build_success_response(age_groups=AGE_GROUPS),
    )


@router.get("/languages")
async def get_languages(
    request: Request,
    simulate_error: Optional[str] = Query(None, description="Simulate error (Error Codes Matrix); 500, 503"),
):
    """Список языков (code, name, native_name). ?simulate_error=500|503 → simulate_error_response()."""
    r = _ensure_simulate(simulate_error, request)
    if r is not None:
        return r
    return JSONResponse(
        status_code=200,
        content=build_success_response(languages=LANGUAGES),
    )
