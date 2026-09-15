"""A partner garage or mobile unit that can receive a roadside job."""
from __future__ import annotations

from dataclasses import dataclass

from app.models._convert import to_float, to_int


@dataclass
class Garage:
    id: int | None
    name: str
    address: str
    phone: str
    lat: float
    lng: float
    capabilities: str
    hours: str

    FIELDS = [
        "id",
        "name",
        "address",
        "phone",
        "lat",
        "lng",
        "capabilities",
        "hours",
    ]

    @classmethod
    def from_row(cls, row: dict) -> "Garage":
        return cls(
            id=to_int(row.get("id")),
            name=row.get("name", ""),
            address=row.get("address", ""),
            phone=row.get("phone", ""),
            lat=to_float(row.get("lat"), 0.0) or 0.0,
            lng=to_float(row.get("lng"), 0.0) or 0.0,
            capabilities=row.get("capabilities", ""),
            hours=row.get("hours", ""),
        )

    def to_row(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "lat": self.lat,
            "lng": self.lng,
            "capabilities": self.capabilities,
            "hours": self.hours,
        }

    def capability_set(self) -> set[str]:
        return {c.strip() for c in self.capabilities.split(",") if c.strip()}
