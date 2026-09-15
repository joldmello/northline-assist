"""A roadside assistance case. JSON blobs live as lists/dicts in memory."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models._convert import dump_json, to_float, to_int, to_json
from app.models.enums import CaseStatus


@dataclass
class Case:
    id: int | None
    status: str = CaseStatus.NEW.value
    policyholder_id: int | None = None
    caller_name: str = ""
    phone: str = ""
    vehicle: str = ""
    location_text: str = ""
    lat: float | None = None
    lng: float | None = None
    issue_type: str = ""
    situation: str = ""
    listed_driver: str = "unknown"
    transcript: list = field(default_factory=list)
    slots: dict = field(default_factory=dict)
    coverage_decision: str = ""
    coverage_rationale: str = ""
    coverage_citations: list = field(default_factory=list)
    coverage_confidence: str = ""
    action_type: str = ""
    garage_id: int | None = None
    action_rationale: str = ""
    sms_draft: str = ""
    sms_sent: str = ""
    human_note: str = ""
    created_at: str = ""
    updated_at: str = ""

    FIELDS = [
        "id",
        "status",
        "policyholder_id",
        "caller_name",
        "phone",
        "vehicle",
        "location_text",
        "lat",
        "lng",
        "issue_type",
        "situation",
        "listed_driver",
        "transcript",
        "slots",
        "coverage_decision",
        "coverage_rationale",
        "coverage_citations",
        "coverage_confidence",
        "action_type",
        "garage_id",
        "action_rationale",
        "sms_draft",
        "sms_sent",
        "human_note",
        "created_at",
        "updated_at",
    ]

    @classmethod
    def from_row(cls, row: dict) -> "Case":
        return cls(
            id=to_int(row.get("id")),
            status=row.get("status", CaseStatus.NEW.value),
            policyholder_id=to_int(row.get("policyholder_id")),
            caller_name=row.get("caller_name", ""),
            phone=row.get("phone", ""),
            vehicle=row.get("vehicle", ""),
            location_text=row.get("location_text", ""),
            lat=to_float(row.get("lat")),
            lng=to_float(row.get("lng")),
            issue_type=row.get("issue_type", ""),
            situation=row.get("situation", ""),
            listed_driver=row.get("listed_driver", "unknown") or "unknown",
            transcript=to_json(row.get("transcript"), []),
            slots=to_json(row.get("slots"), {}),
            coverage_decision=row.get("coverage_decision", ""),
            coverage_rationale=row.get("coverage_rationale", ""),
            coverage_citations=to_json(row.get("coverage_citations"), []),
            coverage_confidence=row.get("coverage_confidence", ""),
            action_type=row.get("action_type", ""),
            garage_id=to_int(row.get("garage_id")),
            action_rationale=row.get("action_rationale", ""),
            sms_draft=row.get("sms_draft", ""),
            sms_sent=row.get("sms_sent", ""),
            human_note=row.get("human_note", ""),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )

    def to_row(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "policyholder_id": self.policyholder_id if self.policyholder_id is not None else "",
            "caller_name": self.caller_name,
            "phone": self.phone,
            "vehicle": self.vehicle,
            "location_text": self.location_text,
            "lat": "" if self.lat is None else self.lat,
            "lng": "" if self.lng is None else self.lng,
            "issue_type": self.issue_type,
            "situation": self.situation,
            "listed_driver": self.listed_driver,
            "transcript": dump_json(self.transcript),
            "slots": dump_json(self.slots),
            "coverage_decision": self.coverage_decision,
            "coverage_rationale": self.coverage_rationale,
            "coverage_citations": dump_json(self.coverage_citations),
            "coverage_confidence": self.coverage_confidence,
            "action_type": self.action_type,
            "garage_id": self.garage_id if self.garage_id is not None else "",
            "action_rationale": self.action_rationale,
            "sms_draft": self.sms_draft,
            "sms_sent": self.sms_sent,
            "human_note": self.human_note,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def changes(self) -> dict:
        row = self.to_row()
        row.pop("id", None)
        return row
