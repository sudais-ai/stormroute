# StormRoute — Weather-Aware Truck Routing

Compares real route options for a trucking trip by sampling wind, rain, and snow forecasts along each route at the times the truck would arrive, and recommends the safest route using a fixed lexicographic priority order. Built for the Spotter AI Full Stack Developer assessment.

**Status: Phases 1–10 implemented and verified (2026-10-25). Backend tests: 224 (incl. dedicated scoring suite — see Tests), Frontend 80/80, TypeScript clean, production build PASS (2026-10-25). Deliverables remaining: GitHub remote/push, hosted URL, Loom walkthrough.** See `docs/ASSESSMENT_SPEC.md`, `docs/PHASE_PLAN.md`, and `docs/TEST_LOG.md`.

## What it does (assessment scope)

1. **Trip Input** — Origin, Destination, Departure (ISO-8601 with timezone), Load Weight (lb), Checkpoint Interval (10/25/50 mi)
2. **Three Route Generation** — Real Mapbox Directions alternatives (honest 1–3 routes; never fabricated)
3. **Checkpoint Sampling** — Haversine along provider geometry at chosen interval; cap/widening; UTC ETAs
4. **Hourly Weather** — Open-Meteo wind/rain/snow, exact-hour match to checkpoint arrivals
5. **Risk Classification** — Spec-mandated wind/rain/snow bands + load rules; combined = max with No Travel precedence
6. **Route Scoring** — Lexicographic: fewest Severe mi → fewest High mi → lowest average risk → shortest time
7. **Recommendation** — Deterministic; explanation names the deciding tie-break factor
8. **Interactive Map** — MapLibre GL (OpenFreeMap tiles); route lines, risk-colored markers, legend, selection sync
9. **Corridor Heatmap + Forecast Slider** — Gridded ~11 km samples, 0–48 h real timestamps; slider updates map + markers + tooltip consistently
10. **Unknown Handling** — Unknown weather/risk never renders as safe (own legend level)
11. **Deliverables** — GitHub repo, hosted app, Loom walkthrough (Phase 10)
12. **Documentation** — README, Architecture, Limitations (Phase 10)

## Stack

- **Frontend** `frontend/` — React 19 + TypeScript + Vite + Tailwind CSS v4
- **Backend** `backend/` — Python 3.12 + Django 6.1 + Django REST Framework
- **Map** MapLibre GL v6 with OpenFreeMap tiles (no key)
- **Providers** Mapbox (Directions + Geocoding, token), Open-Meteo (hourly weather, no key, non-commercial CC BY 4.0)

## Quick Start

Prerequisites: **Python 3.12+** and **Node 18+**. Commands below are PowerShell (Windows); the same steps apply on macOS/Linux with the venv path adjusted (`source .venv/bin/activate`).

```powershell
# 1) Backend  ->  http://127.0.0.1:8001  (health check: /api/health/)
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
#    -> open backend\.env and paste your Mapbox token into MAPBOX_ACCESS_TOKEN
.venv\Scripts\python.exe manage.py migrate    # one-time; creates a local gitignored db.sqlite3 for Django's built-in system tables (the API itself defines no database models)
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001

# 2) Frontend  ->  http://localhost:5173  (proxies /api to the backend)
cd ..\frontend
npm install
$env:API_PROXY_TARGET = "http://localhost:8001"   # dev proxy default is 8000; point it at the backend port you chose
npm run dev
```

- **Mapbox token:** free tier — create an account at `cloud.mapbox.com` and generate an access token. It belongs **only** in gitignored `backend/.env` (`MAPBOX_ACCESS_TOKEN`); it is required for Directions (route alternatives) and Geocoding. Open-Meteo weather and OpenFreeMap map tiles need no key. Real credentials must never be committed.
- **Health check:** open `http://127.0.0.1:8001/api/health/` — it should respond HTTP 200.
- **Ports:** if a port is taken, pick the next free port and set `API_PROXY_TARGET` before starting Vite. Never kill processes you did not start.
- **Smoke test:** submit **Chicago, IL → Denver, CO** with a departure a few hours ahead. Expect live Mapbox routes (this corridor returns 2), risk-colored checkpoint markers, a heatmap corridor, and a scored recommendation with its deciding factor.

