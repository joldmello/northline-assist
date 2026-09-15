from __future__ import annotations

from flask import Blueprint, jsonify

from app.api._helpers import body, dump, require, services

cases_bp = Blueprint("cases", __name__)


@cases_bp.get("/cases")
def list_cases():
    svc = services().cases
    rows = []
    for case in svc.list_cases():
        rows.append(dump(svc.payload(case)))
    return jsonify(rows)


@cases_bp.post("/cases")
def create_case():
    data = body()
    pid = data.get("policyholder_id")
    case = services().cases.start(int(pid) if pid else None)
    return jsonify(dump(services().cases.payload(case))), 201


@cases_bp.get("/cases/<int:case_id>")
def get_case(case_id: int):
    svc = services().cases
    return jsonify(dump(svc.payload(svc.get(case_id))))


@cases_bp.post("/cases/<int:case_id>/utterance")
def utterance(case_id: int):
    data = body()
    require(data, "text")
    result = services().cases.add_utterance(case_id, data["text"])
    payload = services().cases.payload(result["case"])
    return jsonify(
        {
            **dump(payload),
            "assistant_message": result["assistant_message"],
            "ready_to_assess": result["ready_to_assess"],
        }
    )


@cases_bp.post("/cases/<int:case_id>/assess")
def assess(case_id: int):
    svc = services().cases
    case = svc.assess(case_id)
    return jsonify(dump(svc.payload(case)))


@cases_bp.post("/cases/<int:case_id>/sms")
def send_sms(case_id: int):
    data = body()
    svc = services().cases
    case = svc.send_sms(case_id, data.get("body"))
    return jsonify(dump(svc.payload(case)))


@cases_bp.post("/cases/<int:case_id>/approve")
def approve(case_id: int):
    data = body()
    svc = services().cases
    case = svc.approve(case_id, data.get("note") or "")
    return jsonify(dump(svc.payload(case)))


@cases_bp.post("/cases/<int:case_id>/decline")
def decline(case_id: int):
    data = body()
    svc = services().cases
    case = svc.decline(case_id, data.get("note") or "")
    return jsonify(dump(svc.payload(case)))


@cases_bp.post("/cases/<int:case_id>/override")
def override(case_id: int):
    data = body()
    require(data, "decision")
    svc = services().cases
    case = svc.override(case_id, data["decision"], data.get("note") or "")
    return jsonify(dump(svc.payload(case)))
