# StormRoute — Missing Info, Blockers & Open Questions

Principle: nothing invented. Real values go here only after they are actually configured by the user or verified by
execution. Key status is tracked **set/unset only** — never values.

---

## 2026-10-23 — Phase 1

| Item | Status | Detail |
|---|---|---|
| `MAPBOX_ACCESS_TOKEN` | **SET** *(configured 2026-10-24 — see addendum)* | Live-verified the same day: geocoding + Directions `code=Ok`. Value never printed/tracked; backend-only. |
| `OPEN_METEO` key | **N/A — NOT REQUIRED** *(terms corrected 2026-10-24)* | No key needed, free tier is **non-commercial only** (<=10k calls/day, CC BY 4.0 attribution). Not a commercial license. |
| Weather provider final selection | **PENDING — resolve before Phase 5** | Open-Meteo primary (separate hourly `rain`+`snowfall`); WeatherAPI.com fallback lacks a separate hourly rain rate (precip fields are combined totals; 3-day free horizon). Resolution = one live Open-Meteo fetch verifying semantics, else re-open with WeatherAPI.com. |
| `VITE_API_BASE_URL` | set in code defaults | `http://localhost:8000/api` for dev; deployment URL assigned in Phase 10. |
| Mapbox alternatives reality | **partially resolved 2026-10-24 — see addendum** | Docs promise "up to two alternatives"; a real corridor returned only 2 routes live. Phase 3 must design around non-guaranteed counts. |
| Open-Meteo rate magnitudes | **pending Phase 5 verification** | Hourly rain/snow model rates: confirm plausible scale at boundaries with live samples + fixtures. |
| Deployment provider | **undecided by design** | Per spec, decided in Phase 10 after feasibility (candidates: Render / Railway / Fly.io / Vercel+Render split). |
| GitHub remote | **not yet created** | Repo is initialized locally; remote creation awaits user instruction (Section 7 rules: no push/publish without authorization). |
| Loom walkthrough | **pending Phase 10** | Script drafted at that time; recording by user (us assisting). |
| $100 bonus | acknowledged | Recruiter email referenced a $100 bonus on completion — not a job offer or guaranteed payment; no action item. |
| Playwright MCP | **verified Phase 1; WEDGED in Phase 2 (documented)** | Phase 1 real-Chrome session worked. Phase 2: clicks timed out with zero synthesized input events reaching the page; later navigations also timed out. Substituted with a script-driven real-Chrome Playwright harness (`frontend/scripts/phase2-verify.mjs`, 16/16 checks PASS). Retry MCP first next phase; fall back to the harness. |

---

## 2026-10-24 — Addendum: Mapbox pre-Phase-3 configuration (user-provided token)

| Item | Status | Detail |
|---|---|---|
| `MAPBOX_ACCESS_TOKEN` | **SET (pk-scoped)** | Stored ONLY in gitignored `backend/.env`; loaded via python-dotenv from `stormroute/__init__.py` so every entrypoint (manage.py / shell / tests / WSGI) sees it; exposed as `settings.MAPBOX_ACCESS_TOKEN` for server-side calls only. Frontend never receives it. |
| Live Mapbox confirmation | **VERIFIED** | Sandbox smoke (`backend/scripts/mapbox_smoke.py`): Geocoding Chicago -> `[-87.632362, 41.881953]` and Denver -> `[-104.986109, 39.741681]` (HTTP 200 both); Directions `alternatives=true` returned `code=Ok` with **2 routes** (distances 1614.3 km / 1817.4 km durations 14.83 h / 16.75 h). |
| Three-route reality | **EMPIRICALLY NOT GUARANTEED — one corridor now live-proven** | The Chicago->Denver corridor returned just primary + 1 alternative. Phase 3 must honestly handle 1-route / 2-route responses (no synthetic third route). |
| `backend/requirements.txt` | **CREATED (was missing)** | Pinned runtime versions proven locally: Django 6.1.2, djangorestframework 3.18.3, django-cors-headers 4.9.0, python-dotenv 1.2.4, requests 2.34.2. |
| `python-dotenv`, `requests` installed | done | `requests` = outbound provider client for Mapbox now and Open-Meteo later. |
| Backend restart after settings change | done | Previous server (PID 14144) stopped; new one on PID 19588 at `127.0.0.1:8001`; `/api/health/` re-verified; `manage.py test core` 27/27 OK after loader introduction. |

