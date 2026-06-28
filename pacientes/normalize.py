"""
Normalization layer.

Maps the raw Supabase `pacientes` row (as fetched by the scraper) to the
output shape. Only the keys below are renamed; every other field is passed
through unchanged, with its original key and value.

    scraper field   ->  output field
    -------------------------------------
    nombre          ->  nombres
    apellido        ->  apellidos
    hospital        ->  hospitalDestino
    observaciones   ->  notas
    created_at      ->  createdAt
    updated_at      ->  updatedAt
    cedula          ->  cedula      (unchanged)
    edad            ->  edad        (unchanged)
    estado          ->  estado      (unchanged)

Anything not listed (e.g. id, telefono, direccion, deleted_at) is returned
as-is.
"""
from __future__ import annotations

import datetime as dt

from django.utils.dateparse import parse_datetime

# Raw scraper key -> output key. Keys that map to themselves are omitted; the
# passthrough below keeps them (and any unknown fields) under their own name.
RENAME = {
    "nombre": "nombres",
    "apellido": "apellidos",
    "hospital": "hospitalDestino",
    "observaciones": "notas",
    "created_at": "createdAt",
    "updated_at": "updatedAt",
}

# Venezuela has no DST: UTC-04:00 year-round.
VENEZUELA_TZ = dt.timezone(dt.timedelta(hours=-4))

# Output keys whose values are timestamps to re-express in Venezuelan time.
TIMESTAMP_KEYS = {"createdAt", "updatedAt", "deleted_at"}


def _to_venezuela(value):
    """Re-express an ISO-8601 timestamp string in Venezuelan time (UTC-04:00).

    Supabase returns timestamps in UTC (e.g. ...T00:23:49+00:00); this converts
    them to the same instant in VET (...T20:23:49-04:00). Non-timestamp values
    (None, empty, unparseable) are returned unchanged.
    """
    if not isinstance(value, str) or not value.strip():
        return value
    parsed = parse_datetime(value)
    if parsed is None:
        return value
    # Naive timestamps from the DB are stored as UTC; assume so.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(VENEZUELA_TZ).isoformat()


def normalize_patient(row: dict) -> dict:
    """Return the row with mapped keys renamed and all others passed through.

    Timestamp fields are converted from UTC to Venezuelan time so input
    (`since=`) and output use the same timezone.
    """
    out = {RENAME.get(key, key): value for key, value in row.items()}
    for key in TIMESTAMP_KEYS:
        if key in out:
            out[key] = _to_venezuela(out[key])
    out["fuente"] = "supabase"
    return out


def normalize_many(rows: list[dict]) -> list[dict]:
    return [normalize_patient(r) for r in rows]


# ---------------------------------------------------------------------------
# VenezuelaReporta normalization
# ---------------------------------------------------------------------------

def _build_direccion(ciudad: str | None, zona: str | None) -> str | None:
    parts = [p for p in [ciudad, zona] if p]
    return ", ".join(parts) if parts else None


def normalize_vr_patient(row: dict, split: dict) -> dict:
    """Map a VenezuelaReporta row to the established output schema."""
    ciudad = row.get("ciudad") or None
    zona = row.get("zona") or None
    return {
        "id":             row.get("id"),
        "fuente":         "venezreporta",
        "status":         row.get("status"),
        "nombres":        split.get("nombres") or None,
        "apellidos":      split.get("apellidos") or None,
        "cedula":         row.get("cedula"),
        "edad":           row.get("edad"),
        "genero":         row.get("genero"),
        "estado":         "desconocido",
        "direccion":      _build_direccion(ciudad, zona),
        "hospitalDestino": row.get("ultima_vez"),
        "notas":          row.get("descripcion"),
        "telefono":       None,
        "createdAt":      _to_venezuela(row.get("created_at")),
        "updatedAt":      None,
        "deleted_at":     None,
        "foto_url":       row.get("foto_url"),
        "ficha_url":      row.get("ficha_url"),
        "verificado":     row.get("verificado"),
        "verificado_por": row.get("verificado_por"),
        "verificado_at":  row.get("verificado_at"),
    }


def normalize_vr_many(rows: list[dict], splits: list[dict]) -> list[dict]:
    return [normalize_vr_patient(r, s) for r, s in zip(rows, splits)]


# ---------------------------------------------------------------------------
# tuia911 normalization
# ---------------------------------------------------------------------------

def _build_tuia_direccion(referencia: str | None, municipio: str | None, estado_geo: str | None) -> str | None:
    parts = [p for p in [referencia, municipio, estado_geo] if p]
    return ", ".join(parts) if parts else None


def normalize_tuia_patient(row: dict, split: dict) -> dict:
    """Map a tuia911 row to the established output schema."""
    return {
        "id":              row.get("id"),
        "fuente":          "tuia911",
        "nombres":         split.get("nombres") or None,
        "apellidos":       split.get("apellidos") or None,
        "cedula":          None,
        "edad":            row.get("edad"),
        "genero":          row.get("genero"),
        "estado":          "desconocido",
        "direccion":       _build_tuia_direccion(
                               row.get("referencia"),
                               row.get("municipio"),
                               row.get("estado_geo"),
                           ),
        "hospitalDestino": None,
        "notas":           row.get("descripcion"),
        "telefono":        None,
        "createdAt":       _to_venezuela(row.get("created_at")),
        "updatedAt":       None,
        "deleted_at":      None,
        "foto_url":        row.get("foto_url"),
        "estado_registro": row.get("estado_registro"),
    }


def normalize_tuia_many(rows: list[dict], splits: list[dict]) -> list[dict]:
    return [normalize_tuia_patient(r, s) for r, s in zip(rows, splits)]
