# StormRoute — Assessment Requirement Matrix (Round 8, 2026-10-25)

One row per requirement (R1–R12 = `docs/ASSESSMENT_SPEC.md` §1–§12, verbatim-verified against `docs/fs-assessment-spotter.pdf`). Full narrative: `docs/FINAL_ASSESSMENT_COMPLIANCE_AUDIT.md`.

| ReqID | PDF requirement (faithful summary) | Code location | Test / evidence | Status | Remaining action |
|---|---|---|---|---|---|
| R1 | User enters origin, destination, departure date+time, truck load weight; ordinary-user UI, no coordinates/JSON | `backend/core/serializers.py` · `frontend/src/lib/validation.ts` · `TripForm.tsx` | 27 backend + 27 frontend validation tests; phase-02 browser 16/16 | **PASS** | None |
| R2a | Generate **three distinct route options** via routing API with geometry, distance, travel time, arrival time | `backend/core/services/routing.py:436` | `test_routing.py` (26 tests); live probe `routeCount=2` Chicago→Denver; phase-03 browser 8/8 | **PASS** (honest 1–3; provider gave 2 live) | None |
| R2b | Never fabricate a third route; honest fallback when fewer than 3 return | `routing.py` warning + `duplicatesDropped` | Fewer-than-3 warning tests; phase-03 browser check 4 | **PASS** | None |
| R3 | Checkpoints at 10/25/50 mi; use truck's arrival time per checkpoint; final partial segment + destination | `backend/core/services/checkpoints.py:181` | `test_checkpoints.py` (38); live 42+47 checkpoints; phase-04 browser 9/9 | **PASS** | None |
| R4 | Wind/rain/snow class thresholds with deterministic, documented boundary handling | `backend/core/services/risk.py:236/294/324` | `test_risk.py` L60–84, L172–196, L229–253, BoundaryMatrixTests L686–741; frontend mirror `heatmap.test.ts:197–206` | **PASS** | None |
| R5 | Load rules: ≥55 any load; 45–<55 & >30,000 lb; 35–<45 & >40,000 lb | `risk.py:170–171, 264–291` | `test_risk.py` L94–101, L104/109, L113, L122/127, L131 | **PASS** | None |
| R6 | Consistent combined risk per checkpoint; **No Travel takes precedence** | `risk.py:364` (max-of-conditions, ordinal) | Combined/aggregation tests within `test_risk.py` (67 total) | **PASS** (live-severe demo NOT VERIFIED — calm corridor; unit+synthetic only) | Optional live severe-weather demo |
| R7a | Ranking priority order: fewest Severe mi → fewest High mi → lowest avg risk → shortest time; **not** a weighted sum | `backend/core/services/scoring.py:236` `rank_and_recommend` | `test_scoring.py` LexicographicPriorityTests :132 (incl. weighted-sum reversal proof) | **PASS** | None |
| R7b | A route with a No Travel checkpoint must not be presented as safe | `scoring.py` (exclusion in ranking) | `test_scoring.py` NoTravelExclusionTests :278 | **PASS** | None |
| R7c | All candidates No-Travel → "No safe route found" + explanation | `scoring.py` | `test_scoring.py` AllIneligibleTests :328; ExplanationTests :421 | **PASS** | None |
| R7d | Deterministic ranking incl. full-value ties | `scoring.py:72–81` (tuple-pair `(to_tuple(), route_id)` final tiebreaker — added Round 8) | `test_scoring.py` TieDeterminismTests :217; verified in 224-run | **PASS** (hardened this round) | None |
| R8 | Interactive map: routes, checkpoints, risk levels, ETAs, summaries; heatmap along corridor; **0–48 h** slider on real timestamped data, non-decorative, consistent surfaces | `frontend/src/components/MapViewport.tsx` · `ForecastSlider.tsx` · `lib/heatmap.ts:203,300,371` · `weather_heatmap.py:348` | heatmap tests 47 (frontend 80/80); burst-drag lands last value; hidden-tab fallback; phase-08/09 + `docs/verification/product-quality/` | **PASS** (live-severe rendering NOT VERIFIED — unit+synthetic only) | Optional live severe-weather demo |
| R9 | Deliverables: GitHub repository, hosted application, 5–10 min Loom walkthrough | — (publishing actions) | None possible without user instruction | **BLOCKED (user-gated)** | Push to GitHub · deploy host · record Loom — awaiting explicit instruction |
| R10 | Rubric weighting 40/40/15/5 (builder-side tracking) | `docs/FINAL_ASSESSMENT_COMPLIANCE_AUDIT.md` §17 | Per-bucket evidence table | **PASS** | None |
| R11 | Exclusions: no chatbot/auth/DB/analytics extras; no vehicle-legality or safety-guarantee claims; PDF: "Prioritize correctness and clarity over extra features" | UI copy + docs; Round-8 cleanup | README/DECISIONS audits; UI disclaimers | **PASS** | None |
| R12 | Tech direction: React+TS+Vite+Tailwind; Django+DRF; Python business tests; type check + build + browser E2E | whole repo | Gates: backend 224/224 · frontend 80/80 · build exit 0 (✓ 3.12 s final) · lint 0 errors (2026-10-25) | **PASS** | None |

**Notes**
- **Live severe weather:** Severe/No-Travel classification and rendering are proven by unit tests (`test_risk.py`, `test_scoring.py`, `heatmap.test.ts`) and clearly labeled synthetic fixtures; the live corridor forecast stayed calm, so a real-weather live demo is **NOT VERIFIED** — honestly disclosed, not fabricated.
- **Performance:** ≤25 s target missed (best measured 60.5 s vs 69.5 s baseline, −13%); root-caused to Open-Meteo per-coordinate RTT waves; batching optimization landed after the measurement (audit §16).
- **Git:** local `master` has commits `7e914ea`, `ae00ac8`, `8a590cd`, `97c3552`, `b7b6bc0` + Round-8 changes; **nothing pushed** (R9 gate).
