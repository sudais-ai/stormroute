# StormRoute — Technical Decision Log

Append-only in spirit; each entry dated. Status: **[confirmed]** (verified by execution) or **[pending]** (chosen, awaiting verification).

---

## 2026-10-23 — Project identity & constraints **[confirmed]**

StormRoute is the Spotter AI assessment "Weather-Aware Truck Routing": 3 routes, checkpoint weather risk, fixed priority ranking, interactive map + 0–48h heatmap slider. Budget ≤16 h / ≤4 days. Authoritative spec: `docs/ASSESSMENT_SPEC.md`.

## 2026-10-23 — Stack: React+TS+Vite+Tailwind / Django+DRF / MapLibre GL **[confirmed for scaffold]**

Reason: mandated direction. MapLibre GL chosen over Mapbox GL: open-source, no account/key required for tiles (used with a tile provider), sufficient for route lines + markers + heatmap; avoids key dependency for the map layer itself. Tilesource decision to be finalized in Phase 8 with data source recorded in `API_PROVIDER_RESEARCH.md`. Status: scaffolding verified; actual map rendering pending Phase 8.

## 2026-10-23 — Boundary conventions for weather classes **[confirmed — mandated by assessment]**

Wind: `<25, 25–<35, 35–<45, 45–<55, ≥55`. Rain: `<0.10, 0.10–<0.25, 0.25–<0.50, 0.50–≤1.00, >1.00`. Snow: `<0.5, 0.5–<1.0, 1.0–<2.0, 2.0–≤3.0, >3.0` (units: wind mph; rain/snow in/hr). Implemented verbatim in the risk engine (Phase 6), tested at every boundary value.

## 2026-10-23 — Overall checkpoint risk = max(class per condition) with No Travel highest **[pending verification in Phase 6]**

Reason: spec says "consistent overall risk; No Travel takes precedence". Max-of-classes with No Travel > Severe > High > Moderate > Low is the natural consistent reading. Alternatives considered: weighted average (rejected — could mask a No Travel) / sum of indices (rejected — not "consistent" and could overstate). Load rules applied to the wind condition before max is taken.

## 2026-10-23 — Risk severity ordinal for ranking average risk **[pending Phase 7]**

Average risk computed as mean ordinal index over checkpoint risks: Low=0, Moderate=1, High=2, Severe=3, No Travel=4. Reason: keeps No Travel-dominant routes from winning average despite tie-breaks; simple, deterministic. Will be validated in Phase 7 tests; if the "No safe route found" path triggers first, ranking with NoTravel routes must not present them as safe regardless.

## 2026-10-23 — ETA model: duration-weighted interpolation **[pending Phase 4]**

Checkpoint ETA = departure + (cumulative distance fraction × route total duration). Rationale: simple, no traffic modeling available; documented approximation. Alternatives (per-leg durations where provider offers them) acceptable if provider returns segment durations; decision to finalize in Phase 4 after inspecting live route payloads.

## 2026-10-23 — Environment/tooling **[confirmed]**

Windows × PowerShell 5.1; Node v26.7.0; npm 12.2.0; Python 3.12.10; pip 25.0.1; git 2.55.0. Frontend dev on Vite default port 5173; backend on Django 8000. Playwright MCP (via browser extension) verified: navigation, snapshot, screenshot, console inspection all working; console artifacts land in `.playwright-mcp/` and screenshots can be saved into `docs/verification/…`. No git repo existed → initialized fresh on 2026-10-23 (empty except `.playwright-mcp/` artifacts preserved).

## 2026-10-23 — Provider candidates under evaluation **[pending research verification]**

- Routing/geocoding: candidates = Mapbox Directions (alternatives supported), TomTom, Google Directions, OSRM/OpenRouteService. See `API_PROVIDER_RESEARCH.md` for evaluated facts and the chosen provider.
- Weather: candidates = Open-Meteo (hourly wind_speed / precipitation / snowfall, no key, 48h+ horizon), Met Office DataPoint, Tomorrow.io, OpenWeatherMap. Rain/snow **rate** semantics (in/hr actual rate vs probability vs hourly total) must be confirmed before Phase 5.

## 2026-10-23 — Repo/deployment policy **[confirmed]**

Local git initialized 2026-10-23 (fresh repo, preserved `.playwright-mcp/` artifacts). Commit only when instructed. GitHub remote + deployment provider to be decided in Phase 10 after feasibility, per brief.

## 2026-10-24 — Weather provider selection re-confirmed as PENDING (audit) **[pending verification in Phase 5]**

- **Open-Meteo** remains primary: only candidate with genuinely **separate** hourly `rain` and `snowfall` fields (its docs: preceding-hour amounts; treat per-hour accumulation as the hourly rate — documented, verified before Phase 5).
- Its free tier is **non-commercial only** (10k calls/day, CC BY 4.0 attribution) — corrected record; not a commercial-use license. Assessment demo use = non-commercial. If the app ever serves real commercial operation, terms must be revisited or provider changed.
- **WeatherAPI.com** evaluated from official docs as fallback: has hourly `wind_mph` + `snow_cm`, but **no separate hourly rain rate** (`precip_mm/precip_in` is combined total precipitation; `chance_of_rain` is probability) and free plan covers only a 3-day forecast with no commercial use. Fails the "must not treat total precipitation as the rainfall rate" requirement without an unverified derivation → weaker fit.
- Resolution action before Phase 5: execute one **live** Open-Meteo forecast fetch (real coordinates, real response), inspect `rain`/`snowfall` hourly series semantics and magnitudes, and only then lock the selection. If that live check fails contract expectations, re-open with WeatherAPI.com + live test.
- Rule regardless of provider: probability/total-precip fields are never silently used as the hourly rainfall or snowfall rate.

## 2026-10-24 — Phase 2 validation endpoint lives in `core` app: `POST /api/trips/validate/` **[confirmed]**

Reason: trips input validation is an input-boundary concern, not routing-domain logic; keeping it in `core` avoids a premature `trips`-domain app. When route generation arrives (Phase 3), routing gets its own app while the trip validator remains the canonical entry validator (single validation system — no duplicates). Payload uses camelCase JSON keys (origin, destination, departureISO, loadWeightLb, checkpointIntervalMiles) matching the TypeScript frontend types; the serializer is the single source of backend validation truth; route/weather work explicitly excluded (validate-only this phase).

## 2026-10-24 — Phase 2 design decisions **[confirmed — verified in Phase 2]**

