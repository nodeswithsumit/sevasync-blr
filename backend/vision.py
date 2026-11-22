"""
/backend/vision.py
Vision OCR router for SevaSync BLR.

Owned by Dev 2.  Replace the LLM stubs with real multimodal calls when
OPENAI_API_KEY or GEMINI_API_KEY are present in the environment.

Mounted in main.py as:
    app.include_router(vision_router, prefix="/api")

This exposes:
    POST /api/vision-extract
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SANDBOX_MOCKS_FILE = (
    Path(__file__).parent.parent / "data" / "sandbox_mocks" / "sample_citizen_cases.json"
)

# ---------------------------------------------------------------------------
# Response models (inline — also imported from models.py where available)
# ---------------------------------------------------------------------------

class VisualFlag(BaseModel):
    severity: str  # "high" | "medium"
    issue: str


class ExtractedFields(BaseModel):
    applicant_name: str
    doc_owner_name: str
    account_or_pid: str
    pincode: str
    ward_claimed: str
    built_up_area_sqft: Optional[int] = None
    monthly_units: Optional[int] = None
    application_date: Optional[str] = None


class VisionExtractResponse(BaseModel):
    document_type: str
    extracted_fields: ExtractedFields
    visual_flags: list[VisualFlag]
    confidence: float
    engine: str  # "multimodal_llm" | "deterministic_ocr_fallback"


# ---------------------------------------------------------------------------
# Sandbox mock loader
# ---------------------------------------------------------------------------

_mock_cache: dict = {}


def _load_mocks() -> dict:
    global _mock_cache
    if _mock_cache:
        return _mock_cache
    try:
        with open(_SANDBOX_MOCKS_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        _mock_cache = data.get("cases", {})
    except FileNotFoundError:
        logger.warning("sample_citizen_cases.json not found at %s", _SANDBOX_MOCKS_FILE)
        _mock_cache = {}
    return _mock_cache


def _mock_to_response(case_data: dict) -> VisionExtractResponse:
    ef = case_data["extracted_fields"]
    return VisionExtractResponse(
        document_type=case_data["document_type"],
        extracted_fields=ExtractedFields(**ef),
        visual_flags=[VisualFlag(**f) for f in case_data["visual_flags"]],
        confidence=case_data["confidence"],
        engine=case_data["engine"],
    )


# ---------------------------------------------------------------------------
# LLM extraction — OpenAI GPT-4o or Gemini Pro Vision
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """You are a document intelligence agent for Indian civic services in Bengaluru, Karnataka.

Analyse the provided document image and extract ONLY the following fields as a valid JSON object.
If a field is not present or not legible, return null for that field.

Target document types: BBMP e-Khata / SAS Tax Receipt, BESCOM Electricity Bill, Sale Deed, Rental Lease Agreement, Sakala GSC Acknowledgement.

Required JSON output (no markdown fences, raw JSON only):
{
  "document_type": "<one of: BBMP e-Khata Extract, BESCOM Electricity Bill, Sale Deed, Rental Lease Agreement, Sakala GSC Acknowledgement, Unknown>",
  "applicant_name": "<name of the person submitting the application, if shown>",
  "doc_owner_name": "<name of property/account owner as printed on the document>",
  "account_or_pid": "<SAS PID number, BESCOM RR number, GSC ID, or document reference number>",
  "pincode": "<6-digit PIN code of the property or service address>",
  "ward_claimed": "<BBMP ward name as stated on the document>",
  "built_up_area_sqft": <integer square feet or null>,
  "monthly_units": <integer electricity units for the billing month or null>,
  "application_date": "<ISO date YYYY-MM-DD if any date stamp is visible or null>",
  "visual_flags": [
    {"severity": "<high|medium>", "issue": "<concise description of a visible document quality or compliance issue>"}
  ],
  "confidence": <float 0.0 to 1.0 representing overall extraction confidence>
}

Visual flag triggers to check:
- Blurry or smudged stamp / seal
- Cropped header missing institution name
- Handwritten correction over printed text
- Faded or illegible text in key fields
- Mismatch between name on application vs document
- BESCOM units exceeding 200 (Gruha Jyothi ineligibility)
- Alpha-numeric RR number (Gruha Jyothi requires numeric only)
"""


async def _extract_with_openai(image_bytes: bytes, content_type: str) -> dict | None:
    """Call OpenAI GPT-4o vision. Returns parsed dict or None on failure."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None

    b64 = base64.b64encode(image_bytes).decode()
    mime = content_type if content_type in ("image/png", "image/jpeg", "image/webp") else "image/jpeg"
    payload = {
        "model": "gpt-4o",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _EXTRACTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            }
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            # Strip markdown fences if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
    except Exception as exc:
        logger.warning("OpenAI vision call failed: %s", exc)
        return None


