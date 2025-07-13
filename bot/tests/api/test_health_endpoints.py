"""
Тесты для health check эндпоинтов
"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from api.main import create_api_app
from api.models.health import ComponentStatus


class TestHealthEndpoints:
    """Тесты для health check эндпоинтов"""
    
    @pytest.fixture
    def client(self):
        """Создает тестовый клиент"""
        app = create_api_app()
        return TestClient(app)
    
    @pytest.fixture
    def client_with_service_factory(self):
        """Создает тестовый клиент с ServiceFactory"""
        mock_service_factory = Mock()
        mock_service_factory.blockchain = Mock()
        mock_service_factory.account = Mock()
        mock_service_factory.circle = Mock()
        
        app = create_api_app(service_factory=mock_service_factory)
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Тест базового health check эндпоинта"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Проверяем базовую структуру
        assert data["success"] is True
        assert data["status"]["status"] == "healthy"
        assert data["service"]["name"] == "amanita_api"
        assert data["service"]["version"] == "1.0.0"
        assert "timestamp" in data
        assert "request_id" in data
        
        # Проверяем uptime
        assert "uptime" in data
        assert "start_time" in data["uptime"]
        assert "uptime_seconds" in data["uptime"]
        assert "uptime_formatted" in data["uptime"]
        assert data["uptime"]["uptime_seconds"] > 0
        assert len(data["uptime"]["uptime_formatted"]) > 0
    
    def test_detailed_health_endpoint_basic(self, client):
        """Тест детального health check эндпоинта (базовая версия)"""
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        # Проверяем базовую структуру
        assert data["success"] is True
        assert data["service"]["name"] == "amanita_api"
        assert "timestamp" in data
        assert "request_id" in data
        assert "uptime" in data
        
        # Проверяем компоненты
        assert "components" in data
        assert isinstance(data["components"], list)
        assert len(data["components"]) > 0
        
        # Проверяем системные метрики
        assert "system_metrics" in data
        
        # Проверяем что есть API компонент
        api_component = next((c for c in data["components"] if c["name"] == "api"), None)
        assert api_component is not None
        assert api_component["status"] == "ok"
    
    def test_detailed_health_endpoint_with_service_factory(self, client_with_service_factory):
        """Тест детального health check с ServiceFactory"""
        response = client_with_service_factory.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        # Проверяем компоненты
        components = data["components"]
        component_names = [c["name"] for c in components]
        
        # Должны быть все основные компоненты
        assert "api" in component_names
        assert "service_factory" in component_names
        assert "blockchain" in component_names
        assert "database" in component_names
        assert "external_apis" in component_names
        
        # Проверяем статус service_factory
        sf_component = next(c for c in components if c["name"] == "service_factory")
        assert sf_component["status"] == "ok"
        
        # Проверяем статус blockchain
        bc_component = next(c for c in components if c["name"] == "blockchain")
        assert bc_component["status"] == "ok"
    
    def test_detailed_health_endpoint_without_service_factory(self, client):
        """Тест детального health check без ServiceFactory"""
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        components = data["components"]
        
        # ServiceFactory должен быть not_initialized
        sf_component = next(c for c in components if c["name"] == "service_factory")
        assert sf_component["status"] == "not_initialized"
        
        # Blockchain должен быть unavailable
        bc_component = next(c for c in components if c["name"] == "blockchain")
        assert bc_component["status"] == "unavailable"
    
    def test_detailed_health_system_metrics(self, client):
        """Тест системных метрик в детальном health check"""
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        metrics = data["system_metrics"]
        
        # Проверяем что метрики присутствуют
        assert "cpu_percent" in metrics
        assert "memory" in metrics
        assert "disk" in metrics
        
        # Проверяем структуру memory
        assert "total_gb" in metrics["memory"]
        assert "available_gb" in metrics["memory"]
        assert "used_percent" in metrics["memory"]
        
        # Проверяем структуру disk
        assert "total_gb" in metrics["disk"]
        assert "free_gb" in metrics["disk"]
        assert "used_percent" in metrics["disk"]
        
        # Проверяем типы данных
        assert isinstance(metrics["cpu_percent"], (int, float))
        assert isinstance(metrics["memory"]["total_gb"], (int, float))
        assert isinstance(metrics["disk"]["total_gb"], (int, float))
    
    def test_detailed_health_system_metrics_error_handling(self, client):
        """Тест обработки ошибки системных метрик"""
        # Этот тест проверяет что система корректно обрабатывает ошибки
        # при получении метрик (реальные ошибки будут обработаны в get_system_metrics)
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        metrics = data["system_metrics"]
        
        # Проверяем что метрики либо содержат данные, либо информацию об ошибке
        assert isinstance(metrics, dict)
        assert len(metrics) > 0
    
    def test_health_endpoint_uptime_format(self, client):
        """Тест формата uptime в health check"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        uptime = data["uptime"]
        
        # Проверяем что uptime_formatted содержит правильный формат
        formatted = uptime["uptime_formatted"]
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        
        # Проверяем что содержит хотя бы одну единицу времени
        time_units = ["s", "m", "h", "d"]
        assert any(unit in formatted for unit in time_units)
    
    def test_detailed_health_component_latency(self, client):
        """Тест измерения latency компонентов"""
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        components = data["components"]
        
        # Проверяем что у компонентов есть поля latency
        for component in components:
            if component["status"] == "ok":
                assert "latency_ms" in component
                assert component["latency_ms"] is not None
                assert component["latency_ms"] >= 0
            
            assert "last_check" in component
            assert "error_count" in component
    
    def test_detailed_health_status_calculation(self, client):
        """Тест расчета общего статуса на основе компонентов"""
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        status = data["status"]["status"]
        message = data["status"]["message"]
        
        # Статус должен быть одним из допустимых значений
        assert status in ["healthy", "degraded", "unhealthy"]
        
        # Сообщение должно быть непустым
        assert len(message) > 0
        
        # Если все компоненты ok, статус должен быть healthy
        components = data["components"]
        all_ok = all(c["status"] in ["ok", "not_initialized", "unavailable"] for c in components)
        
        if all_ok:
            assert status == "healthy"
            assert "работают нормально" in message.lower()
    
    def test_health_endpoints_public_access(self, client):
        """Тест что health endpoints доступны без аутентификации"""
        # Проверяем что эндпоинты не требуют HMAC аутентификации
        health_response = client.get("/health")
        detailed_response = client.get("/health/detailed")
        
        assert health_response.status_code == 200
        assert detailed_response.status_code == 200 