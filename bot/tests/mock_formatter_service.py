"""
Мок-сервис форматирования для отладки каталога
"""
import logging
from typing import Dict, Any
from services.common.localization import Localization

logger = logging.getLogger(__name__)

class MockFormatterService:
    """Мок-сервис форматирования продуктов"""
    
    def format_product_for_telegram(self, product: Any, loc: Localization) -> Dict[str, str]:
        """
        Форматирует продукт для отправки в Telegram
        
        Args:
            product: Объект продукта
            loc: Объект локализации
            
        Returns:
            Словарь с отформатированными секциями
        """
        try:
            title = getattr(product, 'title', 'Продукт')
            business_id = getattr(product, 'business_id', 'unknown')
            categories = getattr(product, 'categories', [])
            forms = getattr(product, 'forms', [])
            species = getattr(product, 'species', 'Не указано')
            
            # Основная информация
            main_info = f"🍄 <b>{title}</b>\n"
            main_info += f"📋 ID: {business_id}\n"
            
            if categories:
                main_info += f"🏷️ Категории: {', '.join(categories)}\n"
            
            # Состав
            composition = "\n🧬 <b>Состав:</b>\n"
            if hasattr(product, 'organic_components') and product.organic_components:
                for component in product.organic_components:
                    component_id = getattr(component, 'component_id', 'Неизвестно')
                    proportion = getattr(component, 'proportion', 'Не указано')
                    composition += f"• {component_id} ({proportion})\n"
            else:
                composition += "• Состав не указан\n"
            
            # Формы и виды
            details = f"\n📦 <b>Формы:</b> {', '.join(forms) if forms else 'Не указано'}\n"
            details += f"🌿 <b>Вид:</b> {species}\n"
            
            # Цены
            pricing = "\n💰 <b>Цены:</b>\n"
            if hasattr(product, 'prices') and product.prices:
                for price_info in product.prices:
                    # Обрабатываем как вес, так и объем
                    weight = getattr(price_info, 'weight', None)
                    volume = getattr(price_info, 'volume', None)
                    weight_unit = getattr(price_info, 'weight_unit', 'г')
                    volume_unit = getattr(price_info, 'volume_unit', 'мл')
                    price = getattr(price_info, 'price', 'Не указано')
                    currency = getattr(price_info, 'currency', 'EUR')
                    
                    if weight:
                        pricing += f"• {weight} {weight_unit}: {price} {currency}\n"
                    elif volume:
                        pricing += f"• {volume} {volume_unit}: {price} {currency}\n"
                    else:
                        pricing += f"• {price} {currency}\n"
            else:
                pricing += "• Цены не указаны\n"
            
            return {
                'main_info': main_info,
                'composition': composition,
                'pricing': pricing,
                'details': details
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования продукта: {e}")
            # Возвращаем минимальную информацию
            return {
                'main_info': f"🍄 <b>{getattr(product, 'title', 'Продукт')}</b>\n",
                'composition': "\n🧬 <b>Состав:</b> Информация недоступна\n",
                'pricing': "\n💰 <b>Цены:</b> Информация недоступна\n",
                'details': "\n📦 <b>Детали:</b> Информация недоступна\n"
            }
    
    def format_product_main_info_for_telegram(self, product: Any, loc: Localization) -> str:
        """
        Форматирует основную информацию о продукте
        
        Args:
            product: Объект продукта
            loc: Объект локализации
            
        Returns:
            Отформатированная строка
        """
        try:
            title = getattr(product, 'title', 'Продукт')
            business_id = getattr(product, 'business_id', 'unknown')
            categories = getattr(product, 'categories', [])
            
            main_info = f"🍄 <b>{title}</b>\n"
            main_info += f"📋 ID: {business_id}\n"
            
            if categories:
                main_info += f"🏷️ Категории: {', '.join(categories)}\n"
            
            return main_info
            
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования основной информации: {e}")
            return f"🍄 <b>{getattr(product, 'title', 'Продукт')}</b>\n"

# Создаем глобальный экземпляр
mock_formatter_service = MockFormatterService()
