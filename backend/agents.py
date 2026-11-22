"""
/backend/agents.py
4-agent sequential pipeline for SevaSync BLR.
Called by POST /api/orchestrate in main.py.

All logic is deterministic — no LLM key required.
LLM enhancement hooks are marked # LLM HOOK for future integration.
"""

from __future__ import annotations

import difflib
import re
import time
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any

from models import (
    AgentTraceEntry,
    BilingualDraft,
    Discrepancy,
    LiveGeoCheck,
    OrchestrateRequest,
    OrchestrateResponse,
    SelectedPolicy,
)

if TYPE_CHECKING:
    from main import PolicyRegistry


# ---------------------------------------------------------------------------
# Agent 1 — Intake & Policy Router
# ---------------------------------------------------------------------------

def agent_1_policy_router(
    request: OrchestrateRequest,
    registry: "PolicyRegistry",
) -> tuple[dict, AgentTraceEntry]:
    t0 = time.perf_counter()
    findings: list[str] = []
    policy: dict | None = None

    # Explicit policy_id selection
    if request.policy_id and request.policy_id != "auto":
        policy = registry.get_by_id(request.policy_id)
        if policy:
            findings.append(f"Explicit policy_id='{request.policy_id}' matched: {policy['name']}")

    # Keyword scan across query + extracted field values
    if policy is None:
        query_lower = request.query.lower()
        # Also scan extracted field values for hints
        ef = request.extracted_fields
        combined = query_lower + " " + " ".join(
            str(v).lower() for v in ef.values() if v
        )
        all_packs = registry.get_all()
        scored: list[tuple[int, dict]] = []
        for pack in all_packs:
            keywords: list[str] = pack.get("keywords", [])
            score = sum(1 for kw in keywords if kw.lower() in combined)
            if score > 0:
                scored.append((score, pack))
        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            policy = scored[0][1]
            findings.append(
                f"Keyword match: '{policy['name']}' (score={scored[0][0]})"
            )

    # LLM HOOK: replace keyword fallback with watsonx.ai policy classification

    # Fallback: first loaded pack
    if policy is None:
        all_packs = registry.get_all()
        if all_packs:
            policy = all_packs[0]
            findings.append(f"No keyword match — defaulted to first policy: {policy['name']}")
        else:
            policy = {
                "id": "unknown",
                "name": "Unknown Policy",
                "department": "Unknown",
                "sakala_sla_days": 30,
                "version": "0.0.0",
                "keywords": [],
                "validation_rules": [],
                "bilingual_draft_templates": {},
            }
            findings.append("No policies loaded — using empty fallback policy.")

    ms = int((time.perf_counter() - t0) * 1000)
    trace = AgentTraceEntry(
        agent_name="Intake & Policy Router",
        status="pass",
        latency_ms=ms,
        summary=f"Routed to policy: {policy['name']} (SLA {policy.get('sakala_sla_days', '?')} days)",
        findings=findings,
    )
    return policy, trace


# ---------------------------------------------------------------------------
# Agent 2 — Pre-Flight Discrepancy Validator
# ---------------------------------------------------------------------------

def _fuzzy_ratio(a: str, b: str) -> float:
    """SequenceMatcher ratio between two strings, case-insensitive."""
    return difflib.SequenceMatcher(
        None, a.strip().lower(), b.strip().lower()
    ).ratio()


def _is_numeric_only(value: str) -> bool:
    return bool(re.fullmatch(r"\d+", value.strip()))


