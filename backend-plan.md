# SevaSync BLR — Backend Build Plan

## Top-Level Overview

Build the complete Python/FastAPI backend for SevaSync BLR from scratch. The workspace currently contains only `AGENTS.md`. All `/backend/` and `/data/` directories, source files, and tests must be created.

The backend implements a **Civic-as-Code** architecture: JSON Policy Packs drive all validation logic, the server is stateless (no database), and every LLM call has a deterministic fallback. The 4-agent sequential pipeline in `/backend/agents.py` is the core business logic.

**Strict constraint**: API response shapes defined in AGENTS.md must not be altered.

---

## Sub-Tasks

---

### Sub-Task 1 — Seed data: JSON Policy Packs & sandbox mocks

**Intent**
Create realistic JSON Policy Pack files that the server loads at startup, and sandbox mock files used by vision-extract. These are the data contracts that all other sub-tasks depend on.

**Expected Outcomes**
- `/data/real_ground_truth/policy_pack_ekhata.json` — e-Khata mutation policy
- `/data/real_ground_truth/policy_pack_gruha_jyothi.json` — Gruha Jyothi electricity subsidy policy
- `/data/real_ground_truth/policy_pack_sakala.json` — Sakala grievance escalation policy
- `/data/sandbox_mocks/ekhata_mismatch.json` — extracted_fields for name mismatch case
- `/data/sandbox_mocks/gruha_jyothi_tenant.json` — extracted_fields for tenant occupancy case
- `/data/sandbox_mocks/sakala_sla_breach.json` — extracted_fields for SLA breach case

Each policy pack must contain at minimum: `id`, `name`, `department`, `sakala_sla_days`, `version`, `keywords` (list of English/Kannada/Kanglish terms for routing), `validation_rules` (list of rule objects with `rule_id`, `field`, `check`, `severity`, `message`, `remediation`).

**Todo List**
1. Create `/data/real_ground_truth/policy_pack_ekhata.json` with e-Khata fields: applicant_name/doc_owner_name fuzzy match rule, ePID/SAS ID presence rule, built-up area delta ≤ 5% rule, Sakala SLA 30 days.
2. Create `/data/real_ground_truth/policy_pack_gruha_jyothi.json` with BESCOM monthly_units ≤ 200 rule, RR number format (alpha-numeric forbidden), owner-occupancy declaration rule, Sakala SLA 15 days.
3. Create `/data/real_ground_truth/policy_pack_sakala.json` with SLA breach escalation rule (application_date + sla_days < today), Sakala SLA 7 days.
4. Create `/data/sandbox_mocks/ekhata_mismatch.json` with applicant_name="R. Kumar", doc_owner_name="Ramesh Kumar", account_or_pid="SAS123456", ward_claimed="Shivajinagar", pincode="560001".
5. Create `/data/sandbox_mocks/gruha_jyothi_tenant.json` with monthly_units=250, account_or_pid="KA2BLR123ABC" (alpha-numeric RR), ward_claimed="Koramangala", pincode="560034".
6. Create `/data/sandbox_mocks/sakala_sla_breach.json` with application_date set ~60 days ago, ward_claimed="Whitefield", pincode="560066".

**Relevant Context**
- AGENTS.md § extracted_fields schema
- AGENTS.md § POST /api/vision-extract sample_case_id values

**Status** — `[ ] pending`

---

### Sub-Task 2 — Pydantic models in `/backend/models.py`

**Intent**
Define all shared request/response Pydantic v2 models that `main.py`, `agents.py`, and `vision.py` import. Single source of truth for API shapes.

**Expected Outcomes**
- `PolicySummary`, `PoliciesResponse` for GET /api/policies
- `PolicyPack` (full pack with keywords + validation_rules) for POST /api/policies/register
- `OrchestrateRequest`, `OrchestrateResponse` and all nested types: `SelectedPolicy`, `LiveGeoCheck`, `AgentTraceEntry`, `Discrepancy`, `BilingualDraft`
- `SandboxSubmitRequest`, `SandboxSubmitResponse`
- `VisionExtractResponse`, `ExtractedFields`, `VisualFlag`

