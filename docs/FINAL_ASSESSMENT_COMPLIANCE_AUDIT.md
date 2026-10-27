# StormRoute — Final Assessment Compliance Audit (Round 8)

- **Date:** 2026-10-25 (fifth session, Round 8)
- **Authority:** `docs/ASSESSMENT_SPEC.md` (verbatim-verified against the original PDF, §2 below)
- **Basis:** repo evidence only — every number below traces to a recorded command, test run, or screenshot in `docs/TEST_LOG.md` / `docs/DECISIONS.md`. Nothing is fabricated; gaps are marked NOT VERIFIED.
- **Companion:** `docs/ASSESSMENT_REQUIREMENT_MATRIX.md` (navigable one-row-per-requirement table).

---

## 1. Executive summary

**Verdict: functionally compliant, evidence-based; submission deliverables are user-gated.**

| Area | Verdict |
|---|---|
| Assessment functionality (R1–R8, R10–R12) | **COMPLIANT** — all specified behavior implemented and test-verified |
| Automated gates (2026-10-25) | Backend **224/224 OK**, Frontend **80/80 PASS**, `tsc` clean, build **exit 0 (✓ 3.12 s final run), lint **0 errors** |
| Known honest misses | Performance ≤25 s target **MISSED** (best measured 60.5 s, −13% vs 69.5 s baseline); live Severe/No-Travel weather **NOT VERIFIED** (unit + synthetic only) |
| Submission deliverables (R9) | **NOT DONE — user-gated**: GitHub push, hosted URL, Loom walkthrough await explicit instruction |

## 2. Assessment PDF — location + inspection evidence

