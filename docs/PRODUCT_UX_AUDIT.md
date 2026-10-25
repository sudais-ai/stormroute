# StormRoute — Product UX Audit

**Date:** 2026-10-24  
**Scope:** Complete inspection of the running application, codebase, and data flow against the assessment specification and real user expectations.

---

## Executive Summary

StormRoute Phases 1–9 are functionally complete and verified. All 12 assessment requirements are implemented with automated tests (200 backend + 80 frontend), browser verification (91 checks), and live provider integration. However, the **frontend user experience has significant usability gaps** that prevent an ordinary truck driver or trip planner from confidently understanding and acting on the results.

**Core problem:** The application presents correct data but in a format that requires technical knowledge to interpret. An ordinary user cannot easily answer: "Which route should I take? Why? Where are the real weather concerns?"

---

## Usability Audit Findings

### 1. Trip Input Form — Clear but Verbose

| Issue | Impact | Fix Priority |
|-------|--------|--------------|
| "Plan a trip" heading + 3 paragraphs of technical explanation before the form | User must read before acting; obscures the primary action | High |
| Load weight hint "Cargo weight in pounds; 0 lb is valid for empty cargo" is helpful but passive | Minor | Low |
| "Converted to your browser's timezone before sending" — user doesn't need to know this | Unnecessary cognitive load | Medium |
| No immediate validation feedback until submit | Users don't know if fields are valid as they type | High |
| "Weather checkpoint interval" label uses internal terminology ("weather checkpoint") | Confusing for ordinary users | High |
| Radio buttons lack visual distinction between selected/unselected | Hard to see current choice | Medium |
| Form doesn't show character limits or format hints for origin/destination | Users guess format | Medium |

### 2. Route Results — Overwhelming & Technical

| Issue | Impact | Fix Priority |
|-------|--------|--------------|
| **No clear "recommended route" at top** — user must scroll to find recommendation section | Critical decision buried | Critical |
| Route cards use neutral "Route 1"/"Route 2" labels with no visual distinction for recommended | User cannot identify the best option at a glance | Critical |
| Risk summary tables use internal terminology: "Severe miles (est.)", "Avg risk ordinal", "riskOrdinal" | Requires domain knowledge | High |
| "Severe miles (est.) 0.0 mi" — "est." abbreviation and decimal for zero miles | Confusing, looks like system output | Medium |
| Weather per checkpoint shows 42 rows for Route 1 — unscannable wall of data | User cannot find concerns | Critical |
| "timeMatch: exact" / "provider error" — internal status codes exposed | Not user-facing language | High |
| Duplicate disclaimer text appears twice (with/without warning) | Visual clutter | Low |
| Checkpoint risk detail shows factors like "wind 6.7 mph in [25, 35) → Moderate" | Internal logic exposed | High |

### 3. Map & Heatmap — Functional but Not Guiding

| Issue | Impact | Fix Priority |
|-------|--------|--------------|
| Map legend shows 7 risk levels but no context — user doesn't know what "No Travel" means practically | No actionable guidance | High |
| Heatmap legend footnote "Corridor circles = gridded samples at the slider hour (+N h)" uses technical language | Not user-friendly | Medium |
| Hover tooltip shows "At +40 h · 2026-10-25T16:00 UTC · Low · Wind: 5.1 mph" — ISO timestamp, no context | Hard to interpret | High |
| No visual indicator for "this is the forecast time slider controls" | Slider purpose unclear | Medium |
| Checkpoint markers are dense (89 total) with no clustering — hard to click individual | Frustrating interaction | Medium |
| Route lines use severity colors but legend doesn't explain the mapping | Confusing color coding | Medium |

### 4. Forecast Slider — Functional but Ambiguous

| Issue | Impact | Fix Priority |
|-------|--------|--------------|
| Label "+24 h · Oct 25, 2026 · 00:00 UTC" — mixes relative and absolute, UTC confusing | User doesn't know what time it means for them | High |
| Tick labels "now", "+12h", "+24h", "+36h", "+48h" — no date context for future hours | Can't plan around specific dates | Medium |
| "Moving the slider re-colors the ~11 km corridor grid..." — technical disclosure in UI | Not user-facing | Medium |
| No visual feedback when slider changes map/heatmap | User doesn't know if action worked | Medium |

