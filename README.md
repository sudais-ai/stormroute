# StormRoute — Weather-Aware Truck Routing

Compares real route options for a trucking trip by sampling wind, rain, and snow forecasts along each route at the times the truck would arrive, and recommends the safest route using a fixed lexicographic priority order. Built for the Spotter AI Full Stack Developer assessment.

**Status: Phases 1–10 implemented and verified — UI product-quality rebuild + browser re-verification completed 2026-10-25 (backend 200/200, frontend 80/80, build PASS, console-clean browser runs). Deliverables that remain: GitHub remote/push, hosted URL, Loom walkthrough.** See `docs/STATUS.md`, `docs/ASSESSMENT_SPEC.md`, `docs/PHASE_PLAN.md`, and `docs/TEST_LOG.md`.

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

## Local Development (Windows)

```powershell
# Frontend  -> http://localhost:5173 (proxies /api to backend)
cd frontend
npm install
$env:API_PROXY_TARGET = "http://localhost:8001"   # keep proxy on the right backend port
npm run dev

# Backend   -> http://127.0.0.1:8001 (health: /api/health/)
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001
```

**Port conflicts (real, updated 2026-10-25):** earlier phases ran the stack on 5174/8001 because a stale sibling session held 5173/8000; that session is gone — today 5173 serves the dev frontend and 8001 the backend. If a port is taken, pick the next free port and set `API_PROXY_TARGET` before starting Vite. Never kill processes you did not start.

Real provider credentials belong **only** in gitignored `backend/.env` — copy `.env.example` and fill values locally; **never commit them**.

## Tests

```powershell
# Backend (200 tests)
cd backend
.venv\Scripts\python.exe manage.py test core

# Frontend (80 tests)
cd ..\frontend
npm run test
npx tsc --noEmit
npm run build
```

**Current results (2026-10-25 re-run):** Backend 200/200 PASS (exit 0), Frontend 80/80 PASS, TypeScript clean, Build PASS (worker chunk emitted). Browser: console 0 errors, dark UI, 89 live checkpoint markers, hour-slider ↔ marker-title math verified; screenshots in `docs/verification/product-quality/` (product-quality-01…04).

`docs/TEST_LOG.md` records every real command, browser check, and outcome per phase.
`docs/verification/` contains screenshots across phases 1–10.

## Production Preview

```powershell
cd frontend
npm run build
$env:API_PROXY_TARGET = "http://localhost:8001"
npm run preview -- --port 4179
```

(4175 occupied by an unrelated local process on 2026-10-25 — use any free port; `vite.config.ts` routes `/api` through `preview.proxy`.)

## Assessment Evidence

| Requirement | Status | Evidence |
|---|---|---|
| 1. Trip Input | PASS | 27 backend + 27 frontend tests; 16 browser checks (phase-02) |
| 2. Route Generation | PASS | 53 backend tests; live probe 2 routes; 8 browser checks (phase-03) |
| 3. Checkpoints | PASS | 91 backend tests; live probe 42+47 checkpoints; 9 browser checks (phase-04) |
| 4. Weather | PASS | 114 backend tests; live probe 42/47 with weather; 8 browser checks (phase-05) |
| 5. Risk | PASS | 67 backend tests; classification boundaries tested |
| 6. Scoring | PASS | Lexicographic integration tested; UI rendering verified |
| 7. Recommendation | PASS | Explanation strings per route; deciding factor named |
| 8. Map | PASS | 80 frontend tests; phase-08 screenshots (map viewport, full page) |
| 9. Heatmap + Slider | PASS | 200 backend / 80 frontend tests; burst drag + hidden-tab fallback verified; 7 screenshots (phase-09) |
| 10. Unknown Handling | PASS | Unit tested both sides; legend includes Unknown |
| 11. Deliverables | **PENDING** | GitHub remote/push, hosted URL, Loom — awaiting explicit instruction |
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
│   ├── core/          # Services (routing, checkpoints, weather, risk, scoring, heatmap)
│   ├── stormroute/    # Django settings, urls
│   └── scripts/       # Live probe scripts
├── frontend/          # React + Vite + Tailwind
│   ├── src/
│   │   ├── components/  # TripForm, RouteOptions, MapViewport, ForecastSlider, etc.
│   │   ├── lib/         # heatmap.ts (pure helpers), validation.ts, api/trips.ts
│   │   └── types/       # TypeScript interfaces
│   └── scripts/         # Browser verification harnesses
├── docs/
│   ├── ASSESSMENT_SPEC.md      # Assessment requirements (authoritative)
│   ├── PHASE_PLAN.md           # 10-phase plan with hour budgets
│   ├── STATUS.md               # Canonical status (updated every session)
│   ├── TEST_LOG.md             # Evidence log with real commands + outcomes
│   ├── DECISIONS.md            # Append-only design decisions
│   ├── MISSING_INFO.md         # Blocker/key tracker (set/unset only)
│   ├── VERIFICATION_PROTOCOL.md # Mandatory browser verification rules
│   └── verification/           # 44+ screenshots per phase
├── .env.example
├── .gitignore
├── AGENTS.md          # Session rules + multi-agent pipeline
├── FINAL_ASSESSMENT_CHECKLIST.md # Requirements 1-12 mapped to evidence
└── PLAN.md            # Phase 10 execution plan
```