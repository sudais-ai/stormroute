# StormRoute — Ten-Phase Delivery Plan

Time budget: exactly **16 hours**, ≤ **4 calendar days** (Spotter AI assessment). Execution is phase-by-phase on explicit instruction — never batch phases without authorization.

| # | Phase | Budget | Status |
|---|---|---:|---|
| 1 | Project Foundation & API Readiness | 1 h | **in progress** |
| 2 | Trip Input & Validation | 1 h | pending |
| 3 | Three-Route Generation | 2 h | pending |
| 4 | Checkpoint Sampling & ETA Calculation | 1.5 h | pending |
| 5 | Hourly Weather Integration | 2 h | pending |
| 6 | Deterministic Weather Risk Engine | 2 h | pending |
| 7 | Route Scoring & Recommendation | 1 h | pending |
| 8 | Interactive Map & Route Comparison | 2 h | pending |
| 9 | Weather Heatmap & Forecast Slider | 1.5 h | pending |
| 10 | QA, Deployment & Submission | 2 h | pending |

Total: 16.0 h. Statuses are updated only in `docs/STATUS.md` (this table is a mirror).

---

## Phase 1 — Project Foundation & API Readiness (1 h)

**Goal:** trustworthy workspace + project memory + verified dev foundation.

**Tasks:**
- Verify workspace path, inspect existing files, git status; preserve existing work.
- Inspect MCP availability; verify Playwright MCP controls a real browser (navigation, screenshot, console, network).
- Create project-local memory: root `AGENTS.md`, `docs/*` set.
- Research routing/geocoding + weather providers; record in `docs/API_PROVIDER_RESEARCH.md`; set/unset key status only.
- Scaffold `frontend/` (React+TS+Vite+Tailwind) and `backend/` (Django+DRF, `/api/health/`); `.env.example`, `.gitignore`, baseline README stub.
- Verify deps install; `tsc` + `npm run build` pass; Django checks pass.
- Start both servers; Playwright-verify the rendered app; screenshot to `docs/verification/phase-01/`.

**Acceptance criteria (all must actually pass):**
1. Correct project directory confirmed; existing work preserved.
2. All listed memory files exist with real content; consistent with each other.
3. Assessment spec + ten-phase plan recorded in full.
4. MCP connection status documented truthfully incl. any blockers.
5. Playwright browser verification completed for the scaffold.
6. Frontend and backend servers run; actual URLs + endpoint results recorded.
7. Initial checks executed with real outcomes recorded in `TEST_LOG.md`.
8. No secrets exposed; `.env.example` contains placeholder names only.
9. Only Phase 1 work performed.

## Phase 2 — Trip Input & Validation (1 h)

**Goal:** professional trip-input form users can complete without technical knowledge.

**Tasks:** Origin/destination text fields (unit tested labels), date-time picker (`datetime-local`), load-weight numeric field with lb unit note, checkpoint-interval selector (10/25/50 mi), defaults (interval 25 mi, departure = now+1h rounding, weight 34,000 lb), inline validation (required, non-negative, departure within practical bounds), accessible fieldset structure, loading/empty/error UI states defined.
**Deliverable:** validated form; submitted payload visible in dev only as structured request (not fake results).
**Acceptance:** `tsc`+build pass; Playwright: enter values, observe client validation messages for bad input (empty origin, past date, negative weight), console clean; screenshots `phase-02/`; pytest for any form-supporting validation helpers if backend-side validation exists.

## Phase 3 — Three-Route Generation (2 h)

**Tasks:** backend route service: geocode both endpoints (provider adapter), fetch alternatives (≤3), normalize to canonical route model (geometry, distance, duration, ETA, provider metadata + distinctness check), honest handling when provider returns <1/2/3 alternatives (documented fallback, disclosed to user), rate-limit/timeout/error mapping to user-facing messages, tests against deterministic fixtures (clearly labeled), production provider path with real key when set.
**Acceptance:** unit tests pass (fixtures); pipeline runs against live provider when key present, real responses used; any fallback clearly labeled; `tsc`+build pass; Playwright: submit real trip, verify messages for what provider actually returned, console/network clean, screenshots `phase-03/`.
**Dependency:** Phase 2 form; Phase 1 provider research verdict.

