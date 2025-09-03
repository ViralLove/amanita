from .section_types import SectionTypes

class SectionTracker:
    """Отслеживание выведенных секций для предотвращения дублирования"""
    
    def __init__(self):
        self.outputted_sections = set()
        self.section_headers = {
            SectionTypes.SHAMANIC: '🧙‍♂️ <b>Шаманская перспектива</b>',
            SectionTypes.WARNINGS: '⚠️ <b>Предупреждения</b>',
            SectionTypes.EFFECTS: '✨ <b>Эффекты</b>',
            SectionTypes.GENERIC_DESCRIPTION: '📖 <b>Описание</b>',
            SectionTypes.DOSAGE_INSTRUCTIONS: '💊 <b>Дозировка</b>',
            SectionTypes.FEATURES: '🌟 <b>Особенности</b>',
            SectionTypes.SCIENTIFIC_NAME: '🔬 <b>Научное название:</b>',
            SectionTypes.CATEGORIES: '🏷️ <b>Категории</b>',
            SectionTypes.PRICES: '💰 <b>Цены</b>',
            SectionTypes.FORMS: '📦 <b>Формы</b>'
        }
    
    def is_section_outputted(self, section_type: str) -> bool:
        """Проверяет, была ли секция уже выведена"""
        return section_type in self.outputted_sections
    
    def mark_section_outputted(self, section_type: str):
        """Отмечает секцию как выведенную"""
        self.outputted_sections.add(section_type)
    
    def get_section_header(self, section_type: str) -> str:
        """Возвращает заголовок секции"""
        return self.section_headers.get(section_type, f"<b>{section_type}</b>")
    
    def can_output_section(self, section_type: str, level: str = 'product') -> bool:
        """
        Определяет, можно ли выводить секцию
        
        Args:
            section_type: Тип секции
            level: Уровень данных ('component' или 'product')
        
        Returns:
            bool: True если секцию можно вывести
        """
        # Компоненты всегда могут выводить секции (приоритет)
        if level == 'component':
            return True
        
        # Продукт может выводить секцию только если она еще не была выведена
        return not self.is_section_outputted(section_type)