- **Location:** `docs/fs-assessment-spotter.pdf` — now **inside the repo** (copied from the user's disk this session).
- **Inspection:** 2 pages; text extracted **verbatim via pypdf** and compared line-by-line against `docs/ASSESSMENT_SPEC.md` — **FAITHFUL MATCH** (all thresholds, load rules, 4-priority ranking, deliverables, 40/40/15/5 weighting).
- The spec header now cites the PDF as its direct source (updated this session).
- One PDF phrase beyond the structured spec: *"Prioritize correctness and clarity over extra features."* — honored by the Round-8 cleanup (§13).

## 3. Requirements & weighting

Twelve requirement areas R1–R12 (spec §1–§12); rubric weighting **40/40/15/5**:

| Rubric bucket | Weight |
|---|---:|
| Routes, weather, risk, recommendation logic | 40% |
| UI, map, heatmap smoothness, performance | 40% |
| Code quality | 15% |
| Documentation & walkthrough | 5% |

## 4. R1–R12 compliance matrix (full)

Status legend: PASS (tests + code evidence) · PARTIAL · BLOCKED (user-gated) · NOT VERIFIED (aspect). Navigable version: `docs/ASSESSMENT_REQUIREMENT_MATRIX.md`.

| ID | Requirement (spec §) | Status | Evidence (code · tests · browser) |
|---|---|---|---|
| R1 | User inputs (§1) | **PASS** | `core/serializers.py` + `frontend/src/lib/validation.ts` mirrored; 27 backend + 27 frontend validation tests; phase-02 browser 16/16 |
| R2 | Routing — 3 distinct options, honest <3 (§2) | **PASS** | `routing.py:436` `generate_routes`; `test_routing.py` 26 tests; live probe `routeCount=2` (Chicago→Denver); no fabricated third route; phase-03 browser 8/8 |
| R3 | Weather checkpoints 10/25/50 mi, arrival-time forecast (§3) | **PASS** | `checkpoints.py:181` `sample_route_checkpoints`; `test_checkpoints.py` 38 tests; live 42+47 checkpoints; phase-04 browser 9/9 |
| R4 | Classification thresholds + documented boundaries (§4) | **PASS** | `risk.py:236/294/324`; `test_risk.py` L60–84 / L172–196 / L229–253 + BoundaryMatrixTests L686–741; frontend mirror `heatmap.test.ts:197–206` |
| R5 | Load rules (§5) | **PASS** | `risk.py:170–171, 264–291`; `test_risk.py` L94–131 (55-any-load, >30k, >40k, exact 30,000/40,000) |
| R6 | Combined risk, No Travel precedence (§6) | **PASS** | `risk.py:364` max-of-conditions; combined/aggregation tests in `test_risk.py` (67 total). Live-severe demo: **NOT VERIFIED** (calm corridor) |
| R7 | Route recommendation — lexicographic (§7) | **PASS** | `scoring.py:236` `rank_and_recommend`; NEW 24-test `test_scoring.py` (§7 below) |
| R8 | Map, heatmap, 0–48 h slider (§8) | **PASS** | `MapViewport.tsx`, `ForecastSlider.tsx`, `heatmap.ts:203,300,371`; 47 heatmap tests; burst-drag + hidden-tab fallback verified; phase-09 + product-quality screenshots |
| R9 | Deliverables: GitHub / hosted / Loom (§9) | **BLOCKED (user-gated)** | Nothing pushed/published without explicit instruction (§18) |
| R10 | Assessment weighting tracking (§10) | **PASS** | Bucket status with evidence in §17 |
| R11 | Exclusions respected (§11) | **PASS** | No chatbot/auth/DB-product/analytics; no vehicle-legality or safety-guarantee claims anywhere in UI or docs |
| R12 | Technology direction (§12) | **PASS** | React+TS+Vite+Tailwind; Django+DRF; Python business-logic tests; `tsc` + build + browser E2E |

## 5. Weather classification thresholds — exact boundaries

Implementation: `backend/core/services/risk.py` (`classify_wind` :236, `classify_rain` :294, `classify_snow` :324).

| Condition | Class boundaries | Boundary tests (`test_risk.py`) |
|---|---|---|
| Wind (mph) | <25 Low · 25–<35 Moderate · 35–<45 High · 45–<55 Severe · ≥55 No Travel | L60–84 |
| Rain (in/hr) | <0.10 Low · 0.10–<0.25 Moderate · 0.25–<0.50 High · 0.50–≤1.00 Severe · >1.00 No Travel | L172–196 |
| Snow (in/hr) | <0.5 Low · 0.5–<1.0 Moderate · 1.0–<2.0 High · 2.0–≤3.0 Severe · >3.0 No Travel | L229–253 |
| Cross-product matrix | all band combinations | BoundaryMatrixTests L686–741 |

**Documented endpoint convention** (spec §4, mandated deterministic resolution): printed ranges overlap at endpoints; the resolution is **rain Severe ≤1.00 inclusive** and **snow Severe ≤3.0 inclusive** (upper ends), while **wind bands are upper-exclusive** (Severe ends at 55 exactly → No Travel). Frontend render mirror is pinned at `heatmap.test.ts:197–206`.

## 6. Load rules + precedence

Per spec §5, implemented in `risk.py` (threshold constants :170–171) and tested at `test_risk.py`:

| Rule | Boundary tests |
|---|---|
| Wind ≥55 mph → No Travel for **every** load | L94–101 |
| Wind 45–<55 + load **>30,000** lb → No Travel | 30,001 → No Travel (L104/109); **exactly 30,000** → NOT No Travel (L113) |
| Wind 35–<45 + load **>40,000** lb → Severe | 40,001 → Severe (L122/127); **exactly 40,000** → NOT Severe (L131) |

**Precedence (§6):** overall checkpoint risk = **max of per-condition classes**, ordinal No Travel > Severe > High > Moderate > Low (`risk.py:364`; ordinal `NO_TRAVEL = 4` :74). Load rules apply to the wind condition before the max; **No Travel is dominant** — a single No Travel checkpoint blocks a "safe" recommendation regardless of other conditions.

## 7. Scoring — lexicographic priorities (spec §7)

- **Implementation:** `scoring.py` `rank_and_recommend` (:236) compares routes lexicographically: 1) fewest Severe-risk miles, 2) fewest High-risk miles, 3) lowest average risk (ordinal), 4) shortest travel time. **No weighted sum** — the suite includes a proof test that a weighted score would reverse the order the spec fixes.
- **NEW dedicated suite this round:** `backend/core/test_scoring.py` — **24 tests, 10 classes** (existing 200 tests untouched — frozen contract honored):

| Class (line) | Tests | Covers |
|---|---:|---|
| LexicographicPriorityTests (:132) | 5 | priority order incl. not-a-weighted-sum proof |
| TieDeterminismTests (:217) | 3 | full-value ties resolve deterministically |
| NoTravelExclusionTests (:278) | 3 | No-Travel routes never presented as safe |
| AllIneligibleTests (:328) | 1 | "No safe route found" + explanation |
| SingleRouteTests (:368) | 1 | degenerate single-route input |
| FewerThanThreeTests (:387) | 2 | honest 1–2 route ranking |
| ExplanationTests (:421) | 3 | deciding-factor explanations |
| RiskMileMathTests (:557) | 3 | severe/high mile accumulation math |
| PayloadShapeTests (:620) | 1 | response contract shape |
| UnavailableRiskTests (:667) | 2 | missing/unknown risk handling |

