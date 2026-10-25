# StormRoute — Canonical Project Status

**Last updated:** 2026-10-25 (second session) — **Current phase: 10 — Product Quality Transformation: complete — plus the product-quality UI redesign round per PLAN.md, implemented + browser-verified 2026-10-25 second session (earlier 2026-10-24 "overhaul" entries remain corrected to match reality)**

## Phase tracker

| Phase | Name | Status |
|---|---|---|
| 1 | Project Foundation & API Readiness | **complete** |
| 2 | Trip Input & Validation | **complete** |
| 3 | Three-Route Generation | **complete** |
| 4 | Checkpoint Sampling & ETA Calculation | **complete** |
| 5 | Hourly Weather Integration | **complete** |
| 6 | Deterministic Weather Risk Engine | **complete** |
| 7 | Route Scoring & Recommendation | **complete** |
| 8 | Interactive Map & Route Comparison | **complete** |
| 9 | Weather Heatmap & Forecast Slider | **complete** |
| 10 | Product Quality Transformation | **complete** |

## Last completed phase

**Phase 10 — Product Quality Transformation**: the 2026-10-24 session had only *described* an overhaul in docs without landing it as code (aspirational entries — corrected). The actual implementation, a real MapViewport detached-container bug + fix, a backend warning-copy truth fix, and the full browser re-verification were completed **2026-10-25** with gates backend **200/200** (exit-0 re-run), frontend **80/80**, tsc+build **PASS**, console **0 errors**, prod-preview smoke on **4179**, and screenshots in `docs/verification/product-quality/` (4 files). Details in `docs/TEST_LOG.md` (2026-10-25 entry). The product-quality UI redesign round (root `PLAN.md`) then ran as the second 2026-10-25 session and is CLOSED with all gates green and a 12/12 ALL-CLEAR post-fix spot-check — see the round subsection below and the second 2026-10-25 entry in `docs/TEST_LOG.md`.

## Working features (verified — local foundation only)

### Foundation (Phase 1)
- Frontend: React 19 + TypeScript + Vite + Tailwind v4; `npm run build` + `tsc` PASS; dev server at `http://localhost:5174`
- Backend: Python 3.12 + Django 6.1.2 + DRF 3.18.3; `/api/health/` returns `{status:"ok", service:"stormroute-backend", version:"0.1.0"}` at `http://127.0.0.1:8001`
- No secrets exposed; `.env.example` only placeholders

### Phase 2 additions (all verified — see TEST_LOG/phase-02 evidence)
- `POST /api/trips/validate/` (Django + DRF): validates origin, destination, departureISO (must be ISO-8601 **with timezone offset**, server re-derives UTC), loadWeightLb (finite numeric, >=0, zero valid, no invented maximum), checkpointIntervalMiles in {10, 25, 50} (default 25 when omitted). Validate-only — no persistence, no routing, no weather.
- React trip form (Origin, Destination, datetime-local Departure, Load weight, 10/25/50-mile radio defaulted to 25). Client-side validation mirrors backend rules.

