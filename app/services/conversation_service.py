"""Voice-agent turn: extract slots and produce the next question.

Uses Gemini Flash when a key is present; otherwise a scripted fallback so
intake still runs without a key.
"""
from __future__ import annotations

import json
import re

from app.models import Case, Policyholder
from app.services.llm_service import LLMService

SLOT_KEYS = (
    "caller_name",
    "vehicle",
    "location_text",
    "issue_type",
    "situation",
    "listed_driver",
)

ISSUE_TYPES = {
    "flat_tire",
    "battery",
    "lockout",
    "collision",
    "engine",
    "other",
}

SYSTEM = """You are Northline Assist, a calm roadside-assistance voice agent for Northline Mutual.
You gather facts. You do not decide coverage. You do not promise a truck.

Return a JSON object with exactly:
{
  "assistant_message": "one short spoken sentence or two, no markdown",
  "slots": {
    "caller_name": "",
    "vehicle": "",
    "location_text": "",
    "issue_type": "flat_tire|battery|lockout|collision|engine|other|",
    "situation": "",
    "listed_driver": "yes|no|unknown"
  },
  "ready_to_assess": false
}

Rules:
- Only fill a slot when the caller actually provided it. Leave unknown/empty otherwise.
- issue_type: flat tire / puncture → flat_tire; jump / dead battery → battery; locked out / keys → lockout; crash / accident / hit / collision / fender-bender → collision; engine / won't start / overheat / transmission → engine; else other.
- listed_driver is "no" if someone other than a listed driver is operating the vehicle (brother, friend, valet, unlisted). "yes" if the caller is a listed driver and is driving. Otherwise "unknown".
- If they mention racing, a track, a drag strip, or timed runs, put that in situation and keep gathering other slots.
- Ask only for the most important missing slot. Be brief. Do not ask for policy numbers if we already have the member record.
- ready_to_assess is true only when issue_type is set AND (location_text or a known member address) AND we know whether the driver is listed or the caller said they don't know.
- Never discuss coverage, garages, or ETAs. Say you will check the policy after you have the facts.
"""


def merge_slots(existing: dict, incoming: dict) -> dict:
    merged = dict(existing or {})
    for key in SLOT_KEYS:
        if key not in incoming:
            continue
        value = incoming.get(key)
        if value is None or value == "":
            continue
        if key == "listed_driver" and value == "unknown" and merged.get(key) in ("yes", "no"):
            continue
        if key == "issue_type" and value not in ISSUE_TYPES:
            continue
        merged[key] = value
    return merged


def slots_ready(slots: dict, case: Case) -> bool:
    issue = slots.get("issue_type") or case.issue_type
    location = slots.get("location_text") or case.location_text
    driver = slots.get("listed_driver") or case.listed_driver or "unknown"
    return bool(issue) and bool(location) and driver in ("yes", "no")


class ConversationService:
    def __init__(self, llm: LLMService):
        self.llm = llm

    def reply(
        self,
        case: Case,
        user_text: str,
        policyholder: Policyholder | None,
    ) -> dict:
        if self.llm.available:
            result = self._llm_reply(case, user_text, policyholder)
            if result is not None:
                return result
        return self._fallback_reply(case, user_text, policyholder)

    def _llm_reply(
        self,
        case: Case,
        user_text: str,
        policyholder: Policyholder | None,
    ) -> dict | None:
        member = "unknown caller, no policy on file"
        if policyholder:
            member = (
                f"name={policyholder.name}; phone={policyholder.phone}; "
                f"policy={policyholder.policy_number}; status={policyholder.status}; "
                f"vehicle={policyholder.vehicle}; address={policyholder.address}; "
                f"listed_drivers={policyholder.listed_drivers}; doc={policyholder.policy_doc}"
            )
        payload = {
            "member_record": member,
            "current_slots": case.slots,
            "known_fields": {
                "caller_name": case.caller_name,
                "vehicle": case.vehicle,
                "location_text": case.location_text,
                "issue_type": case.issue_type,
                "situation": case.situation,
                "listed_driver": case.listed_driver,
            },
            "transcript_tail": case.transcript[-8:],
            "latest_caller_utterance": user_text,
        }
        data = self.llm.complete_json(SYSTEM, json.dumps(payload, ensure_ascii=False))
        if not data:
            return None
        slots = merge_slots(case.slots, data.get("slots") or {})
        message = (data.get("assistant_message") or "").strip()
        if not message:
            return None
        ready = bool(data.get("ready_to_assess")) or slots_ready(slots, case)
        return {
            "assistant_message": message,
            "slots": slots,
            "ready_to_assess": ready,
        }

    def _fallback_reply(
        self,
        case: Case,
        user_text: str,
        policyholder: Policyholder | None,
    ) -> dict:
        slots = merge_slots(case.slots, _heuristic_slots(user_text, case, policyholder))
        missing = _missing(slots, case)
        if not missing:
            message = (
                "I have what I need. I will check your policy and the nearest help. "
                "Press finish call when you are ready."
            )
            ready = True
        else:
            message = _QUESTION[missing[0]]
            ready = False
        return {
            "assistant_message": message,
            "slots": slots,
            "ready_to_assess": ready,
        }


