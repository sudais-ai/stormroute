# StormRoute — Limitations & Honest Disclosures

**Generated:** 2026-10-24 | **Status:** Phase 10 complete

This document enumerates every known limitation, approximation, and scope boundary in StormRoute. Per the assessment honesty rules: **nothing is claimed that is not implemented and verified**. All items below are reflected in code, docs, UI copy, and test evidence.

---

## 1. Route & Geometry Limitations

| Limitation | Detail | Disclosed In |
|---|---|---|
| **Simplified overview geometry** | Mapbox Directions `overview=full` returns a simplified LineString. Haversine length of this geometry (1,001.9 mi) differs from provider's reported route distance (1,003.1 mi). Both values returned in `checkpointSummary` (`geometryDistanceMeters` vs `providerDistanceMeters`). | API response, RouteOptions UI copy |
| **No turn-by-turn or per-leg durations** | Mapbox overview response gives route-level duration only. Checkpoint ETAs spread the total duration by cumulative distance fraction (constant average speed). No traffic, stops, or per-leg provider durations. | `checkpointSummary` method label, RouteOptions ETA honesty copy |
| **Alternatives not guaranteed** | Mapbox returns 1–3 routes corridor-dependent. Chicago→Denver live returns 2. UI + API surface actual counts with honest `<3` warning; **no synthetic third route is ever invented**. | `threeRoutesReturned` boolean, `warning` string, RouteOptions `<3` alert |
| **Geocoding fuzzy matching** | Mapbox geocoder resolves nonsense strings to real places. `geocode_failed` stage attribution verified only via mocked tests (live failure not triggerable). | TEST_LOG.md, DECISIONS.md |
| **Duplicate route detection** | Replays (identical geometry fingerprint) dropped; near-distinct corridors kept. Live replays not forceable — unit tests cover the logic. | `duplicatesDropped` count, test_routing.py |

---

## 2. Checkpoint Sampling Limitations

| Limitation | Detail | Disclosed In |
|---|---|---|
| **Haversine on simplified geometry** | Checkpoint distances measured along the simplified Mapbox overview LineString, not the full-resolution route. Small delta vs provider distance acknowledged. | API: `geometryDistanceMeters` vs `providerDistanceMeters` |
| **Constant-speed ETA** | `departureUTC + providerDurationSeconds × (cumulativeDistance / geometryLength)`. No traffic, weather delays, stops, speed changes, or per-leg durations. | RouteOptions ETA copy, checkpoints.py docstring |
| **Interval widening under cap** | If requested spacing would exceed `CHECKPOINT_MAX_PER_ROUTE` (default 500), spacing is **widened** (never truncated); destination retained. Response discloses `capped`, `effectiveIntervalMiles`. | API response, RouteOptions capped disclosure |
| **Interpolation flag** | Checkpoints between provider vertices carry `interpolated: true`; actual vertices `false`. Origin/destination never interpolated. | Checkpoint `interpolated` field |
| **Stable IDs** | `cp_` + SHA-256 of `routeId|sequence|distance|coords`. Identical requests → identical IDs (verified live). Different routes → different IDs. | checkpointId field, live probe |

---

## 3. Weather Integration Limitations

| Limitation | Detail | Disclosed In |
|---|---|---|
| **Exact-hour match only** | Checkpoint `arrivalISO` truncated to hour; matched against provider hourly `time` array (UTC). **No interpolation, no nearest-hour fallback.** Missing hour → `timeMatch: "out_of_horizon"`. | API `timeMatch` field, weather.py docstring |
| **Forecast, not observation** | Open-Meteo provides model forecast data matched to checkpoint ETAs. Not real-time observations. Accuracy degrades with forecast horizon. | RouteOptions weather section, footer attribution |
| **Rain/Snow semantics** | Open-Meteo `rain` and `snowfall` are "preceding hour accumulation" in requested units (inches). Treated as hourly rate per provider docs. `precipitation_probability` explicitly NOT used as rate. | weather.py docstring, DECISIONS.md |
| **Coordinate dedup at 4 dp** | Checkpoints rounded to 4 dp (~11 m) before Open-Meteo call to avoid duplicate fetches for co-located checkpoints. | weather.py, MISSING_INFO.md |
| **Free tier non-commercial** | Open-Meteo free tier: 10k calls/day, CC BY 4.0 attribution, **non-commercial only**. Assessment use is non-commercial. | Footer attribution, MISSING_INFO.md, API_PROVIDER_RESEARCH.md |
| **Error degradation** | Weather failures preserve routes; checkpoints get `timeMatch: "provider_error"`; `weatherError` field at route level. Routes never dropped. | weather.py error taxonomy, integration tests |

