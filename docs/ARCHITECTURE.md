# StormRoute — Architecture Documentation

**Generated:** 2026-10-24 | **Status:** Phase 10 complete

---

## 1. High-Level Data Flow

```
┌─────────────┐    POST /api/trips/routes/    ┌──────────────────┐
│  Frontend   │ ─────────────────────────────► │     Backend      │
│  (React)    │ ◄───────────────────────────── │   (Django+DRF)   │
└─────────────┘     JSON: routes + risk +       └────────┬─────────┘
                          checkpoints + weather +                 │
                          heatmaps                                │
                               │                                  │
                               ▼                                  ▼
                    ┌─────────────────────┐           ┌──────────────────┐
                    │   MapLibre GL Map   │           │  External APIs   │
                    │   (OpenFreeMap)     │           │  Mapbox (token)  │
                    │   Routes + Heatmap  │           │  Open-Meteo (no  │
                    │   Markers + Slider  │           │  key, non-comm)  │
                    └─────────────────────┘           └──────────────────┘
```

---

## 2. Component Architecture

### Frontend (`frontend/src/`)

| Layer | Files | Responsibility |
|-------|-------|----------------|
| **Entry** | `main.tsx`, `App.tsx` | Bootstrap, state orchestration (trip form → route data → map + slider) |
| **Trip Form** | `TripForm.tsx`, `lib/validation.ts` | Client-side validation mirroring DRF serializer; ISO-8601 + offset required |
| **Route Display** | `RouteOptions.tsx` | Neutral Route N cards; risk breakdown; weather section; honest <3 warning |
| **Map** | `MapViewport.tsx` | MapLibre GL init; worker URL fix; route layers; checkpoint markers; heatmap layer; hover tooltip; legend; dev handle `window.__stormrouteMap` |
| **Slider** | `ForecastSlider.tsx` | Real `<input type=range>` 0–48; tick labels; approximation disclosure; honest disabled state |
| **API Client** | `api/trips.ts` | `generateRoutesOnBackend()`, `validateTripOnBackend()`; proxied via Vite `/api` |
| **Pure Helpers** | `lib/heatmap.ts` | Classification mirror, hourOffset/ISO mapping, grid/point weather lookup, `createCoalescedDraw` (visibility-aware frame scheduler) |
| **Types** | `types/route.ts` | All request/response interfaces (TripInput, RouteOption, RouteCheckpoint, RouteHeatmap, etc.) |

### Backend (`backend/core/`)

| Service | File | Responsibility |
|---------|------|----------------|
| **Routing** | `services/routing.py` | `generate_routes()` — Mapbox geocode + Directions, dedup, checkpoint sampling, weather enrichment, risk analysis, scoring, heatmap generation, response assembly |
| **Checkpoints** | `services/checkpoints.py` | Pure: haversine sampling along LineString, interval/cap/widening, interpolation, stable IDs, UTC ETA distribution |
| **Weather** | `services/weather.py` | Pure: Open-Meteo fetch (multi-location batched), exact-hour match, coordinate dedup, error taxonomy |
| **Risk** | `services/risk.py` | Pure: wind/rain/snow band classification, load rules, combined = max (No Travel dominant), route risk-mile aggregation |
| **Scoring** | `services/scoring.py` | Pure: `rank_and_recommend()` — lexicographic priority (Severe mi → High mi → avg risk → duration) |
| **Heatmap** | `services/weather_heatmap.py` | Pure: corridor grid sampling (~11 km, ≤60 pts/route, cross-route dedup), Open-Meteo batches (50 coords), 49 hourly buckets, null-safe |
| **Views** | `views.py` | DRF endpoints: `TripValidateView` (POST /api/trips/validate/), `TripRoutesView` (POST /api/trips/routes/) |
| **Settings** | `stormroute/settings.py` | `MAPBOX_ACCESS_TOKEN` from env; `CHECKPOINT_MAX_PER_ROUTE=500`; risk thresholds from settings with spec defaults |

---

## 3. API Contracts

### POST `/api/trips/validate/`
**Input:** `origin`, `destination`, `departureISO` (ISO-8601 **with timezone offset**), `loadWeightLb` (>=0), `checkpointIntervalMiles` in {10,25,50}
**Output:** Normalized trip or 400 with field errors. **No persistence, no routing, no weather.**

