"""
Read-only client for the public VenezuelaReporta API.

Fetches persons with status=encontrado created after a given datetime,
paginating via limit/offset until the page is smaller than VR_PAGE_SIZE.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Iterator

import requests

logger = logging.getLogger(__name__)

VR_BASE_URL = "https://venezuelareporta.org/api/v1/personas"
VR_PAGE_SIZE = 100
VR_TIMEOUT = 30


class VRError(RuntimeError):
    """Raised when the VenezuelaReporta API returns an error."""


def iter_vr_patients(since: dt.datetime) -> Iterator[dict]:
    params: dict = {
        "status": "encontrado",
        "since": since.isoformat(),
        "limit": VR_PAGE_SIZE,
    }
    offset = 0
    while True:
        params["offset"] = offset
        resp = requests.get(VR_BASE_URL, params=params, timeout=VR_TIMEOUT)
        if resp.status_code != 200:
            raise VRError(
                f"VenezuelaReporta returned {resp.status_code}: {resp.text[:500]}"
            )
        data = resp.json()
        if not data.get("ok"):
            raise VRError(f"VenezuelaReporta ok=false: {resp.text[:500]}")
        personas = data.get("personas", [])
        yield from personas
        if len(personas) < VR_PAGE_SIZE:
            break
        offset += VR_PAGE_SIZE


def fetch_vr_patients(since: dt.datetime) -> list[dict]:
    rows = list(iter_vr_patients(since=since))
    logger.info("Fetched %d VenezuelaReporta records (since=%s)", len(rows), since.isoformat())
    return rows