- **Tie-determinism hardening (this round):** full-value ties previously depended on input order. Fix: `route_id` added as the **final tiebreaker** via tuple-pair comparison `(to_tuple(), route_id)` in `__lt__`/`__le__` (`scoring.py:72–81`) — stable SHA-derived ids (Phase 3 design) make ties deterministic per spec §7; `__eq__` (:83) unchanged. Verified by the 224-test run.

## 8. Route generation, checkpoints, ETA, timezone

- **Routes:** Mapbox Directions `alternatives=true`; honest 1–3 options — live corridor returns **2**; `routeCount` / `threeRoutesReturned` / `duplicatesDropped` / warning reported; no synthetic padding. Stable `rt_` + SHA-256 route ids. (`routing.py:436`; `test_routing.py` 26 tests.)
- **Checkpoints:** haversine (mean Earth radius 6,371,008.8 m) along provider geometry by **traveled distance**; interval ∈ {10, 25, 50}; cap 500 with widening (never truncation); origin = checkpoint 1, destination appended as final partial segment; `interpolated` flag distinguishes provider vertices. (`checkpoints.py:181`; 38 tests; live 42+47 at 25 mi.)
- **ETA:** `departureUTC + providerDurationSeconds × (cumulative distance ÷ geometry length)` — constant-average-speed, distance-weighted; explicitly **not** traffic/weather-aware (disclosed in API labels + UI copy).
- **Timezone:** request departure accepted only with explicit UTC offset, normalized to UTC; naive timestamps rejected; all arrivals UTC ISO-8601.
- **Honest geometry note:** overview-geometry haversine length ≠ provider distance (live: 1,001.9 vs 1,003.1 mi); both returned, difference disclosed, never reconciled away.

## 9. Weather source, units, freshness, missing data

- **Provider:** Open-Meteo Forecast API (no key; CC BY 4.0, non-commercial free tier). Hourly `wind_speed_10m` (mph), `rain`, `snowfall` (inches); `precipitation_unit=inch`, `wind_speed_unit=mph`, `timezone=UTC`, `forecast_days=3` → **~72 h**, covering the 48 h slider.
- **Matching:** checkpoint arrival truncated to the hour; **exact match** against the provider hourly array — no interpolation, no nearest-hour fallback; miss → `timeMatch: "out_of_horizon"`. (`weather.py:389`.)
- **Freshness/efficiency:** shared corridor fetch — one fetch per unique coordinate across checkpoints + heatmap grid (`weather.py:344`); heatmap grid holds 49 hourly buckets (0–48 h) per point (`weather_heatmap.py:348`).
- **Missing data:** per-coordinate failures → `null`/unknown values; batch failure → points dropped; **heatmap failure never breaks the route response** (degrades to `heatmaps: []`). Unknown weather/risk never renders as safe (own legend level).

## 10. Map, checkpoint markers, heatmap, slider

- **MapLibre worker fix (root cause):** `vite.config.ts:35–36` `optimizeDeps.exclude: ['maplibre-gl']` + explicit `?url` worker import — 0 console errors in dev **and** production.
- **Coalesced drawing:** `createCoalescedDraw` (`heatmap.ts:371`) — one draw per rAF, **per-enqueue visibility check**; hidden tabs fall back to 16 ms `setTimeout` (Chrome pauses rAF when hidden).
- **Burst test:** rapid drag `[0…48]` lands on the **LAST** value consistently across slider label, heatmap, and all 89 checkpoint markers (phase-09 + product-quality rounds).
- **Stable-container fix:** map container div never swapped after load (loading state is an overlay) — detached-canvas bug found and fixed 2026-10-25.
- **Honesty surfaces:** legend includes Unknown; hover tooltip shows per-checkpoint value at the selected hour; approximation disclosure ("gridded corridor samples, not road-level certainty").

## 11. UI palette & contrast (Round-6 light theme)