---

## 4. Risk Classification Limitations

| Limitation | Detail | Disclosed In |
|---|---|---|
| **Spec-mandated bands only** | Wind: `<25, 25–<35, 35–<45, 45–<55, ≥55` mph. Rain: `<0.10, 0.10–<0.25, 0.25–<0.50, 0.50–≤1.00, >1.00` in/hr. Snow: `<0.5, 0.5–<1.0, 1.0–<2.0, 2.0–≤3.0, >3.0` in/hr. Load rules applied per spec. No custom thresholds. | DECISIONS.md, risk.py, test_risk.py boundaries |
| **Combined = max with No Travel precedence** | Checkpoint risk = max(wind, rain, snow, load-adjusted) with **No Travel dominant**. Unknown → unknown (never Low). | risk.py `combine_checkpoint_risk` |
| **Risk-miles are checkpoint-based estimates** | Route risk miles = sum of segment distances weighted by checkpoint risk. Not continuous integration; approximate. Disclosed as "est." in UI. | RouteOptions risk summary, risk.py aggregation |
| **Unknown never safe** | Unknown weather → unknown risk → own legend color (slate). Never renders as Low/Moderate. | MapViewport legend, heatmap.ts classification |

---

## 5. Route Scoring & Recommendation Limitations

| Limitation | Detail | Disclosed In |
|---|---|---|
| **Lexicographic only — no weighted sum** | Priority: 1) fewest Severe mi, 2) fewest High mi, 3) lowest avg risk (ordinal Low=0 → No Travel=4), 4) shortest time. Tie-break order is **fixed and unchangeable**. | scoring.py, DECISIONS.md |
| **No Travel routes never "safe"** | If a route has any No Travel checkpoint, it ranks last. If all routes have No Travel → "No safe route found" with explanation. | scoring.py, RouteOptions recommendation |
| **Average risk = mean ordinal** | Simple arithmetic mean of checkpoint risk ordinals. Not distance-weighted. | scoring.py docstring |
| **Explanation names deciding factor** | `routeExplanations` strings explicitly name the tie-break step (e.g., "fewest Severe miles", "shortest travel time"). | RouteOptions recommendation text |

---

## 6. Map & Visualization Limitations

| Limitation | Detail | Disclosed In |
|---|---|---|
| **OpenFreeMap tiles** | No key required; attribution to OpenStreetMap contributors. Not a commercial tile provider. | MapViewport.tsx, README attribution |
| **Risk-colored markers only at checkpoints** | Markers show risk at discrete checkpoint locations. Interpolation between checkpoints not visualized on map. | MapViewport.tsx |
| **Heatmap = gridded corridor samples** | ~11 km spacing along LineString; ≤60 points/route; cross-route dedup at 4 dp. **Not road-level certainty.** Values between grid points are approximations. | MapViewport corridor-heatmap layer, ForecastSlider approximation disclosure, heatmap.py docstring |
| **Slider = 0–48 h from provider forecast start** | Provider returns ~72 h (3 days); slider covers first 49 buckets (0–48 h inclusive). `forecastStartISO`/`EndISO` per heatmap for UI bounds. | heatmap.ts `FORECAST_SLIDER_MAX_HOURS = 48` |
| **Rapid drag consistency** | `createCoalescedDraw` ensures rapid slider drag lands on LAST value (frame-coalesced, latest-wins). Hidden-tab fallback via setTimeout proven live. | heatmap.ts, Phase 9 burst test |
| **Dev handle** | `window.__stormrouteMap` exposed in dev only for Playwright verification. Stripped in production build (guarded by `import.meta.env.DEV`). | MapViewport.tsx |

---

## 7. Provider & Infrastructure Limitations

