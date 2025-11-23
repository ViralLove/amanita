"""
Падающие тесты для DI в LocalizationService (п.4.1.2 плана)
Методика: @unit-test-build.mdc, Phase 2.2 — проверяем, что сервис принимает
внешние зависимости (cache/fallback/ipfs) и передаёт их внутрь product/component сервисов.
"""

import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.common.localization_service import LocalizationService  # noqa: E402


class TestLocalizationServiceDI(unittest.TestCase):
    def test_accepts_external_dependencies(self):
        """LocalizationService должен принимать внешние сервисы и прокидывать внутрь"""
        cache_service = MagicMock(name="TranslationCacheService")
        fallback_service = MagicMock(name="FallbackLocalizationService")
        ipfs_service = MagicMock(name="MultilingualIPFSService")

        with patch("services.common.localization_service.ProductLocalizationService") as product_cls, \
                patch("services.common.localization_service.ComponentLocalizationService") as component_cls:
            LocalizationService(
                lang='en',
                cache_service=cache_service,
                fallback_service=fallback_service,
                ipfs_service=ipfs_service,
            )

        product_cls.assert_called_once_with(
            'en',
            cache_service=cache_service,
            fallback_service=fallback_service,
            ipfs_service=ipfs_service,
        )
        component_cls.assert_called_once_with(
            'en',
            cache_service=cache_service,
            fallback_service=fallback_service,
            ipfs_service=ipfs_service,
        )


if __name__ == "__main__":
    unittest.main()

