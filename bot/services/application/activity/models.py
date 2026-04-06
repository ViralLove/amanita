"""Типы результата для вертикали Activity (ASG-3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Optional

ActivityMutationError = Literal["not_found", "invalid_state"]


@dataclass
class ActivityCreateDraftResult:
    """Результат оркестрации POST /activities/draft (storage + prepare + cache + push)."""

    activity: dict[str, Any]
    upload_id: str
    upload_token: str
    expires_at: Optional[datetime]


@dataclass
class ActivityMutationOutcome:
    """
    Итог изменяющей операции жизненного цикла (update / submit-review / publish / unpublish).

    Паттерн «либо успех с сущностью, либо ошибка с кодом» (упрощённый Result / railway),
    без зависимости application-слоя от FastAPI.

    При маппинге в HTTP для not_found часто вызывают ``simulate_error_response`` из
    ``api.utils.error_simulation`` — это имя историческое: та же функция формирует каноничное
    тело 404 по Error Codes Matrix и для *реальных* отсутствующих сущностей, не только для
    ``?simulate_error=`` в тестах GPT.
    """

    activity: Optional[dict[str, Any]] = None
    error: Optional[ActivityMutationError] = None
    current_state: Optional[str] = None
    required_state: Optional[str] = None
