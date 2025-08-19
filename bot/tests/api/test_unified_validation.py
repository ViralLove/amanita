"""
Тесты для унифицированной системы валидации и обработки ошибок
"""
import pytest
from unittest.mock import Mock, patch
from fastapi import Request
from fastapi.responses import JSONResponse

from bot.api.error_handlers import product_validation_exception_handler
from bot.api.models.errors import ErrorDetail, UnifiedValidationErrorResponse
from bot.api.exceptions.validation import UnifiedValidationError, ProductValidationError
from bot.api.models.common import get_current_timestamp, Timestamp


class TestUnifiedValidationErrorHandler:
    """Тесты для обработчика UnifiedValidationError"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.mock_request = Mock(spec=Request)
        self.mock_request.url.path = "/test/path"
    
    @pytest.mark.asyncio
    async def test_unified_validation_error_handler(self):
        """Тест обработки UnifiedValidationError"""
        # Создаем тестовое исключение
        test_error = UnifiedValidationError(
            message="Тестовая ошибка валидации",
            field="test_field",
            value="invalid_value",
            error_code="TEST_ERROR"
        )
        
        # Вызываем обработчик
        response = await product_validation_exception_handler(self.mock_request, test_error)
        
        # Проверяем, что это JSONResponse
        assert isinstance(response, JSONResponse)
        assert response.status_code == 422
        
        # Проверяем структуру ответа
        content = response.body.decode()
        assert "unified_validation_error" in content
        assert "Тестовая ошибка валидации" in content
        assert "test_field" in content
        assert "TEST_ERROR" in content
    
    @pytest.mark.asyncio
    async def test_unified_validation_error_with_details(self):
        """Тест обработки UnifiedValidationError с деталями"""
        test_error = UnifiedValidationError(
            message="Ошибка валидации CID",
            field="description_cid",
            value="invalid_cid",
            error_code="INVALID_CID_FORMAT"
        )
        
        response = await product_validation_exception_handler(self.mock_request, test_error)
        content = response.body.decode()
        
        # Проверяем детали ошибки
        assert "description_cid" in content
        assert "invalid_cid" in content
        assert "INVALID_CID_FORMAT" in content
    
    @pytest.mark.asyncio
    async def test_product_validation_error_fallback(self):
        """Тест fallback на ProductValidationError"""
        test_error = ProductValidationError(
            message="Ошибка продукта",
            field="product_field",
            value="invalid_value"
        )
        
        response = await product_validation_exception_handler(self.mock_request, test_error)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 422
        content = response.body.decode()
        assert "validation_error" in content
        assert "Ошибка продукта" in content
    
    @pytest.mark.asyncio
    async def test_other_exception_passthrough(self):
        """Тест передачи других исключений"""
        test_error = ValueError("Неожиданная ошибка")
        
        with pytest.raises(ValueError):
            await product_validation_exception_handler(self.mock_request, test_error)


class TestErrorDetailStructure:
    """Тесты для структуры ErrorDetail"""
    
    def test_error_detail_with_new_fields(self):
        """Тест ErrorDetail с новыми полями"""
        error_detail = ErrorDetail(
            field="test_field",
            message="Тестовая ошибка",
            value="invalid_value",
            error_code="TEST_ERROR",
            suggestions=["Предложение 1", "Предложение 2"]
        )
        
        assert error_detail.field == "test_field"
        assert error_detail.message == "Тестовая ошибка"
        assert error_detail.value == "invalid_value"
        assert error_detail.error_code == "TEST_ERROR"
        assert error_detail.suggestions == ["Предложение 1", "Предложение 2"]
    
    def test_error_detail_minimal(self):
        """Тест ErrorDetail с минимальными полями"""
        error_detail = ErrorDetail(
            message="Минимальная ошибка"
        )
        
        assert error_detail.message == "Минимальная ошибка"
        assert error_detail.field is None
        assert error_detail.value is None
        assert error_detail.error_code is None
        assert error_detail.suggestions is None
    
    def test_error_detail_serialization(self):
        """Тест сериализации ErrorDetail"""
        error_detail = ErrorDetail(
            field="serialization_test",
            message="Тест сериализации",
            value={"nested": "value"},
            error_code="SERIALIZATION_TEST",
            suggestions=["Сериализация работает"]
        )
        
        # Проверяем, что модель может быть сериализована
        serialized = error_detail.model_dump()
        
        assert serialized["field"] == "serialization_test"
        assert serialized["message"] == "Тест сериализации"
        assert serialized["value"] == {"nested": "value"}
        assert serialized["error_code"] == "SERIALIZATION_TEST"
        assert serialized["suggestions"] == ["Сериализация работает"]


class TestUnifiedValidationErrorResponse:
    """Тесты для UnifiedValidationErrorResponse"""
    
    def test_unified_validation_error_response_creation(self):
        """Тест создания UnifiedValidationErrorResponse"""
        response = UnifiedValidationErrorResponse(
            success=False,
            message="Ошибка валидации данных",
            details=[
                ErrorDetail(
                    field="test_field",
                    message="Тестовая ошибка",
                    error_code="TEST_ERROR"
                )
            ],
            validation_source="api",
            timestamp=Timestamp(get_current_timestamp()),
            path="/test/path"
        )
        
        assert response.success is False
        assert response.error == "unified_validation_error"
        assert response.message == "Ошибка валидации данных"
        assert response.validation_source == "api"
        assert len(response.details) == 1
        assert response.details[0].field == "test_field"
    
    def test_unified_validation_error_response_serialization(self):
        """Тест сериализации UnifiedValidationErrorResponse"""
        response = UnifiedValidationErrorResponse(
            success=False,
            message="Тест сериализации",
            details=[
                ErrorDetail(
                    field="serialization_test",
                    message="Тест",
                    error_code="SERIALIZATION_TEST"
                )
            ],
            validation_source="service",
            timestamp=Timestamp(get_current_timestamp()),
            path="/test/path"
        )
        
        serialized = response.model_dump()
        
        assert serialized["success"] is False
        assert serialized["error"] == "unified_validation_error"
        assert serialized["validation_source"] == "service"
        assert len(serialized["details"]) == 1
        assert serialized["details"][0]["field"] == "serialization_test"


class TestValidationErrorIntegration:
    """Интеграционные тесты для системы валидации"""
    
    @pytest.mark.asyncio
    async def test_cid_validation_error_integration(self):
        """Тест интеграции ошибки валидации CID"""
        from bot.validation.exceptions import CIDValidationError
        
        test_error = CIDValidationError(
            message="Некорректный формат CID",
            cid_value="invalid_cid",
            error_code="INVALID_CID_FORMAT"
        )
        
        # Преобразуем в UnifiedValidationError
        unified_error = UnifiedValidationError(
            message=test_error.message,
            field=test_error.field_name,
            value=test_error.field_value,
            error_code=test_error.error_code
        )
        
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test/path"
        
        response = await product_validation_exception_handler(mock_request, unified_error)
        
        assert response.status_code == 422
        content = response.body.decode()
        assert "INVALID_CID_FORMAT" in content
        assert "invalid_cid" in content
    
    @pytest.mark.asyncio
    async def test_proportion_validation_error_integration(self):
        """Тест интеграции ошибки валидации пропорции"""
        from bot.validation.exceptions import ProportionValidationError
        
        test_error = ProportionValidationError(
            message="Некорректный формат пропорции",
            proportion_value="invalid_proportion",
            error_code="INVALID_PROPORTION_FORMAT"
        )
        
        unified_error = UnifiedValidationError(
            message=test_error.message,
            field=test_error.field_name,
            value=test_error.field_value,
            error_code=test_error.error_code
        )
        
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/test/path"
        
        response = await product_validation_exception_handler(mock_request, unified_error)
        
        assert response.status_code == 422
        content = response.body.decode()
        assert "INVALID_PROPORTION_FORMAT" in content
        assert "invalid_proportion" in content
