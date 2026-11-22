"""
/backend/models.py
Pydantic v2 request/response models for SevaSync BLR.
Single source of truth for all API shapes defined in AGENTS.md.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Shared base config
# ---------------------------------------------------------------------------

class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ---------------------------------------------------------------------------
# Policy Pack models
# ---------------------------------------------------------------------------

class PolicySummary(_Base):
    id: str
    name: str
    department: str
    sakala_sla_days: int
    version: str


class PoliciesResponse(_Base):
    policies: list[PolicySummary]


class PolicyPack(_Base):
    """Full policy pack — used for hot-loading via POST /api/policies/register."""
    id: str
    name: str
    department: str
    sakala_sla_days: int
    version: str
    keywords: list[str] = []
    validation_rules: list[dict[str, Any]] = []
    bilingual_draft_templates: dict[str, Any] = {}
    # allow any extra fields (fee_structure, governing_act, etc.)
    model_config = ConfigDict(extra="allow")


class PolicyRegisterResponse(_Base):
    status: str
    total_policies: int
    policy_id: str


# ---------------------------------------------------------------------------
# Vision Extract models
# ---------------------------------------------------------------------------

class VisualFlag(_Base):
    severity: Literal["high", "medium"]
    issue: str


class ExtractedFields(_Base):
    applicant_name: str = ""
    doc_owner_name: str = ""
    account_or_pid: str = ""
    pincode: str = ""
    ward_claimed: str = ""
    built_up_area_sqft: Optional[int] = None
    monthly_units: Optional[int] = None
    application_date: Optional[str] = None


class VisionExtractResponse(_Base):
    document_type: str
    extracted_fields: ExtractedFields
    visual_flags: list[VisualFlag]
    confidence: float
    engine: str


# ---------------------------------------------------------------------------
# Orchestrate models
# ---------------------------------------------------------------------------

class OrchestrateRequest(_Base):
    query: str = ""
    language: Literal["en-IN", "kn-IN", "hi-IN"] = "en-IN"
    extracted_fields: dict[str, Any] = {}
    visual_flags: list[dict[str, Any]] = []
    policy_id: str = "auto"


class SelectedPolicy(_Base):
    id: str
    name: str
    department: str
    sakala_sla_days: int


class LiveGeoCheck(_Base):
    pincode: str
    locality: str
    matched_ward: str
    gba_zone: str
    aro_office: str
    is_live_api: bool
    ward_mismatch: bool


class AgentTraceEntry(_Base):
    agent_name: str
    status: Literal["pass", "warn", "fail"]
    latency_ms: int
    summary: str
    findings: list[str] = []


class Discrepancy(_Base):
    code: str
    severity: Literal["critical", "warning"]
    field: str
    message: str
    remediation: str


class BilingualDraft(_Base):
    english: str
    kannada: str
    document_title: str


class OrchestrateResponse(_Base):
    selected_policy: SelectedPolicy
    live_geo_check: LiveGeoCheck
    readiness_score: int
    status: Literal["BLOCKED_FIX_REQUIRED", "READY_TO_SUBMIT"]
    agent_trace: list[AgentTraceEntry]
    discrepancies: list[Discrepancy]
    fix_checklist: list[str]
    bilingual_draft: BilingualDraft
    sandbox_payload: dict[str, Any]


# ---------------------------------------------------------------------------
# Sandbox Submit models
# ---------------------------------------------------------------------------

class SandboxSubmitRequest(_Base):
    policy_id: str
    payload: dict[str, Any]


class SandboxSubmitResponse(_Base):
    status: str
    sakala_gsc_id: str
    submitted_at: str
    sla_deadline_days: int
    adapter: str
