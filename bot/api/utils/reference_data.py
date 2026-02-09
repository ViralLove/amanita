"""
Справочные данные для Reference Data API (моки).

По api-methods-reference.md и Activity Data Model (таск 7.2):
- Форматы: session, workshop, ceremony, class_regular, class_single, retreat, performance, other
- Таксономия: двухуровневая (primary, secondary)
- Возрастные группы: children, teens, adults, seniors, all_ages
- Языки: ru, en, et, и другие
"""

from __future__ import annotations

from typing import Any

FORMATS: list[dict[str, str]] = [
    {"value": "session", "label": "Session", "description": "Single session activity"},
    {"value": "workshop", "label": "Workshop", "description": "Workshop activity"},
    {"value": "ceremony", "label": "Ceremony", "description": "Ceremonial activity"},
    {"value": "class_regular", "label": "Regular Class", "description": "Regular recurring class"},
    {"value": "class_single", "label": "Single Class", "description": "One-time class"},
    {"value": "retreat", "label": "Retreat", "description": "Retreat activity"},
    {"value": "performance", "label": "Performance", "description": "Performance or show"},
    {"value": "other", "label": "Other", "description": "Other format"},
]

TAXONOMY: dict[str, Any] = {
    "primary_categories": [
        {
            "value": "wellness",
            "label": "Wellness",
            "description": "Wellness and health activities",
            "secondary_categories": [
                {"value": "yoga", "label": "Yoga", "description": "Yoga practices"},
                {"value": "meditation", "label": "Meditation", "description": "Meditation practices"},
            ],
        },
        {
            "value": "arts",
            "label": "Arts & Culture",
            "description": "Creative and cultural activities",
            "secondary_categories": [
                {"value": "music", "label": "Music", "description": "Music activities"},
                {"value": "visual_arts", "label": "Visual Arts", "description": "Visual arts"},
            ],
        },
    ],
}

AGE_GROUPS: list[dict[str, str]] = [
    {"value": "children", "label": "Children", "description": "Children"},
    {"value": "teens", "label": "Teens", "description": "Teenagers"},
    {"value": "adults", "label": "Adults", "description": "Adults"},
    {"value": "seniors", "label": "Seniors", "description": "Seniors"},
    {"value": "all_ages", "label": "All Ages", "description": "All age groups"},
]

LANGUAGES: list[dict[str, str]] = [
    {"code": "ru", "name": "Russian", "native_name": "Русский"},
    {"code": "en", "name": "English", "native_name": "English"},
    {"code": "et", "name": "Estonian", "native_name": "Eesti"},
    {"code": "lv", "name": "Latvian", "native_name": "Latviešu"},
    {"code": "lt", "name": "Lithuanian", "native_name": "Lietuvių"},
]