## Tests

```powershell
# Backend (224 tests — routing, checkpoints, weather, risk, scoring, heatmap suites)
cd backend
.venv\Scripts\python.exe manage.py test core

# Frontend (80 tests)
cd ..\frontend
npm run test
npx tsc --noEmit
npm run build
```

**Current results (2026-10-25):** Backend 224/224 PASS (incl. 24-test dedicated scoring suite, `test_scoring.py`), Frontend 80/80 PASS, TypeScript clean, production build PASS. Browser: console 0 errors, light UI, 89 live checkpoint markers, hour-slider ↔ marker-title math verified; screenshots in `docs/verification/product-quality/`.

`docs/TEST_LOG.md` records every real command, browser check, and outcome per phase.
`docs/verification/` contains screenshots across phases 1–10.

## Production Preview

```powershell
cd frontend
npm run build
$env:API_PROXY_TARGET = "http://localhost:8001"
npm run preview -- --port 4179
```

(Use any free port; `vite.config.ts` routes `/api` through `preview.proxy`.)

## Deploy (Render backend + Netlify frontend)

Config files live at repo root: `render.yaml` (backend blueprint) and `netlify.toml`
(frontend build + `/api/*` proxy). No secrets are committed anywhere — you supply
account-specific values in each platform's dashboard.

**1) Backend on Render** — New Blueprint → pick this repo → `render.yaml` is read
automatically (service `stormroute-backend`, `backend/` root, migrate on build,
gunicorn start with `--timeout 180`). On first sync, fill these env vars (no real
values needed in the repo):

| Env var | Set it to |
|---|---|
| `DJANGO_ALLOWED_HOSTS` | your Render service domain, e.g. `stormroute-backend.onrender.com` |
| `CORS_ALLOWED_ORIGINS` | your Netlify site URL, e.g. `https://stormroute.netlify.app` |
| `MAPBOX_ACCESS_TOKEN` | your Mapbox token (server-side only; never bundled into the frontend) |

`DJANGO_DEBUG` is pinned to `0` in the blueprint. The free plan sleeps after
~15 min idle — the first request after a nap takes ~50 s to cold-start.

Two `check --deploy` residuals are accepted on purpose: `mail.E001` (the app
sends no email — the console mail backend is startproject boilerplate and
harmless to logs) and the `W004/W009-style` secret warnings your Render env
closes automatically via `DJANGO_SECRET_KEY` (`generateValue: true`).

**2) Frontend on Netlify** — New site from Git → build base `frontend`,
command `npm run build`, publish `dist` (already in `netlify.toml`). Then open
`netlify.toml` and replace `RENDER-BACKEND-URL.onrender.com` in the `/api/*`
redirect with your real Render domain, and redeploy.

**Behavior notes (honest):** the frontend already calls relative `/api/*`
endpoints, so no code change is needed — only the proxy rule. Netlify's proxy
layer may cut very long responses (route generation takes 60–120 s live); the
180 s gunicorn timeout on Render is the source of truth, but if a first request
times out at Netlify, retry once on a warm instance. The sqlite database only
holds Django system tables (no app models), so the free-tier ephemeral disk is
harmless here.

## Assessment Evidence