### Phase 3 additions (all verified — see TEST_LOG/phase-03 evidence)
- `POST /api/trips/routes/` (Phase 3 primary endpoint): parses the same trip input (shared serializer; Phase 2 validate endpoint byte-for-byte preserved), geocodes origin + destination via Mapbox Geocoding v5 (200-char, non-empty distinct strings), then asks Directions v5 with `alternatives=true, geometries=geojson, overview=full` for real driving alternatives. Returns `202-style 200` success body with: `routesAvailable: true`, `trip`, resolved `origin`/`destination` (label + [longitude, latitude] **[lng, lat] order**), `routesRequested: 3`, `routeCount`, `threeRoutesReturned` boolean, `duplicatesDropped` count, honest `warning` string when fewer than 3 distinct routes returned, and `routes[]`: neutral `label` (`Route N`), stable `routeId` (`rt_` + SHA-256 of summary — never a provider raw id), `distanceMeters`/`distanceMiles`, `durationSeconds`/`durationReadable`, `providerRouteSummary`, Compute `arrivalISO` (UTC, departure + duration), `geometry` (GeoJSON LineString, full overview). NO safety/best/recommended claim — weather/scoring are later phases.
- **Honest counts:** live Mapbox on Chicago->Denver returns 2 distinct routes; the < 3 case renders an in-app warning: "Mapbox returned 2 distinct routes — Only real provider options are shown — no route is invented. Weather analysis (later phases) will use exactly these 2 routes." *(copy as of Phase 3; updated 2026-10-25 to drop "(later phases)" — see Phase 10 additions)*
- Structured provider-failure taxonomy: `config_missing` 503, `auth_failed` 502 (401/403), `geocode_failed` 422 (**stage attribution** `origin` | `destination`), `no_routes` 422, `provider_timeout` 504, `rate_limited` 429, `provider_response` 502/400-passthrough. Bodies are honest JSON: `{"routesAvailable": false, "error": {"code", "message" [, "stage"]}}`; messages are fixed, no provider text/URL echo (URL carries the token).
- **Token security (hard rules):** `MAPBOX_ACCESS_TOKEN` lives only in gitignored `backend/.env`, loaded via python-dotenv at import; server-side only (never in a `VITE_*` var, never rendered, never logged beyond a coarse endpoint label). Leak audit PASS; token never appears in any response body, log, doc, or screenshot.
- Frontend flow: submit -> "Finding routes" -> route-options panel with per-route cards (distance mi + m, readable duration, UTC arrival, geometry-point count, `providerRouteSummary`), fewer-than-3 warning as `role=alert`, duplicate-drop note, and explicit "no best/safest/recommended choice" honesty note (explicitly stated, no invented ranking).
- No persistence anywhere (SQLite stays absent; Django serverless state may per-phase append more later if user approves).
- Backend test suite: **53/53 OK** (`manage.py test core`) — 27 earlier + 26 new Phase 3 mocked tests (upstream `requests` patched — REAL network never invoked inside the test suite).
- Frontend: **32/32 PASS** (`npm run test`) — 17 TripForm (route flow, error mapping, neutral labels) + 15 validation-lib. `npm run build` + `tsc` PASS (bundle 237.08 kB).
- Live browser verification (real Chrome, script-driven): **8/8 checks PASS** (`frontend/scripts/phase3-verify.mjs`; screenshots + `results.json` in `docs/verification/phase-03/`).
- Live end-to-end probe (requests -> real dev server): `POST /api/trips/routes/` -> HTTP 200, `routeCount=2`, 1,003.1/1,129.3 mi, neutral labels, honest <3 warning, correct `[lng,last]` geometry — `routeCount` and counts match provider only, no invented third route (`backend/scripts/phase3_live_probe.py`).

### Phase 4 additions (all verified — see TEST_LOG/phase-04 evidence)
- **Checkpoint sampling service** (`backend/core/services/checkpoints.py`, pure/deterministic): validates GeoJSON LineString coordinates strictly as `[longitude, latitude]`, rejects non-finite/out-of-range/malformed points and zero-length geometry, measures **traveled** distance with haversine along the real vertices (R = 6 371 008.8 m), interpolates between vertices when a sample target falls mid-segment, and returns ordered checkpoints with stable ids. No weather provider, HTTP, or map code is involved.
- **Checkpoint fields:** `checkpointId` (`cp_` + 12-hex SHA-256 of routeId + sequence + distance + coords), `routeId`, 1-based `sequence`, `coordinates` **[lng, lat]**, `distanceFromStartMeters` / `distanceFromStartMiles`, `elapsedSeconds`, UTC `arrivalISO`, and `interpolated` boolean (true only when the position falls between provider vertices). Origin is sequence 1 at 0 m; destination is always the final checkpoint (no duplicate when it coincides with an interval sample).
- **Interval + cap policy:** interval = the validated trip's `checkpointIntervalMiles` in {10, 25, 50}. Hard cap `CHECKPOINT_MAX_PER_ROUTE` (default **500**, env-configurable); when the requested spacing would exceed it, spacing is **widened** (never truncated), destination retained, and the response discloses `capped` + `effectiveIntervalMiles`.
- **ETA method:** departure (UTC, from the existing contract) + provider `durationSeconds` * (cumulative distance / geometry length). Constant-average-speed approximation by distance — explicitly **not** traffic- or weather-adjusted. Provider distance/duration/geometry are preserved unchanged; `checkpointSummary` reports both `geometryDistanceMeters` and `providerDistanceMeters` so the small simplified-geometry difference is visible rather than hidden.
- **API integration:** `POST /api/trips/routes/` now adds `checkpoints[]` + `checkpointSummary` per route. Phase 2 `/api/trips/validate/` unchanged; all Phase 3 fields unchanged; no DB persistence; new structured safe error `geometry_invalid` (HTTP 502) for unusable provider geometry.
- **Frontend (Phase 4 UI):** route cards show checkpoint count/spacing, a widened-spacing disclosure when capped, sampled span ("0 mi -> X mi — the destination is always the final checkpoint"), and explicit ETA/geometry-distance honesty copy. Header badge reads "Live routes + checkpoints + Phase 4"; the "coming later" list now starts at Phase 5. No ranking, no map, no weather claims.
- **Tests:** backend **91/91 OK** (`manage.py test core`) — 38 new Phase 4 tests (haversine, malformed/duplicate geometry, round-trip, zero-length, short/long/uneven routes, `[lng,lat]`, stable ids, ETA/UTC, caps, invalid settings, endpoint integration, Phase 3 field preservation, token hygiene) + all 53 Phase 1-3 tests still green. Frontend **33/33 PASS** (`npm run test`) — 18 TripForm + 15 validation-lib. `npx tsc --noEmit` exit 0; `npm run build` PASS (238.34 kB JS / 21.29 kB CSS); `npm run lint` = only the 2 pre-existing `ServiceStatusCard` warnings.
- **Live probe:** `backend/scripts/phase4_live_probe.py` -> HTTP 200, **42 checkpoints** (Route 1, 1,001.9 mi geometry vs 1,003.1 mi provider) and **47 checkpoints** (Route 2, 1,128.0 vs 1,129.3 mi) at 25 mi; last checkpoint arrival exactly equals route arrival; monotonic distances/ETAs; destination vertex preserved; identical checkpoint ids across repeated identical requests; no token leak.
- **Browser verification:** **9/9 checks PASS** — script-driven real-Chrome fallback after the Playwright MCP extension again wedged on clicks. Live 25-mi run (counts 42/47, formula-verified), live 50-mi run (22 checkpoints), capped-spacing UI exercised with a **clearly labeled synthetic fixture** (request interception; live provider never hit the cap). Screenshots + `results.json` in `docs/verification/phase-04/`.

