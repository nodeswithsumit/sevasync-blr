"""
/backend/tests/test_agents.py
4 pytest integration tests for SevaSync BLR.
All tests run deterministically — no LLM API key required.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend/ is on the path when pytest runs from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def client():
    """TestClient with lifespan — loads policy packs from disk at startup."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# Test 1 — e-Khata initial/name mismatch caught
# ---------------------------------------------------------------------------

def test_ekhata_name_mismatch_caught(client: TestClient):
    """
    'R. Kumar' vs 'Ramesh Kumar S' should trigger NAME_MISMATCH_INITIAL (critical).
    """
    resp = client.post(
        "/api/orchestrate",
        json={
            "query": "My e-Khata mutation application is rejected",
            "language": "en-IN",
            "extracted_fields": {
                "applicant_name": "R. Kumar",
                "doc_owner_name": "Ramesh Kumar S",
                "account_or_pid": "SAS-BLR-560048-78923",
                "pincode": "560048",
                "ward_claimed": "Koramangala",
            },
            "visual_flags": [],
            "policy_id": "ekhata",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Correct policy selected
    assert data["selected_policy"]["id"] == "ekhata"

    # At least one critical discrepancy about name mismatch
    critical = [d for d in data["discrepancies"] if d["severity"] == "critical"]
    assert any(
        "NAME_MISMATCH" in d["code"] or "name" in d["field"].lower()
        for d in critical
    ), f"Expected name mismatch discrepancy, got: {[d['code'] for d in data['discrepancies']]}"

    # Application must be blocked
    assert data["status"] == "BLOCKED_FIX_REQUIRED"
    assert data["readiness_score"] < 80


# ---------------------------------------------------------------------------
# Test 2 — Gruha Jyothi tenant checks (units + alpha-numeric RR)
# ---------------------------------------------------------------------------

def test_gruha_jyothi_tenant_check(client: TestClient):
    """
    253 units + alpha-numeric RR 'KA2BLR0056ABC' should trigger 2 critical discrepancies.
    """
    resp = client.post(
        "/api/orchestrate",
        json={
            "query": "I want to apply for Gruha Jyothi electricity subsidy",
            "language": "en-IN",
            "extracted_fields": {
                "applicant_name": "Suresh Babu",
                "doc_owner_name": "Priya Suresh",
                "account_or_pid": "KA2BLR0056ABC",
                "pincode": "560047",
                "ward_claimed": "HSR Layout",
                "monthly_units": 253,
            },
            "visual_flags": [],
            "policy_id": "gruha_jyothi",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["selected_policy"]["id"] == "gruha_jyothi"

    discrepancy_codes = [d["code"] for d in data["discrepancies"]]

    # Units > 200 must be caught
    assert any("UNITS" in c or "unit" in c.lower() for c in discrepancy_codes), (
        f"Expected UNITS_EXCEEDS_200, got: {discrepancy_codes}"
    )
    # Alpha-numeric RR must be caught
    assert any("RR" in c or "NUMERIC" in c or "ALPHA" in c for c in discrepancy_codes), (
        f"Expected ALPHANUMERIC_RR_NUMBER, got: {discrepancy_codes}"
    )

    assert data["status"] == "BLOCKED_FIX_REQUIRED"


# ---------------------------------------------------------------------------
# Test 3 — Sakala SLA breach escalation
# ---------------------------------------------------------------------------

def test_sakala_sla_breach_escalation(client: TestClient):
    """
    Application dated 60+ days ago must trigger SAKALA_SLA_ELAPSED.
    """
    resp = client.post(
        "/api/orchestrate",
        json={
            "query": "My Sakala application has not been processed for 60 days",
            "language": "en-IN",
            "extracted_fields": {
                "applicant_name": "Kavitha Reddy",
                "doc_owner_name": "Kavitha Reddy",
                "account_or_pid": "GSC2026BLR001234",
                "pincode": "560066",
                "ward_claimed": "Whitefield",
                "application_date": "2026-04-01",
            },
            "visual_flags": [],
            "policy_id": "sakala",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    discrepancy_codes = [d["code"] for d in data["discrepancies"]]
    assert any("SLA" in c for c in discrepancy_codes), (
        f"Expected SAKALA_SLA_ELAPSED, got: {discrepancy_codes}"
    )

    # bilingual draft must have both english and kannada
    assert data["bilingual_draft"]["english"]
    assert data["bilingual_draft"]["kannada"]


# ---------------------------------------------------------------------------
# Test 4 — Hot-register a new policy pack live
# ---------------------------------------------------------------------------

def test_hot_register_new_policy(client: TestClient):
    """
    POST /api/policies/register should hot-load a new policy without restart
    and increment total_policies.
    """
    # Get current count
    before = client.get("/api/policies").json()
    before_count = len(before["policies"])

    # Register the e-Swathu plugin pack
    new_pack = {
        "id": "test_e_swathu_live",
        "name": "Test e-Swathu Form 11A — Live Hot-Plug",
        "department": "Revenue Department, GoK",
        "sakala_sla_days": 30,
        "version": "1.0.0",
        "keywords": ["e-swathu", "form 11a", "rural property"],
        "validation_rules": [],
    }
    resp = client.post("/api/policies/register", json=new_pack)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["status"] == "registered"
    assert data["policy_id"] == "test_e_swathu_live"
    assert data["total_policies"] == before_count + 1

    # Confirm it appears in the listing
    after = client.get("/api/policies").json()
    ids = [p["id"] for p in after["policies"]]
    assert "test_e_swathu_live" in ids
