class SectionTypes:
    """Типы секций для предотвращения дублирования"""
    
    # Основные секции
    SHAMANIC = 'shamanic'
    WARNINGS = 'warnings'
    EFFECTS = 'effects'
    GENERIC_DESCRIPTION = 'generic_description'
    DOSAGE_INSTRUCTIONS = 'dosage_instructions'
    FEATURES = 'features'
    
    # Дополнительные секции
    SCIENTIFIC_NAME = 'scientific_name'
    CATEGORIES = 'categories'
    PRICES = 'prices'
    FORMS = 'forms'
    
    @classmethod
    def get_all_sections(cls):
        """Возвращает все типы секций"""
        return [
            cls.SHAMANIC, cls.WARNINGS, cls.EFFECTS, cls.GENERIC_DESCRIPTION,
            cls.DOSAGE_INSTRUCTIONS, cls.FEATURES, cls.SCIENTIFIC_NAME,
            cls.CATEGORIES, cls.PRICES, cls.FORMS
        ]