### 4.5. Trip Form Submission & Loading State — Broken

| Issue | Impact | Fix Priority |
|-------|--------|--------------|
| **Form submission doesn't reliably show results** — route cards don't appear after submit | Core workflow broken | Critical |
| No visible loading indicator during the 60-75s API call | User thinks nothing happened | Critical |
| No error handling visible for failed API calls | Silent failures | Critical |
| Form values preserved but no way to edit/resubmit after failure | Frustrating | High |

### 5. Recommendation Section — Correct Logic, Poor Presentation

| Issue | Impact | Fix Priority |
|-------|--------|--------------|
| Recommended route shown in a list with others, not prominently | User can't identify the answer | Critical |
| Explanation text "fewest severe-risk miles" — internal terminology | Not plain English | High |
| No Travel routes shown with red badge but still in ranking list | Confusing — looks like an option | High |
| "No safe route found" state works but not tested in UI | Unknown if user-facing | Medium |

### 6. Information Architecture — Redundancy & Clutter

| Issue | Impact | Fix Priority |
|-------|--------|--------------|
| Runtime status panel always visible — not actionable | Wastes screen space | Low |
| "What comes after validation" panel shows future phases — irrelevant to current user | Distracting | Low |
| Disclaimer text duplicated (2 versions for with/without warning) | Code smell + visual noise | Low |
| Phase badges ("Phase 6", "Phase 7") in sidebar — internal process, not user info | Confusing | Low |
| Footer disclaimer about "not guaranteed safety" appears on every page | Appropriate but could be shorter | Low |

---

## Correctness & Data Flow Audit

### Verified Correct (✅)
- Coordinate order: `[longitude, latitude]` preserved from Mapbox throughout
- Haversine distance calculation: R = 6,371,008.8 m, segment interpolation correct
- Checkpoint ETA: `departureUTC + providerDuration × (cumulativeDist / geometryLength)`
- Weather matching: exact-hour truncation, no interpolation, out-of-horizon handled
- Risk classification: boundary conventions exactly per spec (inclusive lower, exclusive upper)
- Load rules: No Travel ≥55 mph any load; 45–55 + >30k lb = No Travel; 35–45 + >40k lb = Severe
- Combined risk: max per condition with No Travel precedence
- Lexicographic ranking: severe mi → high mi → avg risk → duration
- No Travel gate: routes with No Travel checkpoints never recommended
- Heatmap: ~11km grid, cross-route dedup, 49 hourly buckets, null-safe
- MapLibre worker: fixed via `optimizeDeps.exclude` + `?url` import

### Issues Found / Fixed in Inspection (🔧)

| Issue | Location | Status |
|-------|----------|--------|
| `riskSummaries` duplicate key in `routing.py` response | `routing.py:591-592` | Fixed in Phase 9 |
| Trip form submission not showing results in live test | `TripForm.tsx` → `generateRoutesOnBackend` | **Investigating** |
| Loading state not visible during 60-75s API call | `TripForm.tsx` | **Investigating** |
| `MapViewport` hover tooltip shows ISO timestamp without context | `MapViewport.tsx` | Documented |
| Heatmap legend footnote technical language | `MapViewport.tsx` | Documented |

---

## Planned Fixes (Implementation Priority)

### Phase A — Critical Path (Must Fix)

1. **Fix trip form submission & loading state** — Ensure `generateRoutesOnBackend` returns data, show spinner, handle errors visibly
2. **Add prominent "Recommended Route" card at top of results** — Visual hierarchy: recommendation first, alternatives below
3. **Redesign route cards for decision-making** — Distance, time, risk badge, one-line explanation; move detailed tables to accordion
4. **Simplify trip form** — Remove technical copy, add inline validation, clearer labels
5. **Make forecast slider label user-friendly** — "Forecast for Oct 25, 12:00 PM local" not "+24 h · 2026-10-25T00:00 UTC"

### Phase B — High Impact (Should Fix)