async def _extract_with_gemini(image_bytes: bytes, content_type: str) -> dict | None:
    """Call Google Gemini Pro Vision. Returns parsed dict or None on failure."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None

    b64 = base64.b64encode(image_bytes).decode()
    mime = content_type if content_type in ("image/png", "image/jpeg", "image/webp") else "image/jpeg"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": _EXTRACTION_PROMPT},
                    {"inline_data": {"mime_type": mime, "data": b64}},
                ]
            }
        ]
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-pro-vision:generateContent?key={api_key}"
    )
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
    except Exception as exc:
        logger.warning("Gemini vision call failed: %s", exc)
        return None


def _llm_dict_to_response(result: dict) -> VisionExtractResponse:
    """Coerce a raw LLM JSON dict into VisionExtractResponse, tolerating missing keys."""
    ef = ExtractedFields(
        applicant_name=result.get("applicant_name") or "",
        doc_owner_name=result.get("doc_owner_name") or "",
        account_or_pid=result.get("account_or_pid") or "",
        pincode=str(result.get("pincode") or ""),
        ward_claimed=result.get("ward_claimed") or "",
        built_up_area_sqft=result.get("built_up_area_sqft"),
        monthly_units=result.get("monthly_units"),
        application_date=result.get("application_date"),
    )
    flags = [
        VisualFlag(
            severity=f.get("severity", "medium"),
            issue=f.get("issue", ""),
        )
        for f in (result.get("visual_flags") or [])
        if f.get("issue")
    ]
    return VisionExtractResponse(
        document_type=result.get("document_type") or "Unknown",
        extracted_fields=ef,
        visual_flags=flags,
        confidence=float(result.get("confidence") or 0.5),
        engine="multimodal_llm",
    )


# ---------------------------------------------------------------------------
# Deterministic fallback for uploaded files (no LLM key)
# ---------------------------------------------------------------------------

def _filename_heuristic(filename: str) -> VisionExtractResponse:
    """
    When no LLM key is available, produce a safe placeholder extraction
    based on filename keywords so the demo never crashes.
    """
    fname = (filename or "").lower()

    if any(k in fname for k in ("bescom", "electricity", "bill", "gruha")):
        doc_type = "BESCOM Electricity Bill"
        flags = [VisualFlag(severity="medium", issue="Auto-detected from filename; manual review recommended.")]
    elif any(k in fname for k in ("ekhata", "khata", "sas", "bbmp", "property")):
        doc_type = "BBMP e-Khata Extract"
        flags = [VisualFlag(severity="medium", issue="Auto-detected from filename; manual review recommended.")]
    elif any(k in fname for k in ("sakala", "gsc", "grievance")):
        doc_type = "Sakala GSC Acknowledgement"
        flags = [VisualFlag(severity="medium", issue="Auto-detected from filename; manual review recommended.")]
    elif any(k in fname for k in ("sale", "deed", "reg")):
        doc_type = "Sale Deed"
        flags = [VisualFlag(severity="medium", issue="Auto-detected from filename; manual review recommended.")]
    elif any(k in fname for k in ("lease", "rental", "rent")):
        doc_type = "Rental Lease Agreement"
        flags = [VisualFlag(severity="medium", issue="Auto-detected from filename; manual review recommended.")]
    else:
        doc_type = "Unknown"
        flags = [
            VisualFlag(
                severity="medium",
                issue="Document type could not be determined without an LLM API key. "
                      "Set OPENAI_API_KEY or GEMINI_API_KEY for automatic extraction.",
            )
        ]

    ef = ExtractedFields(
        applicant_name="",
        doc_owner_name="",
        account_or_pid="",
        pincode="",
        ward_claimed="",
    )
    return VisionExtractResponse(
        document_type=doc_type,
        extracted_fields=ef,
        visual_flags=flags,
        confidence=0.0,
        engine="deterministic_ocr_fallback",
    )


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post("/vision-extract", response_model=VisionExtractResponse, tags=["Vision OCR"])
async def vision_extract(
    file: Optional[UploadFile] = File(default=None),
    sample_case_id: Optional[str] = Query(
        default=None,
        description="Demo case: ekhata_mismatch | gruha_jyothi_tenant | sakala_sla_breach",
    ),
) -> VisionExtractResponse:
    """
    Extract structured civic document fields via Vision OCR.

    **Path A — sample_case_id**: Returns pre-canned deterministic extraction
    from /data/sandbox_mocks/sample_citizen_cases.json with ~400 ms simulated
    latency for reliable demo playback.

    **Path B — file upload**: If OPENAI_API_KEY or GEMINI_API_KEY is set,
    calls the multimodal LLM with a strict JSON extraction prompt.  Falls back
    to filename-heuristic deterministic extraction if no key is configured or
    the LLM call fails.
    """

    # ------------------------------------------------------------------
    # Path A: pre-canned sandbox demo case
    # ------------------------------------------------------------------
    if sample_case_id:
        mocks = _load_mocks()
        case_data = mocks.get(sample_case_id)
        if case_data is None:
            valid = list(mocks.keys()) or ["ekhata_mismatch", "gruha_jyothi_tenant", "sakala_sla_breach"]
            raise HTTPException(
                status_code=404,
                detail=f"Unknown sample_case_id '{sample_case_id}'. Valid values: {valid}",
            )
        # Simulate realistic OCR latency for demo credibility
        await asyncio.sleep(0.4)
        return _mock_to_response(case_data)

    # ------------------------------------------------------------------
    # Path B: uploaded file
    # ------------------------------------------------------------------
    if file is None:
        raise HTTPException(
            status_code=422,
            detail="Provide either 'file' (image upload) or 'sample_case_id' query parameter.",
        )

    allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
    content_type = (file.content_type or "").lower()
    if content_type not in allowed_types and not (file.filename or "").lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{content_type}'. Upload PNG, JPG, or WebP.",
        )

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    # Try OpenAI first, then Gemini, then deterministic fallback
    result: dict | None = await _extract_with_openai(image_bytes, content_type)
    if result is None:
        result = await _extract_with_gemini(image_bytes, content_type)

    if result is not None:
        return _llm_dict_to_response(result)

    # No LLM key / both failed → deterministic fallback
    return _filename_heuristic(file.filename or "")
