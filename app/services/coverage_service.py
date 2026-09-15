"""Coverage check: deterministic exclusions first, then RAG-lite + LLM JSON."""
from __future__ import annotations

import json
import re
from pathlib import Path

from app.config import Config
from app.models import Case, Policyholder
from app.models.enums import CoverageDecision, IssueType
from app.services.llm_service import LLMService

COVERED_STANDARD = {
    IssueType.FLAT_TIRE.value,
    IssueType.BATTERY.value,
    IssueType.LOCKOUT.value,
    IssueType.ENGINE.value,
}
COVERED_PLUS = COVERED_STANDARD | {IssueType.COLLISION.value}

SYSTEM = """You are a coverage analyst for Northline Mutual roadside. You may only use the policy excerpts provided.
Return JSON:
{
  "decision": "covered" | "not_covered" | "needs_review",
  "confidence": "high" | "medium" | "low",
  "rationale": "2-4 sentences. Quote the section ids you used.",
  "citations": [{"section": "§2.1 Flat tire", "quote": "short quote"}]
}
Rules:
- If excerpts do not support coverage, decision is not_covered or needs_review. Never invent a section.
- Collision is not covered on Standard. Collision tow is covered on Plus only.
- Unlisted drivers, racing/track, and lapsed policies are not covered.
- You do not dispatch. You only decide roadside coverage.
"""


def split_sections(markdown: str) -> list[dict]:
    sections: list[dict] = []
    heading = "Preamble"
    body: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("## ") or line.startswith("### "):
            if body:
                sections.append({"heading": heading, "body": "\n".join(body).strip()})
            heading = line.lstrip("#").strip()
            body = []
        else:
            body.append(line)
    if body:
        sections.append({"heading": heading, "body": "\n".join(body).strip()})
    return [s for s in sections if s["body"]]


def score_section(section: dict, query: str) -> int:
    words = {w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 3}
    text = (section["heading"] + " " + section["body"]).lower()
    return sum(1 for w in words if w in text)


