"""
Read-only client for the tuia911 API (Supabase-backed).

Fetches persons with tipo=encontrada without location filter, then filters
client-side to records created within the last 10 minutes. The API has no
server-side `since` parameter, so we paginate until has_more=false and
discard stale rows.
"""
from __future__ import annotations

import datetime as dt
import logging

import requests

logger = logging.getLogger(__name__)

TUIA_BASE_URL = "https://gkpivfmnclcahppkrfzl.supabase.co/functions/v1/api/personas"
TUIA_PAGE_SIZE = 500
TUIA_TIMEOUT = 30


class TuiaError(RuntimeError):
    """Raised when the tuia911 API returns an error."""


def _parse_ts(ts: str | None) -> dt.datetime | None:
    if not ts:
        return None
    parsed = dt.datetime.fromisoformat(ts)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def fetch_tuia_patients(since: dt.datetime) -> list[dict]:
    """
    Return all tipo=encontrada records created at or after `since`.
    Paginates via limit/offset until has_more=false, then filters client-side.
    """
    all_rows: list[dict] = []
    offset = 0

    while True:
        resp = requests.get(
            TUIA_BASE_URL,
            params={"tipo": "encontrada", "limit": TUIA_PAGE_SIZE, "offset": offset},
            timeout=TUIA_TIMEOUT,
        )
        if resp.status_code != 200:
            raise TuiaError(
                f"tuia911 returned {resp.status_code}: {resp.text[:500]}"
            )
        data = resp.json()
        if not data.get("ok"):
            raise TuiaError(f"tuia911 ok=false: {resp.text[:500]}")

        rows = data.get("data", [])
        all_rows.extend(rows)

        pagination = data.get("pagination", {})
        if not pagination.get("has_more"):
            break
        offset += TUIA_PAGE_SIZE

    recent = [r for r in all_rows if (_parse_ts(r.get("created_at")) or dt.datetime.min.replace(tzinfo=dt.timezone.utc)) >= since]
    logger.info(
        "tuia911: fetched %d records, %d within the since window",
        len(all_rows),
        len(recent),
    )
    return recent