### Phase 5 additions (all verified — see TEST_LOG/phase-05 evidence)
- **Open-Meteo weather service** (`backend/core/services/weather.py`, pure/deterministic): fetches hourly `wind_speed_10m`, `rain`, `snowfall` from Open-Meteo Forecast API (no key required, CC BY 4.0 attribution, non-commercial free tier 10k calls/day). Requests `wind_speed_unit=mph`, `precipitation_unit=inch`, `timezone=UTC`, `forecast_days=3`. No HTTP, Django, or map code involved.
- **Weather matching policy:** checkpoint `arrivalISO` (UTC from Phase 4) is truncated to the hour; matched against provider hourly `time` array (also UTC). Exact hour match only — no interpolation, no nearest-hour fallback. If hour not in provider response, marked `out_of_horizon`. Metadata includes `timeMatch` (`exact` | `out_of_horizon` | `provider_error`), `matchedForecastISO`, `providerForecastISO`.
- **Coordinate handling:** checkpoints are `[longitude, latitude]` (GeoJSON order); service correctly converts to `latitude, longitude` for Open-Meteo parameters. Unique coordinate deduplication (rounded to 4dp) avoids duplicate API calls for checkpoints at the same location.
- **Error taxonomy:** `weather_provider` (502, malformed/unexpected response), `weather_timeout` (504), `weather_rate_limited` (429). Safe structured payloads, no provider text/URL echo. On any weather error, routes preserved with `weatherError` field and checkpoints get `timeMatch: "provider_error"`.
- **API integration:** `POST /api/trips/routes/` adds `weather` object to each checkpoint + `weatherSummaries` array at response root. Phase 2/3/4 fields unchanged; no DB persistence; routes always returned even if weather fails.
- **Frontend (Phase 5 UI):** route cards show "Hourly weather at checkpoint arrival times (Open-Meteo)" section with per-checkpoint wind/rain/snow values, `timeMatch` status, provider timestamp. Weather summary shows coverage (X/Y checkpoints with data, Z unavailable, provider forecast window). Attribution "Open-Meteo (CC BY 4.0)" in footer and honesty copy.
- **Tests:** backend **114/114 OK** (`manage.py test core`) — 23 new Phase 5 tests (URL building, matching, validation, enrichment, error handling, endpoint integration, token hygiene) + all 91 Phase 1-4 tests still green. Frontend **33/33 PASS** (`npm run test`) — 18 TripForm + 15 validation-lib. `npx tsc --noEmit` exit 0; `npm run build` PASS (241.21 kB JS / 21.96 kB CSS); `npm run lint` = only the 2 pre-existing `ServiceStatusCard` warnings.
- **Live probe:** `backend/scripts/phase5_live_probe.py` -> HTTP 200, **42 checkpoints all with weather** (Route 1) and **47 checkpoints all with weather** (Route 2) at 25 mi; `timeMatch: "exact"`, wind ~6 mph, rain/snow 0; weather summaries show 42/42 and 47/47 coverage; provider window 2026-10-24 to 2026-10-26; no token leak.
- **Browser verification:** **8/8 checks PASS** — script-driven real-Chrome fallback after Playwright MCP again wedged on clicks. Live 25-mi run (42 checkpoints all with weather), live 50-mi run (22 checkpoints with weather), mobile 420px, no token/persistence/canvas. Screenshots + `results.json` in `docs/verification/phase-05/`.