---

## 2026-10-24 — Addendum 2: Phase 3 status

| Item | Status | Detail |
|---|---|---|
| `MAPBOX_ACCESS_TOKEN` | **SET (pk-scoped) — unchanged** | Server-side only; never in the test environment (mocks cover suite); never in any response body (asserted by 26 unit tests) or wire check. |
| Live route generation via app | **VERIFIED** | `POST /api/trips/routes/` on the real dev server (curl + probe script + browser harness): HTTP 200, real Mapbox alternatives (I-80/I-76 + I-80/I-70 on Chicago->Denver), honest <3 warning, no token leakage. |
| Three-route reality | **CONFIRMED for this corridor — 2 routes** | Route counts are corridor-dependent. UI + API surface actual counts with honest warning; no synthetic padding. |
| Geocode-failure branch | **unit-verified only (live-not-triggerable)** | Live Mapbox geocoder resolved every nonsense test string (fuzzy matching); `geocode_failed` stage attribution remains proven by mocked tests (documented honestly in TEST_LOG). |
| Duplicate-drop branch | **unit-verified only** | `duplicatesDropped > 0` path covered by unit tests; live replays were not forceable this session (live runs even returned different alternative pairs run-to-run). |
| Open-Meteo weather | unchanged — NOT touched in Phase 3 | Phase 5 prerequisite: live fetch + semantics confirmation first. |
| Deployment provider | unchanged — decided in Phase 10 | candidates unchanged. |
| GitHub remote | unchanged — awaits instruction | nothing committed/pushed. |
| Playwright MCP | **wedged again in Phase 3 (clicks time out)** | harness substitution per instruction: `frontend/scripts/phase3-verify.mjs` — 8/8 PASS, evidence in `docs/verification/phase-03/`. Retry MCP first next phase; fall back to harness. |
| New dev-server state | backend PID 24564 @ 8001 (fresh instance with Phase 3 code), frontend PID 16004 @ 5174 | both left running per policy; ports 8000/5173 remain held by foreign process untouched. |

---

## 2026-10-24 — Addendum 3: Phase 4 status

| Item | Status | Detail |
|---|---|---|
| `CHECKPOINT_MAX_PER_ROUTE` | **DEFAULTED — 500 per route** | Configurable via env (validated integer >= 2; invalid values fall back to 500). Not an assessment-mandated number — a documented engineering ceiling to bound later weather-provider work. Exceeding it widens spacing (never truncates); response discloses `capped` + `effectiveIntervalMiles`. |
| Live checkpoint counts | **VERIFIED** | Real Chicago->Denver run at 25 mi: 42 checkpoints (1,001.9 mi geometry) and 47 checkpoints (1,128.0 mi); 50-mi run: 22. Last checkpoint arrival equals route arrival; monotonic distance/ETA; destination vertex preserved; ids stable across identical requests. |
| Cap reached live? | **NO** | Max observed 47 of 500. Capped **UI** branch verified with a clearly labeled synthetic fixture (request interception); capped **backend** branch verified deterministically with `CHECKPOINT_MAX_PER_ROUTE=12`. Not presented as live provider data. |
| Geometry vs provider distance | **KNOWN, DISCLOSED DELTA** | Haversine length of the simplified Mapbox overview geometry is slightly shorter than the provider's reported route distance (live: 1,001.9 vs 1,003.1 mi; 1,128.0 vs 1,129.3 mi). Both are returned separately; no provider value is rewritten. Checkpoint distances use geometry length and are labeled as such. |
| ETA data available | **ROUTE-LEVEL ONLY** | Mapbox response exposes route-level duration, not per-leg durations; ETA therefore uses distance-weighted constant average speed. No traffic provider is integrated, so no traffic-aware claim is made. |
| Open-Meteo weather | unchanged — NOT touched in Phase 4 | Phase 5 prerequisite still: one live fetch + semantics confirmation before integration. |
| Playwright MCP | **wedged again in Phase 4 (clicks time out)** | Navigation/snapshot/fill worked; two click attempts timed out; extension executor logged its own `M_ID` crash. Substitution: `frontend/scripts/phase4-verify.mjs` — 9/9 PASS, evidence in `docs/verification/phase-04/` (`results.json` discloses method and synthetic fixture). |
| New dev-server state | backend desktop-commander session PID 24768 @ `127.0.0.1:8001` (`--noreload`, Phase 4 code), frontend PID 16004 @ 5174 (HMR) | health 200 re-probed; both left running per policy; ports 8000/5173 remain held by the foreign `StormRoute CL` stack, untouched. |
| Deployment / GitHub remote / Loom | unchanged — Phase 10 / awaits instruction | nothing committed or pushed; repo still untracked. |

