"""
In-memory хранилище для Activities API mocks.

Dict-based store, генерация activity_id act_{n}, pagination для list/search.
Используется эндпоинтами activities при тестировании GPT без БД.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from api.utils.state_transitions import get_state_transition_error_message, validate_state_transition

_STATUS_PUBLISHED = "Published"
_STATUS_DRAFT = "Draft"

_RESERVED = frozenset({"activity_id", "created_at", "updated_at", "published_at"})


def _search_sort_key(field: str):
    """Возвращает key-функцию для sorted(). Поля: date, title, created_at."""
    if field == "title":
        return lambda x: (x.get("title") or "")
    if field == "created_at":
        return lambda x: (x.get("created_at") or "")
    if field == "date":
        def _date_key(x: dict[str, Any]) -> str:
            et = x.get("event_timing") or {}
            fd = et.get("fixed_dates") or []
            if fd and len(fd) > 0 and isinstance(fd[0], dict) and fd[0].get("start"):
                return fd[0]["start"]
            return x.get("created_at") or ""
        return _date_key
    return lambda x: (x.get("title") or "")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_storage_record(
    payload: dict[str, Any],
    activity_id: str,
    owner_id: str,
    now: str,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "activity_id": activity_id,
        "owner_id": owner_id,
        "created_at": now,
        "updated_at": now,
        "published_at": None,
    }
    for k, v in payload.items():
        if k not in _RESERVED:
            out[k] = v
    return out


def _build_test_activities_template() -> list[dict[str, Any]]:
    """8 Activities по Activity Data Model: event/service, все статусы, макс. структурная вариативность."""
    return [
        # 1. Event, Draft — fixed_dates, workshop, in_person, ticket, event_cta
        {
            "activity_type": "event",
            "status": "Draft",
            "title": "Yoga Workshop",
            "short_summary": "Relaxing morning yoga for all levels.",
            "full_description": "Join us for a 90-minute workshop combining asana, breathwork and short meditation. Mats provided.",
            "format": "workshop",
            "delivery_mode": "in_person",
            "location_info": {"city": "Tallinn", "area": "Kesklinn", "venue": "Studio Lumina"},
            "event_timing": {
                "schedule_model": "fixed_dates",
                "fixed_dates": [
                    {"start": "2025-02-15T09:00:00Z", "end": "2025-02-15T10:30:00Z", "timezone": "Europe/Tallinn"},
                ],
            },
            "event_capacity": {"group_capacity": 20, "min_participants": 5, "max_participants": 20},
            "event_duration": {"duration_type": "per_occurrence", "per_occurrence": {"duration_minutes": 90}},
            "event_pricing": {
                "pricing_type": "ticket_price",
                "ticket_price": {"amount": 25, "currency": "EUR"},
            },
            "event_cta": {"event_page_link": "https://example.com/yoga-workshop", "tickets_link": "https://example.com/yoga-tickets"},
        },
        # 2. Event, SentToReview — recurring, class_regular, online, donation
        {
            "activity_type": "event",
            "status": "SentToReview",
            "title": "Weekly Meditation Class",
            "short_summary": "Guided meditation every Wednesday.",
            "full_description": "A recurring one-hour guided meditation session. Suitable for beginners. We focus on breath awareness and body scan. Bring a comfortable seat and quiet space.",
            "format": "class_regular",
            "delivery_mode": "online",
            "location_info": {"online_platform": "Zoom", "online_link": "https://zoom.us/j/example"},
            "event_timing": {
                "schedule_model": "recurring",
                "recurring": {
                    "recurrence_rule": "FREQ=WEEKLY;BYDAY=WE",
                    "start_date": "2025-02-01",
                    "end_date": "2025-06-30",
                    "timezone": "Europe/Tallinn",
                },
            },
            "event_capacity": {"seats": 50},
            "event_duration": {"duration_type": "per_occurrence", "per_occurrence": {"duration_minutes": 60}},
            "event_pricing": {"pricing_type": "donation"},
            "event_cta": {"event_page_link": "https://example.com/meditation"},
        },
        # 3. Event, Approved — fixed_dates, ceremony, hybrid, free, age_groups, parental
        {
            "activity_type": "event",
            "status": "Approved",
            "title": "Spring Equinox Ceremony",
            "short_summary": "Community ceremony to welcome spring.",
            "full_description": "An outdoor ceremony with music, sharing and a simple ritual. Family-friendly. We meet at sunset. Please dress for the weather. No previous experience needed.",
            "format": "ceremony",
            "delivery_mode": "hybrid",
            "location_info": {
                "city": "Tartu",
                "venue": "Toomemägi",
                "online_platform": "YouTube",
                "online_link": "https://youtube.com/live/example",
            },
            "event_timing": {
                "schedule_model": "fixed_dates",
                "fixed_dates": [
                    {"start": "2025-03-20T18:00:00Z", "end": "2025-03-20T20:00:00Z", "timezone": "Europe/Tallinn"},
                ],
            },
            "event_capacity": {"group_capacity": 100, "max_participants": 100},
            "event_duration": {"duration_type": "fixed", "fixed": "approx. 2 hours"},
            "event_pricing": {"pricing_type": "free"},
            "event_cta": {"event_page_link": "https://example.com/equinox"},
            "age_groups": ["adults", "teenagers", "youngsters_18_25"],
            "parental_accompaniment": "optional",
        },
        # 4. Event, Published — retreat, in_person, ticket+price_range, categories, media
        {
            "activity_type": "event",
            "status": "Published",
            "title": "Forest Retreat Weekend",
            "short_summary": "Two-day nature retreat with yoga, hiking and sauna.",
            "full_description": "Escape the city for a weekend in the Estonian forest. Program includes morning yoga, guided hike, communal meals and evening sauna. Accommodation in shared cottages. Vegetarian meals included.",
            "format": "retreat",
            "delivery_mode": "in_person",
            "location_info": {"city": "Otepää", "area": "Nature Park", "venue": "Retreat Center Pühajärv"},
            "event_timing": {
                "schedule_model": "fixed_dates",
                "fixed_dates": [
                    {"start": "2025-04-11T16:00:00Z", "end": "2025-04-13T12:00:00Z", "timezone": "Europe/Tallinn"},
                ],
            },
            "event_capacity": {"group_capacity": 24, "min_participants": 8, "max_participants": 24},
            "event_duration": {"duration_type": "fixed", "fixed": "2 days"},
            "event_pricing": {
                "pricing_type": "ticket_price",
                "ticket_price": {"amount": 199, "currency": "EUR", "price_range": {"min": 179, "max": 219}},
            },
            "event_cta": {"event_page_link": "https://example.com/forest-retreat", "tickets_link": "https://example.com/retreat-tickets"},
            "categories": {"primary": {"id": "wellbeing", "name": "Wellbeing"}, "secondary": [{"id": "nature", "name": "Nature"}]},
            "age_groups": ["adults", "seniors"],
            "media": {
                "official_site": "https://example.com/retreat",
                "social_links": [{"platform": "instagram", "url": "https://instagram.com/example", "account": "example"}],
            },
        },
        # 5. Service, Draft — by_request, one_to_one, per_session, online, session
        {
            "activity_type": "service",
            "status": "Draft",
            "title": "Private Coaching",
            "short_summary": "One-to-one coaching sessions.",
            "full_description": "Individual coaching tailored to your goals. We work on mindset, habits and life design. Sessions are confidential and held via video call.",
            "format": "session",
            "delivery_mode": "online",
            "location_info": {"online_platform": "Google Meet", "online_link": "https://meet.google.com"},
            "service_timing": {"availability_type": "by_request", "booking_policy": "Book via Calendly or email."},
            "service_participation": {"session_mode": "one_to_one", "concurrent_clients": 1},
            "service_duration_options": [
                {"duration_minutes": 60, "label": "Standard"},
                {"duration_minutes": 90, "label": "Extended"},
            ],
            "service_pricing_model": {"model": "per_session"},
            "service_cta": {"booking_url": "https://calendly.com/example", "amanita_booking": False},
        },
        # 6. Service, SentToReview — fixed_windows, family, per_hour, in_person, service_area
        {
            "activity_type": "service",
            "status": "SentToReview",
            "title": "Family Constellation Session",
            "short_summary": "Family constellation sessions for families.",
            "full_description": "In-person family constellation sessions. We work with family dynamics and patterns. Sessions are held in a quiet room. Duration varies; typically 90–120 minutes.",
            "format": "session",
            "delivery_mode": "in_person",
            "location_info": {"city": "Tallinn", "area": "Nõmme", "venue": "Private practice"},
            "service_area": {"radius": 30, "districts": ["Tallinn", "Harjumaa"], "travel_notes": "Home visits possible."},
            "service_timing": {
                "availability_type": "fixed_windows",
                "availability_windows": [
                    {"day_of_week": "tuesday", "start_time": "09:00", "end_time": "17:00", "timezone": "Europe/Tallinn"},
                    {"day_of_week": "thursday", "start_time": "09:00", "end_time": "17:00", "timezone": "Europe/Tallinn"},
                ],
                "booking_policy": "Advance booking required.",
            },
            "service_participation": {"session_mode": "family", "concurrent_clients": 1},
            "service_duration_options": [{"duration_minutes": 90}, {"duration_minutes": 120, "label": "Extended"}],
            "service_pricing_model": {"model": "per_hour"},
            "service_cta": {"contact_channel": {"type": "email", "value": "family@example.com"}},
        },
        # 7. Service, Approved — by_request, small_group, per_package, hybrid, format other
        {
            "activity_type": "service",
            "status": "Approved",
            "title": "Small Group Sound Journey",
            "short_summary": "Group sound healing sessions by appointment.",
            "full_description": "Small group sound baths with gongs, singing bowls and other instruments. Sessions can be in-person or online. Book a package of 3 or 6 sessions for a discount.",
            "format": "other",
            "format_other_label": "Sound journey (group)",
            "delivery_mode": "hybrid",
            "location_info": {"city": "Tartu", "venue": "Studio Heli", "online_platform": "Zoom", "online_link": "https://zoom.us/j/example"},
            "service_area": {"districts": ["Tartu", "Tartumaa"]},
            "service_timing": {"availability_type": "by_request", "booking_policy": "Contact to arrange dates."},
            "service_participation": {"session_mode": "small_group", "concurrent_clients": 6},
            "service_duration_options": [{"duration_minutes": 75}],
            "service_pricing_model": {
                "model": "per_package",
                "package_definition": {"sessions_count": 3, "total_price": 120, "currency": "EUR"},
            },
            "service_cta": {"contact_channel": {"type": "other", "value": "Telegram @example"}},
        },
        # 8. Service, Published — fixed_windows, one_to_one, free, online, language_requirements, media
        {
            "activity_type": "service",
            "status": "Published",
            "title": "Free Intro Consultation",
            "short_summary": "30-minute intro call to explore fit.",
            "full_description": "A free 30-minute video call to discuss your goals and whether we are a good fit. No obligation. Available in Estonian and English.",
            "format": "session",
            "delivery_mode": "online",
            "location_info": {"online_platform": "Google Meet", "online_link": "https://meet.google.com"},
            "service_timing": {
                "availability_type": "fixed_windows",
                "availability_windows": [
                    {"day_of_week": "monday", "start_time": "10:00", "end_time": "14:00", "timezone": "Europe/Tallinn"},
                    {"day_of_week": "wednesday", "start_time": "10:00", "end_time": "14:00", "timezone": "Europe/Tallinn"},
                ],
                "booking_policy": "Book via link.",
            },
            "service_participation": {"session_mode": "one_to_one", "concurrent_clients": 1},
            "service_duration_options": [{"duration_minutes": 30, "label": "Intro"}],
            "service_pricing_model": {"model": "free"},
            "service_cta": {"booking_url": "https://calendly.com/intro", "amanita_booking": True},
            "age_groups": ["adults", "youngsters_18_25"],
            "language_requirements": {
                "mode": "mixed",
                "languages_to_understand": ["et", "en"],
                "languages_to_speak": ["et", "en"],
            },
            "media": {"official_site": "https://example.com", "social_links": [{"platform": "telegram", "url": "https://t.me/example"}]},
        },
    ]


class ActivityStorage:
    """Dict-based in-memory хранилище Activity."""

    def __init__(self) -> None:
        self._activities: dict[str, dict[str, Any]] = {}
        self._counter = 1
        self._init_test_data()

    def _next_id(self) -> str:
        aid = f"act_{self._counter}"
        self._counter += 1
        return aid

    def _init_test_data(self) -> None:
        """Предзаполнение 8 Activities по Activity Data Model: макс. структурная вариативность (event/service, форматы, timing, pricing, delivery, CTA, media и т.д.)."""
        owner = "owner_mock"
        base = _build_test_activities_template()
        for p in base:
            aid = self._next_id()
            now = _utc_now_iso()
            rec = _to_storage_record(p, aid, owner, now)
            if rec["status"] == _STATUS_PUBLISHED:
                rec["published_at"] = now
            self._activities[aid] = rec

    def create(self, activity_data: dict[str, Any]) -> dict[str, Any]:
        """Создать Activity, вернуть с activity_id. Статус Draft."""
        aid = self._next_id()
        now = _utc_now_iso()
        rec = {
            "activity_id": aid,
            "status": _STATUS_DRAFT,
            "created_at": now,
            "updated_at": now,
            "published_at": None,
            **{k: v for k, v in activity_data.items() if k not in ("activity_id", "created_at", "updated_at", "published_at")},
        }
        self._activities[aid] = rec
        return rec.copy()

    def get(self, activity_id: str) -> Optional[dict[str, Any]]:
        """Получить Activity по ID."""
        raw = self._activities.get(activity_id)
        return raw.copy() if raw else None

    def update(self, activity_id: str, activity_data: dict[str, Any]) -> dict[str, Any]:
        """Обновить Activity. updated_at перезаписывается."""
        if activity_id not in self._activities:
            raise KeyError(activity_id)
        rec = self._activities[activity_id]
        skip = {"activity_id", "created_at", "published_at"}
        for k, v in activity_data.items():
            if k not in skip:
                rec[k] = v
        rec["updated_at"] = _utc_now_iso()
        return rec.copy()

    def delete(self, activity_id: str) -> bool:
        """Удалить Activity. Возвращает True, если запись была."""
        if activity_id in self._activities:
            del self._activities[activity_id]
            return True
        return False

    def list(
        self,
        *,
        owner_id: Optional[str] = None,
        status: Optional[str] = None,
        activity_type: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """Список Activities с фильтрами и pagination. Возвращает (items, total)."""
        out: list[dict[str, Any]] = []
        for r in self._activities.values():
            if owner_id is not None and r.get("owner_id") != owner_id:
                continue
            if status is not None and r.get("status") != status:
                continue
            if activity_type is not None and r.get("activity_type") != activity_type:
                continue
            out.append(r)
        total = len(out)
        start = (page - 1) * per_page
        end = start + per_page
        page_items = [x.copy() for x in out[start:end]]
        return page_items, total

    def search(
        self,
        *,
        text: Optional[str] = None,
        activity_type: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
        per_page: int = 20,
        sort_field: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Поиск только Published. Фильтры: text (title/description), activity_type. (items, total)."""
        out: list[dict[str, Any]] = []
        text_lower = (text or "").lower()
        for r in self._activities.values():
            if r.get("status") != _STATUS_PUBLISHED:
                continue
            if activity_type is not None and r.get("activity_type") != activity_type:
                continue
            if text_lower:
                t = (r.get("title") or "") + " " + (r.get("full_description") or "") + " " + (r.get("short_summary") or "")
                if text_lower not in t.lower():
                    continue
            out.append(r)
        total = len(out)
        if sort_field and sort_order:
            key_fn = _search_sort_key(sort_field)
            reverse = sort_order.lower() == "desc"
            out = sorted(out, key=key_fn, reverse=reverse)
        start = (page - 1) * per_page
        end = start + per_page
        page_items = [x.copy() for x in out[start:end]]
        return page_items, total

    def update_status(self, activity_id: str, new_status: str) -> dict[str, Any]:
        """
        Обновить статус Activity. Валидирует переход через validate_state_transition.
        При невалидном переходе выбрасывает ValueError — вызывающий код возвращает 400.
        """
        rec = self._activities.get(activity_id)
        if not rec:
            raise KeyError(activity_id)
        current = rec.get("status", _STATUS_DRAFT)
        if not validate_state_transition(current, new_status):
            raise ValueError(get_state_transition_error_message(current, new_status))
        rec["status"] = new_status
        rec["updated_at"] = _utc_now_iso()
        if new_status == _STATUS_PUBLISHED:
            rec["published_at"] = rec["updated_at"]
        return rec.copy()