### Phase 6 additions (all verified — see TEST_LOG backfill & re-run this session)
- **Deterministic risk engine** (`backend/core/services/risk.py`): classification of wind/rain/snow per `docs/DECISIONS.md` band table (wind `<25, 25–<35, 35–<45, 45–<55, >=55` mph; rain `<0.10, 0.10–<0.25, 0.25–<0.50, 0.50–<=1.00, >1.00` in/hr; snow `<0.5, 0.5–<1.0, 1.0–<2.0, 2.0–<=3.0, >3.0` in/hr), combined risk = **max** per checkpoint with No Travel dominant, includes load-based rules for gusts/precip, route-level aggregation of risk-miles per severity level. Pure Python; no HTTP/DB.
- **Pipeline integration:** `generate_routes` calls `analyze_route_risk` per route; response adds `riskSummary` per route + top-level `riskSummaries[]`; unknown weather NEVER renders as safe (unknown is its own risk level in the map legend).
- **Tests:** `manage.py test core.test_risk` → **67 tests, OK** (8 test classes: wind/rain/snow classification boundaries, combined, checkpoint, route aggregation, determinism, config overrides).
- **Evidence:** Risk summaries visually verified live in Phase 7/8 browser sessions (route cards + legend); dedicated screenshots were not captured per-phase at that time — the Phase 8 screenshots set (`docs/verification/phase-08/`) shows the risk-colored UI as shipped. Gaps acknowledged here honestly.

### Phase 7 additions (all verified — see TEST_LOG backfill & re-run this session)
- **Lexicographic ranking** (`backend/core/services/scoring.py`) exactly per spec §7 — priority order:
  1) fewest Severe-risk miles, 2) fewest High-risk miles, 3) lowest average risk (ordinal Low=0 -> No Travel=4), 4) shortest travel time. `rank_and_recommend(routes, riskSummaries)` returns deterministic recommendation (`recommendedRouteId`, `rankedRouteIds`, `routeExplanations`).
- **UI:** route order = ranked order; explanation text names the deciding factor honestly.
- **Evidence:** Recommendation surface verified live in the Phase 8 browser set (`docs/verification/phase-08/`); no separate per-phase screenshots were captured then. Acknowledged honestly.

### Phase 8 additions (all verified — see TEST_LOG backfill & re-run this session)
- **Interactive map** (`frontend/src/components/MapViewport.tsx`): MapLibre GL map (OpenFreeMap tiles, no key), per-route line layers `route-layer-<routeId>` (selectable), checkpoint circle markers colored by risk, selected-route highlight, hover tooltip with checkpoint details, legend with severity colors.
- **Selection sync:** Click a route card / map line -> selection drives both card and map highlight consistently.
- **Browser verification:** Evidence screenshots exist: `docs/verification/phase-08/phase8-map-viewport.png`, `phase8-full-page.png` + two page-state captures.
- **Known Phase 8 probe hole at that time:** MapLibre v6 worker injected through Vite's dev pre-bundling threw worker-load console errors in dev (`Worker failed to load` x2). Guardrail documented — this was the explicit Phase 8 re-verification gate that Phase 9 had to clear at root cause before completion. Cleared in Phase 9 (see next entry): worker is served from its raw module file via `optimizeDeps.exclude` + an explicit `?url` import; dev + production both verified error-free this session.