- **Dual validation with mirrored rules:** client-side pure validator (`frontend/src/lib/validation.ts`) mirrors the DRF serializer so obvious mistakes never leave the browser; the backend remains the single authoritative boundary and its errors render verbatim. Reasons: instant feedback + no server round-trip waste; tested on both sides (27 backend + 27 frontend checks).
- **Departure representation:** client converts the browser-local `datetime-local` input to an ISO-8601 timestamp WITH its local UTC offset; the server re-parses, rejects naive timestamps, re-checks future-dated, and normalizes to UTC (`+00:00`). Reasons: preserves the user's intended wall-clock, keeps server logic deterministic; verified both sides (e.g. `2099-01-01T08:00:00-08:00` → `2099-01-01T16:00:00+00:00`).
- **Interval input:** radio group exactly {10, 25, 50} with default 25 — an unsupported interval is unreachable through the UI (verified in browser); the serializer still rejects any other value for direct-API clients. Spec-based.
- **UX defaults (documented, not domain data):** departure defaults to now + 2 hours (rounded to 5 min); load weight defaults to 34,000 lb. These are form conveniences only — no routing/truck assumptions claimed; zero weight remains explicitly valid and explained in the UI hint.
- **Frontend test tooling:** vitest 5 + jsdom + Testing Library (minimal appropriate set — no Jest/flaky E2E framework added). Real-browser phase verification runs via `frontend/scripts/phase2-verify.mjs` after the connected Playwright MCP session wedged (substitution documented in `TEST_LOG.md`, not hidden).

## 2026-10-24 — Mapbox token loading architecture **[confirmed — live-verified same day]**

- **Token loading:** `python-dotenv` in `backend/stormroute/__init__.py` loads gitignored `backend/.env` on every Django entrypoint (manage.py/shell/tests/WSGI); settings expose `MAPBOX_ACCESS_TOKEN` for server-side use only. Reasons: single loading point, no per-script plumbing, works in deployment with real env vars when `.env` is absent.
- **Token storage/scoping:** `backend/.env` in backend dir (never committed, frontend has no `VITE_` equivalent). Token is pk-scoped by its own design, but the app treats it as a backend secret — routing/geocoding calls happen only in Django code.
- **Outbound HTTP client:** `requests==2.34.2` as the runtime dependency for provider calls (Mapbox now, Open-Meteo later); recorded in newly created `backend/requirements.txt` (was missing).
- **Live confirmation results (honest):** Geocoding 200×2, Directions `alternatives=true` on Chicago→Denver returned **2 routes** — NOT a fixed three. Phase 3 design must render whatever real alternatives come back (1/2/3), never fabricate a third route.

## 2026-10-24 — Docs tooling rule (from a real encoding incident) **[confirmed]**

An editing session re-encoded `docs/DECISIONS.md` through Windows PowerShell 5.1 (ANSI re-read of UTF-8 without BOM) and corrupted em-dashes/en-dashes/≥ symbols. Lesson encoded: never round-trip project docs through PowerShell `Get-Content`/`Set-Content` for editing; use the file tools (read/write/edit) that preserve UTF-8. Revert path if repeated: reconstruct from Git history once commits exist.

## 2026-10-24 — Phase 3 route-generation architecture **[confirmed — backend 53/53, frontend 32/32, live 200]**

- **Endpoint shape:** `POST /api/trips/routes/` returns the full generation result in one response (no follow-up detail call). Reasons: the trip input is already validated by the shared serializer, route generation is a single read-only computation, and the fewer-than-3 warning + duplicates count must be judged together on one screen; no persistence contract with the client this phase.
- **Route options as first-class list (1–3 honest options):** live Mapbox `alternatives=true` yields corridor-dependent counts (verified: 2 on Chicago→Denver). The response reports `routeCount`, `threeRoutesReturned`, `duplicatesDropped`, and a human-readable `warning` string when fewer than three were returned. NO fabricated third route, NO padding with synthetic options. Reasons: accuracy over appearance — the UI must represent provider reality.
- **`routeId` stability:** `rt_` + 12-hex SHA-256 of the route's own fingerprint (distance + duration + summary + endpoint coords) rather than the provider's raw id or array index — survives re-requests of the same corridor and is safe thematically when Phase 7 needs deterministic route-keyed scoring later. Names of internal fingerprint parts are stable-by-construction (unit tests pin the conversion + fingerprint helpers).
- **`Route 1 / Route 2 …` label semantics:** order = provider response order (Geocoding/Directions output), which is not "best ranked". No safest/best/recommended language this phase by design; ranking arrives at Phase 7. UI copy explicitly says no ranking happened (honesty rule, verified in tests).
- **[lng, lat] order preserved from GeoJSON upstream** (Mapbox geometries are [longitude, latitude]); the React map later consumes the same ordering. Unit-tested.
- **Duplicate detection:** exact fingerprint equality only (summary + distance + duration + endpoints). No fuzzy near-same merging — близко-but-different routes remain distinct. Reasons: correctness over dedupe cleverness at this stage; duplicatesDropped surfaced in the UI if > 0.
- **Failure taxonomy (fixed honest messages, no provider text echo):** Mapbox returns status + syllable codes; mapped into `config_missing` (503, unset token), `auth_failed` (502), `geocode_failed` + stage (422), `no_routes` (422), `provider_response` (502), `provider_timeout` (504), `rate_limited` (429). Reasons: the frontend (and future API consumers) must distinguish "our config broke" vs "provider quota" vs "that string has no location"; provider HTTP bodies sometimes carry the request URL containing the token — echoing raw provider text would leak it, so messages are authored constants.
- **Shared `_TripRequestMixin.parse_or_error()`:** Phase 2 validate + Phase 3 routes endpoints parse identical payload through the same DRF serializer; `/api/trips/validate/` byte-level contract unchanged (27/27 pre-phase tests still green). Reasons: single validation truth per the Phase 2 decision; no validation drift between endpoints.
- **Departure normalization:** request `departureISO` is accepted WITH explicit offset (same rule as Phase 2), converted once to UTC at parse; per-route `arrivalISO` = departureUTC + `durationSeconds` formatted ISO-8601 `+00:00`. Duration is provider-driving-time only — no break/rest modeling (out of spec scope this phase).
- **Geometry:** full `overview=full` GeoJSON pipeline passed through unchanged ([lng, lat]); per-route `geometry.coordinates` length reported as `geometry-points` count in the UI informational line; Phase 4 checkpoint sampling will decimate over it. No geometry simplification this phase to keep Phase 4 input exact.
- **Given-token boundaries test-proofed:** `test_routing.py` pins no-token-in-response-body + provider-text-not-echoed; upstream `requests.get` is unit-mocked — the suite NEVER performs live network calls (the live token is never loaded into the test runner environment path).
- **Frontend flow decision:** the form now submits to the Phase 3 routes endpoint directly (skip the intermediate validate-only hop); `/api/trips/validate/` remains for direct-API consumers and future phases. Client-side validation still runs first (mirrored rules), so most malformed inputs never leave the browser. Reasons: one obvious click → real visible routes; validate-only endpoint kept intact for Phase 4+ UI if authored this way.
- **Route card data honesty:** cards show distance (mi + m), readable duration, UTC arrival, geometry-point count, `via …` summary, stable routeId, with the fewer-than-3 warning when applicable. No mock artifacts, no invented names, no ranking, no weather mention beyond an honest "later phases" note.