**Todo List**
1. Create `/backend/models.py` with all models using Pydantic v2 `model_config = ConfigDict(...)`.
2. Ensure `OrchestrateResponse.status` is `Literal["BLOCKED_FIX_REQUIRED", "READY_TO_SUBMIT"]`.
3. Ensure `AgentTraceEntry.status` is `Literal["pass", "warn", "fail"]`.
4. Ensure `Discrepancy.severity` is `Literal["critical", "warning"]`.
5. Ensure `VisualFlag.severity` is `Literal["high", "medium"]`.
6. `PolicyPack` must include `keywords: list[str]` and `validation_rules: list[dict]` beyond the summary fields.

**Relevant Context**
- AGENTS.md § Shared API Contracts (all 5 endpoints)

**Status** — `[ ] pending`

---

### Sub-Task 3 — Policy Registry & `/backend/main.py`

**Intent**
Create the FastAPI app, implement the in-memory `PolicyRegistry` (a module-level singleton), and wire up all five API routes: GET /api/policies, POST /api/policies/register, POST /api/orchestrate, POST /api/sandbox/submit, and mount the vision router.

**Expected Outcomes**
- `main.py` starts cleanly with `uvicorn main:app --reload` from the `/backend/` directory.
- Policy packs from `/data/real_ground_truth/policy_pack_*.json` are loaded into `PolicyRegistry` at startup via a FastAPI `lifespan` handler.
- GET /api/policies returns the correct summary list.
- POST /api/policies/register adds a new pack to the registry without restart.
- POST /api/sandbox/submit returns a 15-digit Sakala GSC ID (`GSC2026BLR` + 6 random digits), `submitted_at` ISO timestamp, correct `sla_deadline_days` from the registry.
- CORS is enabled for `http://localhost:5173`.
- `/api/vision-extract` router is mounted cleanly from `vision.py`.

**Todo List**
1. Create `/backend/main.py` with `lifespan` context manager that calls `registry.load_from_disk()`.
2. Implement `PolicyRegistry` class (or module-level dict + functions) with `load_from_disk()`, `get_all()`, `get_by_id()`, `register()`.
3. Implement GET `/api/policies` using registry.
4. Implement POST `/api/policies/register` — parse body as `PolicyPack`, call `registry.register()`, return `{"status": "registered", "total_policies": n, "policy_id": id}`.
5. Implement POST `/api/orchestrate` — delegate to `run_pipeline()` from `agents.py`.
6. Implement POST `/api/sandbox/submit` — generate `GSC2026BLR` + 6 random digits, look up `sla_deadline_days` from registry.
7. Add CORS middleware for `http://localhost:5173`.
8. Mount vision router: `app.include_router(vision_router, prefix="/api")`.

**Relevant Context**
- AGENTS.md § folder ownership: main.py owned by Dev 1
- Sub-Task 1 data files must exist first
- Sub-Task 2 models must exist first

**Status** — `[ ] pending`

---

### Sub-Task 4 — Geo stub in `/backend/geo.py`

**Intent**
Create a clean stub for `resolve_bengaluru_location()` that Agent 3 calls. Dev 2 owns this file long-term; the stub must be safe to overwrite — it only needs to return a valid `LiveGeoCheck`-shaped dict deterministically so Agent 3 never crashes.

**Expected Outcomes**
- `/backend/geo.py` exists with `resolve_bengaluru_location(pincode: str, ward_claimed: str) -> dict`.
- Returns a dict with keys: `pincode`, `locality`, `matched_ward`, `gba_zone`, `aro_office`, `is_live_api: False`, `ward_mismatch: bool`.
- Uses a small hardcoded lookup table for the three test pincodes (560001, 560034, 560066) and known demo wards.
- `ward_mismatch` is `True` when `ward_claimed` does not case-insensitively match `matched_ward`.
- Falls back gracefully for unknown pincodes (returns locality="Unknown", ward_mismatch=False).