_QUESTION = {
    "issue_type": "What happened — flat tire, battery, lockout, a crash, or something else?",
    "location_text": "Where are you right now? A street, exit, or parking lot is enough.",
    "listed_driver": "Are you a driver listed on the Northline policy, or is someone else behind the wheel?",
    "caller_name": "What name should I use for this request?",
}


def _missing(slots: dict, case: Case) -> list[str]:
    issue = slots.get("issue_type") or case.issue_type
    location = slots.get("location_text") or case.location_text
    driver = slots.get("listed_driver") or case.listed_driver or "unknown"
    name = slots.get("caller_name") or case.caller_name
    ordered = []
    if not issue:
        ordered.append("issue_type")
    if not location:
        ordered.append("location_text")
    if driver not in ("yes", "no"):
        ordered.append("listed_driver")
    if not name:
        ordered.append("caller_name")
    return ordered


def _heuristic_slots(text: str, case: Case, policyholder: Policyholder | None) -> dict:
    lower = text.lower()
    found: dict = {}
    if re.search(r"flat|puncture|blowout|tire", lower):
        found["issue_type"] = "flat_tire"
    elif re.search(r"battery|jump.?start|won't start|wont start|dead batt", lower):
        found["issue_type"] = "battery"
    elif re.search(r"lock(ed)? out|keys? (in|inside)|locked the", lower):
        found["issue_type"] = "lockout"
    elif re.search(r"crash|accident|collision|fender.?bender|wreck|rear.?end|hit (a |the )?(car|truck|van)", lower):
        found["issue_type"] = "collision"
    elif re.search(r"engine|overheat|transmission|smoke", lower):
        found["issue_type"] = "engine"

    if re.search(r"brother|sister|friend|boyfriend|girlfriend|valet|not (me|listed)|someone else", lower):
        found["listed_driver"] = "no"
    elif re.search(
        r"listed driver|\bi am listed\b|\bi'm listed\b|it's me\b|it is me\b|"
        r"i'm the driver\b|i am the driver|i was driving|i'm driving",
        lower,
    ):
        found["listed_driver"] = "yes"
    elif policyholder and policyholder.name.lower() in lower:
        found["listed_driver"] = "yes"

    if re.search(r"race|racing|track|drag strip|timed run", lower):
        found["situation"] = (case.situation + " " + text).strip()
        found["listed_driver"] = found.get("listed_driver") or case.listed_driver

    found["situation"] = ((case.situation or "") + " " + text).strip()[:500]

    loc = _extract_location(text)
    if loc:
        found["location_text"] = loc

    if policyholder and not case.caller_name:
        found["caller_name"] = policyholder.name
        found["vehicle"] = policyholder.vehicle

    return found


def _extract_location(text: str) -> str:
    match = re.search(
        r"(?:on|at|near|i(?:'m| am) on) ([A-Z0-9][^.]{6,80})",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    if re.search(r"\b(i-?\d+|exit|peachtree|piedmont|downtown|midtown|decatur|buckhead)\b", text, re.I):
        return text.strip()[:120]
    return ""
