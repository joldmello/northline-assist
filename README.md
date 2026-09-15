# Northline Assist

Roadside copilot for **Northline Mutual**. A member describes a disablement by voice or typed message. Assist extracts the facts, checks the member’s roadside endorsement, recommends mobile repair or a tow plus the nearest capable partner, and sends a member text. A specialist on the operations board can approve, decline, or override. Assist does **not** dispatch a truck.

```
api / web  →  services  →  models  →  database (CSV)
```

Gemini Flash fills two JSON boxes (next question + coverage decision). Everything else is rules.

## Run

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Put `GEMINI_API_KEY=` in `.env` (optional). Get a key at [Google AI Studio](https://aistudio.google.com/apikey). Without a key, intake uses keyword heuristics and coverage uses the same hard rules.

```powershell
python seed.py
python run.py
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Chrome is required for the microphone; typing always works. Sample members and garages are also created automatically on first start if `data/` is empty.

## Deploy on Render

1. Push this repo to GitHub (already `origin` → `northline-assist`).
2. In [Render](https://dashboard.render.com/), **New → Blueprint**, connect the repo. `render.yaml` fills in the web service.
3. When prompted, paste `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey). Leave it blank and intake still runs with keyword fallbacks.
4. After the first deploy, open `https://northline-assist.onrender.com/` (or the URL Render prints).

Manual path if you skip the Blueprint: **New → Web Service**, Python, build `pip install -r requirements.txt`, start `gunicorn run:app --bind 0.0.0.0:$PORT --workers 1 --threads 4`. One worker is required because the CSV store is process-local.

Free instances sleep after idle time. The CSV disk is ephemeral, so cases reset on a cold start; members and garages are re-seeded automatically.

| Surface | URL |
|---|---|
| Members / start a request | `/` |
| Voice call | `/call/<id>` |
| Operations board | `/ops` |
| Member messages (fake SMS) | `/inbox` |

## Example calls

Open **Members** and **Operations** in two windows.

**Maya Chen · Standard · flat tire**  
`I have a flat tire on Piedmont near 10th. I'm the listed driver.`  
Expect `covered`, `mobile_repair`, a Midtown-area van, SMS **drafted**. Specialist: **Approve & close** (that sends the text).

**James Okonkwo · Plus · collision**  
`I was in a fender-bender on Ponce in Decatur. I was driving. The F-150 won't move.`  
Expect Plus collision **tow only** (not body repair), a Decatur-area shop, SMS drafted. **Approve** sends it.

**Maya Chen · unlisted driver**  
`My brother Tom is driving and we have a dead battery on Piedmont.`  
Expect `not_covered`, SMS drafted. Specialist **Decline & close** (sends the hold text), or override with a note then Approve.

Derek Walsh (lapsed) and an unknown caller both hold for a specialist (`not_covered` / `needs_review`).

## What the model is allowed to do

- Ask the next intake question and fill extracted facts (name, vehicle, location, issue, listed driver).
- Write a coverage JSON object from retrieved policy excerpts. Hard rules win on lapsed / unlisted / racing / Standard-collision.

It is **not** allowed to pick the next workflow box, invent a shop, auto-close a denial, or dispatch a truck. Tow vs. mobile and garage selection are a rule table plus haversine.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/cases` | start (`policyholder_id` optional) |
| GET | `/api/cases`, `/api/cases/{id}` | list / get + member + garage + SMS |
| POST | `/api/cases/{id}/utterance` | `{ "text": "..." }` |
| POST | `/api/cases/{id}/assess` | coverage + next action + draft SMS (not sent) |
| POST | `/api/cases/{id}/sms` | send / resend |
| POST | `/api/cases/{id}/approve` | close a covered case |
| POST | `/api/cases/{id}/decline` | force not_covered, send, close |
| POST | `/api/cases/{id}/override` | `{ "decision", "note" }` — does not close |

## Layout

```
app/           Flask factory, api, web, services, models, database
app/static/    CSS, voice/ops JS, Northline Mutual mark
data_seed/     policy markdown (committed)
data/          runtime CSVs (gitignored; created by seed.py)
docs/          design.html, prd.html (not linked from the app)
PRD.md         two-page product requirements
```

Open the HTML files in `docs/` from disk. `docs/prd.html` prints to two pages (Ctrl+P → PDF, letter).
