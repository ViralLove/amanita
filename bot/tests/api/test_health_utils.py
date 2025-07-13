"""
Тесты для утилит health check
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from api.utils.health_utils import (
    format_uptime, calculate_uptime, get_system_metrics,
    check_component_latency, check_api_component,
    check_service_factory_component, check_blockchain_component
)
from api.models.health import ComponentStatus


class TestFormatUptime:
    """Тесты для форматирования uptime"""
    
    def test_seconds_only(self):
        """Тест для времени менее минуты"""
        assert format_uptime(30) == "30s"
        assert format_uptime(59.9) == "59s"
    
    def test_minutes_and_seconds(self):
        """Тест для времени в минутах"""
        assert format_uptime(90) == "1m 30s"
        assert format_uptime(3599) == "59m 59s"
    
    def test_hours_minutes_seconds(self):
        """Тест для времени в часах"""
        assert format_uptime(3661) == "1h 1m 1s"
        assert format_uptime(86399) == "23h 59m 59s"
    
    def test_days_hours_minutes_seconds(self):
        """Тест для времени в днях"""
        assert format_uptime(90061) == "1d 1h 1m 1s"
        assert format_uptime(172799) == "1d 23h 59m 59s"


class TestCalculateUptime:
    """Тесты для вычисления uptime"""
    
    def test_calculate_uptime(self):
        """Тест вычисления uptime"""
        start_time = datetime.now() - timedelta(hours=2, minutes=30, seconds=45)
        uptime = calculate_uptime(start_time)
        
        assert uptime.start_time == start_time
        assert uptime.uptime_seconds > 0
        assert "2h 30m" in uptime.uptime_formatted
        assert uptime.uptime_seconds >= 9000  # 2.5 часа в секундах


class TestGetSystemMetrics:
    """Тесты для получения системных метрик"""
    
    @patch('api.utils.health_utils.psutil')
    def test_get_system_metrics_success(self, mock_psutil):
        """Тест успешного получения системных метрик"""
        # Мокаем psutil
        mock_psutil.cpu_percent.return_value = 25.5
        mock_psutil.virtual_memory.return_value = Mock(
            total=8589934592,  # 8GB
            available=4294967296,  # 4GB
            percent=50.0
        )
        mock_psutil.disk_usage.return_value = Mock(
            total=107374182400,  # 100GB
            free=53687091200,  # 50GB
            used=53687091200  # 50GB
        )
        
        metrics = get_system_metrics()
        
        assert "cpu_percent" in metrics
        assert "memory" in metrics
        assert "disk" in metrics
        assert metrics["cpu_percent"] == 25.5
        assert metrics["memory"]["total_gb"] == 8.0
        assert metrics["memory"]["available_gb"] == 4.0
        assert metrics["memory"]["used_percent"] == 50.0
        assert metrics["disk"]["total_gb"] == 100.0
        assert metrics["disk"]["free_gb"] == 50.0
        assert metrics["disk"]["used_percent"] == 50.0
    
    @patch('api.utils.health_utils.psutil')
    def test_get_system_metrics_error(self, mock_psutil):
        """Тест обработки ошибки при получении метрик"""
        mock_psutil.cpu_percent.side_effect = Exception("Test error")
        
        metrics = get_system_metrics()
        
        assert "error" in metrics
        assert "Test error" in metrics["error"]


class TestCheckComponentLatency:
    """Тесты для проверки компонентов с измерением latency"""
    
    @pytest.mark.asyncio
    async def test_check_component_success(self):
        """Тест успешной проверки компонента"""
        async def mock_check():
            await asyncio.sleep(0.1)
            return {"status": "ok"}
        
        component = await check_component_latency(mock_check, "test_component")
        
        assert component.name == "test_component"
        assert component.status == ComponentStatus.OK
        assert component.latency_ms is not None
        assert component.latency_ms > 0
        assert component.error_count == 0
        assert component.last_error is None
        assert component.details == {"status": "ok"}
    
    @pytest.mark.asyncio
    async def test_check_component_timeout(self):
        """Тест таймаута компонента"""
        async def mock_check():
            await asyncio.sleep(1.0)  # Дольше таймаута
            return {"status": "ok"}
        
        component = await check_component_latency(mock_check, "test_component", timeout=0.1)
        
        assert component.name == "test_component"
        assert component.status == ComponentStatus.ERROR
        assert component.latency_ms is None
        assert component.error_count == 1
        assert component.last_error == "Timeout"
        assert component.details["timeout_seconds"] == 0.1
    
    @pytest.mark.asyncio
    async def test_check_component_exception(self):
        """Тест исключения в компоненте"""
        async def mock_check():
            raise Exception("Test error")
        
        component = await check_component_latency(mock_check, "test_component")
        
        assert component.name == "test_component"
        assert component.status == ComponentStatus.ERROR
        assert component.latency_ms is None
        assert component.error_count == 1
        assert component.last_error == "Test error"
        assert component.details["error_type"] == "Exception"


class TestComponentChecks:
    """Тесты для проверки конкретных компонентов"""
    
    @pytest.mark.asyncio
    async def test_check_api_component(self):
        """Тест проверки API компонента"""
        result = await check_api_component()
        
        assert result["status"] == "operational"
        assert result["endpoints_available"] is True
    
    @pytest.mark.asyncio
    async def test_check_service_factory_component_success(self):
        """Тест успешной проверки ServiceFactory"""
        mock_service_factory = Mock()
        mock_service_factory.blockchain = Mock()
        mock_service_factory.account = Mock()
        mock_service_factory.circle = Mock()
        
        result = await check_service_factory_component(mock_service_factory)
        
        assert result["status"] == "operational"
        assert "blockchain" in result["available_services"]
        assert "account" in result["available_services"]
        assert "circle" in result["available_services"]
        assert result["total_services"] == 3
    
    @pytest.mark.asyncio
    async def test_check_service_factory_component_none(self):
        """Тест проверки ServiceFactory когда он None"""
        with pytest.raises(Exception, match="ServiceFactory не инициализирован"):
            await check_service_factory_component(None)
    
    @pytest.mark.asyncio
    async def test_check_blockchain_component_success(self):
        """Тест успешной проверки блокчейн компонента"""
        mock_service_factory = Mock()
        mock_service_factory.blockchain = Mock()
        
        result = await check_blockchain_component(mock_service_factory)
        
        assert result["status"] == "operational"
        assert result["network"] == "ethereum"
        assert result["connection"] == "active"
    
    @pytest.mark.asyncio
    async def test_check_blockchain_component_no_service_factory(self):
        """Тест проверки блокчейн компонента без ServiceFactory"""
        with pytest.raises(Exception, match="Blockchain service недоступен"):
            await check_blockchain_component(None)
    
    @pytest.mark.asyncio
    async def test_check_blockchain_component_no_blockchain(self):
        """Тест проверки блокчейн компонента без blockchain сервиса"""
        mock_service_factory = Mock()
        del mock_service_factory.blockchain
        
        with pytest.raises(Exception, match="Blockchain service недоступен"):
            await check_blockchain_component(mock_service_factory) 