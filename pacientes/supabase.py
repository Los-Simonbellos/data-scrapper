"""
Thin read-only client for the public Supabase backend that powers
https://registro-pacientes-sismo-vzla.pages.dev/.

The site's "Exportar a Excel" button is built entirely in the browser
(SheetJS) from rows the SPA fetches out of the `pacientes` table via the
Supabase REST API using the public anon key. So instead of driving a
headless browser, we query that same REST endpoint directly.

Supabase/PostgREST caps a single response at 1000 rows, so we page with
the `Range` header until we've pulled everything.
"""
from __future__ import annotations

import logging
from typing import Iterator

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

PAGE_SIZE = 1000
REQUEST_TIMEOUT = 30  # seconds


class SupabaseError(RuntimeError):
    """Raised when the upstream Supabase API returns an error."""


def _headers() -> dict:
    key = settings.SUPABASE_ANON_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }


def iter_patients(active_only: bool = True) -> Iterator[dict]:
    """
    Yield every patient row from the `pacientes` table, transparently
    paginating through the dataset.

    active_only: when True (default) only rows with deleted_at IS NULL are
    returned — this matches what the public site shows and exports.
    """
    base_url = f"{settings.SUPABASE_URL}/rest/v1/{settings.SUPABASE_TABLE}"
    params = {
        "select": "*",
        "order": "created_at.desc",
    }
    if active_only:
        params["deleted_at"] = "is.null"

    offset = 0
    while True:
        headers = _headers()
        headers["Range-Unit"] = "items"
        headers["Range"] = f"{offset}-{offset + PAGE_SIZE - 1}"

        resp = requests.get(
            base_url, params=params, headers=headers, timeout=REQUEST_TIMEOUT
        )
        if resp.status_code not in (200, 206):
            raise SupabaseError(
                f"Supabase returned {resp.status_code}: {resp.text[:500]}"
            )

        batch = resp.json()
        if not batch:
            break

        yield from batch

        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE


def fetch_patients(active_only: bool = True) -> list[dict]:
    """Return all patient rows as a list (convenience over iter_patients)."""
    rows = list(iter_patients(active_only=active_only))
    logger.info("Fetched %d patient rows from Supabase", len(rows))
    return rows
