# registro-pacientes scraper service

A small **Django** service that exposes the patient registry behind
[registro-pacientes-sismo-vzla.pages.dev](https://registro-pacientes-sismo-vzla.pages.dev/)
as a clean API another app can call. Deployable as a standalone service on **Vercel**.

## How it works

The source site is a React SPA. Its **"Exportar a Excel"** button is built
entirely **client-side** (SheetJS) from rows the SPA reads out of a public
**Supabase** `pacientes` table via the REST API + anon key.

So this service skips the browser entirely: it queries that same Supabase REST
endpoint directly (paginating through all rows), **normalizes** the data, and
returns it as JSON. This is far faster and more reliable on serverless than
driving a headless browser.

## Endpoints

| Method | Path                  | Description                                   |
| ------ | --------------------- | --------------------------------------------- |
| GET    | `/`                   | Health check + metadata                       |
| GET    | `/api/patients`       | Normalized patient records as JSON            |

Query params:

- `active=false` — include soft-deleted rows (default: active only).
- `since=<datetime>` — keep only rows whose latest timestamp (`updated_at`,
  else `created_at`) is strictly newer than the given ISO-8601 datetime;
  times without an offset are read as Venezuelan time (UTC-04:00).
- `raw=true` — return raw Supabase rows instead of normalized.

### Auth (API key)

Set `SERVICE_API_KEYS` (comma-separated) to require callers to send a matching
key, either as an `X-API-Key` header or `Authorization: Bearer <key>`. Keys are
compared in constant time. Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

```bash
curl -H "X-API-Key: <your-key>" http://127.0.0.1:8000/api/patients
```

Behaviour when no keys are configured is controlled by `SERVICE_REQUIRE_API_KEY`:

- `false` (default) — endpoint is **open**.
- `true` — endpoint **fails closed** (every request returns `401`), so a
  deploy that forgets to set keys is never accidentally public.

The `/` health check stays open regardless.

## Local development

```bash
python -m venv .venv
. .venv/Scripts/activate      # Windows (Git Bash);  use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env          # optional; sensible defaults are baked in
python manage.py runserver
```

Then:

```bash
curl http://127.0.0.1:8000/api/patients | head
```

## Deploy to Vercel

```bash
npm i -g vercel
vercel            # first deploy / link
vercel --prod
```

`vercel.json` routes all traffic to `config/wsgi.py` via `@vercel/python`.
Set the same env vars (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SERVICE_API_KEYS`,
`SERVICE_REQUIRE_API_KEY`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`) in the
Vercel dashboard.

> Vercel's Python runtime targets **3.12**. The code is 3.9+ compatible.

## Normalization

`pacientes/normalize.py` renames a fixed set of scraper fields and passes
everything else through unchanged: `nombre→nombres`, `apellido→apellidos`,
`hospital→hospitalDestino`, `observaciones→notas`, `created_at→createdAt`,
`updated_at→updatedAt`. Any other field (e.g. `id`, `cedula`, `edad`,
`estado`, `telefono`, `direccion`) keeps its original name and value.