### POST `/api/trips/routes/`
**Input:** Same as validate.
**Output (success):**
```json
{
  "routesAvailable": true,
  "trip": { ... },
  "origin": { "resolvedName", "longitude", "latitude" },
  "destination": { ... },
  "routesRequested": 3,
  "routeCount": 2,
  "threeRoutesReturned": false,
  "duplicatesDropped": 0,
  "warning": "Mapbox returned 2 distinct routes — Only real provider options are shown...",
  "routes": [
    { "routeId": "rt_...", "label": "Route 1", "geometry", "distanceMeters", "distanceMiles",
      "durationSeconds", "durationReadable", "providerRouteSummary", "arrivalISO",
      "checkpoints": [...], "checkpointSummary": {...} }
  ],
  "weatherSummaries": [ { "routeId", "totalCheckpoints", "checkpointsWithWeather", ... } ],
  "riskSummaries": [ { "routeId", "riskMiles": { "no_travel":0, "severe":0, ... }, "totalMiles" } ],
  "recommendation": { "status", "explanation", "recommendedRouteId", "rankedRouteIds", "routeExplanations" },
  "heatmaps": [ { "routeId", "gridPoints": [{ "longitude", "latitude", "hours[]", "windMph[]", ... }], "forecastStartISO", "forecastEndISO", "forecastHours": 48 } ]
}
```
**Error taxonomy:** `config_missing` 503, `auth_failed` 502, `geocode_failed` 422 (stage: origin/destination), `no_routes` 422, `provider_timeout` 504, `rate_limited` 429, `provider_response` 502, `geometry_invalid` 502.

---

## 4. Key Algorithms

### Checkpoint Sampling (`checkpoints.py`)
- Validates GeoJSON LineString coordinates strictly as `[longitude, latitude]`
- Measures **traveled** distance via haversine (R = 6,371,008.8 m) along real vertices
- Interpolates between vertices when sample target falls mid-segment
- Interval = validated `checkpointIntervalMiles` ∈ {10, 25, 50}
- Cap `CHECKPOINT_MAX_PER_ROUTE` (default 500): **widens spacing** (never truncates), destination retained, response discloses `capped` + `effectiveIntervalMiles`
- Origin = seq 1 at 0 m; destination always final checkpoint; no duplicate when dest coincides with interval
- ETA = `departureUTC + providerDurationSeconds × (cumulativeDistance / geometryLength)`

### Weather Matching (`weather.py`)
- Checkpoint `arrivalISO` truncated to hour (e.g., `2099-01-01T16:23:45Z` → `2099-01-01T16:00`)
- Exact match against provider `hourly.time` array (UTC) — **no interpolation, no nearest-hour fallback**
- Missing hour → `timeMatch: "out_of_horizon"`; provider error → `timeMatch: "provider_error"`
- Coordinate conversion: checkpoints are `[lng, lat]` → Open-Meteo needs `(lat, lon)`
- Deduplication: round to 4 dp (~11 m) to avoid duplicate API calls

### Risk Classification (`risk.py`)
- **Wind** (mph): `<25` Low, `25–<35` Moderate, `35–<45` High, `45–<55` Severe, `≥55` No Travel
- **Rain** (in/hr): `<0.10` Low, `0.10–<0.25` Moderate, `0.25–<0.50` High, `0.50–≤1.00` Severe, `>1.00` No Travel
- **Snow** (in/hr): `<0.5` Low, `0.5–<1.0` Moderate, `1.0–<2.0` High, `2.0–≤3.0` Severe, `>3.0` No Travel
- **Load rules**: ≥55 mph wind = No Travel any load; 45–55 mph + >30k lb = No Travel; 35–45 mph + >40k lb = Severe
- **Combined** = `max(condition risks)` with **No Travel precedence**; unknown → unknown

### Scoring (`scoring.py`)
Lexicographic priority (no weighted sum):
1. Fewest **Severe-risk miles**
2. Fewest **High-risk miles**
3. Lowest **average risk** (ordinal: Low=0, Moderate=1, High=2, Severe=3, No Travel=4)
4. Shortest **travel time**

### Heatmap Grid (`weather_heatmap.py`)
- Deterministic haversine sampling along LineString at ~11 km spacing (stretched at cap)
- Cross-route coordinate dedup by 4 dp rounding (~11 m)
- Open-Meteo multi-location: `latitude=a,b,c&longitude=...` returns array in request order
- 50 coords/request; 49 hourly buckets (0–48 h inclusive)
- Per-value null-safety: missing hour → unknown; provider failures drop points
- Try/except wrapped — heatmap outage degrades to `[]`, never breaks routes

---

## 5. MapLibre Worker Fix (Phase 8→9 Root Cause)

**Problem:** MapLibre v6 `setWorkerUrl` + Vite dev pre-bundling corrupted the module-worker URL → "Worker failed to load" ×2 in dev console.