---

## 2026-10-24 — Addendum 4: Phase 5 status

| Item | Status | Detail |
|---|---|---|
| `OPEN_METEO` key | **N/A — NOT REQUIRED** | No key needed, free tier is **non-commercial only** (<=10k calls/day, CC BY 4.0 attribution). Not a commercial license. |
| Weather provider final selection | **CONFIRMED — Open-Meteo** | Live-verified 2026-10-24: Open-Meteo Forecast API returns hourly `wind_speed_10m`, `rain`, `snowfall` with exact-hour matching to checkpoint ETAs. WeatherAPI.com fallback lacks separate hourly rain rate; not selected. |
| Open-Meteo rate magnitudes | **VERIFIED** | Live Chicago->Denver at 25 mi: wind ~6 mph, rain 0.0 in/hr, snow 0.0 in/hr across all checkpoints. Rate magnitudes plausible for classification boundaries (will be tested in Phase 6). |
| Live weather integration | **VERIFIED** | `backend/scripts/phase5_live_probe.py` -> HTTP 200, 42/42 checkpoints with weather (Route 1), 47/47 (Route 2); `timeMatch: exact`; weather summaries show full coverage; provider window 2026-10-24 to 2026-10-26. |
| Weather forecast semantics | **CONFIRMED** | Open-Meteo `rain`/`snowfall` are "preceding hour accumulation" in requested units (inches); treated as hourly rate per provider documentation. `precipitation_probability` explicitly NOT used as rate. |
| Phase 5 fields available | **ROUTE + CHECKPOINT LEVEL** | Per-checkpoint `weather` object with wind/rain/snow, timestamps, match status; per-route `weatherSummaries` with coverage counts and provider window. |
| Playwright MCP | **wedged again in Phase 5 (clicks time out)** | Navigation/snapshot/fill worked; click attempts timed out; extension executor logged its own `M_ID` crash. Substitution: `frontend/scripts/phase5-verify.mjs` — 8/8 PASS, evidence in `docs/verification/phase-05/`. |
| New dev-server state | backend shell PID 14712 @ `127.0.0.1:8001` (`--noreload`, Phase 5 code), frontend PID 16004 @ 5174 (HMR) | health 200 re-probed; both left running per policy; ports 8000/5173 remain held by the foreign `StormRoute CL` stack, untouched. |
| Deployment / GitHub remote / Loom | unchanged — Phase 10 / awaits instruction | nothing committed or pushed; repo still untracked. |

---

## 2026-10-24 — Addendum 5: Phase 9 status (this session)

