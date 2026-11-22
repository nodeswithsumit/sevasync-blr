"""
/backend/geo.py
Geo resolver for Bengaluru ward/zone/ARO lookup.

Owned by Dev 2. This module is intentionally safe to overwrite with a live
BBMP / Google Maps implementation — the contract is:

    async def resolve_bengaluru_location(pincode: str, ward_claimed: str) -> dict

Returns a dict matching the LiveGeoCheck response shape defined in AGENTS.md.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ward / zone reference data
# ---------------------------------------------------------------------------

_DATA_FILE = Path(__file__).parent.parent / "data" / "real_ground_truth" / "bengaluru_wards_zones.json"

_ward_data: dict = {}


def _load_ward_data() -> dict:
    """Load bengaluru_wards_zones.json once and cache it."""
    global _ward_data
    if _ward_data:
        return _ward_data
    try:
        with open(_DATA_FILE, "r", encoding="utf-8") as fh:
            _ward_data = json.load(fh)
    except FileNotFoundError:
        logger.warning("bengaluru_wards_zones.json not found at %s — geo fallback will return Unknown.", _DATA_FILE)
        _ward_data = {"pincode_to_ward": {}, "ward_aliases": {}}
    return _ward_data


# ---------------------------------------------------------------------------
# Ward-mismatch helper
# ---------------------------------------------------------------------------

def _wards_match(claimed: str, canonical: str, aliases: dict[str, str]) -> bool:
    """
    Return True when the ward_claimed by the citizen matches the canonical ward
    for this pincode.  Comparison is case-insensitive and also checks the
    aliases table so "koramangala" matches "Koramangala".
    """
    claimed_norm = claimed.strip().lower()
    canonical_norm = canonical.strip().lower()

    if claimed_norm == canonical_norm:
        return True

    # Resolve claimed ward through aliases
    resolved = aliases.get(claimed_norm, claimed).strip().lower()
    return resolved == canonical_norm


# ---------------------------------------------------------------------------
# Live postal-pincode API call
# ---------------------------------------------------------------------------

_POSTAL_API = "https://api.postalpincode.in/pincode/{pincode}"
_TIMEOUT_SECONDS = 3.0


async def _fetch_live_locality(pincode: str) -> str | None:
    """
    Call api.postalpincode.in and return the first post-office name found in
    Bengaluru, or None if the call fails / times out / returns no data.
    """
    url = _POSTAL_API.format(pincode=pincode)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()

        # Response shape: [ { "Status": "Success", "PostOffice": [ {...} ] } ]
        if (
            isinstance(payload, list)
            and payload
            and payload[0].get("Status") == "Success"
        ):
            post_offices = payload[0].get("PostOffice") or []
            # Filter to Karnataka / Bengaluru post offices
            blr_offices = [
                po for po in post_offices
                if po.get("State", "").lower() in ("karnataka",)
                and po.get("District", "").lower() in ("bangalore", "bengaluru", "bangalore urban", "bengaluru urban")
            ]
            if blr_offices:
                return blr_offices[0].get("Name") or blr_offices[0].get("Block")
            # If not specifically tagged Bengaluru, return first office name anyway
            if post_offices:
                return post_offices[0].get("Name")

    except (httpx.TimeoutException, httpx.RequestError, Exception) as exc:
        logger.warning("Live geo API failed for pincode %s: %s", pincode, exc)

    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def resolve_bengaluru_location(pincode: str, ward_claimed: str) -> dict:
    """
    Resolve a Bengaluru pincode to ward, GBA zone, and ARO office.

    Strategy
    --------
    1. Attempt a live call to api.postalpincode.in (3 s timeout) to get the
       real post-office / locality name → is_live_api=True.
    2. Cross-reference our bengaluru_wards_zones.json for ward, zone, ARO.
    3. On any live-API failure, fall back entirely to the JSON file
       → is_live_api=False.
    4. Unknown pincodes return a safe "Unknown" response with ward_mismatch=False
       so the pipeline never crashes.

    Returns a dict matching the LiveGeoCheck schema in AGENTS.md:
        pincode, locality, matched_ward, gba_zone, aro_office,
        is_live_api (bool), ward_mismatch (bool)
    """
    data = _load_ward_data()
    pincode_map: dict = data.get("pincode_to_ward", {})
    aliases: dict = data.get("ward_aliases", {})

    # --- Step 1: attempt live API for locality name ---
    live_locality: str | None = None
    is_live = False
    try:
        live_locality = await _fetch_live_locality(pincode)
        if live_locality:
            is_live = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unexpected error in live geo call: %s", exc)

    # --- Step 2: look up reference data ---
    entry = pincode_map.get(str(pincode))

    if entry is None:
        # Unknown pincode — safe fallback
        logger.info("Pincode %s not in ward reference data; returning Unknown.", pincode)
        return {
            "pincode": pincode,
            "locality": live_locality or "Unknown",
            "matched_ward": "Unknown",
            "gba_zone": "Unknown",
            "aro_office": "Unknown",
            "is_live_api": is_live,
            "ward_mismatch": False,
        }

    matched_ward: str = entry["matched_ward"]
    gba_zone: str = entry["gba_zone"]
    aro_office: str = entry["aro_office"]

    # Locality: prefer live API result for freshness, fall back to JSON
    locality: str = live_locality or entry.get("locality", matched_ward)

    # --- Step 3: compute ward_mismatch ---
    mismatch = False
    if ward_claimed and ward_claimed.strip():
        mismatch = not _wards_match(ward_claimed, matched_ward, aliases)

    return {
        "pincode": pincode,
        "locality": locality,
        "matched_ward": matched_ward,
        "gba_zone": gba_zone,
        "aro_office": aro_office,
        "is_live_api": is_live,
        "ward_mismatch": mismatch,
    }