6. **Consolidate weather display** — Show only checkpoints with risk ≥ Moderate; "All checkpoints Low" summary for calm routes
6. **Improve map legend & tooltips** — Plain English risk meanings; local time in tooltips
7. **Add checkpoint clustering on map** — Reduce marker density
8. **Slider label with local time** — Convert UTC to user's timezone for display
9. **Remove internal terminology from UI** — "riskOrdinal", "timeMatch", "forecastStartISO" → plain English

### Phase C — Polish (Nice to Have)

10. **Add React error boundary** — Graceful degradation
11. **Mobile layout refinements** — Stack cards, collapsible map
12. **Accessibility audit** — Focus states, ARIA labels, color+text risk indicators
13. **Error boundary + retry UX** — Network failure → "Try again" button

---

## Audit Methodology

- **Live browser inspection:** Playwright MCP in Chrome (dev server 5174 + prod preview 4175)
- **Code inspection:** All frontend components, backend services, types, API contracts
- **Data flow trace:** User input → validation → geocode → directions → checkpoints → weather → risk → scoring → recommendation → map/heatmap
- **Test evidence:** 200 backend tests, 80 frontend tests, 91 browser checks, 44+ screenshots
- **Specification compliance:** Checked against `ASSESSMENT_SPEC.md` requirements 1–12

---

## Next Steps

1. **Create `docs/PRODUCT_UX_AUDIT.md`** (this document) — Done
2. **Implement Phase A fixes** — Critical path
3. **Run regression tests** — Backend 200, Frontend 80, TypeScript, Build
4. **Browser verify fixed workflow** — End-to-end with screenshots
5. **Update documentation** — `STATUS.md`, `TEST_LOG.md`, `DECISIONS.md`, `LIMITATIONS.md`
6. **Final report** — Ready for Phase 10 submission preparation

---

## Resolution status (2026-10-25 — what is now real, appended; original findings above preserved)

**Truth note:** this audit was written 2026-10-24 against the pre-overhaul UI. The overhaul it proposed became actual code on 2026-10-25 and was verified in the browser (evidence: `docs/TEST_LOG.md` 2026-10-25 entry; screenshots in `docs/verification/product-quality/`).

| Audit item | Status 2026-10-25 |
|---|---|
| 4.5 Trip form submission / loading state broken (Critical) | **FIXED + VERIFIED** — pending state ("Finding routes…", disabled, `aria-busy`), visible error handling (`role`-block copy incl. "backend is not responding"), proxy timeout 120 s; real ~85 s pipeline completes with results |
| No clear recommended route at top (Critical) | **PARTIALLY DONE** — ranked recommendation with `Rank #N` + single "Recommended" chip renders directly under the route cards (in-flow, not a separate hero banner; App-side pills mark the recommended route with ★) |
| Route cards with internal terminology / wall-of-42-rows (Critical/High) | **IMPROVED** — per-checkpoint weather rows moved inside collapsed native `<details>` ("Show checkpoint weather & risk"); summary chips use plain risk labels; `timeMatch`-style internals not shown in cards |
| Simplify trip form copy (High) | **DONE as designed** — one-line helper texts; interval hint in plain language; departure hint explains local-time handling without timezone jargon |
| Slider label user-friendly (High) | **DONE** — locale wall-clock + `+N h from forecast start` chip; honest offset semantics; testids stable |
| Map legend & tooltip clarity (High) | **IMPROVED** — plain-English legend ("No Travel — park it", "No data") + footnote "Dots = corridor forecast samples, not road-level certainty."; tooltip shows arrival + arrival-hour risk |
| Consolidated "risk ≥ Moderate" waypoint summary (B) | **NOT DONE** (deferred; route cards keep full checkpoint list in `<details>`) |
| Checkpoint clustering (B) | **NOT DONE** (deferred) |
| React error boundary / retry UX (C) | **NOT DONE** (deferred) |
| Type-as-you-go inline validation (A in finding #1) | **NOT DONE** (validation on submit only — matches the frozen test contract) |

**Method note:** the original methodology line below mentions prod preview on 4175; on 2026-10-25 the preview smoke ran on **4179** (4175 was held by an unrelated process; verified + screenshot evidence in the test log).