def agent_2_validator(
    request: OrchestrateRequest,
    policy: dict,
) -> tuple[list[Discrepancy], AgentTraceEntry]:
    t0 = time.perf_counter()
    discrepancies: list[Discrepancy] = []
    findings: list[str] = []

    ef = request.extracted_fields
    applicant_name: str = str(ef.get("applicant_name") or "")
    doc_owner_name: str = str(ef.get("doc_owner_name") or "")
    account_or_pid: str = str(ef.get("account_or_pid") or "")
    monthly_units_raw = ef.get("monthly_units")
    built_up_area_raw = ef.get("built_up_area_sqft")
    application_date_str: str = str(ef.get("application_date") or "")
    sla_days: int = policy.get("sakala_sla_days", 30)

    # ── Run policy validation_rules ─────────────────────────────────────────
    for rule in policy.get("validation_rules", []):
        rule_id: str = rule.get("rule_id", "UNKNOWN")
        field: str = rule.get("field", "")
        check: str = rule.get("check", "")
        severity: str = rule.get("severity", "warning")
        message: str = rule.get("message", "")
        remediation: str = rule.get("remediation", "")

        triggered = False
        detail = ""

        if check == "fuzzy_name_match":
            if applicant_name and doc_owner_name:
                threshold = float(rule.get("threshold", 0.75))
                ratio = _fuzzy_ratio(applicant_name, doc_owner_name)
                if ratio < threshold:
                    triggered = True
                    detail = (
                        f"'{applicant_name}' vs '{doc_owner_name}' — "
                        f"similarity {ratio:.0%} < {threshold:.0%} threshold"
                    )

        elif check == "not_empty":
            value = ef.get(field, "")
            if not value or str(value).strip() == "":
                triggered = True
                detail = f"Field '{field}' is empty or missing"

        elif check == "value_lte":
            threshold = float(rule.get("threshold", 200))
            value = ef.get(field)
            if value is not None:
                try:
                    if float(value) > threshold:
                        triggered = True
                        detail = f"{field}={value} exceeds ceiling of {threshold}"
                except (TypeError, ValueError):
                    pass

        elif check == "numeric_only":
            value = str(ef.get(field) or "")
            if value and not _is_numeric_only(value):
                triggered = True
                detail = f"'{value}' contains non-numeric characters"

        elif check == "area_delta_within_5pct":
            # Compare applicant-declared vs a reference value if two area
            # values are present in extracted_fields.  For demo, we detect
            # the delta from the visual_flag text as a proxy.
            vf_texts = " ".join(f.get("issue", "") for f in request.visual_flags)
            if "%" in vf_texts and ("sqft" in vf_texts.lower() or "sq.ft" in vf_texts.lower()):
                # Extract percentage from flag text, e.g. "12.9%"
                match = re.search(r"(\d+\.?\d*)\s*%", vf_texts)
                if match:
                    pct = float(match.group(1))
                    if pct > 5.0:
                        triggered = True
                        detail = f"Built-up area variance {pct:.1f}% > 5% threshold"

        elif check == "sla_not_elapsed":
            if application_date_str:
                try:
                    app_date = date.fromisoformat(application_date_str)
                    days_elapsed = (date.today() - app_date).days
                    effective_sla = rule.get("sla_days", sla_days)
                    if days_elapsed > effective_sla:
                        triggered = True
                        detail = (
                            f"Application date {application_date_str}: "
                            f"{days_elapsed} days elapsed > {effective_sla}-day SLA"
                        )
                except ValueError:
                    pass

        elif check in ("ward_matches_pincode", "geo_ward_match"):
            # Handled in Agent 3 — skip here
            pass

        if triggered:
            discrepancies.append(
                Discrepancy(
                    code=rule_id,
                    severity=severity,  # type: ignore[arg-type]
                    field=field,
                    message=f"{message} {detail}".strip(),
                    remediation=remediation,
                )
            )
            findings.append(f"[{severity.upper()}] {rule_id}: {detail}")

    # ── Also surface high-severity visual flags as discrepancies ───────────
    for vf in request.visual_flags:
        sev = vf.get("severity", "medium")
        issue = vf.get("issue", "")
        if sev == "high" and issue:
            # Avoid duplicating if already caught by a rule
            already = any(
                d.message and issue[:40].lower() in d.message.lower()
                for d in discrepancies
            )
            if not already:
                discrepancies.append(
                    Discrepancy(
                        code="VISUAL_FLAG_HIGH",
                        severity="critical",
                        field="document",
                        message=issue,
                        remediation="Review the uploaded document and correct the flagged issue before resubmission.",
                    )
                )
                findings.append(f"[VISUAL] HIGH flag: {issue[:80]}")

    ms = int((time.perf_counter() - t0) * 1000)
    agent_status = "fail" if any(d.severity == "critical" for d in discrepancies) else (
        "warn" if discrepancies else "pass"
    )
    trace = AgentTraceEntry(
        agent_name="Pre-Flight Discrepancy Validator",
        status=agent_status,
        latency_ms=ms,
        summary=(
            f"{len(discrepancies)} discrepancy/ies found "
            f"({sum(1 for d in discrepancies if d.severity == 'critical')} critical, "
            f"{sum(1 for d in discrepancies if d.severity == 'warning')} warning)"
        ),
        findings=findings,
    )
    return discrepancies, trace


