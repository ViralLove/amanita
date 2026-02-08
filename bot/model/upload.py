"""
Upload flow model: status constants, allowed transitions, DTO for table uploads.

State machine: prepared → queued_for_publish → published → finalized | failed.
Payload is not stored; only hash and metadata (Arweave data upload, task 3.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

# Status constants (match DB and Edge contract)
PREPARED = "prepared"
SIGNED_VALIDATED = "signed_validated"
QUEUED_FOR_PUBLISH = "queued_for_publish"
PUBLISHED = "published"
FINALIZED = "finalized"
FAILED = "failed"

STATUS_VALUES = (
    PREPARED,
    SIGNED_VALIDATED,
    QUEUED_FOR_PUBLISH,
    PUBLISHED,
    FINALIZED,
    FAILED,
)

# Allowed transitions: from_status -> (to_status, ...)
ALLOWED_TRANSITIONS: Dict[str, tuple] = {
    PREPARED: (QUEUED_FOR_PUBLISH, FAILED),
    QUEUED_FOR_PUBLISH: (PUBLISHED,),  # via callback
    PUBLISHED: (FINALIZED,),  # via finalizer
    FAILED: (),  # terminal
    FINALIZED: (),  # terminal
    SIGNED_VALIDATED: (QUEUED_FOR_PUBLISH, FAILED),
}


def can_transition(from_status: str, to_status: str) -> bool:
    """Returns True if transition from_status → to_status is allowed."""
    if from_status not in ALLOWED_TRANSITIONS:
        return False
    return to_status in ALLOWED_TRANSITIONS[from_status]


@dataclass
class UploadRecord:
    """
    One row from table uploads. UUIDs and timestamps may come as str from Supabase.
    """
    upload_id: str
    user_id: str
    status: str
    payload_hash: Optional[str] = None
    payload_size: Optional[int] = None
    tags_snapshot: Optional[Dict[str, Any]] = None
    anchor: Optional[str] = None
    expires_at: Optional[datetime] = None
    owner_address: Optional[str] = None
    item_id: Optional[str] = None
    bundle_tx_id: Optional[str] = None
    failure_reason: Optional[str] = None
    failure_code: Optional[str] = None
    activity_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "UploadRecord":
        """Build UploadRecord from Supabase row (dict). Handles str dates."""
        def _opt_ts(v: Any) -> Optional[datetime]:
            if v is None:
                return None
            if isinstance(v, datetime):
                return v
            if isinstance(v, str):
                try:
                    return datetime.fromisoformat(v.replace("Z", "+00:00"))
                except Exception:
                    return None
            return None

        return cls(
            upload_id=str(row["upload_id"]),
            user_id=str(row["user_id"]),
            status=str(row["status"]),
            payload_hash=row.get("payload_hash"),
            payload_size=row.get("payload_size"),
            tags_snapshot=row.get("tags_snapshot"),
            anchor=row.get("anchor"),
            expires_at=_opt_ts(row.get("expires_at")),
            owner_address=row.get("owner_address"),
            item_id=row.get("item_id"),
            bundle_tx_id=row.get("bundle_tx_id"),
            failure_reason=row.get("failure_reason"),
            failure_code=row.get("failure_code"),
            activity_id=row.get("activity_id"),
            created_at=_opt_ts(row.get("created_at")),
            updated_at=_opt_ts(row.get("updated_at")),
        )

    def to_insert_row(self) -> Dict[str, Any]:
        """Dict suitable for Supabase insert. Include upload_id if set (else DB generates)."""
        row: Dict[str, Any] = {
            "user_id": self.user_id,
            "status": self.status,
            "payload_hash": self.payload_hash,
            "payload_size": self.payload_size,
            "tags_snapshot": self.tags_snapshot,
            "anchor": self.anchor,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "owner_address": self.owner_address,
            "item_id": self.item_id,
            "bundle_tx_id": self.bundle_tx_id,
            "failure_reason": self.failure_reason,
            "failure_code": self.failure_code,
            "activity_id": self.activity_id,
        }
        if self.upload_id:
            row["upload_id"] = self.upload_id
        return {k: v for k, v in row.items() if v is not None}
