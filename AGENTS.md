# AGENTS.md — SevaSync BLR (IBM Bobathon)

## Project Overview
SevaSync BLR is a Track 01 Agentic AI civic co-pilot for Bengaluru enhanced with Voice AI (Web Speech API) and Vision OCR ("Speak, Scan, Solve"). It uses a Civic-as-Code architecture driven by pluggable JSON Policy Packs.

## Tech Stack & Standards
- Backend: Python 3.11+, FastAPI, Pydantic v2, httpx, pytest (runs on port 8000, CORS enabled for http://localhost:5173)
- Frontend: React + Vite + TypeScript + Tailwind CSS (runs on port 5173)
- Styling: Clean enterprise aesthetic using IBM Plex Sans font, primary accent #0f62fe, crisp neutral surfaces (#f4f4f4 / #ffffff), high-contrast status badges.
- Zero external database required: Read JSON files from /data/real_ground_truth and /data/sandbox_mocks.
- Graceful fallback mandatory: Every LLM/Vision call MUST fall back seamlessly to deterministic Python logic if an API key is missing or times out, so the demo never crashes.

## Strict Folder Ownership (No Merge Conflicts)
- /data/                         -> Owned by Dev 4
- /backend/main.py, agents.py    -> Owned by Dev 1
- /backend/vision.py, geo.py     -> Owned by Dev 2
- /frontend/                     -> Owned by Dev 3
- /docs/, README.md              -> Owned by Dev 5

## Shared API Contracts (DO NOT ALTER KEYS)
1. GET  /api/policies
   Returns: { "policies": [ { "id": str, "name": str, "department": str, "sakala_sla_days": int, "version": str } ] }

2. POST /api/policies/register
   Body: Full PolicyPack JSON object
   Returns: { "status": "registered", "total_policies": int, "policy_id": str }

3. POST /api/vision-extract
   Accepts multipart/form-data (file) OR query param ?sample_case_id=ekhata_mismatch|gruha_jyothi_tenant|sakala_sla_breach
   Returns: {
     "document_type": str,
     "extracted_fields": { "applicant_name": str, "doc_owner_name": str, "account_or_pid": str, "pincode": str, "ward_claimed": str, "built_up_area_sqft": int|null, "monthly_units": int|null, "application_date": str|null },
     "visual_flags": [ { "severity": "high|medium", "issue": str } ],
     "confidence": float,
     "engine": "multimodal_llm|deterministic_ocr_fallback"
   }

4. POST /api/orchestrate
   Body: { "query": str, "language": "en-IN|kn-IN|hi-IN", "extracted_fields": dict, "visual_flags": list, "policy_id": "auto|str" }
   Returns: {
     "selected_policy": { "id": str, "name": str, "department": str, "sakala_sla_days": int },
     "live_geo_check": { "pincode": str, "locality": str, "matched_ward": str, "gba_zone": str, "aro_office": str, "is_live_api": bool, "ward_mismatch": bool },
     "readiness_score": int,
     "status": "BLOCKED_FIX_REQUIRED|READY_TO_SUBMIT",
     "agent_trace": [ { "agent_name": str, "status": "pass|warn|fail", "latency_ms": int, "summary": str, "findings": [str] } ],
     "discrepancies": [ { "code": str, "severity": "critical|warning", "field": str, "message": str, "remediation": str } ],
     "fix_checklist": [str],
     "bilingual_draft": { "english": str, "kannada": str, "document_title": str },
     "sandbox_payload": dict
   }

5. POST /api/sandbox/submit
   Body: { "policy_id": str, "payload": dict }
   Returns: { "status": "SUBMITTED_SANDBOX", "sakala_gsc_id": str, "submitted_at": str, "sla_deadline_days": int, "adapter": "API_SETU_SANDBOX_V1" }