class CoverageService:
    def __init__(self, llm: LLMService, policy_dir: str | None = None):
        self.llm = llm
        self.policy_dir = Path(policy_dir or Config.POLICY_DIR)

    def assess(self, case: Case, policyholder: Policyholder | None) -> dict:
        rules = self._rule_decision(case, policyholder)
        excerpts = self._retrieve(case, policyholder)
        llm_result = self._llm_decision(case, policyholder, excerpts, rules)
        if llm_result:
            # Never let the model override a hard exclusion.
            if rules["decision"] == CoverageDecision.NOT_COVERED.value:
                llm_result["decision"] = CoverageDecision.NOT_COVERED.value
                if rules["rationale"] and rules["rationale"] not in llm_result.get("rationale", ""):
                    llm_result["rationale"] = rules["rationale"] + " " + llm_result.get("rationale", "")
                cites = llm_result.get("citations") or []
                for c in rules.get("citations") or []:
                    if c not in cites:
                        cites.append(c)
                llm_result["citations"] = cites
            return llm_result
        return rules

    def _rule_decision(self, case: Case, policyholder: Policyholder | None) -> dict:
        situation = (case.situation or "").lower()
        issue = case.issue_type or (case.slots or {}).get("issue_type", "")

        if policyholder is None:
            return {
                "decision": CoverageDecision.NEEDS_REVIEW.value,
                "confidence": "low",
                "rationale": "No member record is linked. A human must identify the policy before any dispatch.",
                "citations": [{"section": "§1 Eligibility", "quote": "Benefits apply only while the policy is in force."}],
            }

        if policyholder.status != "active" or policyholder.policy_doc == "lapsed-notice":
            return {
                "decision": CoverageDecision.NOT_COVERED.value,
                "confidence": "high",
                "rationale": f"Policy {policyholder.policy_number} is not in force (status: {policyholder.status}). Roadside is unavailable until reinstatement.",
                "citations": [{"section": "§1 Status", "quote": "The policy is not in force. No roadside benefits apply."}],
            }

        if case.listed_driver == "no":
            return {
                "decision": CoverageDecision.NOT_COVERED.value,
                "confidence": "high",
                "rationale": "The operator is not a listed driver. Standard and Plus roadside both require a listed driver.",
                "citations": [{"section": "§1 Eligibility", "quote": "The operator must be a listed driver on the policy."}],
            }

        if re.search(r"rac(e|ing)|drag strip|closed track|timed run", situation):
            return {
                "decision": CoverageDecision.NOT_COVERED.value,
                "confidence": "high",
                "rationale": "The incident involves racing or a closed track, which both endorsements exclude.",
                "citations": [{"section": "§4 Exclusions", "quote": "Vehicles used in racing, timed runs, or on a closed track."}],
            }

        if case.listed_driver not in ("yes", "no"):
            return {
                "decision": CoverageDecision.NEEDS_REVIEW.value,
                "confidence": "medium",
                "rationale": "We do not yet know if the operator is a listed driver. A human should confirm before dispatch.",
                "citations": [{"section": "§1 Eligibility", "quote": "The operator of the vehicle must be a listed driver."}],
            }

        doc = policyholder.policy_doc
        if issue == IssueType.COLLISION.value and doc != "roadside-plus":
            return {
                "decision": CoverageDecision.NOT_COVERED.value,
                "confidence": "high",
                "rationale": "Collision disablement is not a Standard roadside event. Plus covers a tow only; this member has Standard.",
                "citations": [{"section": "§4 Exclusions", "quote": "Standard roadside does not dispatch for crash damage."}],
            }

        if issue == IssueType.COLLISION.value and doc == "roadside-plus":
            return {
                "decision": CoverageDecision.COVERED.value,
                "confidence": "high",
                "rationale": "Plus §2.5 covers a collision tow to the nearest qualified shop. This is not a body-repair settlement.",
                "citations": [{"section": "§2.5 Collision or overturn (tow only)", "quote": "Plus covers a tow to the nearest qualified body or mechanical shop."}],
            }

        allowed = COVERED_PLUS if doc == "roadside-plus" else COVERED_STANDARD
        if issue in allowed:
            label = issue.replace("_", " ")
            return {
                "decision": CoverageDecision.COVERED.value,
                "confidence": "high",
                "rationale": f"{label} is a covered roadside event on this member's {doc.replace('-', ' ')} endorsement, and the operator is a listed driver on an active policy.",
                "citations": [{"section": "§2 Covered events", "quote": "Covered when the insured vehicle is disabled on a public road."}],
            }

        if issue == IssueType.OTHER.value or not issue:
            return {
                "decision": CoverageDecision.NEEDS_REVIEW.value,
                "confidence": "low",
                "rationale": "The disablement type is not mapped to a named roadside event. A human should read the transcript.",
                "citations": [{"section": "§2 Covered events", "quote": "Named events: flat tire, battery, lockout, mechanical tow."}],
            }

        return {
            "decision": CoverageDecision.NOT_COVERED.value,
            "confidence": "medium",
            "rationale": f"Issue '{issue}' is not a covered roadside event on this endorsement.",
            "citations": [{"section": "§4 Exclusions", "quote": "Events not listed in §2 are not covered."}],
        }

    def _retrieve(self, case: Case, policyholder: Policyholder | None) -> list[dict]:
        name = "roadside-standard.md"
        if policyholder:
            name = f"{policyholder.policy_doc}.md"
        path = self.policy_dir / name
        if not path.exists():
            path = self.policy_dir / "roadside-standard.md"
        markdown = path.read_text(encoding="utf-8")
        sections = split_sections(markdown)
        query = " ".join(
            [
                case.issue_type or "",
                case.situation or "",
                case.listed_driver or "",
                "exclusion listed driver racing collision tow battery tire lockout lapsed",
            ]
        )
        ranked = sorted(sections, key=lambda s: score_section(s, query), reverse=True)
        return ranked[:5]

    def _llm_decision(
        self,
        case: Case,
        policyholder: Policyholder | None,
        excerpts: list[dict],
        rules: dict,
    ) -> dict | None:
        if not self.llm.available:
            return None
        payload = {
            "rule_hint": rules,
            "member": None
            if not policyholder
            else {
                "name": policyholder.name,
                "policy_number": policyholder.policy_number,
                "status": policyholder.status,
                "doc": policyholder.policy_doc,
                "listed_drivers": policyholder.listed_drivers,
            },
            "facts": {
                "issue_type": case.issue_type,
                "situation": case.situation,
                "listed_driver": case.listed_driver,
                "location": case.location_text,
                "vehicle": case.vehicle,
            },
            "excerpts": excerpts,
        }
        data = self.llm.complete_json(SYSTEM, json.dumps(payload, ensure_ascii=False))
        if not data:
            return None
        decision = data.get("decision")
        if decision not in (
            CoverageDecision.COVERED.value,
            CoverageDecision.NOT_COVERED.value,
            CoverageDecision.NEEDS_REVIEW.value,
        ):
            return None
        citations = data.get("citations") or rules.get("citations") or []
        clean = []
        for c in citations:
            if isinstance(c, dict) and c.get("section"):
                clean.append(
                    {"section": str(c.get("section")), "quote": str(c.get("quote") or "")[:240]}
                )
        return {
            "decision": decision,
            "confidence": data.get("confidence") or rules.get("confidence") or "medium",
            "rationale": (data.get("rationale") or rules.get("rationale") or "").strip(),
            "citations": clean or rules.get("citations") or [],
        }
