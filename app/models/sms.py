"""A fake SMS row shown in the customer inbox."""
from __future__ import annotations

from dataclasses import dataclass

from app.models._convert import to_int


@dataclass
class Sms:
    id: int | None
    case_id: int
    to_phone: str
    body: str
    sent_at: str
    status: str

    FIELDS = ["id", "case_id", "to_phone", "body", "sent_at", "status"]

    @classmethod
    def from_row(cls, row: dict) -> "Sms":
        return cls(
            id=to_int(row.get("id")),
            case_id=to_int(row.get("case_id")),
            to_phone=row.get("to_phone", ""),
            body=row.get("body", ""),
            sent_at=row.get("sent_at", ""),
            status=row.get("status", "sent"),
        )

    def to_row(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "to_phone": self.to_phone,
            "body": self.body,
            "sent_at": self.sent_at,
            "status": self.status,
        }