### Phase 9 additions (all verified — THIS SESSION)
- **Backend service** `backend/core/services/weather_heatmap.py`: gridded corridor forecast samples. Deterministic sampling along the provider LineString (~11 km spacing, <=60 points/route, spacing stretched at the cap — never fewer endpoints), coordinates deduped across routes (4 dp ~ 11 m), multi-location Open-Meteo batches (50 coords per request), 49 hourly buckets (0–48 h inclusive), per-value null-safety (missing hour -> unknown; provider failures drop points — response never fails).
- **API:** `POST /api/trips/routes/` response gains top-level `heatmaps[]` (`routeId`, `gridPoints[]{longitude,latitude,hours[],windMph[],rainInPerHr[],snowfallInPerHr[]}`, `forecastStartISO/EndISO`, `forecastHours: 48`), wrapped try/except — heatmap outage degrades to `[]` and never breaks routes (integration-tested). `riskSummaries` duplicate-key slip fixed.
- **Frontend helpers** `frontend/src/lib/heatmap.ts` (pure): classification mirror of risk bands documented as RENDER mirror (backend authoritative), `hourOffsetToISO`/`isoToHourOffset`, `gridWeatherAtHour`, `nearestGridPoint`, `checkpointWeatherAtHour`, `pickRouteHeatmap`, `buildHeatmapGeoJSON`, `createCoalescedDraw`.
- **UI:** `ForecastSlider.tsx` — real `<input type=range>` 0–48 with tick labels, approximation disclosure ("gridded corridor samples, not road-level certainty"), honest disabled empty state when no heatmap data. `MapViewport.tsx` — `corridor-heatmap` circle layer under route lines; markers recolor + retitles per selected hour; hover tooltip gains "At +N h ..." snapshot block; legend footnote. `App.tsx` — slider state bounded 0–48, reset to 0 per new trip.
- **Markdown cleanup:** 16 one-off `fix_*.js` / `check_*.js` scratch scripts removed from the repo root (user-approved cleanup); root reduced to README/AGENTS/.env.example/.gitignore.

### Root-cause queue work (Phase 8 gap closed BEFORE Phase 9 completion)
- MapLibre Worker: set `setWorkerUrl(new URL via import 'maplibre-gl/dist/maplibre-gl-worker.mjs?url')` once at module top; dev `optimizeDeps.exclude: ['maplibre-gl']` so the pre-bundling no longer rewrites the worker URL.
- Result: 0 console errors in dev AND production serving; the worker chunk is a real emitted asset.

### Automated tests (exact results)
- Backend `manage.py test` → **200 tests, OK** (27 phase 1-3 `core/tests.py` + 38 checkpoints + 23 weather + 67 risk + 28 routing [26 prior + 2 new heatmap-response integration tests] + 17 `test_weather_heatmap.py`).
- Frontend `npx vitest run` → **3 files, 80 tests, PASS** (TripForm 18, validation 15, heatmap 47 — 42 slider/heat helpers + 5 `createCoalescedDraw` scheduling tests incl. hidden-tab fallback).
- `npx tsc --noEmit` exit 0; `npm run build` PASS → `dist/assets/maplibre-gl-worker-BrB25tGK.mjs` emitted (518.80 kB) + `index-b7gZw23V.js` 1,325.59 kB (existing bundle-size warning only).

### Live browser verification (real Chrome via Playwright MCP; tab foregrounded once for style load)
- Fresh trip (Chicago -> Denver, 2026-10-24T18:30, 34,000 lb, 25 mi): route count 2, **89 checkpoint markers** (42+47), correlation of layers `corridor-heatmap` + `route-layer-*` x2 confirmed via `map.getStyle()` in dev handle `window.__stormrouteMap` (dev-only inspection handle).
- Heatmap source holds **60 real Open-Meteo grid points**; calm forecast, all levels `low` (max wind 13 mph at +48 h baseline later run; +0 h start wind 3.1 mph) — **REAL provider data, not fabricated severity**.
- **Slider semantics:** reset to 0 h -> heatmap `forecastISO 2026-10-24T00:00`, label "Now (start of forecast) · Oct 24, 2026 · 00:00 UTC", marker titles match.
- **Rapid-burst drag (the Phase 9 hard gate):** burst `[5, 12, 19, 26, 31, 33, 40]` with zero waits -> final state = LAST value everywhere: label `+40 h · Oct 25, 2026 · 16:00 UTC`, heatmap `forecastISO 2026-10-25T16:00`, marker titles `forecast 2026-10-25T16:00`. **Consistent across all three surfaces.** Baseline (0 h) landed first; no stale trailing values.
- **Hidden-tab fallback proven live:** during the burst the tab was again `document.hidden === true` (window occluded) — the draw still landed <=1 s later via the 16 ms setTimeout fallback (Chrome pauses rAF entirely in occluded tabs; earlier single rAF-only implementation left the map stale — root cause found and fixed this session).
- Hover tooltip snapshot: `At +40 h · 2026-10-25T16:00 UTC · Low · Wind: 5.1 mph` (real per-checkpoint value, matched hour).
- Console: **0 errors / 0 warnings** throughout (worker + style + tiles all 200).