## 2026-10-24 — Playwright MCP wedge recurrence + harness substitution **[confirmed]**

The MCP extension again accepted navigation/snapshot/screenshot but synthesized CLICKS timed out (2 attempts × >5 s waits, element resolved but click action never completed) — same signature as Phase 2. Substitution policy per instruction: script-driven real Chrome (`frontend/scripts/phase3-verify.mjs`, playwright-core `channel:"chrome"`, headless, CDP). Method disclosed in `TEST_LOG.md` and screenshots' `results.json`. No fabricated browser evidence (the two earlier failed harness runs are documented in this file's `failure-dump.txt` history; final run: 8/8 PASS).

## 2026-10-24 — Live-geocoding fuzzy-match reality (check conditioning) **[confirmed]**

Deliberately nonsense strings ("Xyznomatch City 99999999" etc.) STILL geocode to real places (Shelf Road, Cañon City CO). Decision: the browser check for `geocode_failed` is marked CONDITIONAL rather than fabricated — the failure path itself is verified at unit level with mocked empty geocode responses. If Phase 4+ needs live-triggerable branch states, use clearly protocol-level failures (e.g. temporarily misconfigured token in a sandbox run), not fuzzy-matching tricks.

## 2026-10-24 — Phase 4 checkpoint sampling, cap policy & ETA method **[confirmed — backend 91/91, frontend 33/33, live probe, browser 9/9]**

Supersedes the provisional 2026-10-23 "ETA model" entry; the chosen method matches its distance-weighted intent.

- **Sampling interval:** comes from the validated trip field `checkpointIntervalMiles` ∈ {10, 25, 50} (the Phase 2 user choice). No new assessment requirement was invented; this reuses the existing contract. Sampling is by **traveled distance** along the provider LineString, never by vertex index and never by origin→destination straight-line distance.
- **Distance metric:** haversine with mean Earth radius `6_371_008.8 m` (IUGG), applied segment-by-segment in `[longitude, latitude]` order. Cumulative distances are computed once per route (O(vertices)), keeping sampling bounded.
- **Cap / widening policy:** `CHECKPOINT_MAX_PER_ROUTE` (default **500**, env-configurable, minimum 2) is a hard ceiling per route. If requested spacing would exceed it, the effective spacing is **widened** via `ceil(total / (cap − 2))` — never truncation, so the destination survives and no route silently loses its end. Responses disclose `capped`, `requestedIntervalMiles`, `effectiveIntervalMiles`, `maxPerRoute`. Invalid setting values fall back to 500 (settings parsing) or are rejected by the service (invalid explicit argument).
- **Origin/destination semantics:** checkpoint 1 is always the origin at 0 m; full-interval samples follow; the destination is appended as a final partial segment only when it does not coincide with the last interval sample (> 0.5 m). This yields no duplicate checkpoints and a monotonic cumulative distance. Route length below one interval therefore returns exactly two checkpoints (origin + destination).
- **Interpolation & vertex honesty:** targets falling between provider vertices are linearly interpolated in coordinate space within the containing segment; each checkpoint carries `interpolated` (`false` for actual provider vertices, including origin/destination). Duplicate consecutive vertices contribute zero length and are handled safely (no division by zero). Coordinates are rounded to 6 decimal places for response stability.
- **Stable IDs:** `cp_` + first 12 hex chars of SHA-256(`routeId|sequence|distanceFromStartMeters|longitude|latitude`) = 15 chars. Timestamps are deliberately excluded, so the same trip/route/interval yields identical ids across identical requests (live probe confirms); different route ids always differ. `routeId` is embedded on every checkpoint for standalone consumption.
- **ETA:** `departureUTC + providerDurationSeconds × (cumulativeDistance ÷ geometryLength)`. This spreads the provider's real driving duration by distance (constant average speed). It deliberately does **not** model traffic, stops, weather, or per-leg provider durations (Mapbox overview response gives route-level duration only). Explicit limitations are surfaced in API method labels and UI copy; no traffic- or weather-awareness is claimed.
- **Provider values preserved:** sampling never mutates `distanceMeters`, `durationSeconds`, `arrivalISO`, or `geometry`. Because the overview geometry is simplified, its haversine length differs slightly from the provider's reported distance (live: 1,001.9 vs 1,003.1 mi; 1,128.0 vs 1,129.3 mi). Both are returned (`geometryDistanceMeters` vs `providerDistanceMeters`) and the UI discloses the difference; neither is rewritten.
- **Error handling:** mathematically unusable provider geometry (malformed points, out-of-range/non-finite coordinates, fewer than 2 points, zero length) raises `CheckpointSamplingError` locally and becomes the safe structured API error `geometry_invalid` with HTTP 502. Raw provider text and geometry details never reach clients or logs. Missing/invalid duration/distance, invalid interval, and naive departure timestamps are rejected the same way. No timestamps are invented.
- **Integration boundary:** checkpoint logic lives in a pure service (`core/services/checkpoints.py`) called once per normalized route inside the existing `generate_routes` pipeline. No new endpoint, no DB writes, no new dependency, no Mapbox call added. Phase 2 validate behavior and Phase 3 route fields remain unchanged (regression-tested).
- **Cap UI evidence honesty:** the real provider never hit the 500 cap this session (max 47 checkpoints live). The capped-spacing UI branch is therefore exercised through a **clearly labeled synthetic fixture** via request interception in the browser harness; the backend capped path is covered by deterministic tests with `CHECKPOINT_MAX_PER_ROUTE=12`. The distinction is recorded in `results.json` and `TEST_LOG.md`, never presented as live provider data.
- **Verification method:** Playwright MCP again accepted navigation/snapshot/fill but wedged on clicks (its own extension executor threw `M_ID`; page unaffected), so the sanctioned script-driven real-Chrome fallback was used (`frontend/scripts/phase4-verify.mjs`). Not claimed as MCP click verification.