**Fix:**
1. `vite.config.ts`: `optimizeDeps.exclude: ['maplibre-gl']` — skips pre-bundling
2. `MapViewport.tsx`: `import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'` (static analysis) + `setWorkerUrl(maplibreWorkerUrl)` at module top
3. `vite.config.ts` preview: added `preview.proxy` for `/api` (vite preview doesn't inherit server.proxy)

**Result:** 0 console errors dev + prod; worker chunk `maplibre-gl-worker-BrB25tGK.mjs` (518.80 kB) emitted as real asset.

---

## 6. Visibility-Aware Draw Scheduler (`lib/heatmap.ts`)

**Problem:** `requestAnimationFrame` pauses entirely in hidden/occluded Chrome tabs → rapid slider drag left map on stale value.

**Solution:** `createCoalescedDraw` with **per-enqueue visibility check**:
- Visible tab → `requestAnimationFrame` (fluid drag, ≤1 frame)
- Hidden tab / SSR / tests → 16 ms `setTimeout` (Chrome throttles but fires; lands ≤1 s)
- Test-injectable timer for deterministic unit tests
- Frame-coalesced, latest-wins: burst enqueues collapse to single draw with last value

---

## 7. Security & Configuration

| Aspect | Implementation |
|--------|----------------|
| **Mapbox token** | Server-side only; `backend/.env` (gitignored); loaded via python-dotenv at import; never in `VITE_*` vars, never rendered, never logged |
| **Open-Meteo** | No key; free tier non-commercial (CC BY 4.0) |
| **Map tiles** | OpenFreeMap (no key) |
| **CORS** | `localhost:5173`, `localhost:5174` allowed |
| **Debug** | `DEBUG=True` local; production would set `DEBUG=False`, `ALLOWED_HOSTS` |
| **Secrets in build** | Verified: `npm run build` output scanned — no `MAPBOX_ACCESS_TOKEN`, `pk.`, `sk.`, or secrets in `dist/` |
| **Error messages** | Fixed strings only; no provider text/URL/token echo |

---

## 8. Testing Strategy

| Layer | Tool | Scope |
|-------|------|-------|
| Backend unit | Django TestCase + mocked `requests` | 200 tests: validation, routing, checkpoints, weather, risk, scoring, heatmap, token hygiene |
| Frontend unit | Vitest + jsdom | 80 tests: validation, TripForm flow, heatmap helpers, coalesced-draw scheduling (incl. hidden-tab) |
| Integration | Live probe scripts | Real Mapbox + Open-Meteo against dev servers (phases 3–5) |
| Browser E2E | Playwright-core (script-driven real Chrome) | 9 verification sessions, 91 checks, 44+ screenshots per `docs/verification/` |
| Type check | `tsc --noEmit` | Exit 0 |
| Lint | oxlint | Only 2 pre-existing `ServiceStatusCard` warnings |

---

## 9. Deployment Configuration

### Environment Variables (Production)
| Variable | Required | Description |
|----------|----------|-------------|
| `MAPBOX_ACCESS_TOKEN` | Yes | Mapbox Directions + Geocoding token (server-only) |
| `DJANGO_SECRET_KEY` | Yes | Random 50+ char string |
| `DEBUG` | No | `False` in production |
| `ALLOWED_HOSTS` | Yes | Comma-separated hostnames |
| `CHECKPOINT_MAX_PER_ROUTE` | No | Default 500 (min 2) |
| `API_PROXY_TARGET` | Frontend only | Backend URL for Vite dev/preview proxy |

### Build Outputs
- **Frontend**: `frontend/dist/` — `index.html`, `assets/index-*.js` (~1.3 MB), `assets/index-*.css`, `assets/maplibre-gl-worker-*.mjs` (518 kB)
- **Backend**: No build step; runs via `python manage.py runserver`

---

## 10. File Ownership Summary (Multi-Agent)

| Agent | Files | Phase |
|-------|-------|-------|
| `coder-new` | `weather_heatmap.py`, `ForecastSlider.tsx`, `heatmap.ts`, `MapViewport.tsx` (Ph 9) | 1-9 |
| `coder-fix` | `routing.py` (riskSummaries dup), `MapViewport.tsx` (worker + coalesced draw) | 8-9 |
| `tester` | `test_weather_heatmap.py`, `test_routing.py` (+2), `heatmap.test.ts` (47) | 1-9 |
| `docs-writer` | `STATUS.md`, `TEST_LOG.md`, `DECISIONS.md`, `MISSING_INFO.md`, `README.md`, `ARCHITECTURE.md`, `LIMITATIONS.md` | 1-10 |
| `browser-qa` | `phaseX-verify.mjs`, `docs/verification/phase-XX/` | 1-10 |
| `runner` | Test execution, build, tsc | 1-10 |
| `git-agent` | Git operations only | 10 |
| `summarizer` | Final report | 10 |