"""
Activity models: on-chain (ActivityRegistry), metadata (Arweave), and assembled Activity.

Policy: No ActivityStatus enum anywhere. Lifecycle is expressed only as active (bool):
  false = draft (not in search), true = published. Gate keeper validation is UI-level.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, Optional, Tuple, Union


class ActivityType(IntEnum):
    """Activity type; matches ActivityRegistry smart contract enum."""
    Event = 0
    Service = 1


@dataclass
class ActivityOnChain:
    """
    On-chain Activity data (1:1 with ActivityRegistry.getActivity() struct).
    No status enum — only active (bool). Contract: id, creator, activity_type, metadataCID, active.
    """
    id: int
    creator: str
    activity_type: ActivityType
    metadata_cid: str
    active: bool

    def __post_init__(self) -> None:
        if not isinstance(self.id, int) or self.id < 0:
            raise ValueError("id must be a non-negative int")
        if not self.creator or not isinstance(self.creator, str):
            raise ValueError("creator must be a non-empty string")
        if not isinstance(self.activity_type, ActivityType):
            self.activity_type = ActivityType(int(self.activity_type))
        if not isinstance(self.metadata_cid, str):
            raise ValueError("metadata_cid must be a string")
        if not isinstance(self.active, bool):
            self.active = bool(self.active)

    @classmethod
    def from_blockchain_tuple(cls, tuple_data: Union[Tuple[Any, ...], list]) -> "ActivityOnChain":
        """
        Build ActivityOnChain from ActivityRegistry.getActivity() result.
        Tuple format: (id, creator, activity_type, metadataCID, active) — 5 fields, no status.
        """
        if len(tuple_data) < 5:
            raise ValueError(
                f"Expected tuple of 5 elements (id, creator, activity_type, metadataCID, active), got {len(tuple_data)}"
            )
        return cls(
            id=int(tuple_data[0]),
            creator=str(tuple_data[1]),
            activity_type=ActivityType(int(tuple_data[2])),
            metadata_cid=str(tuple_data[3]),
            active=bool(tuple_data[4]),
        )


# ---------------------------------------------------------------------------
# ActivityMetadata: data from Arweave (Activity Data Model). Conditional fields
# event_* vs service_* are mutually exclusive by activity_type.
# ---------------------------------------------------------------------------

@dataclass
class ActivityMetadata:
    """
    Activity metadata from Arweave (Activity Data Model).
    Conditional fields: event_timing/service_timing, event_capacity/service_participation,
    event_duration/event_pricing vs service_duration_options/service_pricing_model,
    event_cta/service_cta. Event cannot have service_* fields; Service cannot have event_*.
    No status enum — only active is on-chain; metadata may hold timestamps/versioning.
    """
    activity_type: ActivityType
    title: str
    short_summary: Optional[str] = None
    full_description: Optional[str] = None
    delivery_mode: Optional[str] = None
    location_info: Optional[Dict[str, Any]] = None
    service_area: Optional[Dict[str, Any]] = None
    sources: Optional[Dict[str, Any]] = None
    review_submission: Optional[Dict[str, Any]] = None
    policy_gate_result: Optional[Dict[str, Any]] = None
    # Event-only (mutually exclusive with service_*)
    event_timing: Optional[Dict[str, Any]] = None
    event_capacity: Optional[Dict[str, Any]] = None
    event_duration: Optional[Dict[str, Any]] = None
    event_pricing: Optional[Dict[str, Any]] = None
    event_cta: Optional[Dict[str, Any]] = None
    # Service-only (mutually exclusive with event_*)
    service_timing: Optional[Dict[str, Any]] = None
    service_participation: Optional[Dict[str, Any]] = None
    service_duration_options: Optional[Any] = None  # list of objects
    service_pricing_model: Optional[Dict[str, Any]] = None
    service_cta: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not isinstance(self.activity_type, ActivityType):
            self.activity_type = ActivityType(int(self.activity_type))
        if not self.title or not isinstance(self.title, str):
            raise ValueError("title must be a non-empty string")
        # Conditional fields: Event cannot have service_*; Service cannot have event_*
        event_fields = (
            self.event_timing,
            self.event_capacity,
            self.event_duration,
            self.event_pricing,
            self.event_cta,
        )
        service_fields = (
            self.service_timing,
            self.service_participation,
            self.service_duration_options,
            self.service_pricing_model,
            self.service_cta,
        )
        if self.activity_type == ActivityType.Event:
            if any(f is not None for f in service_fields):
                raise ValueError("Event activity cannot have service_* fields")
        elif self.activity_type == ActivityType.Service:
            if any(f is not None for f in event_fields):
                raise ValueError("Service activity cannot have event_* fields")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActivityMetadata":
        """Build ActivityMetadata from JSON dict (e.g. from Arweave). Validates conditional fields."""
        if not isinstance(data, dict):
            raise ValueError("Input must be a dict")
        activity_type_raw = data.get("activity_type")
        if activity_type_raw is None:
            raise ValueError("activity_type is required")
        if isinstance(activity_type_raw, str):
            activity_type = ActivityType.Event if activity_type_raw.lower() == "event" else ActivityType.Service
        else:
            activity_type = ActivityType(int(activity_type_raw))
        title = data.get("title") or ""
        if not title:
            raise ValueError("title is required")
        meta = cls(
            activity_type=activity_type,
            title=str(title),
            short_summary=data.get("short_summary"),
            full_description=data.get("full_description"),
            delivery_mode=data.get("delivery_mode"),
            location_info=data.get("location_info"),
            service_area=data.get("service_area"),
            sources=data.get("sources"),
            review_submission=data.get("review_submission"),
            policy_gate_result=data.get("policy_gate_result"),
            event_timing=data.get("event_timing"),
            event_capacity=data.get("event_capacity"),
            event_duration=data.get("event_duration"),
            event_pricing=data.get("event_pricing"),
            event_cta=data.get("event_cta"),
            service_timing=data.get("service_timing"),
            service_participation=data.get("service_participation"),
            service_duration_options=data.get("service_duration_options"),
            service_pricing_model=data.get("service_pricing_model"),
            service_cta=data.get("service_cta"),
        )
        return meta


@dataclass
class Activity:
    """
    Full Activity: on-chain data + metadata. No status enum — use .active from on_chain.
    """
    on_chain: ActivityOnChain
    metadata: ActivityMetadata

    @property
    def activity_id(self) -> int:
        return self.on_chain.id

    @property
    def activity_type(self) -> ActivityType:
        return self.on_chain.activity_type

    @property
    def active(self) -> bool:
        return self.on_chain.active

    @property
    def creator(self) -> str:
        return self.on_chain.creator

    @classmethod
    def from_assembled(
        cls,
        on_chain: ActivityOnChain,
        metadata: ActivityMetadata,
    ) -> "Activity":
        """Build Activity from assembled on-chain + metadata. Validates activity_type match."""
        if on_chain.activity_type != metadata.activity_type:
            raise ValueError(
                f"activity_type mismatch: on_chain={on_chain.activity_type}, metadata={metadata.activity_type}"
            )
        return cls(on_chain=on_chain, metadata=metadata)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict (e.g. for API response). No status enum — only active."""
        return {
            "activity_id": self.activity_id,
            "activity_type": self.activity_type.name.lower(),
            "active": self.active,
            "creator": self.creator,
            "metadata_cid": self.on_chain.metadata_cid,
            "title": self.metadata.title,
            "short_summary": self.metadata.short_summary,
            "full_description": self.metadata.full_description,
        }
