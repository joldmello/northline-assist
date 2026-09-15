"""Case lifecycle. Routes never call the LLM or CSV layer directly."""
from __future__ import annotations

from app.database.store import Database
from app.models import Case, Garage, Policyholder
from app.models.enums import ActionType, CaseStatus, CoverageDecision
from app.services._clock import now_iso
from app.services.conversation_service import ConversationService, merge_slots
from app.services.coverage_service import CoverageService
from app.services.dispatch_service import DispatchService
from app.services.exceptions import ConflictError, NotFoundError, ValidationError
from app.services.notify_service import NotifyService

OPEN_STATUSES = {
    CaseStatus.NEW.value,
    CaseStatus.GATHERING.value,
    CaseStatus.ASSESSING.value,
    CaseStatus.RECOMMENDING.value,
    CaseStatus.NOTIFYING.value,
    CaseStatus.AWAITING_HUMAN.value,
}

CLOSED = {CaseStatus.CLOSED_COVERED.value, CaseStatus.CLOSED_DECLINED.value}


def _one_line(text: str, limit: int = 800) -> str:
    return " ".join((text or "").split())[:limit]


class CaseService:
    def __init__(
        self,
        db: Database,
        conversation: ConversationService,
        coverage: CoverageService,
        dispatch: DispatchService,
        notify: NotifyService,
    ):
        self.db = db
        self.conversation = conversation
        self.coverage = coverage
        self.dispatch = dispatch
        self.notify = notify

    def list_policyholders(self) -> list[Policyholder]:
        return self.db.policyholders.all()

    def get_policyholder(self, policyholder_id: int) -> Policyholder:
        row = self.db.policyholders.get(policyholder_id)
        if not row:
            raise NotFoundError(f"policyholder {policyholder_id} not found")
        return row

    def list_cases(self) -> list[Case]:
        return sorted(self.db.cases.all(), key=lambda c: c.id or 0, reverse=True)

    def get(self, case_id: int) -> Case:
        row = self.db.cases.get(case_id)
        if not row:
            raise NotFoundError(f"case {case_id} not found")
        return row

    def start(self, policyholder_id: int | None = None) -> Case:
        holder = None
        if policyholder_id:
            holder = self.get_policyholder(policyholder_id)
        now = now_iso()
        greeting = (
            "Hi, this is Northline Assist. I can help with your roadside situation. "
            "What's going on with the vehicle?"
        )
        case = Case(
            id=None,
            status=CaseStatus.GATHERING.value,
            policyholder_id=holder.id if holder else None,
            caller_name=holder.name if holder else "",
            phone=holder.phone if holder else "",
            vehicle=holder.vehicle if holder else "",
            location_text=holder.address if holder else "",
            lat=holder.lat if holder else None,
            lng=holder.lng if holder else None,
            listed_driver="unknown",
            transcript=[{"role": "assistant", "text": greeting, "ts": now}],
            slots={},
            created_at=now,
            updated_at=now,
        )
        return self.db.cases.add(case)

    def add_utterance(self, case_id: int, text: str) -> dict:
        case = self.get(case_id)
        if case.status in CLOSED:
            raise ConflictError("this case is already closed")
        text = (text or "").strip()
        if not text:
            raise ValidationError("utterance text is required")
        if case.status == CaseStatus.NEW.value:
            case.status = CaseStatus.GATHERING.value
        now = now_iso()
        case.transcript = list(case.transcript) + [{"role": "user", "text": text, "ts": now}]
        holder = self._holder(case)
        reply = self.conversation.reply(case, text, holder)
        slots = merge_slots(case.slots, reply.get("slots") or {})
        case.slots = slots
        self._apply_slots(case, slots)
        assistant_text = reply["assistant_message"]
        case.transcript = list(case.transcript) + [
            {"role": "assistant", "text": assistant_text, "ts": now_iso()}
        ]
        case.status = CaseStatus.GATHERING.value
        case.updated_at = now_iso()
        saved = self.db.cases.update(case.id, case.changes())
        return {
            "case": saved,
            "assistant_message": assistant_text,
            "ready_to_assess": bool(reply.get("ready_to_assess")),
        }

    def assess(self, case_id: int) -> Case:
        case = self.get(case_id)
        if case.status in CLOSED:
            raise ConflictError("this case is already closed")
        case.status = CaseStatus.ASSESSING.value
        case.updated_at = now_iso()
        self.db.cases.update(case.id, case.changes())

        holder = self._holder(case)
        result = self.coverage.assess(case, holder)
        case.coverage_decision = result["decision"]
        case.coverage_rationale = result.get("rationale") or ""
        case.coverage_citations = result.get("citations") or []
        case.coverage_confidence = result.get("confidence") or ""

        garage = None
        if case.coverage_decision == CoverageDecision.COVERED.value:
            case.status = CaseStatus.RECOMMENDING.value
            rec = self.dispatch.recommend(case)
            case.action_type = rec["action_type"]
            garage = rec.get("garage")
            case.garage_id = garage.id if garage else None
            case.action_rationale = rec.get("rationale") or ""
        else:
            case.action_type = ActionType.NONE.value
            case.garage_id = None
            case.action_rationale = "No dispatch while coverage is not confirmed."

        case.status = CaseStatus.NOTIFYING.value
        case.sms_draft = self.notify.draft(case, holder, garage)
        case.sms_sent = "no"
        case.transcript = list(case.transcript) + [
            {
                "role": "system",
                "text": (
                    f"Coverage: {case.coverage_decision}. "
                    "Member SMS drafted — a specialist must send it."
                ),
                "ts": now_iso(),
            }
        ]

        case.status = CaseStatus.AWAITING_HUMAN.value
        case.updated_at = now_iso()
        return self.db.cases.update(case.id, case.changes())

    def send_sms(self, case_id: int, body: str | None = None) -> Case:
        case = self.get(case_id)
        self._require_review(case)
        text = body if body is not None else case.sms_draft
        if body is not None:
            case.sms_draft = body
        if not (text or "").strip():
            raise ValidationError("SMS body is empty")
        self.notify.send(case, text)
        case.sms_sent = "yes"
        case.updated_at = now_iso()
        return self.db.cases.update(case.id, case.changes())

    def approve(self, case_id: int, note: str = "") -> Case:
        case = self.get(case_id)
        self._require_review(case)
        if case.coverage_decision != CoverageDecision.COVERED.value:
            raise ConflictError("Approve is only for covered cases. Decline or override first.")
        case.human_note = note or case.human_note
        if case.sms_sent != "yes":
            self.notify.send(case, case.sms_draft)
            case.sms_sent = "yes"
            case.transcript = list(case.transcript) + [
                {
                    "role": "system",
                    "text": "Specialist approved. Member SMS sent.",
                    "ts": now_iso(),
                }
            ]
        case.status = CaseStatus.CLOSED_COVERED.value
        case.updated_at = now_iso()
        return self.db.cases.update(case.id, case.changes())

    def decline(self, case_id: int, note: str = "") -> Case:
        case = self.get(case_id)
        self._require_review(case)
        case.coverage_decision = CoverageDecision.NOT_COVERED.value
        case.action_type = ActionType.NONE.value
        case.garage_id = None
        case.action_rationale = "No dispatch — specialist declined coverage."
        case.human_note = note
        if note:
            case.coverage_rationale = _one_line(
                f"Human specialist declined. {note} {case.coverage_rationale}"
            )
        holder = self._holder(case)
        case.sms_draft = self.notify.draft(case, holder, None)
        self.notify.send(case, case.sms_draft)
        case.sms_sent = "yes"
        case.status = CaseStatus.CLOSED_DECLINED.value
        case.updated_at = now_iso()
        return self.db.cases.update(case.id, case.changes())

    def override(self, case_id: int, decision: str, note: str = "") -> Case:
        case = self.get(case_id)
        self._require_review(case)
        if decision not in (
            CoverageDecision.COVERED.value,
            CoverageDecision.NOT_COVERED.value,
            CoverageDecision.NEEDS_REVIEW.value,
        ):
            raise ValidationError("decision must be covered, not_covered, or needs_review")
        note = (note or "").strip()
        if not note:
            raise ValidationError("a note is required to override coverage")
        prior = case.coverage_decision
        original = case.coverage_rationale
        case.coverage_decision = decision
        case.human_note = note
        case.coverage_rationale = _one_line(
            f"Human override: {prior or 'pending'} → {decision}. {note}. Original: {original}"
        )
        garage = None
        if decision == CoverageDecision.COVERED.value:
            rec = self.dispatch.recommend(case)
            case.action_type = rec["action_type"]
            garage = rec.get("garage")
            case.garage_id = garage.id if garage else None
            case.action_rationale = rec.get("rationale") or ""
        else:
            case.action_type = ActionType.NONE.value
            case.garage_id = None
            case.action_rationale = "No dispatch while coverage is not confirmed."
        holder = self._holder(case)
        case.sms_draft = self.notify.draft(case, holder, garage)
        case.sms_sent = "no"
        case.transcript = list(case.transcript) + [
            {
                "role": "system",
                "text": f"Human override: {prior or 'pending'} → {decision}. {note}",
                "ts": now_iso(),
            }
        ]
        case.status = CaseStatus.AWAITING_HUMAN.value
        case.updated_at = now_iso()
        saved = self.db.cases.update(case.id, case.changes())
        if saved is None:
            raise ConflictError("could not save override")
        return saved

    def _require_review(self, case: Case) -> None:
        if case.status in CLOSED:
            raise ConflictError("this case is already closed")
        if case.status != CaseStatus.AWAITING_HUMAN.value:
            raise ConflictError(
                "specialist actions unlock after coverage check (status must be awaiting_human)"
            )

    def payload(self, case: Case) -> dict:
        holder = self._holder(case)
        garage = self.db.garages.get(case.garage_id) if case.garage_id else None
        return {
            "case": case,
            "policyholder": holder,
            "garage": garage,
            "sms": self.notify.for_case(case.id) if case.id else [],
        }

    def _holder(self, case: Case) -> Policyholder | None:
        if not case.policyholder_id:
            return None
        return self.db.policyholders.get(case.policyholder_id)

    def _apply_slots(self, case: Case, slots: dict) -> None:
        if slots.get("caller_name"):
            case.caller_name = slots["caller_name"]
        if slots.get("vehicle"):
            case.vehicle = slots["vehicle"]
        if slots.get("location_text"):
            case.location_text = slots["location_text"]
        if slots.get("issue_type"):
            case.issue_type = slots["issue_type"]
        if slots.get("situation"):
            case.situation = slots["situation"]
        if slots.get("listed_driver"):
            case.listed_driver = slots["listed_driver"]