## 2026-10-24 — Phase 5 weather provider integration **[confirmed — backend 114/114, frontend 33/33, live probe, browser 8/8]**

Supersedes the provisional 2026-10-23 "Weather provider selection re-confirmed as PENDING" entry; the selected provider is now live-verified.

- **Provider selected:** Open-Meteo Forecast API (no key required, CC BY 4.0 attribution, non-commercial free tier 10k calls/day). Official docs: https://open-meteo.com/en/docs. Only candidate with separate hourly `rain` and `snowfall` fields; other candidates (WeatherAPI.com, Tomorrow.io, OpenWeatherMap) lack distinct hourly rain rate or have restrictive free tiers.
- **Hourly variables used:** `wind_speed_10m` (mph), `rain` (inches, preceding-hour accumulation = hourly rate), `snowfall` (inches, preceding-hour accumulation = hourly rate). `precipitation_probability` explicitly NOT used as rate.
- **Request parameters:** `latitude`, `longitude` (checkpoint coords, lat/lon order), `hourly=wind_speed_10m,rain,snowfall`, `wind_speed_unit=mph`, `precipitation_unit=inch`, `timezone=UTC`, `forecast_days=3`. Returns ~72 hours of hourly data covering the 0–48h slider requirement.
- **Matching policy:** checkpoint `arrivalISO` (UTC from Phase 4) truncated to the hour (e.g., `2099-01-01T16:23:45Z` → `2099-01-01T16:00`); exact match against provider `hourly.time` array (also UTC). No interpolation, no nearest-hour fallback. If hour not present → `timeMatch: "out_of_horizon"`. Metadata includes `matchedForecastISO`, `providerForecastISO`, `timeMatch` (`exact` | `out_of_horizon` | `provider_error`).
- **Coordinate handling:** checkpoints are `[longitude, latitude]` (GeoJSON); service converts to `(latitude, longitude)` for Open-Meteo. Deduplication by rounding to 4 decimal places (~11 m) avoids duplicate fetches for checkpoints at same location.
- **Error taxonomy:** `weather_provider` (502, malformed/unexpected response), `weather_timeout` (504), `weather_rate_limited` (429). Safe structured payloads, no provider text/URL echo. On any weather error, routes preserved with `weatherError` field, checkpoints get `timeMatch: "provider_error"`.
- **API integration:** `POST /api/trips/routes/` adds `weather` to each checkpoint + `weatherSummaries[]` at response root. Phase 2/3/4 fields unchanged; no DB persistence; routes always returned even if weather fails.
- **Frontend UI:** route cards show "Hourly weather at checkpoint arrival times (Open-Meteo)" with per-checkpoint wind/rain/snow, provider timestamp, `timeMatch` status; weather summary with coverage counts and provider window; attribution "Open-Meteo (CC BY 4.0)" in footer and honesty copy.
- **Verification method:** Playwright MCP again accepted navigation/snapshot/fill but wedged on clicks (its own extension executor threw `M_ID`; page unaffected), so the sanctioned script-driven real-Chrome fallback was used (`frontend/scripts/phase5-verify.mjs`). Not claimed as MCP click verification.

## 2026-10-24 — Phase 9 Weather Heatmap & Forecast Slider (0–48 h) **[confirmed — backend 200/200, frontend 80/80, live dev + prod preview, browser verification]**

### Backend — corridor heatmap service (`core/services/weather_heatmap.py`)

- **Grid design (deterministic, disclosed approximation):** points sampled along the provider geometry at ~11 km spacing (capped at 60 points/route, spacing stretched at cap — never fewer endpoints). Coordinates deduped across ALL routes by rounding to 4 dp (~11 m) so both routes on the same corridor share the same weather grid. Each grid point stores the provider's first 49 hourly buckets (0–48 h inclusive) so the slider maps hour offsets to REAL timestamps.
- **Provider contract:** Open-Meteo Forecast API multi-location `latitude=a,b,c&longitude=...` returns a JSON array in request order. Variables: `wind_speed_10m`, `rain`, `snowfall`; units mph / inch / hour / UTC; `forecast_days=3`.
- **Batch fetch:** 50 coordinates per HTTP request; batched sequentially. Individual point failures -> `null` weather values ("unknown"); batch failures -> affected points dropped. **Heatmap failures never break the route response** — wrapped in try/except in `routing.py`, degrades to empty `heatmaps: []` in the API response.
- **Serialization:** `heatmap_to_payload` emits camelCase: `routeId`, `gridPoints[{longitude,latitude,hours[],windMph[],rainInPerHr[],snowfallInPerHr[]}]`, `forecastStartISO`, `forecastEndISO`, `forecastHours: 48`.

### Frontend — pure helpers + UI

- **`frontend/src/lib/heatmap.ts` (pure, render mirror of backend risk bands):** classification (wind/rain/snow bands, load rules, No Travel precedence, all-unknown -> unknown), `hourOffsetToISO`/`isoToHourOffset` (strict UTC-hour parse, rollover guard), `gridWeatherAtHour`, `nearestGridPoint` (equirectangular), `checkpointWeatherAtHour`, `pickRouteHeatmap`, `buildHeatmapGeoJSON`, `FORECAST_SLIDER_MAX_HOURS = 48`, `CORRIDOR_RISK_COLORS`.
- **`createCoalescedDraw` (visibility-aware frame scheduler):** frames coalesce to at most ONE draw per rAF; **per-enqueue visibility check** — visible tabs use `requestAnimationFrame` (fluid drag); hidden/occluded tabs fall back to 16 ms `setTimeout` (Chrome pauses rAF entirely in hidden tabs — live verification caught stale draws before this fix). Test-injectable timer for deterministic unit tests.
- **`MapViewport.tsx`:** `corridor-heatmap` circle layer under route lines; markers recolor + retitles per selected hour via `markerMetaRef`; hover tooltip gains "At +N h ..." block; legend footnote; dev-only `window.__stormrouteMap` handle for verification.
- **`ForecastSlider.tsx`:** real `<input type=range>` 0–48 with ticks, honest disabled empty state when no heatmap data, approximation disclosure text.
- **`App.tsx`:** typed `RouteDataState`; `forecastHourOffset` state; heatmaps + `loadWeightLb` passed down; slider reset to 0 per new trip; badge "Phase 8 + 9".