| Requirement | Status | Evidence |
|---|---|---|
| 1. Trip Input | PASS | 27 backend + 27 frontend tests; 16 browser checks (phase-02) |
| 2. Route Generation | PASS | 53 backend tests; live probe 2 routes; 8 browser checks (phase-03) |
| 3. Checkpoints | PASS | 91 backend tests; live probe 42+47 checkpoints; 9 browser checks (phase-04) |
| 4. Weather | PASS | 114 backend tests; live probe 42/47 with weather; 8 browser checks (phase-05) |
| 5. Risk | PASS | 67 backend tests; classification boundaries tested |
| 6. Scoring | PASS | 24-test dedicated suite (`test_scoring.py`): priorities, exclusion, determinism, no-safe-route |
| 7. Recommendation | PASS | Explanation strings per route; deciding factor named |
| 8. Map | PASS | 80 frontend tests; phase-08 screenshots (map viewport, full page) |
| 9. Heatmap + Slider | PASS | 224 backend / 80 frontend tests; burst drag + hidden-tab fallback verified; 7 screenshots (phase-09) |
| 10. Unknown Handling | PASS | Unit tested both sides; legend includes Unknown |
| 11. Deliverables | **BLOCKED (user-gated)** | GitHub remote/push, hosted URL, Loom — awaiting explicit instruction |
| 12. Documentation | PASS | README (this), `docs/` set current to 2026-10-25 reality |

## Honest Limitations

- **Checkpoint sampling**: Haversine on simplified overview geometry (geometry distance ≠ provider distance; both disclosed in API response and UI)
- **ETA**: Constant average speed by distance — no traffic, weather, stops, or per-leg provider durations
- **Heatmap**: ~11 km gridded corridor approximation — not road-level certainty; disclosed in UI copy and backend docstrings
- **Live forecast**: Was calm (all Low); Severe/No Travel rendering proven by unit tests + synthetic matrix, not live event
- **Weather API**: Open-Meteo free tier is **non-commercial only** (CC BY 4.0) — assessment use is non-commercial
- **Mapbox alternatives**: Corridor-dependent; Chicago→Denver returns 2 routes live; honest <3 warning rendered, no synthetic padding
- **Playwright MCP**: Extension wedges on synthesized clicks; substituted with script-driven real-Chrome harness (disclosed in every phase)

## Attribution

- Map data: OpenStreetMap contributors via OpenFreeMap (no key required)
- Weather: Open-Meteo Forecast API (CC BY 4.0 attribution; non-commercial free tier)

## Project Structure

```
StormRoute CH/
├── backend/           # Django + DRF
│   ├── core/          # Services (routing, checkpoints, weather, risk, scoring, heatmap) + test suites (incl. test_scoring.py)
│   ├── stormroute/    # Django settings, urls
│   └── scripts/       # Live probe scripts
├── frontend/          # React + Vite + Tailwind
│   ├── src/
│   │   ├── components/  # TripForm, RouteOptions, MapViewport, ForecastSlider, etc.
│   │   ├── lib/         # heatmap.ts (pure helpers), validation.ts, api/trips.ts
│   │   └── types/       # TypeScript interfaces
│   └── scripts/         # Browser verification harnesses
├── docs/
│   ├── fs-assessment-spotter.pdf           # Original assessment brief (PDF)
│   ├── ASSESSMENT_SPEC.md                  # Assessment requirements (authoritative)
│   ├── ASSESSMENT_REQUIREMENT_MATRIX.md    # Requirement-by-requirement compliance matrix
│   ├── FINAL_ASSESSMENT_COMPLIANCE_AUDIT.md # Final compliance audit report
│   ├── PHASE_PLAN.md                       # 10-phase plan with hour budgets
│   ├── TEST_LOG.md                         # Evidence log with real commands + outcomes
│   ├── DECISIONS.md                        # Append-only design decisions
│   ├── ARCHITECTURE.md                     # System architecture
│   ├── LIMITATIONS.md                      # Known limitations in detail
│   ├── API_PROVIDER_RESEARCH.md            # Provider research (Mapbox, Open-Meteo)
│   └── verification/                       # Screenshots + results per phase
├── .env.example        # Variable names only (placeholders; real values never committed)
├── .gitignore
└── README.md
```
