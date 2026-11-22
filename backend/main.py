"""
/backend/main.py
FastAPI application for SevaSync BLR.

Run from /backend/:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import glob
import json
import logging
import random
import string
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agents import run_pipeline
from models import (
    OrchestrateRequest,
    OrchestrateResponse,
    PoliciesResponse,
    PolicyPack,
    PolicyRegisterResponse,
    PolicySummary,
    SandboxSubmitRequest,
    SandboxSubmitResponse,
)
from vision import router as vision_router

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Policy Registry
# ---------------------------------------------------------------------------

# Paths are relative to this file so they work whether uvicorn is run from
# /backend/ or the repo root.
_DATA_DIR = Path(__file__).parent.parent / "data" / "real_ground_truth"


class PolicyRegistry:
    """In-memory store of loaded PolicyPacks. Thread-safe for single-process use."""

    def __init__(self) -> None:
        self._packs: dict[str, dict[str, Any]] = {}

    def load_from_disk(self) -> int:
        """Glob all policy_pack_*.json files and load them into the registry."""
        pattern = str(_DATA_DIR / "policy_pack_*.json")
        files = glob.glob(pattern)
        loaded = 0
        for filepath in sorted(files):
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    data: dict = json.load(fh)
                pack_id: str = data.get("id", Path(filepath).stem)
                self._packs[pack_id] = data
                loaded += 1
                logger.info("Loaded policy pack '%s' from %s", pack_id, filepath)
            except Exception as exc:
                logger.warning("Failed to load %s: %s", filepath, exc)
        logger.info("PolicyRegistry: %d pack(s) loaded from disk", loaded)
        return loaded

    def get_all(self) -> list[dict[str, Any]]:
        return list(self._packs.values())

    def get_by_id(self, pack_id: str) -> dict[str, Any] | None:
        return self._packs.get(pack_id)

    def register(self, pack: dict[str, Any]) -> None:
        pack_id: str = pack["id"]
        self._packs[pack_id] = pack
        logger.info("Hot-registered policy pack '%s'", pack_id)

    def __len__(self) -> int:
        return len(self._packs)


# Module-level singleton — shared across all requests
registry = PolicyRegistry()


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load policy packs at startup."""
    n = registry.load_from_disk()
    logger.info("SevaSync BLR backend started — %d policy pack(s) active", n)
    yield
    logger.info("SevaSync BLR backend shutting down")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SevaSync BLR — Civic Co-Pilot API",
    description=(
        "Agentic AI civic co-pilot for Bengaluru citizens. "
        "Voice + Vision OCR + 4-Agent Pre-Flight Pipeline."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount vision router under /api prefix
app.include_router(vision_router, prefix="/api", tags=["Vision OCR"])


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/policies", response_model=PoliciesResponse, tags=["Policies"])
def get_policies() -> PoliciesResponse:
    """List all currently loaded Civic Policy Packs."""
    summaries = [
        PolicySummary(
            id=p["id"],
            name=p["name"],
            department=p["department"],
            sakala_sla_days=p.get("sakala_sla_days", 30),
            version=p.get("version", "1.0.0"),
        )
        for p in registry.get_all()
    ]
    return PoliciesResponse(policies=summaries)


@app.post("/api/policies/register", response_model=PolicyRegisterResponse, tags=["Policies"])
def register_policy(pack: PolicyPack) -> PolicyRegisterResponse:
    """
    Hot-load a new JSON Policy Pack into the live registry without restarting.
    Demonstrates Civic-as-Code zero-downtime scalability.
    """
    registry.register(pack.model_dump())
    return PolicyRegisterResponse(
        status="registered",
        total_policies=len(registry),
        policy_id=pack.id,
    )


@app.post("/api/orchestrate", response_model=OrchestrateResponse, tags=["Pipeline"])
async def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
    """
    Run the 4-agent sequential pre-flight pipeline:
    1. Intake & Policy Router
    2. Pre-Flight Discrepancy Validator
    3. Live Bengaluru Geo & Ward Router
    4. Bilingual Action & Draft Agent
    """
    return await run_pipeline(request, registry)


@app.post("/api/sandbox/submit", response_model=SandboxSubmitResponse, tags=["Sandbox"])
def sandbox_submit(request: SandboxSubmitRequest) -> SandboxSubmitResponse:
    """
    Submit to the API Setu sandbox adapter.
    Returns a realistic 15-character Sakala GSC Tracking ID.
    """
    # Look up SLA days from registry; default to 30
    pack = registry.get_by_id(request.policy_id)
    sla_days: int = pack.get("sakala_sla_days", 30) if pack else 30

    # Generate GSC2026BLR + 6 random digits = 15 chars total
    suffix = "".join(random.choices(string.digits, k=6))
    gsc_id = f"GSC2026BLR{suffix}"

    return SandboxSubmitResponse(
        status="SUBMITTED_SANDBOX",
        sakala_gsc_id=gsc_id,
        submitted_at=datetime.now(timezone.utc).isoformat(),
        sla_deadline_days=sla_days,
        adapter="API_SETU_SANDBOX_V1",
    )


@app.get("/", tags=["Health"])
def root() -> dict:
    return {
        "service": "SevaSync BLR",
        "status": "running",
        "policies_loaded": len(registry),
        "docs": "/docs",
    }