| Item | Status | Detail |
|---|---|---|
| Heatmap grid spacing | **~11 km (~11 000 m), <=60 pts/route** | Deterministic haversine sampling along LineString; spacing stretched at cap (never fewer endpoints). Coords deduped across routes by 4-dp rounding (~11 m). Disclosed approximation, not road-level certainty. |
| Heatmap provider buckets | **49 (0–48 h inclusive)** | Open-Meteo hourly arrays sliced to 49 UTC buckets; slider offset N indexes directly. `forecastStartISO` / `forecastEndISO` per heatmap for UI bounds. |
| Multi-location batch | **50 coords/request** | Single HTTP request per batch; `latitude=a,b,c&longitude=...` returns array in same order. Sequential batches; failures drop points, never break route response. |
| Heatmap API response | **TOP-LEVEL `heatmaps[]`** | `routeId`, `gridPoints[]`, `forecastStartISO`, `forecastEndISO`, `forecastHours: 48`. Try/except wrapped — outage degrades to `[]`, routes preserved. |
| `riskSummaries` duplicate | **FIXED** | `routing.py` had duplicate key line 591-592; removed second occurrence this session. |
| Frontend slider | **real `<input type=range>` 0–48** | Tick labels, approximation disclosure, honest disabled empty state. `forecastHourOffset` state bounded 0–48, reset 0 per new trip. |
| Map heatmap layer | **`corridor-heatmap` circle layer** | Under route lines; markers recolor + retitles per selected hour; hover tooltip "At +N h ..." block; legend footnote. |
| **MapLibre Worker ROOT CAUSE** | **CLOSED this session** | Vite dev pre-bundling corrupted module-worker URL -> "Worker failed to load" x2. Fix: `optimizeDeps.exclude: ['maplibre-gl']` + explicit `import ...worker.mjs?url` + `setWorkerUrl()`. 0 console errors dev + prod; worker chunk emitted as asset. |
| Coalesced draw scheduler | **`createCoalescedDraw` (visibility-aware)** | rAF when visible (fluid drag); per-enqueue `document.visibilityState === 'visible'` check; hidden tabs -> 16 ms setTimeout (Chrome throttles but fires). Test-injectable timer. |
| Rapid-burst drag gate | **PASS (dev + prod preview)** | Burst `[5,12,19,26,31,33,40]` zero waits -> label + heatmap + markers ALL land on LAST value (+40 h = `2026-10-25T16:00`). Hidden-tab fallback proven live. |
| Production preview | **verified @4175** | Worker chunk 200, main bundle 200, `/api/*` 200 via new `preview.proxy` (vite preview doesn't inherit server.proxy — gap fixed). Console 0 errors. |
| Scratch cleanup | **16 scripts removed** | `fix_*.js` / `check_*.js` from repo root (user-approved); root now only README/AGENTS/.env.example/.gitignore. |
| Test counts | **Backend 200/200, Frontend 80/80** | 17 new heatmap service tests, 2 new routing integration tests, 42 heatmap helpers + 5 coalesced-draw tests. |
| Screenshots | **7 files in `docs/verification/phase-09/`** | burst-landed (viewport + fullpage), hover hour snapshot, prod preview 4175, earlier 24h/48h captures. |
| Dev servers | backend 8001, frontend 5174 | Left running per policy; Phase 9 code active. |
| Deployment / Git / Loom | unchanged — Phase 10 / awaits instruction | nothing committed or pushed; repo still untracked. |


---

## 2026-10-24 � Addendum 6: Phase 10 status (this session)

| Item | Status | Detail |
|---|---|---|
| Frontend UX overhaul | **COMPLETE** | Form submission, results hierarchy, forecast slider labels, map legend, tooltips, recommendation section all redesigned for ordinary users |
| Form submission proxy timeout | **FIXED** | ite.config.ts server.proxy: proxyTimeout: 120000, 	imeout: 120000 � verified dev + prod preview |
| Trip form UX | **IMPROVED** | Clearer labels, inline validation, loading spinner, error preservation, removed stale copy |
| Results hierarchy | **REDESIGNED** | Recommended route first (green badge), alternatives below, collapsible details, plain-English explanations |
| Forecast slider labels | **LOCALIZED** | Local time display, date-based ticks, simplified disclosure |
| Map legend & tooltips | **PLAIN ENGLISH** | Risk levels named, local time in tooltips, heatmap footnote clarified |
| Recommendation section | **CLEAR** | Recommended badge, No Travel flagged, plain-English explanations, No Travel gate visible |
| Proxy timeout fix | **ROOT CAUSE** | Vite default 30s timeout < 60�90s backend pipeline; fixed to 120s in ite.config.ts |
| Regression tests | **PASS** | Backend 200/200, frontend 80/80, tsc 0, build PASS |
| Dev + prod preview | **VERIFIED** | Both environments end-to-end verified with screenshots |
| Console errors | **0** | Dev + prod preview clean |
| Screenshots | **6 files** | docs/verification/phase-10/ (workflow, prod preview, hover, fullpage) |
| Dev servers | **RUNNING** | Backend 8001, frontend 5174 (Phase 10 code active) |
| Deployment / Git / Loom | **PENDING** | Phase 11 � awaits explicit instruction |