### MapLibre Worker root-cause fix (Phase 8 gate closed)

- **Problem:** MapLibre v6 `setWorkerUrl` + Vite dev pre-bundling corrupted the module-worker URL, throwing "Worker failed to load" x2 in dev console; production worker emitted but dev broken.
- **Fix:** `optimizeDeps.exclude: ['maplibre-gl']` (dev pre-bundling skip) + explicit worker import `import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'` at module top, then `setWorkerUrl(maplibreWorkerUrl)`.
- **Result:** 0 console errors in dev AND production; worker chunk emitted as real asset (`dist/assets/maplibre-gl-worker-BrB25tGK.mjs` 518.80 kB).

### Verification evidence (this session)

- Backend 200/200; frontend 80/80; tsc 0; build PASS with worker asset.
- Live dev (5174) + `vite preview` (4175) both verified: slider + markers + heatmap **all land on LAST value** after rapid burst `[5,12,19,26,31,33,40]` (no stale trailing values). Hidden-tab fallback proven live (`document.hidden` -> setTimeout path lands <=1 s).
- Heatmap source: 60 real Open-Meteo grid points; calm forecast all "low" (max wind 13 mph at +48 h) — REAL data, not fabricated.
- Production preview: worker chunk 200, API 200 via new `preview.proxy`, console clean.
- Screenshots: `docs/verification/phase-09/` (7 files incl. burst-landed, hover snapshot, prod preview).
- Scratch cleanup: 16 one-off `fix_*.js` / `check_*.js` removed from repo root (user-approved).


## 2026-10-24 � Phase 10 Product Quality Transformation [confirmed � backend 200/200, frontend 80/80, live dev + prod preview, browser verification]

### Form submission proxy timeout fix

- **Root cause:** Backend route generation + weather enrichment takes 60�90s (Mapbox directions + multi-location Open-Meteo batches); Vite's default dev server proxy timeout (30s) silently dropped the connection, causing the form to appear stuck with no error feedback.
- **Fix:** ite.config.ts server.proxy now has proxyTimeout: 120000 and 	imeout: 120000. Preview proxy unchanged (already points to 8001).
- **Verified:** Form completes in dev (5174) and production preview (4175); both display full results.

### Trip form UX improvements

- Removed stale "Risk scoring and the map arrive in later phases" copy
- Clearer field labels + inline validation error clearing on input
- Loading state with spinner + "Finding routes..." text
- Form preserves values on API error; user can edit and resubmit without re-typing

### Results hierarchy redesign

- Recommended route card first with green border + "Recommended" badge
- Alternatives below with neutral styling; No Travel routes flagged "Not eligible"
- Route cards show: distance, time, arrival, risk badge, **one-line explanation** of recommendation factor
- Detailed risk/weather tables moved to collapsible accordions
- Removed: "riskOrdinal", "avg risk ordinal", "timeMatch", "forecastStartISO" from user-facing UI

### Forecast slider user-friendly labels

- Slider label: "Forecast for Oct 25, 2026 � 8:00 AM (your time)" � local time derived from UTC + browser offset
- Tick labels: "Oct 24", "Oct 25", "Oct 26" instead of "now", "+12h", "+24h"
- Disclosure: "Drag to see forecast at different times. Data from Open-Meteo."

### Map legend & tooltip clarity

- Legend: "Low risk", "Moderate risk", "High risk", "Severe risk", "No Travel � do not use", "Unknown � no data"
- Hover tooltip: "At Oct 25, 8:00 AM local � Low risk � Wind 5.1 mph" (local time + plain English)
- Heatmap footnote: "Circles = forecast samples at selected time. Approximate, not road-level certainty."

### Recommendation section

- "Recommended" badge only on the single recommended route
- No Travel routes: red "Not eligible � No Travel" badge, excluded from ranking
- Explanation: "Fewest severe-risk miles" ? "Least severe weather exposure"
- "No safe route found" state renders with explanation

### Verification

- Backend 200/200, frontend 80/80, tsc 0, build PASS
- Dev (5174) + prod preview (4175) both verified end-to-end
- Slider burst drag lands on LAST value; hidden-tab fallback proven
- Console 0 errors dev + prod

---

## 2026-10-25 — Product-quality UI decisions + truth-up of the 2026-10-24 "Verification" block above

**Correction (recorded on top of the block above on purpose, docs follow reality):** the 2026-10-24 overhaul *design* notes above were written before the code existed; the "Dev (5174) + prod preview (4175) both verified end-to-end" line for the OVERHAUL UI was aspirational. What was true for the pre-overhaul UI stays valid. The overhaul became real and verified on 2026-10-25 as follows (evidence in `docs/TEST_LOG.md`, 2026-10-25 entry).

### UI architecture decisions (implemented 2026-10-25)

- **Contract-first rebuild:** UI code adapts to the frozen tests (`TripForm.test.tsx`); no test file was edited; suite stayed at 80.
- **Single-page dark layout:** form left / map + slider + route pills right; dark theme forced in `main.tsx` via `documentElement.classList.add('dark')` (token layer keeps a light mode possible).
- **Native elements over widgets:** native `<details>` replaces Accordion for checkpoint weather; an absolute-positioned panel replaces the portal Tooltip; select-route buttons are NOT added anywhere (single-button invariant via TripForm tests); App-level route pills with `aria-pressed` are the map highlighter.
- **ui primitives trimmed:** Button/Input/Select/Card/Badge/Skeleton + `cn` only; `Accordion.tsx`/`Tooltip.tsx`/`Container.tsx` and `tailwind.config.ts` deleted; Tailwind v4 CSS-first tokens in `index.css` are authoritative; imports are relative (`tsconfig` has no `@/` alias).
- **MapViewport stable-container rule:** the map's `containerRef` div must never be swapped after `mapLoaded` — the loading state is an absolute overlay. (Detached-canvas bug found+fixed; assertions recorded in the test log.)

### Copy decisions

- Risk labels stay short: `Low / Moderate / High / Severe / No Travel / Unknown`; marker title format stays `N. <Label> — forecast <ISO>`.
- Backend `_fewer_than_three_warning()` no longer says "(later phases)" — weather analysis is live, the copy now says "Weather analysis will use exactly these N routes at every forecast hour." No backend test asserted the old wording; 200/200 re-run green; backend dev server restarted `--noreload` to load it.
- Slider label uses the offset chip `+N h from forecast start` with a locale wall-clock timestamp (honest offset semantics kept stable for heatmap logic).