### Production preview verification (vite preview @4175, same dist bundle)
- Worker chunk served and loaded: `GET /assets/maplibre-gl-worker-BrB25tGK.mjs -> 200`; main bundle `index-b7gZw23V.js` served; `/api/trips/routes/` -> 200 **through the new `preview.proxy`** (`vite preview` does not inherit `server.proxy`; without it `/api/*` 502s — config gap fixed this session, honestly disclosed).
- Single-step slider +24 h: label `+24 h · Oct 25, 2026 · 00:00 UTC` + marker titles `2026-10-25T00:00` — consistent.
- Rapid burst `[5..40]`: label + markers land on LAST value `+40 h · 2026-10-25T16:00`. ✅
- Console: **0 errors / 0 warnings** in production serving.
- `vite preview` server stopped after verification (port released); dev servers left running.

### Screenshots + evidence (`docs/verification/phase-09/`)
- `phase09_slider24h_viewport.png`, `phase09_slider48h_viewport.png`, `phase09_slider48h_fullpage.png` (earlier in-phase state captures).
- `phase09_burst40h_labelMatch_viewport.png`, `phase09_burst40h_fullpage.png` (burst-landed state, label + heatmap + markers all at `2026-10-25T16:00`).
- `phase09_hover_hour_snapshot.png` (hover tooltip hour snapshot block).
- `phase09_prod_4175_slider40h_viewport.png` (production preview bundle, slider +40 h consistent).

### Honest limitations
- Gridded circles are ~11 km corridor samples — an explicitly disclosed approximation, not road certainty; values between grid points are approximations (UI copy + backend docstring say so).
- The live corridor forecast was calm, so every visible severity on the map is `low` — REAL data. Severe/No Travel rendering across slider hours is proven by unit tests + the earlier synthetic matrix, and by classification tests on both sides; it is not asserted from a live severe event.
- Heatmap generation failure path: covered by deterministic tests + integration test — no live provider outage was injected against production (not fabricable honestly).

### End state
- Backend 200/200, frontend 80/80, tsc 0, build PASS (worker asset emitted), preview 4175 verified then closed; dev servers left running: backend 8001, frontend 5174.
- All Phase 9 acceptance criteria executed and passing; Phase 8 re-verification gate completed.
- Next: Phase 10 only on explicit instruction. (Updated 2026-10-25 later: local history now exists on master — commits `7e914ea` code + `ae00ac8` docs/evidence; still not pushed, awaiting explicit instruction.)

### Phase 10 additions (implemented + verified — 2026-10-25 session; real)