| Limitation | Detail | Disclosed In |
|---|---|---|
| **Mapbox token server-side only** | `MAPBOX_ACCESS_TOKEN` in gitignored `backend/.env`; loaded via python-dotenv; never in frontend, never in logs, never in screenshots. | AGENTS.md, settings.py |
| **Mapbox rate limits** | Free tier limits apply; not tested at scale. Assessment traffic well within limits. | MISSING_INFO.md |
| **Open-Meteo rate limits** | 10k calls/day free tier; assessment traffic negligible. | MISSING_INFO.md |
| **No database persistence** | App is stateless; Django SQLite unused (no migrations). No trip/route/weather data stored. | STATUS.md, TEST_LOG.md |
| **CORS restricted to local ports** | `localhost:5173`, `localhost:5174` allowed. Production would need explicit host list. | settings.py |
| **No HTTPS locally** | Dev servers HTTP; production deployment would require TLS. | AGENTS.md, deployment notes |

---

## 8. Verification Method Limitations

| Limitation | Detail | Disclosed In |
|---|---|---|
| **Playwright MCP extension wedges on clicks** | Navigation, snapshot, fill work; synthesized clicks time out (extension executor throws `M_ID`). **Substituted with script-driven real-Chrome harness** (`frontend/scripts/phaseX-verify.mjs`). Documented in every phase. | TEST_LOG.md, STATUS.md, MISSING_INFO.md |
| **Stale StormRoute CL servers** | Ports 8000/5173 held by foreign session. Our stack runs on 8001/5174. **Never kill foreign processes.** | AGENTS.md, STATUS.md |
| **Live severe weather not captured** | Corridor forecast was calm (all Low). Severe/No Travel rendering proven by unit tests + synthetic matrix, **not a live event**. | TEST_LOG.md Phase 9 |
| **Production preview = local `vite preview`** | Not a hosted deployment. Verified worker chunk + API proxy + burst drag + console clean. Actual hosted deployment is Phase 10 work. | PLAN.md, TEST_LOG.md Phase 10 |
| **Console encoding artifacts** | Em-dash / special chars sometimes mojibake in tool output capture. Wire bytes and app behavior verified correct (E2 80 94 check passed). | MISSING_INFO.md |

---

## 9. Scope Boundaries (What We Do NOT Do)

| Out of Scope | Reason |
|---|---|
| Bridge clearances, axle limits, hazmat restrictions | Not in assessment spec; risk engine does not check vehicle restrictions |
| Real-time traffic / dynamic rerouting | Assessment specifies constant-speed ETA from provider duration |
| Commercial weather licensing | Open-Meteo free tier is non-commercial; assessment is non-commercial |
| User accounts / authentication | Not in assessment spec |
| Multi-language / i18n | Not in assessment spec |
| Offline / PWA support | Not in assessment spec |
| Historical weather analysis | Forecast-only per spec |
| 3D terrain / elevation profile | Not in assessment spec |

---

## 10. Version & Dependency Risks

| Risk | Current Version | Mitigation |
|---|---|---|
| MapLibre GL v6 worker API | 6.15.0 | Worker fix tested dev + prod; pinned in package.json |
| Mapbox Directions API v5 | Current | Mocked in all tests; live probe only for integration |
| Open-Meteo API v1 | Current | Mocked in all tests; live probe only for integration |
| Django 6.1.2 | Pinned in requirements.txt | Security updates monitored |
| React 19 + Vite 8 | Pinned in package.json | No breaking changes observed |

---

## 11. Evidence Traceability

Every limitation above maps to:
- **Code**: Specific file + function (referenced in ARCHITECTURE.md)
- **Tests**: Specific test class/method (e.g., `test_risk.py::CombinedRiskTests`, `heatmap.test.ts::createCoalescedDraw`)
- **UI**: Specific component + copy (e.g., RouteOptions ETA honesty text, ForecastSlider approximation disclosure)
- **Browser verification**: Phase-specific screenshots + `results.json` in `docs/verification/`
- **Live probes**: `backend/scripts/phaseX_live_probe.py` outputs recorded in TEST_LOG.md

---

**End of Limitations Document** — This document is part of the Phase 10 submission package and should be read alongside `README.md`, `ARCHITECTURE.md`, `TEST_LOG.md`, `DECISIONS.md`, and `FINAL_ASSESSMENT_CHECKLIST.md`.