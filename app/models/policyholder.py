"""A Northline Mutual member with a roadside endorsement."""
from __future__ import annotations

from dataclasses import dataclass

from app.models._convert import to_float, to_int


@dataclass
class Policyholder:
    id: int | None
    name: str
    phone: str
    policy_number: str
    policy_doc: str
    status: str
    listed_drivers: str
    vehicle: str
    address: str
    lat: float
    lng: float

    FIELDS = [
        "id",
        "name",
        "phone",
        "policy_number",
        "policy_doc",
        "status",
        "listed_drivers",
        "vehicle",
        "address",
        "lat",
        "lng",
    ]

    @classmethod
    def from_row(cls, row: dict) -> "Policyholder":
        return cls(
            id=to_int(row.get("id")),
            name=row.get("name", ""),
            phone=row.get("phone", ""),
            policy_number=row.get("policy_number", ""),
            policy_doc=row.get("policy_doc", ""),
            status=row.get("status", "active"),
            listed_drivers=row.get("listed_drivers", ""),
            vehicle=row.get("vehicle", ""),
            address=row.get("address", ""),
            lat=to_float(row.get("lat"), 0.0) or 0.0,
            lng=to_float(row.get("lng"), 0.0) or 0.0,
        )

    def to_row(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "policy_number": self.policy_number,
            "policy_doc": self.policy_doc,
            "status": self.status,
            "listed_drivers": self.listed_drivers,
            "vehicle": self.vehicle,
            "address": self.address,
            "lat": self.lat,
            "lng": self.lng,
        }
