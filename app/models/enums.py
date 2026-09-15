"""Case lifecycle. The LLM fills slots inside these boxes; it does not pick the next box."""
from __future__ import annotations

from enum import Enum


class CaseStatus(str, Enum):
    NEW = "new"
    GATHERING = "gathering"
    ASSESSING = "assessing"
    RECOMMENDING = "recommending"
    NOTIFYING = "notifying"
    AWAITING_HUMAN = "awaiting_human"
    CLOSED_COVERED = "closed_covered"
    CLOSED_DECLINED = "closed_declined"


class IssueType(str, Enum):
    FLAT_TIRE = "flat_tire"
    BATTERY = "battery"
    LOCKOUT = "lockout"
    COLLISION = "collision"
    ENGINE = "engine"
    OTHER = "other"


class CoverageDecision(str, Enum):
    COVERED = "covered"
    NOT_COVERED = "not_covered"
    NEEDS_REVIEW = "needs_review"


class ActionType(str, Enum):
    MOBILE_REPAIR = "mobile_repair"
    TOW = "tow"
    NONE = "none"
