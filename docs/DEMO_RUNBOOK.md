# SevaSync BLR — 2-Minute Demo Runbook

> **CODE FREEZE READ-ONLY** — reflects exactly what is built in `/frontend/` and `/backend/`.
> Read this script aloud, word-for-word, while screen-recording at 1440×900.
> Practice once before recording. Total target: 2:00 minutes.

---

## Pre-Flight Checklist (do before hitting record)

```bash
# Terminal 1 — Backend
cd /Users/sumit/sevasync-blr/backend
../.venv/bin/uvicorn main:app --reload --port 8000
# Confirm: "SevaSync BLR backend started — 3 policy pack(s) active"

# Terminal 2 — Frontend
cd /Users/sumit/sevasync-blr/frontend
npm run dev
# Confirm: Local: http://localhost:5173/
```

- Open **Chrome** at `http://localhost:5173`
- Confirm the blue Header Tag reads **"3 Civic Policy Packs Active"**
- Confirm the three Column tiles are visible: *Speak & Scan* | *Live 4-Agent Reasoning Trace* | *Solve & Scale*
- Keep the file `data/sandbox_mocks/images/sample_sas_tax_receipt.png` ready on your Desktop for drag-and-drop

---

## 🎬 Recording Script

---

### `0:00 – 0:15` · Hook

**Screen:** Full browser window showing the IBM Bobathon header + 3-column Carbon UI

> **SAY:**
> *"Every day, thousands of Bengaluru citizens get their BBMP e-Khata, BESCOM Gruha Jyothi, and Sakala applications rejected — not because their case is weak, but because of fixable documentation bugs. SevaSync BLR is an agentic AI civic co-pilot that catches every bug before you submit. Watch."*

**ACTION:** No clicks. Let the UI speak.

---

### `0:15 – 0:40` · Speak & Scan — Column 1

**Screen:** Focus on the left column "Speak & Scan" tile

> **SAY:**
> *"Column 1: Speak & Scan. A citizen speaks, or we click a preset."*

**ACTION 1 — Click Demo Preset:**
Click the tertiary button labelled **"e-Khata Mismatch (Mahadevapura)"**

> **SAY:**
> *"I'll click the e-Khata demo preset — this fires a real POST to our Vision OCR endpoint."*

> *(pause 1 second for the ~400ms simulated OCR latency)*

> **SAY:**
> *"The document fields are extracted automatically. Notice: applicant name 'R. Kumar' versus document owner 'Ramesh Kumar S' — a classic initial abbreviation mismatch. And the ward claimed is 'Koramangala' for a PIN code that maps to BTM Layout. Three bugs, instantly visible."*

**Screen shows:** Structured list with `applicant_name: R. Kumar`, `doc_owner_name: Ramesh Kumar S`, `ward_claimed: Koramangala`, `built_up_area_sqft: 1150`. Three red HIGH visual flag chips visible.

---

### `0:40 – 1:15` · Live 4-Agent Reasoning Trace — Column 2

**ACTION 2 — Click Run Audit:**
Click the primary button **"Run 4-Agent Pre-Flight Audit"** (blue, full-width, ArrowRight icon, bottom of Column 1)

> **SAY:**
> *"Now I hit Run — this triggers our 4-agent sequential pipeline on the FastAPI backend."*

> *(pause ~2 seconds for pipeline + live India Post API call)*

**Screen shows:** Column 2 "Live 4-Agent Reasoning Trace" populates

> **SAY:**
> *"Agent 1 routed to the BBMP e-Khata policy in under 10 milliseconds using keyword matching."*

> *"Agent 2 — the Pre-Flight Discrepancy Validator — caught three critical issues: the name mismatch, the ward mismatch, and the built-up area exceeding the 5% variance threshold."*

> *"Agent 3 — the Live Bengaluru Geo Router — just called api.postalpincode.in in real-time."* *(point at the teal "Live India Post API" badge)* *"PIN 560048 resolves to BTM Layout, Bommanahalli Zone, ARO Bommanahalli office. Ward mismatch confirmed."*

