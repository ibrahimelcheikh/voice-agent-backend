# AtlasPrimeX — Product Suite

Four pieces, one backend:

| Folder | What it is | Stack | Deploy |
|---|---|---|---|
| `website/` | Marketing site | static HTML/CSS/JS | Railway (Caddy) |
| `merchant_app/` | Merchant dashboard (EN/AR RTL) | Flutter web + mobile | Railway (Caddy) |
| `primeops_app/` | Operator console | Flutter web | Railway (Caddy) |
| `voice-agent-backend/` | Live voice agent **+ new `/api/v1`** | FastAPI + Postgres | Railway (existing) |

## How they connect (Phase 4)

The existing FastAPI backend gained a versioned **`/api/v1`** that serves both apps,
reusing the multi-tenant models. Nothing about the live voice agent changed.

- **Auth (JWT):** `operator` (a `User` with `tenant_id = NULL`) sees the whole fleet;
  `merchant` (a `User` with a `tenant_id`) is scoped to its own tenant.
- **Reuses existing tables:** `Tenant` (merchant), `Clinic` (branch), `Service`, `Call`
  (calls + transcripts), `Appointment`, `Lead` (website leads).
- **Console edits change real agent behavior:** the merchant Settings screen writes to the
  exact tables the agent reads — greeting → `Tenant.greeting_message`, hours →
  `Clinic.hours`, system prompt → `BehaviorConfig`, voice → `Agent`. `load_tenant_config`
  now also surfaces the closed greeting / holidays / temporary closure.
- **Additive schema only:** new nullable columns (`tenants.closed_greeting`,
  `services.category/details`, `leads.email`, `users.title`) + new tables
  (`holidays`, `ops_alerts`, `ops_tickets`). Applied at startup via the backend's existing
  `ensure_columns()` + `create_all` pattern; a matching alembic revision is included. No
  existing column is altered or dropped.

### Demo logins (seeded automatically, idempotent)
- Operator (PrimeOps): `operator@atlasprimex.ai` / `demo1234`
- Merchant (Divinia): `merchant@atlasprimex.ai` / `demo1234`

## Run locally

**Backend** (needs Postgres, or point `DATABASE_URL` at one):
```bash
cd voice-agent-backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8030      # docs at /docs, API at /api/v1
```

**Flutter apps** — default to bundled mock data (no backend needed):
```bash
cd merchant_app && flutter run -d chrome                 # or: cd primeops_app && ...
```
Against the live backend (a login screen appears):
```bash
flutter run -d chrome --dart-define=USE_MOCK=false --dart-define=API_BASE=http://localhost:8030
```

**Website** — static; set the backend for the "Book a demo" form by editing the
`window.ATLASPRIMEX_API` line in `website/index.html` (blank = mailto fallback).

## Deploy on Railway (each app is its own service)

Each Flutter app + the website has its own `Dockerfile` + `railway.json`. In Railway:
1. **New → GitHub Repo** → this repo, once per app.
2. Set **Root Directory** to `website`, `merchant_app`, or `primeops_app`.
3. For the Flutter apps, set **build variables** `USE_MOCK=false` and
   `API_BASE=https://<your-backend>.up.railway.app` (Flutter bakes these at build time),
   then **Generate Domain**.
4. The backend service is unchanged — redeploying it picks up `/api/v1` and the additive
   migration on boot.

Per-app details are in each folder's `README.md`.