- Light tokens: body `#FAFAF9`, cards/panels `#FFFFFF`, border `#E5E7EB`, text `#1A1A1A`, accent `#2563EB` (`index.css`).
- **Frozen risk hexes** (single source `heatmap.ts:300–307`): low `#22c55e`, moderate `#f59e0b`, high `#f97316`, severe `#ef4444`, no_travel `#dc2626`, unknown `#64748b` — unchanged across the theme flip.
- Basemap: Carto **Positron** (light). Contrast history recorded honestly: Round-6 QA passed 5/16 of the spot checks at code level; the 11 failures (muted text `#9CA3AF` 2.54:1, placeholder 2.43:1, six risk-badge text hues 1.94–4.06:1 on their tints, Rank `#` signal chip 1.99:1, unselected route line `#D1D5DB` 1.41:1) were **fixed in Round 8** via AA text tokens (`#6B7280` muted; darker `--color-risk-text-*` badge text over the same frozen-hue 13% tints; `--color-signal-text #92400E`; route line/border `#6B7280`) and **live re-verified 16/16 AA PASS** (helper/placeholder 4.63:1, badges 5.47–6.79:1, chip 6.41:1; screenshots 24–28; console 0 errors). Dots/legend/heatmap corridor keep the pinned full hues.

## 12. Responsive + accessibility

- Mobile stacking order via classes (map sidebar `order-1`, results band `order-2` under `lg`); verified at 420 px and 480×800 with zero horizontal overflow.
- Field errors `role="alert"`; pending line `role="status"`; live-region semantics on dynamic results; route pills `aria-pressed`; interval radios keyboard-focusable with `focus-visible` styling.
- Skip link + labeled inputs (phase-01/02 browser checks).

## 13. Bugs found + fixed THIS round (Round 8)

1. **Scoring zero-coverage gap** — ranking logic had no dedicated test file → NEW `test_scoring.py`, 24 tests (§7); the 200 existing tests were not touched (frozen-contract discipline).
2. **Tie determinism hardening** — routeId final tiebreaker via tuple-pair in `__lt__`/`__le__` (`scoring.py:72–81`); spec §7 determinism no longer input-order-dependent.
3. **Client-delivery cleanup** (honor "correctness and clarity over extra features"): internal-only docs and dead code removed from git — see `docs/TEST_LOG.md` (fifth-session entry) for the full list; `README.md` polished client-ready; `.gitignore` updated; `ASSESSMENT_SPEC.md` header now cites the PDF.
4. **WCAG AA contrast fix-loop** — browser-qa computed-contrast audit found 11 AA failures (5/16 pass); token-level fix (AA badge-text/muted/signal/route-line values over frozen tints and hexes) re-verified live **16/16 PASS** with the full flow re-run (§11, TEST_LOG fifth-session contrast block).

## 14. Test results — exact commands + counts (run 2026-10-25)

| Gate | Command | Exact result |
|---|---|---|
| Backend | `manage.py test` | **Ran 224 tests in 1.460s — OK** (200 prior + 24 NEW scoring tests) |
| Frontend tests | `npm run test` | **Test Files 3 passed (3) / Tests 80 passed (80)** (TripForm 18 + validation 15 + heatmap 47) |
| Production build | `npm run build` | **exit 0 — ✓ built in 3.12s** (final run after the contrast fix; 1.80s post-cleanup pre-fix run also green) |
| Lint | `npm run lint` | **0 errors**, 5 historic warnings (unchanged set) |

Full per-phase history with every command: `docs/TEST_LOG.md`.

## 15. Browser evidence paths

- `docs/verification/phase-01/` … `phase-10/` — per-phase screenshots + `results.json` (methods disclosed; Playwright MCP click-wedge → script-driven real-Chrome harness substitution recorded each time).
- `docs/verification/product-quality/` — Round-2/3/6 UI evidence; light-theme set **product-quality-21…23** (light chrome, light map, results cards). At docs time the directory holds screenshots 01–17 and 21–23 (slots 18–20 empty); Round-8 browser-qa may append further files — this report references the **directory**, not unverified specific new files.

## 16. Performance, security, production build