# ---------------------------------------------------------------------------
# Agent 3 — Live Bengaluru Geo & Ward Router
# ---------------------------------------------------------------------------

async def agent_3_geo_router(
    request: OrchestrateRequest,
    discrepancies: list[Discrepancy],
) -> tuple[LiveGeoCheck, list[Discrepancy], AgentTraceEntry]:
    from geo import resolve_bengaluru_location  # local import avoids circular

    t0 = time.perf_counter()
    findings: list[str] = []

    ef = request.extracted_fields
    pincode: str = str(ef.get("pincode") or "")
    ward_claimed: str = str(ef.get("ward_claimed") or "")

    if not pincode:
        # No pincode available — return safe unknown
        geo = LiveGeoCheck(
            pincode="",
            locality="Unknown",
            matched_ward="Unknown",
            gba_zone="Unknown",
            aro_office="Unknown",
            is_live_api=False,
            ward_mismatch=False,
        )
        findings.append("No pincode in extracted_fields — skipping geo resolution")
    else:
        raw = await resolve_bengaluru_location(pincode, ward_claimed)
        geo = LiveGeoCheck(**raw)
        api_tag = "Live India Post API" if geo.is_live_api else "Local reference data"
        findings.append(
            f"Pincode {pincode} → {geo.matched_ward} ({geo.gba_zone} Zone) "
            f"via {api_tag}"
        )
        if geo.ward_mismatch:
            findings.append(
                f"Ward mismatch: claimed '{ward_claimed}' ≠ actual '{geo.matched_ward}'"
            )
            # Only add if not already captured by Agent 2
            already = any(d.code == "WARD_ZONE_MISMATCH" for d in discrepancies)
            if not already:
                discrepancies.append(
                    Discrepancy(
                        code="WARD_ZONE_MISMATCH",
                        severity="critical",
                        field="ward_claimed",
                        message=(
                            f"Ward '{ward_claimed}' claimed on application does not match "
                            f"pincode {pincode} → actual ward '{geo.matched_ward}' "
                            f"({geo.gba_zone} Zone, {geo.aro_office})"
                        ),
                        remediation=(
                            "Update the ward on your application to match the pincode. "
                            f"Correct ward: {geo.matched_ward}, ARO: {geo.aro_office}"
                        ),
                    )
                )

    ms = int((time.perf_counter() - t0) * 1000)
    trace = AgentTraceEntry(
        agent_name="Live Bengaluru Geo & Ward Router",
        status="fail" if geo.ward_mismatch else "pass",
        latency_ms=ms,
        summary=(
            f"PIN {geo.pincode or 'N/A'} → {geo.matched_ward}, "
            f"{geo.gba_zone} Zone | "
            f"{'Ward mismatch detected' if geo.ward_mismatch else 'Ward OK'} | "
            f"{'Live API' if geo.is_live_api else 'Offline fallback'}"
        ),
        findings=findings,
    )
    return geo, discrepancies, trace


# ---------------------------------------------------------------------------
# Agent 4 — Bilingual Action & Draft Agent
# ---------------------------------------------------------------------------