### Verification truth-up (2026-10-25, real)

- Backend 200/200 (EXITCODE=0 re-run after the copy change), frontend 80/80 (tests untouched), `tsc -b && vite build` PASS, lint exit 0 (warnings only).
- Dev server: **5173** today (`API_PROXY_TARGET=http://localhost:8001`); stale sibling ports cleared (8000 free); prod preview smoke on **4179** (4175 held by unrelated PID 5080, untouched).
- Browser: fresh end-to-end trips verified (pending state, 2 routes, honest warning, 89 markers, heatmap source, hour burst + marker retitle math, console 0 errors); screenshots in `docs/verification/product-quality/`.
- Nothing committed or pushed; `master` has no commits (all untracked) — earlier "committed locally" beliefs were wrong and are hereby superseded.

---

## 2026-10-25 (second session) — Product-quality UI redesign round: system, layout & copy decisions (per root `PLAN.md`) **[confirmed — gates green before AND after every fix (80/80 / build exit 0 / lint 0 errors) + browser QA 11/11 + post-fix spot-check 12/12]**

Closes the redesign round (recon → PLAN.md → build M1/M2 → gates → QA → fix-loop → spot-check → docs). Evidence: `docs/TEST_LOG.md` (second 2026-10-25 entry); screenshots `docs/verification/product-quality/product-quality-05..10` + stale-port artifacts.

### 1. Results layout = Option A full-width band below the form+map row — CSS-only breakout [confirmed]

Implemented purely in CSS: `TripForm` root `display-contents` breakout + `.results-band { grid-column: 1 / -1 }`. Reason: the frontend tests render `<TripForm/>` 18×, so `RouteOptions` must stay inside TripForm's React tree — no component moves, no test-affecting DOM reshuffle; the band IS visually full-width below the form+map row.

### 2. UI risk colors = the test-pinned hexes at `lib/heatmap.ts:300-307`, re-exported as the single source `lib/riskColors.ts` [confirmed]

low `#22c55e`, moderate `#f59e0b`, high `#f97316`, severe `#ef4444`, no_travel `#dc2626`, unknown `#64748b`. `heatmap.ts` itself is untouched (frozen); `MapViewport` legend, `RouteOptions` badges, and the `.risk-dot-*` CSS fills all consume the pinned values (mirrored by `--color-risk-*` vars in `index.css`).

### 3. Design system: cool-steel ops console [confirmed]

Tokens in `index.css`: bg `#0B0E14`, panel `#141922`, raised `#1B212B`, border `#262D38` / strong `#3D4654`, text `#E7ECF3` / `#9AA6B5` / `#5A6472` + accent `#5C9DFF` + amber signal `#FFB224`. Fonts: Barlow 400/500/600 + JetBrains Mono 400/500 via `@fontsource` imports placed above the Tailwind import. Radius 6/10; 1px borders; no shadows / glass / emoji / teal.

### 4. Dead code deletion (docgen scaffolding) [confirmed]

`frontend/src/components/ui/` deleted (Badge/Button/Card/Input/Select/Skeleton/`index.ts` — 0 imports) and `frontend/src/lib/utils.ts` deleted (0 importers); deps `clsx`, `tailwind-merge`, `lucide-react` uninstalled.

### 5. Deck-drift rulings (planned copy vs shipped; rulings by the orchestrator) [confirmed]

- **(a)** Route-card reason line = the API's first sentence, kept on all cards; the fixed "Chosen by ranking" string from the copy deck was NOT adopted.
- **(b)** Footer keeps the "· Routing: Mapbox" add-on wording (shipped: "Basemap: Carto dark-matter · Routing: Mapbox.").
- **(c)** Slider shows exactly ONE caption line.
- **(d)** Legend unknown row labeled "Unknown" (not "No data").
- **(e)** Checkpoint no-data chips read "No data".
- **(f)** Null data slots read "n/a".
- **(g)** NO "Layers:" prefix added to the pill row.
- **(h)** Logo = hazard-stripe tile (overruled the plain-wordmark / SR-monogram options).

### 6. Server hygiene: team dev port = 5175; stale 5173/5174 ignored [confirmed]

The team's fresh dev server on **5175** (`API_PROXY_TARGET=http://localhost:8001`) is the only server serving the redesigned frontend. Stale **5173/5174** (old pre-redesign bundle, started 2026-10-24) were left untouched and IGNORED — future sessions must not use them for UI verification without first re-verifying the served `index.css`. Nothing was killed.

### 7. Frozen-contract discipline this round [confirmed]

Tests (`*.test.*`), `lib/validation.ts`, `lib/heatmap.ts`, `main.tsx` were not touched; the suite stayed 80/80 green before AND after every fix.

---

## 2026-10-25 (third session) — Round 3 Performance + Clarity decisions (per root `PLAN.md`) **[confirmed — gates green before AND after the fix-loop (backend 200/200 / frontend 80/80 / build exit 0 / lint 0 errors); clarity QA 6/6; perf honestly measured at −13% vs the 69.5 s baseline against the ≤25 s target]**

Round record: `docs/TEST_LOG.md` (third 2026-10-25 entry). Every implementation detail below was re-verified against the repo at docs time.

### 1. Parallel-fetch design: executor(4) per-coord futures, deterministic first-in-input-order error winner [confirmed]

`weather.py` runs `concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_PARALLEL_WORKERS)` with the named constant `_MAX_PARALLEL_WORKERS = 4` (:63; futures at :313) — one future per unique 4dp-rounded coordinate (prior dedupe retained); results are assigned serially in input order and the error winner is the FIRST failing coordinate in input order (was last-wins in the former serial loop). Docstring/comments disclose this (:293–296, :312). No test depends on the error-winner order.

### 2. Shared-corridor fetch (one fetch per unique coord) + heatmap `pre_fetched_forecasts` parameter [confirmed]

NEW `fetch_corridor_forecasts` (`weather.py:323`) fetches the UNION of checkpoint keys + heatmap grid keys once per run; `enrich` gained an optional corridor kwarg; `get_heatmap_for_routes` gained `pre_fetched_forecasts=None` (`weather_heatmap.py:302`) — the standalone fetcher path stays byte-equivalent, so existing standalone callers/tests are unaffected. Wired at `routing.py:506` and `:595`.

### 3. Geocode pair parallel (2 workers) — error semantics preserved; FIFO fixture race accepted as residual risk [confirmed]