> *"The readiness score is 20 out of 100 — BLOCKED. Three critical fixes required before this application can be submitted."*

**Screen shows:** Red "⛔ BLOCKED — FIX REQUIRED" tag, ProgressBar at ~20%, 3 error InlineNotification discrepancy cards, teal "Live India Post API" badge in geo card.

---

### `1:15 – 1:35` · Solve & Scale + Civic-as-Code Hot-Plug — Column 3

**Screen:** Focus on Column 3 "Solve & Scale" tile

> **SAY:**
> *"Column 3: Solve & Scale. Agent 4 generated a step-by-step fix checklist and a fully bilingual government draft."*

**ACTION 3 — Click Kannada tab:**
Click the **"ಕನ್ನಡ (Kannada)"** tab in the Bilingual Draft Viewer

> **SAY:**
> *"The Kannada affidavit draft is ready — citizens can copy it in one click or hear it read aloud in their language."*

**ACTION 4 — Click Read Aloud (Kannada):**
Click the **"Read Aloud"** secondary button under the Kannada tab

> **SAY:**
> *"Now — the Civic-as-Code scalability proof."*

**ACTION 5 — Click "Plug-in New Service":**
Click the primary button **"Plug-in New Service"** in the top-right header

**ACTION 6 — Load e-Swathu:**
In the modal that opens, click **"Load e-Swathu Form 11A JSON"**

**ACTION 7 — Submit:**
Click **"Register Policy Pack"**

> **SAY:**
> *"I just hot-loaded Karnataka e-Swathu Form 11A — a fourth civic service — with zero code changes, zero server restart. The policy count tag just changed from 3 to 4."*

**Screen shows:** Blue tag in header updates to **"4 Civic Policy Packs Active"**

---

### `1:35 – 1:50` · IBM Bob Workflow

**Screen:** Switch to show `/docs/ibm-bob-workflow/` screenshots or the backend terminal

> **SAY:**
> *"This entire backend — the 4-agent pipeline, all 3 policy packs, the geo resolver, the Pydantic models, and 4 passing pytest tests — was scaffolded end-to-end by IBM Bob in Plan mode and Agent mode, reading AGENTS.md as the contract. No manual boilerplate. The pytest suite confirms every agent runs deterministically, with no LLM key required."*

**Screen shows (optional):** Terminal output of `pytest backend/tests/test_agents.py -v` showing `4 passed`

---

### `1:50 – 2:00` · Close

**Screen:** Return to full browser — header, 3 columns, "4 Civic Policy Packs Active" tag

> **SAY:**
> *"SevaSync BLR: Speak. Scan. Solve. Agentic AI for 10 million Bengaluru citizens — built in one day with IBM Bob. Thank you."*

---

## Quick Reference Card

| Element | Exact Text / Path |
|---|---|
| Demo Preset 1 | `"e-Khata Mismatch (Mahadevapura)"` |
| Demo Preset 2 | `"BESCOM Gruha Jyothi Tenant (HSR)"` |
| Demo Preset 3 | `"Sakala SLA Delay Appeal (Hebbal)"` |
| Upload image (optional) | `data/sandbox_mocks/images/sample_sas_tax_receipt.png` |
| Run Audit button | `"Run 4-Agent Pre-Flight Audit"` (blue, ArrowRight icon) |
| Hot-plug button | `"Plug-in New Service"` (header, top-right) |
| Load stub button | `"Load e-Swathu Form 11A JSON"` (inside modal) |
| Register button | `"Register Policy Pack"` (modal primary action) |
| Policy count tag | `"N Civic Policy Packs Active"` (blue, header) |
| Bilingual tab | `"ಕನ್ನಡ (Kannada)"` |
| Read Aloud | `"Read Aloud"` (secondary, VolumeUp icon) |
| Submit | `"Submit to API Setu Sandbox"` (primary, Send icon) |
| Backend health | `http://localhost:8000/` → `{"policies_loaded": 3}` |
| API docs | `http://localhost:8000/docs` |