## Phase 4 — Checkpoint Sampling & ETA Calculation (1.5 h)

**Tasks:** haversine/polyline interpolation along geometry at chosen interval; cumulative distance axis; final partial segment included; destination always included; ETA per checkpoint = departure + cumulative duration fraction along route (duration-weighted); unit tests incl. round trip, zero-length edge cases; coverage + correctness tests.
**Acceptance:** deterministic tests pass for Python sampling; frontend passes type check; Playwright: sample trip visually noting checkpoint count consistent with route distance / interval; `TEST_LOG` updated.

## Phase 5 — Hourly Weather Integration (2 h)

**Tasks:** weather provider adapter: request hourly forecast series at each checkpoint timestamp; extract **wind speed, rainfall rate, snowfall rate as distinct hourly series** (per `API_PROVIDER_RESEARCH.md` field semantics); forecast timezone normalization; 0–48h window coverage check; per-checkpoint time selection; caching + rate-limit handling; tests with deterministic fixtures; live calls gated by key presence with disclosed state.
**Acceptance:** tests pass; live end-to-end fetch of ≥1 checkpoint weather returns real values when key configured; tests identify fixtures; Playwright-verified next phases using this data.

## Phase 6 — Deterministic Weather Risk Engine (2 h)

**Tasks:** implement exact classification (wind/rain/snow) with mandated boundary conventions, load rules (≥55 No Travel any load; 45–55 + >30,000 lb No Travel; 35–45 + >40,000 lb Severe), combined per-checkpoint risk with No Travel precedence; comprehensive boundary matrix tests (min/max of each band, exact boundary values, each load rule); code kept framework-agnostic for direct unit-testing.
**Acceptance:** `manage.py test` 100% boundary pass including all edge values; spec text ↔ code mapping documented in module docstring.

## Phase 7 — Route Scoring & Recommendation (1 h)

**Tasks:** per route aggregate Severe miles / High miles / average checkpoint risk / duration; lexicographic ranking exactly per spec; No Travel flag propagates to "not safe to recommend"; "No safe route found" path when all candidates contain No Travel; explanation strings per route in plain language; deterministic tests incl. tie cases (equal severe, different high; equal severe+high, different avg; all No Travel).
**Acceptance:** unit tests pass for each tie-break step + No Travel paths; ranking engineering matches spec order precisely.

## Phase 8 — Interactive Map & Route Comparison (2 h)

**Tasks:** MapLibre GL map on frontend; render 3 route lines styled by severity mix; checkpoint markers colored per risk; selected-route state; route-summary cards (distance, duration, ETA, risk-mile breakdown, recommendation explanation); tooltip/detail for checkpoint weather at truck arrival hour; map interactions verified in Playwright (hover, click, selection).
**Acceptance:** build passes; Playwright verifies all three routes render, checkpoint markers clickable, summary switches with route selection, console clean, screenshots `phase-08/` (desktop + mobile width).

## Phase 9 — Weather Heatmap & Forecast Slider (1.5 h)

**Tasks:** heatmap layer along trip corridor driven by real trip forecast series (gridded samples from provider data between checkpoints, disclosed approximation), forecast slider 0–48 h bound to actual timestamped data; slider time selection updates map + checkpoint labels + heatmap consistently; smooth performance (throttled draw) verified; tests for slider mapping functions.
**Acceptance:** Playwright proves slider changes values from real data (not decorative); timestamps displayed; screenshots `phase-09/`.

## Phase 10 — QA, Deployment & Submission (2 h)

**Tasks:** full regression suite (backend tests, frontend build, Playwright end-to-end with screenshots); performance sanity (bundle size, first-load check); docs polish; deployment (provider chosen by then); hosted URL verification; Loom script + recording assistance; final review of all docs vs reality.
**Acceptance:** hosted app reachable; repo clean & appropriate; walkthrough recorded; regression pass recorded; final STATUS updated.