def _build_draft(policy: dict, discrepancies: list[Discrepancy],
                 ef: dict[str, Any], geo: LiveGeoCheck) -> BilingualDraft:
    """
    Select the most relevant bilingual template from the policy pack
    and fill in key placeholders.
    """
    templates: dict = policy.get("bilingual_draft_templates", {})

    # Pick template by most critical discrepancy code
    template_key: str | None = None
    critical_codes = [d.code for d in discrepancies if d.severity == "critical"]

    if "NAME_MISMATCH_INITIAL" in critical_codes or "AADHAAR_NAME_MISMATCH" in critical_codes:
        template_key = next(
            (k for k in templates if "name" in k.lower() or "affidavit" in k.lower()), None
        )
    if template_key is None and "SAKALA_SLA_ELAPSED" in [d.code for d in discrepancies]:
        template_key = next(
            (k for k in templates if "sla" in k.lower() or "escalat" in k.lower()), None
        )
    if template_key is None and templates:
        template_key = next(iter(templates))

    if template_key and template_key in templates:
        tmpl = templates[template_key]
        doc_title: str = tmpl.get("document_title", f"{policy['name']} — Action Letter")
        english: str = tmpl.get("english", "")
        kannada: str = tmpl.get("kannada", "")
    else:
        doc_title = f"{policy['name']} — Pre-Audit Action Summary"
        english = (
            f"Dear Citizen,\n\n"
            f"Your application for '{policy['name']}' has been pre-audited by SevaSync BLR.\n\n"
            f"Policy: {policy['name']}\n"
            f"Department: {policy['department']}\n"
            f"Sakala SLA: {policy.get('sakala_sla_days', 'N/A')} working days\n"
            f"ARO Office: {geo.aro_office}\n\n"
            f"Issues found: {len(discrepancies)}\n"
            + "\n".join(f"• [{d.severity.upper()}] {d.code}: {d.message[:100]}" for d in discrepancies)
            + "\n\nPlease resolve all CRITICAL issues before submitting your application."
        )
        kannada = (
            f"ಪ್ರಿಯ ನಾಗರಿಕರೇ,\n\n"
            f"ನಿಮ್ಮ '{policy['name']}' ಅರ್ಜಿಯನ್ನು SevaSync BLR ಪೂರ್ವ-ಲೆಕ್ಕಪರಿಶೋಧನೆ ಮಾಡಿದೆ.\n\n"
            f"ನೀತಿ: {policy['name']}\n"
            f"ಇಲಾಖೆ: {policy['department']}\n"
            f"ಸಕಾಲ SLA: {policy.get('sakala_sla_days', 'N/A')} ಕಾರ್ಯದಿನಗಳು\n"
            f"ARO ಕಚೇರಿ: {geo.aro_office}\n\n"
            f"ಪತ್ತೆ ಆದ ಸಮಸ್ಯೆಗಳು: {len(discrepancies)}\n"
            + "\n".join(f"• [{d.severity.upper()}] {d.code}" for d in discrepancies)
            + "\n\nಸಲ್ಲಿಸುವ ಮೊದಲು ಎಲ್ಲ CRITICAL ಸಮಸ್ಯೆಗಳನ್ನು ಸರಿಪಡಿಸಿ."
        )

    # Simple placeholder fills
    today = datetime.today().strftime("%d-%m-%Y")
    applicant = str(ef.get("applicant_name") or "[APPLICANT_NAME]")
    doc_owner = str(ef.get("doc_owner_name") or "[OWNER_NAME]")
    pid = str(ef.get("account_or_pid") or "[PID_NUMBER]")
    pincode = str(ef.get("pincode") or "[PINCODE]")
    ward = geo.matched_ward or str(ef.get("ward_claimed") or "[WARD_NAME]")

    replacements = {
        "[DATE]": today, "[APPLICANT_NAME]": applicant,
        "[OWNER_NAME]": doc_owner, "[APPLICATION_NAME]": applicant,
        "[DOCUMENT_NAME]": doc_owner, "[PID_NUMBER]": pid,
        "[PINCODE]": pincode, "[WARD_NAME]": ward,
        "[ZONE_NAME]": geo.gba_zone, "[ARO_OFFICE_NAME]": geo.aro_office,
        "[GBA_ZONE]": geo.gba_zone,
    }
    for placeholder, value in replacements.items():
        english = english.replace(placeholder, value)
        kannada = kannada.replace(placeholder, value)

    return BilingualDraft(english=english, kannada=kannada, document_title=doc_title)