- **Single-page dark UI** rebuilt to the unchanged 80-test contract: `TripForm` (form card, `role="alert"` field errors, radio chips, single submit with pending state), `RouteOptions` (`Live route options` region + `<ol aria-label="route options">` + `<article><h3>Route N</h3></article>`, Rank/#N/Recommended chips), `MapViewport`, `ForecastSlider` (`+N h from forecast start` chip, testids), `App` (form left / map right; route pills with `aria-pressed`), `main.tsx` forced dark, token fixes in `index.css`, `ui/*` primitives on relative imports (`tailwind.config.ts` deleted; Accordion/Tooltip/Container removed in favor of native `<details>`/absolute panels).
- **Real bug found + fixed:** `MapViewport` swapped its `containerRef` div when `mapLoaded` flipped — MapLibre kept rendering into a detached node (canvas invisible despite `loaded()===true`). Fix: one stable container + loading overlay. Verified by fresh-mount assertions: `getContainer() === [data-testid="map-viewport"]`, canvas in viewport, 89 markers, `corridor-heatmap` source, 2 route-line sources.
- **Backend warning copy truth-up:** stale "(later phases)" removed from `_fewer_than_three_warning()` (no test locked it); backend 200/200 re-run EXITCODE=0; server restarted `--noreload` to load it (two stale runserver processes on 8001 found and closed by known PID); live wire response + browser render both show the new copy.
- **Gates (exact):** backend **200/200 OK exit 0**; frontend **80/80 PASS** (`npm run test`, 3 files); `npm run build` **PASS** twice (post-fix: `index-bDv-Lx7T.js` 1,315.14 kB); lint warnings-only (exit 0); console **0 errors / 0 warnings**.
- **Browser evidence:** fresh trips (Chicago → Denver, 34,000 lb, 25 mi): pending state (button disabled + `aria-busy=true`), 2 real routes with honest <3 warning, 89 markers, hour-burst labels monotonic, markers retitle exactly `forecast <start+offset>` at +24 h. Screenshots: `docs/verification/product-quality/product-quality-0{1,2,3,4}*.png`.
- **Prod preview smoke on 4179** (4175 occupied by an unrelated PID 5080 — untouched): build-served page 200 + `/api/health/` through preview proxy → `ok/0.1.0`; dark theme + form + hero verified in the real browser on the prod bundle.

### Product-quality UI redesign round (2026-10-25, second session — per PLAN.md; frontend-only)

- **Design system shipped:** cool-steel ops console — tokens in `index.css` (bg `#0B0E14`, panel `#141922`, raised `#1B212B`, border `#262D38`/strong `#3D4654`, text `#E7ECF3`/`#9AA6B5`/`#5A6472`), accent `#5C9DFF`, amber signal `#FFB224`; Barlow 400/500/600 + JetBrains Mono 400/500 via `@fontsource` imports placed above the Tailwind import; radius 6/10; 1px borders; no shadows/glass/emoji/teal.
- **Layout:** Option A results band via CSS-only breakout — `TripForm` root display-contents + `.results-band { grid-column: 1 / -1 }` (RouteOptions stays inside TripForm's React tree; the 18 test renders were never touched); grid contract `lg:grid-cols-[minmax(380px,5fr)_minmax(0,7fr)]`, merged pill row, hazard-stripe logo tile, top-right map legend.
- **Risk colors:** single source `frontend/src/lib/riskColors.ts` re-exporting the test-pinned hexes from `lib/heatmap.ts` (low `#22c55e`, moderate `#f59e0b`, high `#f97316`, severe `#ef4444`, no_travel `#dc2626`, unknown `#64748b`); `heatmap.ts` itself untouched; legend dots, badges and `.risk-dot-*` CSS consume it.
- **Basemap:** Carto dark-matter style with a demotiles catch-fallback + styleRev redraw so route layers + heatmap redraw after the fallback.
- **Dead code removed:** `frontend/src/components/ui/` (7 files, 0 imports), `lib/utils.ts` (0 importers); `clsx` / `tailwind-merge` / `lucide-react` uninstalled.
- **Copy:** route-card reason line = the API's first sentence; ONE "Estimate methods" details block with the fixed haversine sentence (corrupted "haverine along" eradicated); single slider caption; legend rows Low/Moderate/High/Severe/No Travel/Unknown; checkpoint no-data chips "No data"; null slots "n/a"; `ServiceStatusCard` single-word labels "Checking…" / "Online" / "Unhealthy" / "Offline"; footer keeps "· Routing: Mapbox".
- **Gates (before AND after every fix):** `npm run test` **80/80** (3 files) · `npm run build` **exit 0** (worker asset + Barlow/JetBrains Mono fonts emitted) · `npm run lint` **exit 0** (0 errors / 5 historic warnings).
- **Browser QA round 1:** **11/11 PASS** on 5175 — fonts true, results band full-width (left 24 / width 1222), 89 checkpoint markers, dark-matter tiles 200, +24 h flips all 89 marker titles to `2026-10-26T00:00`, console 0 errors, no ≥400 requests. Reviews fired the fix-loop: reviewer-quality **14 findings** (incl. 1 CRITICAL class mismatch) + reviewer-standards consistency audit.
- **Fix-loop round 1:** all 10 findings applied (`.risk-no_travel` alias + `.risk-dot-*` fills; `.badge`/`.risk-badge` one shape rule; duplicate input echo deleted; marker border `#3D4654` + heatmap stroke `#0B0E14`; `lib/utils.ts` deletion + dep uninstall; interval-radio `has-[input:focus-visible]` focus styling; mobile stacking order; styleRev redraw; single-word status labels; "Unknown"/"No data"/"n/a"/one caption) — gates re-run green afterward.
- **Post-fix spot-check:** **12/12 PASS, ALL-CLEAR** on 5175 — computed legend dot colors exactly the six pinned hexes; exactly one input echo (`Chicago, IL → Denver, CO · dep Oct 26 08:30 · 34,000 lb · 25 mi checkpoints`); ~70 s run flow; markers 89/89 with verified paint properties; keyboard focus accent `rgb(92,157,255)`; mobile 480×800 order form 247 < map 844 < band 1523 with all 89 markers surviving; console 0 warnings on second pass (one transient `net::ERR_EMPTY_RESPONSE` on the session's first routes POST, retried 200 OK in 69.5 s — environment transient, not an app bug).
- **Evidence:** `docs/verification/product-quality/` — screenshots `product-quality-05..10` plus stale-port artifacts (`qa-stale-5173-regression-shot.png`, `qa-console-session.log`); the frozen contract (tests, `lib/validation.ts`, `lib/heatmap.ts`, `main.tsx`) untouched the whole round; full log in `docs/TEST_LOG.md` (second 2026-10-25 entry); decisions in `docs/DECISIONS.md` (2026-10-25 second session).

## Unresolved external API prerequisites

- **Routing/geocoding: live-verified 2026-10-24** — `MAPBOX_ACCESS_TOKEN` configured in gitignored `backend/.env` (backend-only via python-dotenv); Directions returns 1-3 routes corridor-dependent; honest <3 warning verified in-app live. Evidence: `backend/scripts/mapbox_smoke.py`, `docs/TEST_LOG.md`.
- **Live weather integration: VERIFIED 2026-10-24** — Open-Meteo Forecast API successfully returns hourly wind/rain/snow for checkpoint ETAs. Non-commercial free tier (10k calls/day, CC BY 4.0) sufficient for assessment. No key required.
- Weather-provider final selection is **CONFIRMED** (Open-Meteo primary — non-commercial-only free tier; WeatherAPI.com fallback has no separate hourly rain-rate field; see `docs/API_PROVIDER_RESEARCH.md`).

## Incomplete / unverified features

- **Remain from the 12 requirements:** hosted deployment, GitHub remote/push, and the Loom walkthrough (deliverable items of Phase 10) — not started; awaiting explicit instruction.
- **UX Phase-B items from `docs/PRODUCT_UX_AUDIT.md` still open (documented, intentionally deferred):** type-as-you-go inline validation, checkpoint clustering on the map, consolidated "risk ≥ Moderate" waypoint summary, React error boundary/retry button.
- Everything else (Phases 1–10 code paths) is implemented and verified as recorded above.

## Known bugs and blockers

- **Playwright MCP extension wedges on synthesized clicks** across sessions (navigation + snapshot + fill work; clicks time out — as recorded Phase 2–5). This session's verification avoided synthesized clicks entirely by using evaluate-based native-value fills + `requestSubmit`; same real browser, real screenshots.
- **Fixed 2026-10-25 — MapView detached container:** `MapViewport` re-rendered its container after `mapLoaded`, detaching the live MapLibre DOM (canvas invisible, markers 0). Root-caused and fixed with a stable container + loading overlay; regression risk watched via the dev-handle assertions in `docs/TEST_LOG.md` (2026-10-25).
- **Port topology (as of 2026-10-25, second session):** the team's fresh Vite dev server — the only one serving the REDESIGNED frontend — runs on **5175** (PID 21876, `API_PROXY_TARGET=http://localhost:8001`). Stale **5173/5174** were found still serving the OLD pre-redesign bundle (started 2026-10-24): captured as regression evidence, left running, NOT killed, and IGNORED — future sessions must not use them for UI verification without first re-verifying the served `index.css`. Backend on **8001**; 4175 is still held by an unrelated process (PID 5080, untouched — the 2026-10-25 first-session prod smoke used 4179). No processes were killed this round.
- Console-encoding artifact (mojibake of em-dash / special chars) sometimes appears in tool output capture; wire bytes and app behavior verified correct (byte-level E2 80 94 check passed; no code change required).

## API / provider status

- Routing/geocoding: Mapbox Directions + Geocoding selected. `MAPBOX_ACCESS_TOKEN` **SET** (gitignored backend/.env; server-side only). Open-Meteo weather: no key needed for **non-commercial use only** (CC BY 4.0 attribution; NOT unrestricted for commercial use). Map tiles: MapLibre demo style in the shipped UI (per-component), OpenFreeMap tiles documented in earlier phases.
- Real keys status: see `docs/MISSING_INFO.md` (tracked set/unset only).

## Development URLs

- Backend (Django, `--noreload`): `http://127.0.0.1:8001` — health `/api/health/`, validation `POST /api/trips/validate/`, routes `POST /api/trips/routes/` (restarted 2026-10-25 to load the warning-copy change)
- Frontend (Vite dev, REDESIGNED bundle, `API_PROXY_TARGET=http://localhost:8001`): `http://localhost:5175` — proxies `/api/*` → backend 8001. Stale 5173/5174 still serve the OLD pre-redesign bundle (2026-10-24) — left running, IGNORED for verification.
- Production preview (2026-10-25 first-session smoke): `http://localhost:4179` (`vite preview` with preview.proxy → 8001)
- Historical note: during Phases 1–9 our stack ran on 5174 while a stale sibling session held 5173/8000; that session ended (8000 free) and a team session served 5173 through the first 2026-10-25 session — superseded on 2026-10-25 (second session) by the fresh redesign server on **5175**, with old-bundle 5173/5174 left running but ignored.

## Next authorized step

Deployment & submission work (GitHub remote/push, hosted URL, Loom) — only on explicit user instruction. UI product-quality items verified 2026-10-25; as of this update the repo has two local commits on master (`7e914ea` code, `ae00ac8` docs/evidence) and has not been pushed.