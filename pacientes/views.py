"""
HTTP endpoints.

    GET /                  -> health check
    GET /api/patients      -> normalized patient records as JSON

Query params:
    active=false   include soft-deleted rows (default: active only)
    since=<datetime>  keep only rows whose latest timestamp (updated_at when
                      set, otherwise created_at) is strictly more recent than
                      the given ISO-8601 datetime. Times without an explicit
                      offset are read as Venezuelan time (UTC-04:00).
                      (e.g. since=2026-06-25T14:30:00)
    raw=true       return raw Supabase rows instead of normalized
"""
from __future__ import annotations

import datetime as dt
import logging
import secrets

from django.conf import settings
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime

from .gemini import split_names
from .normalize import normalize_many, normalize_vr_many
from .supabase import SupabaseError, fetch_patients
from .venezreporta import VRError, fetch_vr_patients

logger = logging.getLogger(__name__)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _provided_api_key(request) -> str:
    """Extract the caller's key from `X-API-Key` or `Authorization: Bearer`."""
    key = request.headers.get("X-API-Key", "").strip()
    if key:
        return key
    auth = request.headers.get("Authorization", "").strip()
    if auth.lower().startswith("bearer "):
        return auth[len("bearer "):].strip()
    return ""


def _check_api_key(request) -> bool:
    """Return True if the request is authorized (or auth is disabled)."""
    allowed = settings.SERVICE_API_KEYS
    if not allowed:
        # No keys configured. When the operator has demanded auth
        # (SERVICE_REQUIRE_API_KEY=true) fail closed so a misconfigured
        # deploy never silently exposes the endpoint; otherwise stay open.
        return not settings.SERVICE_REQUIRE_API_KEY
    provided = _provided_api_key(request)
    if not provided:
        return False
    # Constant-time compare against every configured key to avoid leaking,
    # via response timing, how much of a key a guess got right.
    return any(secrets.compare_digest(provided, key) for key in allowed)


def _unauthorized() -> JsonResponse:
    resp = JsonResponse({"error": "unauthorized", "detail": "Missing or invalid X-API-Key."}, status=401)
    return resp


# All times are interpreted as Venezuelan time (UTC-04:00, no DST).
VENEZUELA_TZ = dt.timezone(dt.timedelta(hours=-4))


def _parse_datetime(value: str | None) -> dt.datetime | None:
    """Parse an ISO-8601 datetime, returning None when blank/invalid.

    A naive datetime is treated as Venezuelan time so it can be compared
    against the timezone-aware timestamps Supabase returns.
    """
    if not value or not value.strip():
        return None
    parsed = parse_datetime(value.strip())
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=VENEZUELA_TZ)
    return parsed


def _row_timestamp(row: dict) -> dt.datetime | None:
    """The row's most recent timestamp: updated_at when set, else created_at."""
    return _parse_datetime(row.get("updated_at")) or _parse_datetime(
        row.get("created_at")
    )


def _filter_since(rows: list[dict], since: dt.datetime) -> list[dict]:
    """Keep only rows whose latest timestamp is strictly newer than `since`."""
    kept = []
    for row in rows:
        ts = _row_timestamp(row)
        if ts is not None and ts > since:
            kept.append(row)
    return kept


def health(request):
    return JsonResponse(
        {
            "service": "registro-pacientes-scraper",
            "status": "ok",
            "source": settings.SUPABASE_URL,
            "table": settings.SUPABASE_TABLE,
            "endpoints": ["/api/patients"],
        }
    )


def _load(request):
    """Shared fetch + normalize. Returns (records, active_only, error_response)."""
    # Active rows only, unless the caller explicitly passes active=false.
    active_only = request.GET.get("active", "true").strip().lower() != "false"

    # Optional `since` filter: only rows newer than the supplied datetime.
    since_raw = request.GET.get("since")
    since = _parse_datetime(since_raw)
    if since_raw and since_raw.strip() and since is None:
        return None, None, JsonResponse(
            {
                "error": "invalid_parameter",
                "detail": "Query param 'since' must be an ISO-8601 datetime, "
                "e.g. 2026-06-25T14:30:00 (Venezuelan time assumed when no "
                "offset is given).",
            },
            status=400,
        )

    try:
        rows = fetch_patients(active_only=active_only)
    except SupabaseError as exc:
        logger.exception("Upstream Supabase error")
        return None, None, JsonResponse(
            {"error": "upstream_error", "detail": str(exc)}, status=502
        )
    except Exception as exc:  # network/timeout/etc.
        logger.exception("Unexpected error fetching patients")
        return None, None, JsonResponse(
            {"error": "internal_error", "detail": str(exc)}, status=500
        )

    if since is not None:
        rows = _filter_since(rows, since)

    return rows, active_only, None


def patients_json(request):
    if not _check_api_key(request):
        return _unauthorized()

    rows, active_only, error = _load(request)
    if error:
        return error

    # --- VenezuelaReporta: always last 10 minutes, status=encontrado ---
    vr_since = dt.datetime.now(VENEZUELA_TZ) - dt.timedelta(minutes=10)
    try:
        vr_rows = fetch_vr_patients(since=vr_since)
    except (VRError, Exception) as exc:
        logger.warning("VenezuelaReporta fetch failed, omitting from response: %s", exc)
        vr_rows = []

    if vr_rows:
        splits = split_names(vr_rows)
        # Filter records Gemini flagged as test/fake data
        real_pairs = [(r, s) for r, s in zip(vr_rows, splits) if s is not None]
        real_vr_rows = [r for r, _ in real_pairs]
        real_splits  = [s for _, s in real_pairs]
        if len(vr_rows) - len(real_vr_rows):
            logger.info(
                "Gemini discarded %d test/fake VR records",
                len(vr_rows) - len(real_vr_rows),
            )
    else:
        real_vr_rows, real_splits = [], []

    if _truthy(request.GET.get("raw")):
        data = rows + real_vr_rows
    else:
        data = normalize_many(rows) + normalize_vr_many(real_vr_rows, real_splits)

    return JsonResponse(
        {
            "count": len(data),
            "active_only": active_only,
            "results": data,
        }
    )