- **Performance (honest):** ≤25 s target **MISSED**. Best measured **60.5 s** vs **69.5 s** baseline (**−13%**). Measured root cause: Open-Meteo per-coordinate RTT waves (190 unique coords ÷ 4 workers ≈ 48 waves × ~1.05 s). The multi-location batching optimization landed **after** the measurement — not yet re-measured. No number fabricated; the miss stands.
- **Security:** Mapbox token server-side only (gitignored `backend/.env`; `.gitignore:14–15` covers `.env`/`.env.*`); no `VITE_*` secret exposure; provider text/URLs (which carry the token) never echoed — test-pinned no-token-in-response assertions; no secrets in docs/logs/screenshots.
- **Production build:** `npm run build` exit 0 (✓ 3.12 s final run after the contrast fix; earlier green runs 1.80 s post-cleanup); MapLibre worker emitted as a real asset; preview proxy verified earlier (phase-09/10).

## 17. Rubric status per bucket (40/40/15/5)

| Bucket | Status | Evidence |
|---|---|---|
| Routes/weather/risk/recommendation (40%) | **PASS** | R2–R7 above; 224 backend tests incl. 67 risk + 24 scoring; live probes for routes/checkpoints/weather |
| UI/map/heatmap/performance (40%) | **PASS with disclosed miss** | 80 frontend tests; burst + hidden-tab fallback; worker fix; WCAG AA live **16/16** after Round-8 fix (§11); perf ≤25 s target honestly missed (§16) |
| Code quality (15%) | **PASS** | `tsc` clean; lint 0 errors; typed API contracts; pure deterministic services; frozen-test discipline |
| Documentation & walkthrough (5%) | **PARTIAL** | Docs comprehensive and current (README, spec, matrix, audit, test log, decisions); **Loom NOT DONE** — user-gated (§18) |

## 18. GitHub / hosting / Loom — NOT DONE (user-gated)

- **GitHub push:** not performed — publishing requires explicit user instruction. Local `master` holds commits `7e914ea`, `ae00ac8`, `8a590cd`, `97c3552`, `b7b6bc0` plus Round-8 staged/unstaged changes; **no push**.
- **Hosted application:** not deployed (same gate).
- **Loom walkthrough:** not recorded (same gate).

## 19. Limitations & ambiguities (documented, honest)

1. **Endpoint overlap convention** — rain/snow Severe upper ends inclusive, wind upper-exclusive (§5); mandated by the spec's own demand for documented deterministic handling.
2. **Sampling approximation** — risk miles come from discrete checkpoints (interval 10/25/50 mi) and the ~11 km heatmap grid; presented as estimates, never road-level certainty (spec §7 requires this disclosure).
3. **Live-calm data** — the live corridor forecast stayed calm; Severe/No-Travel rendering is proven by unit + synthetic tests only, **never** demonstrated in real severe weather (**NOT VERIFIED** live).
4. ETA = constant-average-speed estimate; no traffic/stops/per-leg durations.
5. Geometry-span display rounds to 1,000-mi buckets (frozen-test literal "0 mi to 1,000 mi", `TripForm.test.tsx:331`); live spans <500 mi read "0 mi to 0 mi" (code comment `RouteOptions.tsx:126–128`).
6. Open-Meteo free tier is non-commercial (CC BY 4.0) — assessment use qualifies; commercial use would require revisiting.
7. 91,000 lb loads are accepted end-to-end — the spec disclaims vehicle-legality checks (no bridge/axle limits claimed).

## 20. Remaining gaps (with severity)

| Gap | Severity | Note |
|---|---|---|
| R9 deliverables: push / hosting / Loom | **HIGH** | User-gated; blocking submission only |
| Performance ≤25 s target missed (60.5 s best) | **MEDIUM** | Root-caused; batching landed post-measurement, re-measure pending |
| Live Severe/No-Travel demo | **MEDIUM** | Unit + synthetic proven; live event never observed (**NOT VERIFIED**) |
| Never-settling-fetch residual | LOW | Proper fix `AbortSignal.timeout` in `api/trips.ts` (future item); defensive catch already renders honest copy |
| Geometry-span display <500 mi | LOW | Frozen-test owner decision pending |
| 91,000 lb accepted | LOW | Spec-consistent; sanity cap is a product decision for the user |
| Playwright MCP click wedge | LOW | Script-driven real-Chrome fallback used and disclosed every round |

## 21. Final readiness

- **Assessment code: READY** — all R1–R8/R10–R12 functionality implemented, tested (224 backend + 80 frontend, build/lint clean), browser-verified, honestly documented.
- **Submission deliverables: PENDING USER ACTION** — GitHub push, hosted URL, and Loom walkthrough await explicit instruction; nothing has been published.
