"""
Отслеживание секций для предотвращения дублирования в форматировании продуктов.
"""

from enum import Enum
from typing import Dict, Set

class SectionTypes(Enum):
    """Типы секций для отслеживания"""
    SCIENTIFIC_NAME = "scientific_name"
    GENERIC_DESCRIPTION = "generic_description"
    EFFECTS = "effects"
    SHAMANIC = "shamanic"
    WARNINGS = "warnings"
    DOSAGE_INSTRUCTIONS = "dosage_instructions"
    FEATURES = "features"
    PRICES = "prices"
    FORMS = "forms"
    CATEGORIES = "categories"

class SectionTracker:
    """
    Отслеживает выведенные секции для предотвращения дублирования.
    """
    
    def __init__(self):
        self.outputted_sections: Set[str] = set()
        self.section_contexts: Dict[str, str] = {}
    
    def can_output_section(self, section_type: SectionTypes, context: str = "product") -> bool:
        """
        Проверяет, можно ли вывести секцию.
        
        Args:
            section_type: Тип секции
            context: Контекст (product или component)
            
        Returns:
            bool: True если секцию можно вывести
        """
        section_key = f"{section_type.value}_{context}"
        return section_key not in self.outputted_sections
    
    def mark_section_outputted(self, section_type: SectionTypes, context: str = "product"):
        """
        Отмечает секцию как выведенную.
        
        Args:
            section_type: Тип секции
            context: Контекст (product или component)
        """
        section_key = f"{section_type.value}_{context}"
        self.outputted_sections.add(section_key)
        self.section_contexts[section_key] = context
