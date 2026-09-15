"""Thin HTML UI. Forms post here; JSON from the pages drives voice and HITL."""
from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.services.container import Services
from app.services.exceptions import AppError

web_bp = Blueprint("web", __name__)


def _services() -> Services:
    return current_app.config["services"]


@web_bp.get("/")
def home():
    svc = _services()
    return render_template(
        "home.html",
        policyholders=svc.cases.list_policyholders(),
        llm_on=svc.llm.available,
        llm_model=svc.llm.model,
    )


@web_bp.post("/ui/start")
def ui_start():
    raw = request.form.get("policyholder_id") or ""
    pid = int(raw) if raw.strip() else None
    try:
        case = _services().cases.start(pid)
        return redirect(url_for("web.call", case_id=case.id))
    except AppError as exc:
        flash(exc.message, "error")
        return redirect(url_for("web.home"))


@web_bp.get("/call/<int:case_id>")
def call(case_id: int):
    svc = _services()
    case = svc.cases.get(case_id)
    payload = svc.cases.payload(case)
    return render_template(
        "call.html",
        case=case,
        policyholder=payload["policyholder"],
        garage=payload["garage"],
        llm_on=svc.llm.available,
        llm_model=svc.llm.model,
    )


@web_bp.get("/ops")
def ops():
    svc = _services()
    return render_template("ops.html", cases=svc.cases.list_cases())


@web_bp.get("/ops/<int:case_id>")
def ops_detail(case_id: int):
    svc = _services()
    case = svc.cases.get(case_id)
    payload = svc.cases.payload(case)
    return render_template(
        "ops_detail.html",
        case=case,
        policyholder=payload["policyholder"],
        garage=payload["garage"],
        sms_list=payload["sms"],
    )


@web_bp.get("/inbox")
def inbox():
    svc = _services()
    return render_template("inbox.html", messages=svc.notify.all())