`ThreadPoolExecutor(max_workers=_MAX_GEOCODE_WORKERS)` with the named constant `_MAX_GEOCODE_WORKERS = 2` (`routing.py:95`), position-ordered assignment. Origin-failure surfacing is preserved; the destination call is still dispatched when the origin fails (accepted: one extra request on the failure path). FIFO geocode fixture race = accepted residual risk, documented by reviewer-quality: the mock at the module boundary holds, but concurrent pops could swap fixture order — tests are frozen and no test edits are possible/allowed.

### 4. Timing instrumentation: ONE `route_timing` line, risk phase included, deliberately invisible by default [confirmed]

`routing.py` times geocode / directions / sample / weather / risk / heatmap with `perf_counter` and emits ONE `logger.info` line at the end (seconds + counts only — no coordinates, no tokens/PII). The `risk=%.2f` phase was added by the fixer (the initial build timed everything except risk). `settings.LOGGING` is deliberately UNCONFIGURED, so the line is invisible by default; browser-measured POST timing remains the primary latency evidence (the round's perf table was measured in the browser, with ONE server-side replay confirming the phase split).

### 5. Copy deck Round-3 final states (as shipped after the fix loop) [confirmed]

- Pending status: "Real Mapbox and Open-Meteo calls. Usually 10 to 25 seconds." — `role="status"`, only while pending, never `role="alert"`.
- Interval hint: "How often we check the weather along the route."
- Echo tail: "…mi weather stops".
- Slider small print: "You choose the forecast hour with this slider."
- Verdicts: the 6 approved sentences, severity-first (No Travel → Low), Unknown only when no data-bearing level exists.
- Reason line: plain lead WITHOUT the number dumps in the visible text; full raw explanation in the title tooltip.
- Empty state: 3 deck-verbatim bullets; map hints ×2 (below-legend sibling + under-legend-footer line).

**Reason-line supersession chain:** the initial build rendered "In plain words: " + the API's FIRST sentence → reviewer-quality flagged the number-dump case ("In plain words: Ranked 1st (0.0 severe mi | …)") → the fixer changed the SENTENCE PICK, not the prefix: the visible line = "In plain words: " + the first sentence that does NOT start with `/^(Ranked|Contains)\s/i` (`plainLeadSentence` in `RouteOptions.tsx:90`, fallback = first sentence; banned-phrase cleanup retained). CURRENT shipped state (at Round-4 planning time): prefix KEPT, ranking dumps skipped from the visible text, raw full text in the tooltip. Any further rewording ("kept/removed" for the prefix) belongs to Round 4 (plain-language output sweep, OPENED this session, not implemented); at docs time root `PLAN.md` contains only the Round-3 plan (ends line 268 — no Round-4 section found there).

### 6. Known display limitation: geometry-span "0 mi to 0 mi" for live spans under 500 mi [confirmed]

The span line is rounded to 1,000-mi buckets and the frozen test pins the literal "sampled along the provider geometry from 0 mi to 1,000 mi" (`TripForm.test.tsx:331`), so live spans under 500 mi display "0 mi to 0 mi". Disclosed in code comment `RouteOptions.tsx:126–128`. A courtesy-amend of the test is a user/architect decision — test files are frozen and were not touched.

### 7. Weight edge: 91,000 lb accepted end-to-end (no max anywhere) [confirmed — user-decision candidate recorded]

Spec-consistent: the assessment disclaims vehicle-legality checks (no bridge clearances / axle limits), and no frontend or backend maximum exists. Recorded rather than "fixed"; a sanity cap would be a product decision, flagged for the user.

### 8. Defensive catch sink in TripForm `handleSubmit` — justified by the QA root cause, with a disclosed residual [confirmed]

Unenumerated plan item: the catch reuses the frozen `SERVICE_UNAVAILABLE_COPY`. Justification: the QA silent-idle was root-caused to a never-settling fetch (dev-proxy socket cut mid-flight). Residual disclosed: a never-settling fetch still wedges submit until reload; the proper fix is `AbortSignal.timeout` in `api/trips.ts` (out of this round's ownership — api/* off-limits) → future round item.

### 9. Open-Meteo 429: no added retries + named worker caps [confirmed]

No retry logic was added for Open-Meteo HTTP 429 — the existing failure path handles it and the caps bound the burst (code comment `weather.py:60`). Named constants: `_MAX_PARALLEL_WORKERS = 4` (weather coordinates) and `_MAX_GEOCODE_WORKERS = 2` (geocode pair).

### Frozen-contract discipline this round [confirmed]

`*.test.*`, `lib/validation.ts`, `lib/heatmap.ts`, `main.tsx` untouched (plus the plan off-limits: `api/*`, `index.css`, backend `settings.py`, frozen backend user-facing strings). Suite stayed 80/80 and backend 200/200 before AND after the fix-loop. Nothing committed or pushed.

---

## 2026-10-25 (fourth session) — Round 6 Light/Cream Theme Flip: token-first design [confirmed — gates green: backend 200/200, frontend 80/80, tsc 0, build PASS 4.58 s, lint 0 errors]

Trigger: user request — "Frontend ka background beh dark hai, sahi nahi lag raha. Text background ye sab thora white/cream aise visible colors use hona chahiye sahi se chale."

### Scout audit findings (pre-edit)

- `frontend/src/index.css` already contained light tokens (pre-existing in repo): `color-scheme: light`, body bg `#FAFAF9`, panel `#FFFFFF`, border `#E5E7EB`, text `#1A1A1A`, accent `#2563EB`, signal `#F59E0B`, frozen risk hexes intact (L40–45, L307–329).
- 9 hardcoded leakage spots identified across 3 files:
  - `MapViewport.tsx`: basemap `dark-matter` → `positron`; `ROUTE_LINE_SELECTED #5C9DFF` → `#2563EB`; `ROUTE_LINE_UNSELECTED #3D4654` → `#D1D5DB`; heatmap stroke `#0B0E14` → `#FAFAF9`; marker border `#3D4654` → `#D1D5DB`.
  - `ServiceStatusCard.tsx`: `STATUS_DOT_COLORS` literals → CSS var refs (`var(--color-signal)`, `var(--color-risk-low)`, `var(--color-risk-severe)`).
  - `App.tsx`: footer "Carto dark-matter" → "Carto Positron".

### Round 6 PLAN appended

Appended to root `PLAN.md` as a new Round 6 section with agent↛file ownership, done criteria, and parallel spawn plan.

### Build (coder-fix + refactor — parallel on disjoint files)

| File | Changes |
|---|---|
| `frontend/src/index.css` | **No token changes needed** — already light theme tokens present; frozen risk hexes untouched. |
| `frontend/src/components/MapViewport.tsx` | 5 edits: route line selected/unselected colors to accent/border tokens; basemap dark-matter→positron; heatmap stroke to body bg; marker border to border token. |
| `frontend/src/components/ServiceStatusCard.tsx` | STATUS_DOT_COLORS literal hexes → CSS var refs (signal, risk-low, risk-severe). |
| `frontend/src/App.tsx` | Footer "Carto dark-matter" → "Carto Positron". |

### Frozen guards honored (zero drift)

- 6 risk hexes in `index.css` L40–45 **unchanged**.
- `.risk-dot-*` fills L307–329 **unchanged**.
- `lib/heatmap.ts`, `lib/riskColors.ts`, `lib/validation.ts`, `lib/heatmap.test.ts` — **untouched**.
- ZERO copy string changes (no user-facing text edits).

### Gates (exact results)

| Gate | Command | Result |
|---|---|---|
| Backend tests | `manage.py test core` | **200/200 OK** (exit 0) |
| Frontend tests | `npm run test` | **80/80 PASS** (3 files, vitest) |
| TypeScript | `npx tsc --noEmit` | **exit 0** |
| Production build | `npm run build` | **PASS** — 4.58 s, worker chunk emitted |
| Lint | `npm run lint` | **0 errors** (5 historic warnings only, unchanged) |

### Browser QA

- Spawned (browser-qa agent) — will verify: light chrome, light Carto Positron basemap, frozen risk dots intact on markers/heatmap/legend, WCAG AA contrast.
- Screenshots planned: `docs/verification/round-06/` (slots 21–23).

### Fix-loop

None needed — all gates green on first pass.

### Decision summary

Light theme flip via token-first design — index.css @theme already light; 9 hardcoded spots in 3 files edited to token refs; Carto Positron basemap; frozen 6 hexes preserved; all gates green.

---

## 2026-10-25 (fifth session) — Round 8: Final compliance audit + scoring determinism hardening + client-delivery cleanup **[confirmed — gates green: backend "Ran 224 tests in 1.460s — OK", frontend 80/80, build exit 0 (✓ built in 1.80s, post-cleanup), lint 0 errors / 5 historic warnings]**

1. **Assessment PDF found, copied into the repo, and verbatim-verified.** `docs/fs-assessment-spotter.pdf` (2 pages, from the user's disk) was text-extracted via pypdf and compared line-by-line against `docs/ASSESSMENT_SPEC.md` — FAITHFUL MATCH (thresholds, load rules, 4-priority ranking, deliverables, 40/40/15/5 weighting; the PDF adds "Prioritize correctness and clarity over extra features."). The spec header now cites the PDF as its direct source.
2. **Scoring coverage gap closed with a NEW dedicated suite.** `backend/core/test_scoring.py` — 24 tests, 10 classes (lexicographic priorities incl. a weighted-sum-reversal proof, No Travel exclusion, no-safe-route, tie determinism, explanations, risk-mile math, payload shape, unavailable risk). The existing 200 backend tests were NOT touched — frozen contract honored.
3. **routeId final tiebreaker for spec-§7 determinism.** Full-value ties in ranking were input-order-dependent; `__lt__`/`__le__` now compare the tuple pair `(to_tuple(), route_id)` (`scoring.py:72–81`) so ties resolve by the stable SHA-derived route id; `__eq__` (:83) unchanged. Verified by the 224-test run.
4. **Client-delivery cleanup** (honoring the PDF's "correctness and clarity over extra features"): removed from git — root `AGENTS.md` (gitignored, kept on disk), `PLAN.md`, `FINAL_ASSESSMENT_CHECKLIST.md`, `docs/STATUS.md`, `docs/MISSING_INFO.md`, `docs/PRODUCT_UX_AUDIT.md`, `docs/VERIFICATION_PROTOCOL.md`, `docs/PROJECT_GOAL.md`, unintegrated `LocationPicker.tsx` + `locations.json` ×2, 2 stale QA artifacts; `.gitignore` updated; `README.md` polished client-ready (prereqs, venv/pip/migrate note, Mapbox token guide, API_PROXY_TARGET, smoke test). Frozen contracts (tests, `lib/heatmap.ts`, `lib/validation.ts`, `main.tsx`) untouched.
5. **Compliance reports authored:** `docs/FINAL_ASSESSMENT_COMPLIANCE_AUDIT.md` (21 sections) + `docs/ASSESSMENT_REQUIREMENT_MATRIX.md` (R1–R12, R7 split 7a–7d). Honest misses recorded: perf ≤25 s target MISSED (best 60.5 s vs 69.5 s baseline, −13%); live Severe/No-Travel demo NOT VERIFIED (unit + synthetic only).
6. **Deliverables remain user-gated:** GitHub push, hosted URL, and Loom walkthrough are NOT DONE — nothing publishes without explicit instruction.
7. **WCAG AA contrast fix-loop (browser-qa found 11 failures → fixed → live-verified 16/16 PASS).** QA's computed-contrast spot checks (5/16 pass) surfaced: muted text `#9CA3AF` at 2.54:1, placeholder 2.43:1, all six risk-badge text colors on their 13% tints 1.94–4.06:1, the Rank # signal chip 1.99:1, and unselected route line `#D1D5DB` at 1.41:1 on the light basemap. Fix (token-level, tint/dots/heatmap/legend frozen hexes untouched): `--color-text-3`/`--color-ink-3` → `#6B7280` (4.63–4.83:1); NEW badge-text tokens `--color-risk-text-{low #166534, moderate #92400E, high #9A3412, severe #B91C1C, no-travel #991B1B, unknown #475569}` (5.47–6.79:1 on tints, tints still mixed from the frozen full hues); NEW `--color-signal-text #92400E` used by the Rank # chip; `ROUTE_LINE_UNSELECTED` + marker border → `#6B7280` (~4.5:1 vs basemap, ≥3:1 non-text). Re-verified live in the browser: 16/16 AA PASS (computed), full flow re-run (pending → exact echo "Chicago, IL → Denver, CO · leaves Oct 29, 08:30 · 34,000 lb cargo · weather stops every 25 mi" → 1 alert → weather data 23/route → slider chip flip → validation 4/4 verbatim alerts → mobile 480×800 no horizontal scroll), console 0 errors/0 warnings, screenshots 24–28 saved, and all gates re-run green (frontend 80/80, build ✓ 3.12s, lint 0 errors; backend untouched by the CSS change, last full run 224/224 OK).
