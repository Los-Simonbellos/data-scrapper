"""
Gemini-powered name splitter for VenezuelaReporta records.

Sends all rows in a single API call. Returns one entry per input row:
  - None  → Gemini flagged as test/fake data; caller must skip this record.
  - dict  → {"nombres": str, "apellidos": str | None}

Fallback on any API/parse error: returns {"nombres": raw_nombre, "apellidos": None}
for every row — never silently drops records on failure.
"""
from __future__ import annotations

import json
import logging

from google import genai
from django.conf import settings

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.0-flash-lite"

_PROMPT = """\
You receive a list of patient records from an earthquake relief registry in Venezuela.
For each record, do TWO things:
1. Decide if it looks like test or fake data (e.g. single letters, "QA", "test",
   "prueba", "asdf", obviously fake names or cities). If so, return null.
2. Otherwise, split the full name (nombre) into nombres (first name) and apellidos
   (last name) using Hispanic naming conventions: the last 1-2 words are apellidos,
   the rest is nombres. When uncertain, use your best guess. apellidos can be null
   if only one word is present.

Return ONLY a JSON array in the same order as the input. Each element must be either:
  null
  {{"nombres": "...", "apellidos": "..."}}

Input:
{input_json}

Return only the JSON array, no explanation, no markdown."""


def split_names(rows: list[dict]) -> list[dict | None]:
    if not rows:
        return []

    fallback = [{"nombres": r.get("nombre") or "", "apellidos": None} for r in rows]

    if not getattr(settings, "GEMINI_API_KEY", ""):
        logger.warning("GEMINI_API_KEY not set — name split skipped, using raw nombres")
        return fallback

    input_data = [
        {
            "nombre": r.get("nombre") or "",
            "ciudad": r.get("ciudad") or "",
            "zona": r.get("zona") or "",
        }
        for r in rows
    ]
    prompt = _PROMPT.format(input_json=json.dumps(input_data, ensure_ascii=False))

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(model=_MODEL, contents=prompt)
        text = response.text.strip()

        # Strip markdown fences if the model wraps its output
        if text.startswith("```"):
            text = text[text.index("\n") + 1 :]
            if "```" in text:
                text = text[: text.rindex("```")]

        result = json.loads(text)

        if not isinstance(result, list) or len(result) != len(rows):
            raise ValueError(f"Response length mismatch: expected {len(rows)}, got {len(result)}")

        out: list[dict | None] = []
        for item in result:
            if item is None:
                out.append(None)
            else:
                out.append(
                    {
                        "nombres": item.get("nombres") or "",
                        "apellidos": item.get("apellidos") or None,
                    }
                )
        return out

    except Exception as exc:
        logger.warning("Gemini split failed (%s) — falling back to raw nombres", exc)
        return fallback
