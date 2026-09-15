"""Fake SMS: persist a message the customer inbox can show."""
from __future__ import annotations

from app.database.store import Database
from app.models import Case, Garage, Policyholder, Sms
from app.models.enums import ActionType, CoverageDecision
from app.services._clock import now_iso


class NotifyService:
    def __init__(self, db: Database):
        self.db = db

    def draft(self, case: Case, policyholder: Policyholder | None, garage: Garage | None) -> str:
        name = case.caller_name or (policyholder.name if policyholder else "there")
        case_id = case.id or "?"
        if case.coverage_decision == CoverageDecision.COVERED.value:
            if case.action_type == ActionType.MOBILE_REPAIR.value and garage:
                return (
                    f"Northline Assist: Hi {name.split()[0]}, you're covered. "
                    f"A mobile unit from {garage.name} is being arranged for your "
                    f"{case.issue_type.replace('_', ' ')}. Case #{case_id}. "
                    "A specialist confirmed this request."
                )
            if case.action_type == ActionType.TOW.value and garage:
                return (
                    f"Northline Assist: Hi {name.split()[0]}, you're covered for a tow. "
                    f"{garage.name} ({garage.address}) is the closest capable shop. "
                    f"Case #{case_id}. A specialist confirmed this request."
                )
            return (
                f"Northline Assist: Hi {name.split()[0]}, this looks covered. "
                f"We're lining up the next step. Case #{case_id}."
            )
        if case.coverage_decision == CoverageDecision.NEEDS_REVIEW.value:
            return (
                f"Northline Assist: Hi {name.split()[0]}, we need a specialist to finish "
                f"your roadside request (case #{case_id}). We have not sent a truck yet."
            )
        reason = (case.coverage_rationale or "this event is not a roadside benefit").split(".")[0]
        return (
            f"Northline Assist: Hi {name.split()[0]}, we could not confirm roadside coverage "
            f"({reason}). Case #{case_id}. A specialist will follow up. No truck has been sent."
        )

    def send(self, case: Case, body: str | None = None) -> Sms:
        text = (body if body is not None else case.sms_draft).strip()
        if not text:
            text = self.draft(case, None, None)
        sms = self.db.sms.add(
            Sms(
                id=None,
                case_id=case.id,
                to_phone=case.phone or "unknown",
                body=text,
                sent_at=now_iso(),
                status="sent",
            )
        )
        return sms

    def for_case(self, case_id: int) -> list[Sms]:
        return sorted(self.db.sms.find(case_id=case_id), key=lambda s: s.id or 0)

    def all(self) -> list[Sms]:
        return sorted(self.db.sms.all(), key=lambda s: s.id or 0, reverse=True)
