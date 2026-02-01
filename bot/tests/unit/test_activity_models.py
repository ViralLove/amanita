"""
Unit tests for Activity models: ActivityOnChain, ActivityMetadata, Activity.

Policy: No ActivityStatus enum — only active (bool). Conditional fields: Event vs Service.
"""

import json
import os

import pytest
from model.activity import (
    Activity,
    ActivityOnChain,
    ActivityMetadata,
    ActivityType,
)


@pytest.mark.unit
class TestActivityOnChain:
    """Tests for ActivityOnChain (on-chain data, 1:1 with contract)."""

    def test_from_blockchain_tuple_valid(self):
        """from_blockchain_tuple with 5 fields returns valid ActivityOnChain."""
        t = (1, "0x1234567890123456789012345678901234567890", 0, "QmTestCID", False)
        oc = ActivityOnChain.from_blockchain_tuple(t)
        assert oc.id == 1
        assert oc.creator == "0x1234567890123456789012345678901234567890"
        assert oc.activity_type == ActivityType.Event
        assert oc.metadata_cid == "QmTestCID"
        assert oc.active is False

    def test_from_blockchain_tuple_service_type(self):
        """activity_type=1 (Service) is parsed correctly."""
        t = (2, "0xabc", 1, "QmY", True)
        oc = ActivityOnChain.from_blockchain_tuple(t)
        assert oc.activity_type == ActivityType.Service
        assert oc.active is True

    def test_from_blockchain_tuple_too_short_raises(self):
        """Tuple with fewer than 5 elements raises ValueError."""
        with pytest.raises(ValueError, match="Expected tuple of 5 elements"):
            ActivityOnChain.from_blockchain_tuple((1, "0x", 0))

    def test_constructor_valid(self):
        """Direct constructor with valid data."""
        oc = ActivityOnChain(
            id=1,
            creator="0xabc",
            activity_type=ActivityType.Event,
            metadata_cid="QmX",
            active=False,
        )
        assert oc.id == 1
        assert oc.active is False

    def test_constructor_activity_type_from_int(self):
        """activity_type can be int (converted to ActivityType in __post_init__)."""
        oc = ActivityOnChain(
            id=1,
            creator="0xabc",
            activity_type=0,
            metadata_cid="Qm",
            active=True,
        )
        assert oc.activity_type == ActivityType.Event


@pytest.mark.unit
class TestActivityMetadata:
    """Tests for ActivityMetadata (Arweave JSON). Conditional: event_* vs service_*."""

    def test_from_dict_event_minimal(self):
        """Event with event_timing only."""
        data = {"activity_type": "event", "title": "Test Event", "event_timing": {"schedule_model": "fixed_dates"}}
        m = ActivityMetadata.from_dict(data)
        assert m.activity_type == ActivityType.Event
        assert m.title == "Test Event"
        assert m.event_timing is not None
        assert m.service_timing is None

    def test_from_dict_service_minimal(self):
        """Service with service_timing only."""
        data = {"activity_type": "service", "title": "Test Service", "service_timing": {"availability_type": "by_request"}}
        m = ActivityMetadata.from_dict(data)
        assert m.activity_type == ActivityType.Service
        assert m.title == "Test Service"
        assert m.service_timing is not None
        assert m.event_timing is None

    def test_event_cannot_have_service_fields(self):
        """Event with service_* field raises ValueError."""
        data = {"activity_type": "event", "title": "E", "service_timing": {"availability_type": "by_request"}}
        with pytest.raises(ValueError, match="Event activity cannot have service_\\* fields"):
            ActivityMetadata.from_dict(data)

    def test_service_cannot_have_event_fields(self):
        """Service with event_* field raises ValueError."""
        data = {"activity_type": "service", "title": "S", "event_timing": {"schedule_model": "fixed_dates"}}
        with pytest.raises(ValueError, match="Service activity cannot have event_\\* fields"):
            ActivityMetadata.from_dict(data)

    def test_from_dict_missing_title_raises(self):
        """Missing title raises ValueError."""
        with pytest.raises(ValueError, match="title is required"):
            ActivityMetadata.from_dict({"activity_type": "event"})

    def test_from_dict_missing_activity_type_raises(self):
        """Missing activity_type raises ValueError."""
        with pytest.raises(ValueError, match="activity_type is required"):
            ActivityMetadata.from_dict({"title": "T"})

    def test_from_dict_not_dict_raises(self):
        """Non-dict input raises ValueError."""
        with pytest.raises(ValueError, match="Input must be a dict"):
            ActivityMetadata.from_dict([])


@pytest.mark.unit
class TestActivity:
    """Tests for Activity (on_chain + metadata)."""

    def test_from_assembled(self):
        """from_assembled builds Activity; computed properties from on_chain."""
        oc = ActivityOnChain.from_blockchain_tuple((1, "0xcreator", 0, "QmCID", True))
        meta = ActivityMetadata.from_dict({"activity_type": "event", "title": "My Event"})
        a = Activity.from_assembled(oc, meta)
        assert a.activity_id == 1
        assert a.activity_type == ActivityType.Event
        assert a.active is True
        assert a.creator == "0xcreator"

    def test_from_assembled_type_mismatch_raises(self):
        """Mismatch activity_type between on_chain and metadata raises ValueError."""
        oc = ActivityOnChain.from_blockchain_tuple((1, "0xc", 0, "Qm", False))  # Event
        meta = ActivityMetadata.from_dict({"activity_type": "service", "title": "S"})  # Service
        with pytest.raises(ValueError, match="activity_type mismatch"):
            Activity.from_assembled(oc, meta)

    def test_to_dict_no_status_enum(self):
        """to_dict exposes active (bool), not status enum."""
        oc = ActivityOnChain.from_blockchain_tuple((1, "0xc", 0, "Qm", False))
        meta = ActivityMetadata.from_dict({"activity_type": "event", "title": "E"})
        a = Activity.from_assembled(oc, meta)
        d = a.to_dict()
        assert "active" in d
        assert d["active"] is False
        assert "activity_id" in d
        assert d["activity_type"] == "event"
        assert "status" not in d


@pytest.mark.unit
class TestActivityFixtures:
    """Smoke test: fixtures are loadable and have expected interface."""

    def test_mock_activity_registry_service_has_methods(self, mock_activity_registry_service):
        """mock_activity_registry_service has create_activity, get_activity, activate_activity, deactivate_activity."""
        m = mock_activity_registry_service
        assert hasattr(m, "create_activity")
        assert hasattr(m, "get_activity")
        assert hasattr(m, "activate_activity")
        assert hasattr(m, "deactivate_activity")
        assert hasattr(m, "get_activities_by_creator")

    def test_activities_json_loadable_and_parseable(self):
        """fixtures/activities.json is valid JSON and entries parse via ActivityMetadata.from_dict."""
        fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
        path = os.path.join(fixtures_dir, "activities.json")
        if not os.path.isfile(path):
            pytest.skip("fixtures/activities.json not found")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        activities = data.get("valid_activities", [])
        assert len(activities) >= 1
        for item in activities:
            meta = ActivityMetadata.from_dict(item)
            assert meta.activity_type in (ActivityType.Event, ActivityType.Service)
            assert meta.title
