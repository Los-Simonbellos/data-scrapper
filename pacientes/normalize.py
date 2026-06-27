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


def normalize_patient(row: dict) -> dict:
    """Return the row with mapped keys renamed and all others passed through."""
    return {RENAME.get(key, key): value for key, value in row.items()}


def normalize_many(rows: list[dict]) -> list[dict]:
    return [normalize_patient(r) for r in rows]
