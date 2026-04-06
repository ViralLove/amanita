"""
Сборка ActivityRegistryService (SSOT графа зависимостей).

FastAPI: api.dependencies.get_activity_registry_service → build_activity_registry_service.
Оффлайн/скрипты: services.service_factory.ServiceFactory.create_activity_registry_service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from services.application.activity.activity_registry_service import ActivityRegistryService

if TYPE_CHECKING:
    from api.services import ActivityStorage
    from services.upload.storage import PrepareResolveService
    from services.wallet_push import PayloadCache, PushSender


def build_activity_registry_service(
    storage: ActivityStorage,
    prepare_resolve: PrepareResolveService,
    push_sender: PushSender,
    payload_cache: PayloadCache,
) -> ActivityRegistryService:
    return ActivityRegistryService(
        storage=storage,
        prepare_resolve=prepare_resolve,
        push_sender=push_sender,
        payload_cache=payload_cache,
    )
