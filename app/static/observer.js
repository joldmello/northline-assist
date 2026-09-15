(function () {
  const root = document.querySelector("[data-case-id]");
  if (!root) return;
  const caseId = root.getAttribute("data-case-id");
  const CLOSED = new Set(["closed_covered", "closed_declined"]);

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function setError(msg) {
    const el = document.getElementById("action-error");
    if (!el) return;
    if (!msg) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    el.hidden = false;
    el.textContent = msg;
  }

  function setEnabled(id, on) {
    const el = document.getElementById(id);
    if (!el) return;
    el.disabled = !on;
  }

  function syncActions(c) {
    const review = c.status === "awaiting_human";
    const covered = c.coverage_decision === "covered";
    const closed = CLOSED.has(c.status);
    const hint = document.getElementById("action-hint");
    if (closed) {
      hint.textContent = "Case is closed. Actions are locked.";
      hint.className = "banner closed";
    } else if (review) {
      hint.textContent = covered
        ? "Coverage looks covered. Approve sends the member SMS and closes. You can still decline or override."
        : "Coverage is not confirmed. Decline sends the hold SMS and closes, or override to covered.";
      hint.className = "banner ready";
    } else {
      hint.textContent = "Intake or coverage still running. Specialist actions are locked until awaiting_human.";
      hint.className = "banner wait";
    }
    setEnabled("btn-override", review);
    setEnabled("btn-send", review && Boolean((c.sms_draft || "").trim()));
    setEnabled("btn-approve", review && covered);
    setEnabled("btn-decline", review);
    const draft = document.getElementById("sms-draft");
    const note = document.getElementById("human-note");
    const sel = document.getElementById("override-decision");
    if (draft) draft.disabled = !review;
    if (note) note.disabled = !review;
    if (sel) sel.disabled = !review;
  }

  function render(payload) {
    const c = payload.case || {};
    const garage = payload.garage;
    const transcriptEl = document.getElementById("transcript");
    if (transcriptEl && c.transcript) {
      transcriptEl.innerHTML = c.transcript
        .map(
          (m) =>
            `<div class="msg ${m.role}"><span class="who">${m.role}</span>${escapeHtml(
              m.text
            )}</div>`
        )
        .join("");
      transcriptEl.scrollTop = transcriptEl.scrollHeight;
    }
    const pill = document.getElementById("status-pill");
    if (pill) {
      pill.className = "pill " + (c.status || "");
      pill.textContent = c.status || "";
    }
    const slots = {
      caller_name: c.caller_name,
      vehicle: c.vehicle,
      location_text: c.location_text,
      issue_type: c.issue_type,
      situation: c.situation,
      listed_driver: c.listed_driver,
    };
    Object.entries(slots).forEach(([key, val]) => {
      const el = document.querySelector(`[data-slot="${key}"]`);
      if (el) el.textContent = val || "—";
    });
    const dec = document.getElementById("cov-decision");
    if (dec)
      dec.innerHTML = `<strong>${escapeHtml(c.coverage_decision || "pending")}</strong> <span class="muted" id="cov-conf">${escapeHtml(
        c.coverage_confidence || ""
      )}</span>`;
    const rat = document.getElementById("cov-rationale");
    if (rat) rat.textContent = c.coverage_rationale || "";
    const cites = document.getElementById("cov-cites");
    if (cites) {
      cites.innerHTML = (c.coverage_citations || [])
        .map((x) => `<li><strong>${escapeHtml(x.section)}</strong> — ${escapeHtml(x.quote)}</li>`)
        .join("");
    }
    const noteView = document.getElementById("human-note-view");
    if (noteView) {
      noteView.textContent = c.human_note ? "Specialist note: " + c.human_note : "";
    }
    const nba = document.getElementById("nba");
    if (nba) nba.innerHTML = `<strong>${escapeHtml(c.action_type || "—")}</strong>`;
    const nbar = document.getElementById("nba-r");
    if (nbar) nbar.textContent = c.action_rationale || "";
    const nbag = document.getElementById("nba-g");
    if (nbag) {
      nbag.textContent = garage
        ? `${garage.name} · ${garage.address} · ${garage.phone}`
        : "No garage selected.";
    }
    const draft = document.getElementById("sms-draft");
    if (draft && document.activeElement !== draft) draft.value = c.sms_draft || "";
    const sent = document.getElementById("sms-sent");
    if (sent) sent.textContent = "Sent: " + (c.sms_sent || "no");
    syncActions(c);
  }

  async function tick() {
    const res = await fetch(`/api/cases/${caseId}`);
    if (!res.ok) return;
    render(await res.json());
  }

  async function post(path, body) {
    setError("");
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(data.error || "Request failed");
      return;
    }
    render(data);
  }

  document.getElementById("btn-send").addEventListener("click", () => {
    post(`/api/cases/${caseId}/sms`, {
      body: document.getElementById("sms-draft").value,
    });
  });
  document.getElementById("btn-approve").addEventListener("click", () => {
    post(`/api/cases/${caseId}/approve`, {
      note: document.getElementById("human-note").value,
    });
  });
  document.getElementById("btn-decline").addEventListener("click", () => {
    post(`/api/cases/${caseId}/decline`, {
      note: document.getElementById("human-note").value,
    });
  });
  document.getElementById("btn-override").addEventListener("click", () => {
    const note = document.getElementById("human-note").value.trim();
    if (!note) {
      setError("Add a specialist note before overriding coverage.");
      return;
    }
    post(`/api/cases/${caseId}/override`, {
      decision: document.getElementById("override-decision").value,
      note,
    });
  });

  tick();
  setInterval(tick, 1000);
})();