**Todo List**
1. Create `/backend/geo.py` with a pincode→locality/ward/zone/ARO lookup dict for 560001, 560034, 560066 plus a catch-all.
2. Implement `resolve_bengaluru_location(pincode, ward_claimed)` that looks up the dict and computes `ward_mismatch`.
3. Add a module-level docstring: "Stub — owned by Dev 2. Replace with live BBMP/Google Maps call."

**Relevant Context**
- AGENTS.md § live_geo_check response shape
- Used by Agent 3 in agents.py

**Status** — `[ ] pending`

---

### Sub-Task 5 — 4-Agent pipeline in `/backend/agents.py`

**Intent**
Implement the sequential 4-agent pipeline that powers POST /api/orchestrate. Each agent is a pure Python function that receives context, appends to `agent_trace`, and passes enriched context to the next.

**Expected Outcomes**
- `run_pipeline(request: OrchestrateRequest, registry: PolicyRegistry) -> OrchestrateResponse`
- **Agent 1** selects the correct policy (keyword match first, LLM second with deterministic fallback).
- **Agent 2** runs all `validation_rules` from the selected pack plus checks `visual_flags`; emits `Discrepancy` objects.
  - Fuzzy name check: ratio < 0.75 between `applicant_name` and `doc_owner_name` → critical.
  - Missing ePID/SAS ID: `account_or_pid` empty or None → critical.
  - Built-up area delta > 5% (if two area values present) → critical.
  - BESCOM units > 200 → critical; alpha-numeric RR number → critical.
  - SLA elapsed: `application_date` + `sakala_sla_days` < today → warning.
- **Agent 3** calls `resolve_bengaluru_location()`, surfaces ward mismatch as a discrepancy if found.
- **Agent 4** computes `readiness_score` (100 − 20×critical − 10×warning, min 0), sets `status`, generates `fix_checklist`, produces `bilingual_draft` (English + Kannada), builds `sandbox_payload`.
- Each agent records `agent_name`, `status`, `latency_ms`, `summary`, `findings` in `agent_trace`.
- No LLM key required — all logic is deterministic. LLM enhancement is an optional future layer.

**Todo List**
1. Create `/backend/agents.py` with `run_pipeline()` function.
2. Implement `agent_1_policy_router()` — keyword scan against policy `keywords` list, fallback to first policy if no match.
3. Implement `agent_2_validator()` — iterate `validation_rules`, apply each check function, also process `visual_flags` from request.
4. Implement `agent_3_geo_router()` — call `resolve_bengaluru_location()`, conditionally add ward mismatch discrepancy.
5. Implement `agent_4_draft_agent()` — score, status, checklist, bilingual draft templates, sandbox_payload assembly.
6. Write bilingual draft templates: English correction letter + Kannada equivalent for each policy type.
7. Ensure `latency_ms` is measured with `time.perf_counter()` for each agent.

**Relevant Context**
- Sub-Task 2 models (OrchestrateRequest, OrchestrateResponse, all nested types)
- Sub-Task 1 policy validation_rules schema
- Sub-Task 4 geo stub
- AGENTS.md § POST /api/orchestrate full response shape

**Status** — `[ ] pending`

---

### Sub-Task 6 — Vision stub in `/backend/vision.py`

**Intent**
Create a minimal but functional vision router that satisfies the `/api/vision-extract` contract. Dev 2 owns the real OCR/LLM implementation; this stub returns deterministic data for the three known `sample_case_id` values and a fallback for uploaded files.

**Expected Outcomes**
- `/backend/vision.py` exports `router = APIRouter()`.
- `POST /vision-extract` (mounted under `/api` prefix in main.py) handles both `multipart/form-data` file upload and `?sample_case_id=` query param.
- Returns `VisionExtractResponse` with `engine="deterministic_ocr_fallback"`.
- For the three sample case IDs, loads and returns data from the sandbox mock JSON files.
- For file uploads, returns a generic placeholder response.

