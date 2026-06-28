# registro-pacientes scraper service

A Django service deployed on Vercel that exposes the patient registry from [registro-pacientes-sismo-vzla.pages.dev](https://registro-pacientes-sismo-vzla.pages.dev/) as a clean JSON API.

The source site is a React SPA that reads from a public Supabase `pacientes` table. This service skips the browser entirely and queries that same Supabase REST endpoint directly, paginates all rows, normalizes field names, and returns JSON.

## Endpoints

- `GET /` — health check
- `GET /api/patients` — normalized patient records

Query params: `active=false`, `since=<ISO-8601 datetime>`, `raw=true`

Auth: `X-API-Key` header or `Authorization: Bearer <key>`. Configured via `SERVICE_API_KEYS` env var.

## Stack

- **Django** (Python 3.9+) — web framework
- **Supabase REST API** — data source (`pacientes/supabase.py`)
- **Vercel** — deployment target (`vercel.json`, `config/wsgi.py`)
- Field normalization in `pacientes/normalize.py`: `nombre→nombres`, `apellido→apellidos`, `hospital→hospitalDestino`, `observaciones→notas`, `created_at→createdAt`, `updated_at→updatedAt`

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
- Author a backlog-ready spec/issue → invoke /spec
