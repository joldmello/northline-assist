(function () {
  const root = document.querySelector("[data-case-id]");
  if (!root) return;
  const caseId = root.getAttribute("data-case-id");
  const transcriptEl = document.getElementById("transcript");
  const statusEl = document.getElementById("voice-status");
  const micBtn = document.getElementById("mic");
  const ttsBox = document.getElementById("tts");
  const assessBtn = document.getElementById("assess");
  const typeForm = document.getElementById("type-form");
  const typed = document.getElementById("typed");
  let busy = false;

  function setStatus(text) {
    if (statusEl) statusEl.textContent = text;
  }

  function renderTranscript(messages) {
    if (!transcriptEl || !messages) return;
    transcriptEl.innerHTML = messages
      .map(
        (m) =>
          `<div class="msg ${m.role}"><span class="who">${m.role}</span>${escapeHtml(
            m.text
          )}</div>`
      )
      .join("");
    transcriptEl.scrollTop = transcriptEl.scrollHeight;
  }

  function renderSlots(payload) {
    const c = payload.case || {};
    const map = {
      caller_name: c.caller_name,
      vehicle: c.vehicle,
      location_text: c.location_text,
      issue_type: c.issue_type,
      listed_driver: c.listed_driver,
      status: c.status,
    };
    Object.entries(map).forEach(([key, val]) => {
      const el = document.querySelector(`[data-slot="${key}"]`);
      if (el) el.textContent = val || "—";
    });
    if (c.coverage_decision) {
      const card = document.getElementById("result-card");
      if (card) card.hidden = false;
      const d = document.getElementById("result-decision");
      const a = document.getElementById("result-action");
      if (d) d.innerHTML = `<strong>${escapeHtml(c.coverage_decision)}</strong>`;
      if (a) a.textContent = c.action_rationale || c.coverage_rationale || "";
    }
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function speak(text) {
    if (!ttsBox || !ttsBox.checked || !text || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.02;
    window.speechSynthesis.speak(u);
  }

  async function sendUtterance(text) {
    if (busy || !text.trim()) return;
    busy = true;
    setStatus("Thinking…");
    try {
      const res = await fetch(`/api/cases/${caseId}/utterance`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "utterance failed");
      renderTranscript(data.case.transcript);
      renderSlots(data);
      speak(data.assistant_message);
      if (data.ready_to_assess) {
        setStatus("Facts look complete. Finish the call to run coverage.");
        assessBtn.classList.remove("secondary");
      } else {
        setStatus("Listening.");
      }
    } catch (err) {
      setStatus(err.message || "Request failed");
    } finally {
      busy = false;
    }
  }

  async function assess() {
    if (busy) return;
    busy = true;
    setStatus("Checking the policy…");
    try {
      const res = await fetch(`/api/cases/${caseId}/assess`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "assess failed");
      renderTranscript(data.case.transcript);
      renderSlots(data);
      setStatus("Coverage complete. A specialist must send the member message from Operations.");
    } catch (err) {
      setStatus(err.message || "Assess failed");
    } finally {
      busy = false;
    }
  }

  typeForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = typed.value;
    typed.value = "";
    sendUtterance(text);
  });
  assessBtn.addEventListener("click", assess);

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    setStatus("This browser has no Web Speech API. Type instead (Chrome recommended).");
    micBtn.disabled = true;
    return;
  }

  const rec = new SpeechRecognition();
  rec.lang = "en-US";
  rec.interimResults = false;
  rec.continuous = false;

  rec.onresult = (event) => {
    const text = event.results[0][0].transcript;
    sendUtterance(text);
  };
  rec.onerror = (event) => {
    micBtn.classList.remove("hot");
    setStatus("Mic: " + event.error);
  };
  rec.onend = () => micBtn.classList.remove("hot");

  micBtn.addEventListener("click", () => {
    try {
      rec.start();
      micBtn.classList.add("hot");
      setStatus("Listening… speak, then pause.");
    } catch (err) {
      setStatus("Mic busy. Try again.");
    }
  });
})();