**Todo List**
1. Create `/backend/vision.py` with `router = APIRouter()`.
2. Implement `POST /vision-extract` endpoint with optional `file: UploadFile` and optional `sample_case_id: str` query param.
3. Load sandbox mock JSON for `ekhata_mismatch`, `gruha_jyothi_tenant`, `sakala_sla_breach` and return as VisionExtractResponse.
4. Add module-level docstring: "Stub — owned by Dev 2. Replace with multimodal LLM OCR."

**Relevant Context**
- Sub-Task 1 sandbox mock files
- Sub-Task 2 VisionExtractResponse model
- AGENTS.md § POST /api/vision-extract contract

**Status** — `[ ] pending`

---

### Sub-Task 7 — `requirements.txt` & project bootstrap

**Intent**
Provide a `requirements.txt` so `pip install -r requirements.txt` followed by `uvicorn main:app --reload` works immediately. Also create a minimal `/backend/__init__.py` (empty) and `/backend/tests/__init__.py`.

**Expected Outcomes**
- `/requirements.txt` lists: fastapi, uvicorn[standard], pydantic>=2.0, httpx, python-multipart, pytest, pytest-asyncio, httpx (for TestClient).
- `uvicorn backend.main:app --reload` (from repo root) or `uvicorn main:app --reload` (from `/backend/`) runs cleanly.

**Todo List**
1. Create `/requirements.txt` with pinned-compatible versions.
2. Create `/backend/__init__.py` (empty).
3. Create `/backend/tests/__init__.py` (empty).

**Relevant Context**
- Python 3.11+ per AGENTS.md

**Status** — `[ ] pending`

---

### Sub-Task 8 — Pytest tests in `/backend/tests/test_agents.py`

**Intent**
Write 4 deterministic pytest tests that exercise the full pipeline via FastAPI's `TestClient` (no server needed). Tests must pass without any LLM API key.

**Expected Outcomes**
All 4 tests pass with `pytest backend/tests/test_agents.py` from repo root:

1. **test_ekhata_name_mismatch_caught** — POST /api/orchestrate with e-Khata extracted fields (applicant_name="R. Kumar", doc_owner_name="Ramesh Kumar"). Assert response contains a discrepancy with `code` relating to name mismatch and `severity="critical"`.
2. **test_gruha_jyothi_tenant_check** — POST /api/orchestrate with Gruha Jyothi fields (monthly_units=250). Assert discrepancy for BESCOM units violation.
3. **test_sakala_sla_breach_escalation** — POST /api/orchestrate with application_date 60 days ago and sakala policy. Assert discrepancy for SLA breach.
4. **test_hot_register_new_policy** — POST /api/policies/register with a new minimal policy pack JSON. Assert `status="registered"` and `total_policies` incremented.

**Todo List**
1. Create `/backend/tests/test_agents.py` with TestClient fixture.
2. Implement the 4 test functions using `assert` on response JSON keys defined in AGENTS.md contracts.
3. Ensure tests do not depend on external services or LLM keys.
4. Seed policy registry in test client via `lifespan` by using `app` import from `main.py`.

**Relevant Context**
- Sub-Tasks 1–7 must be complete
- AGENTS.md § Shared API Contracts (exact response keys)

**Status** — `[ ] pending`

---

## Implementation Order

```
Sub-Task 1 (data)  →  Sub-Task 2 (models)  →  Sub-Task 7 (requirements)
                                              ↓
                     Sub-Task 3 (main.py)  ←─┘
                           ↓
                     Sub-Task 4 (geo stub)
                           ↓
                     Sub-Task 5 (agents.py)
                           ↓
                     Sub-Task 6 (vision stub)
                           ↓
                     Sub-Task 8 (tests)
```
