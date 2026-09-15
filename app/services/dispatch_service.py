"""Nearest capable garage + tow vs mobile-repair. LLM does not invent shops."""
from __future__ import annotations

import math

from app.database.store import Database
from app.models import Case, Garage
from app.models.enums import ActionType, IssueType

MOBILE_ISSUES = {
    IssueType.FLAT_TIRE.value,
    IssueType.BATTERY.value,
    IssueType.LOCKOUT.value,
}

LABEL = {
    ActionType.MOBILE_REPAIR.value: "mobile repair van",
    ActionType.TOW.value: "tow truck",
}


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class DispatchService:
    def __init__(self, db: Database):
        self.db = db

    def recommend(self, case: Case) -> dict:
        issue = case.issue_type or ""
        if issue in MOBILE_ISSUES:
            action = ActionType.MOBILE_REPAIR.value
            need = "mobile_repair"
        else:
            action = ActionType.TOW.value
            need = "tow"

        lat = case.lat
        lng = case.lng
        if lat is None or lng is None:
            return {
                "action_type": action,
                "garage": None,
                "miles": None,
                "rationale": f"Recommend a {LABEL[action]}, but the caller location has no coordinates yet.",
            }

        ranked: list[tuple[float, Garage]] = []
        for garage in self.db.garages.all():
            if need not in garage.capability_set():
                continue
            miles = haversine_miles(lat, lng, garage.lat, garage.lng)
            ranked.append((miles, garage))
        ranked.sort(key=lambda pair: pair[0])
        if not ranked:
            return {
                "action_type": action,
                "garage": None,
                "miles": None,
                "rationale": f"Need a {LABEL[action]}, but no partner with '{need}' is in the directory.",
            }

        miles, garage = ranked[0]
        extra = ""
        if issue == IssueType.COLLISION.value:
            extra = " Collision tows prefer a shop that can take the vehicle; body capability is a plus but not required."
        rationale = (
            f"{issue.replace('_', ' ') or 'This disablement'} is a {LABEL[action]} job. "
            f"Closest capable partner is {garage.name} ({miles:.1f} mi) at {garage.address}."
            f"{extra}"
        )
        return {
            "action_type": action,
            "garage": garage,
            "miles": round(miles, 1),
            "rationale": rationale,
        }