def agent_4_draft_agent(
    policy: dict,
    discrepancies: list[Discrepancy],
    geo: LiveGeoCheck,
    request: OrchestrateRequest,
) -> tuple[int, str, list[str], BilingualDraft, dict, AgentTraceEntry]:
    t0 = time.perf_counter()
    findings: list[str] = []

    # ── Readiness Score ─────────────────────────────────────────────────────
    # 100 − 20×critical − 10×warning, floor at 0
    n_critical = sum(1 for d in discrepancies if d.severity == "critical")
    n_warning = sum(1 for d in discrepancies if d.severity == "warning")
    readiness_score = max(0, 100 - 20 * n_critical - 10 * n_warning)
    overall_status = "READY_TO_SUBMIT" if n_critical == 0 else "BLOCKED_FIX_REQUIRED"
    findings.append(
        f"Score: {readiness_score}/100 — {n_critical} critical, {n_warning} warning"
    )

    # ── Fix Checklist ────────────────────────────────────────────────────────
    fix_checklist: list[str] = []
    for d in discrepancies:
        prefix = "🚫 CRITICAL" if d.severity == "critical" else "⚠️ WARNING"
        fix_checklist.append(f"{prefix} [{d.code}]: {d.remediation}")
    if not fix_checklist:
        fix_checklist.append(
            "✅ No issues found — your application appears ready to submit."
        )
    findings.append(f"Generated {len(fix_checklist)} fix checklist items")

    # ── Bilingual Draft ──────────────────────────────────────────────────────
    draft = _build_draft(policy, discrepancies, request.extracted_fields, geo)
    findings.append(f"Draft generated: '{draft.document_title}'")

    # ── Sandbox Payload ──────────────────────────────────────────────────────
    sandbox_payload: dict[str, Any] = {
        "policy_id": policy["id"],
        "policy_name": policy["name"],
        "department": policy["department"],
        "applicant_name": request.extracted_fields.get("applicant_name", ""),
        "account_or_pid": request.extracted_fields.get("account_or_pid", ""),
        "pincode": request.extracted_fields.get("pincode", ""),
        "ward": geo.matched_ward,
        "gba_zone": geo.gba_zone,
        "aro_office": geo.aro_office,
        "readiness_score": readiness_score,
        "discrepancy_count": len(discrepancies),
        "critical_count": n_critical,
        "submission_timestamp": datetime.utcnow().isoformat() + "Z",
        "adapter": "API_SETU_SANDBOX_V1",
    }

    ms = int((time.perf_counter() - t0) * 1000)
    trace = AgentTraceEntry(
        agent_name="Bilingual Action & Draft Agent",
        status="pass",
        latency_ms=ms,
        summary=(
            f"Readiness {readiness_score}/100 — {overall_status.replace('_', ' ')} | "
            f"{len(fix_checklist)} fix items | Bilingual draft ready"
        ),
        findings=findings,
    )
    return readiness_score, overall_status, fix_checklist, draft, sandbox_payload, trace


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_pipeline(
    request: OrchestrateRequest,
    registry: "PolicyRegistry",
) -> OrchestrateResponse:
    """Run the sequential 4-agent pipeline and return a full OrchestrateResponse."""

    # Agent 1
    policy, trace1 = agent_1_policy_router(request, registry)

    selected_policy = SelectedPolicy(
        id=policy["id"],
        name=policy["name"],
        department=policy["department"],
        sakala_sla_days=policy.get("sakala_sla_days", 30),
    )

    # Agent 2
    discrepancies, trace2 = agent_2_validator(request, policy)

    # Agent 3
    geo, discrepancies, trace3 = await agent_3_geo_router(request, discrepancies)

    # Agent 4
    readiness_score, status, fix_checklist, draft, sandbox_payload, trace4 = \
        agent_4_draft_agent(policy, discrepancies, geo, request)

    return OrchestrateResponse(
        selected_policy=selected_policy,
        live_geo_check=geo,
        readiness_score=readiness_score,
        status=status,  # type: ignore[arg-type]
        agent_trace=[trace1, trace2, trace3, trace4],
        discrepancies=discrepancies,
        fix_checklist=fix_checklist,
        bilingual_draft=draft,
        sandbox_payload=sandbox_payload,
    )
