# StormRoute — Authoritative Assessment Specification

Source: **original assessment PDF** `docs/fs-assessment-spotter.pdf` ("Full Stack Developer — Weather-Aware Truck Routing", Spotter AI assessment; 2 pages, text-extracted and verified verbatim 2026-10-25 against this file — FAITHFUL MATCH). This file is the authority for requirements. Items are marked:

- **[ASSESSMENT]** — stated by the recruiter; must not be changed.
- **[INTERPRETATION]** — our documented reading of an ambiguous point; changes require a `docs/DECISIONS.md` entry.

---

## 1. User inputs — [ASSESSMENT]

The application must let a user enter:

- Origin
- Destination
- Departure date and time
- Truck load weight

The interface must be straightforward for ordinary users: understandable labels, helpful validation messages, sensible defaults where appropriate, clear unit explanations. Users must not need coordinates, JSON, or API knowledge.

**[INTERPRETATION]** The checkpoint interval (10/25/25+/50 mi) is exposed as a user choice in Phase 2; the checkpoint-sampling section says "support 10, 25, or 50 mile intervals", so the app must let the user pick.

## 2. Routing — [ASSESSMENT]

- Generate **three distinct route options** using a routing API.
- Each route contains: geometry, distance, estimated travel time, estimated arrival time, and info needed for weather-risk analysis.
- Third-party routing/geocoding/weather APIs are allowed; a routing engine from scratch is **not** required.
- **Never fabricate** three different routes if the provider returns fewer than three genuinely distinct alternatives; investigate and document an honest fallback.

## 3. Weather checkpoints — [ASSESSMENT]

- Sampling intervals: 10-mile, 25-mile, or 50-mile.
- Use the truck's estimated arrival time at each checkpoint to select the forecast.
- Compute cumulative distances, checkpoint coordinates, and checkpoint arrival times consistently, including the final partial segment and destination.

## 4. Weather classification thresholds — [ASSESSMENT], boundary convention documented

### Wind speed (mph)
| Class | Range |
|---|---|
| Low | < 25 |
| Moderate | 25 – < 35 |
| High | 35 – < 45 |
| Severe | 45 – < 55 |
| No Travel | ≥ 55 |

### Rainfall rate (in/hr)
| Class | Range |
|---|---|
| Low | < 0.10 |
| Moderate | 0.10 – < 0.25 |
| High | 0.25 – < 0.50 |
| Severe | 0.50 – ≤ 1.00 |
| No Travel | > 1.00 |

### Snowfall rate (in/hr)
| Class | Range |
|---|---|
| Low | < 0.5 |
| Moderate | 0.5 – < 1.0 |
| High | 1.0 – < 2.0 |
| Severe | 2.0 – ≤ 3.0 |
| No Travel | > 3.0 |

The recruiter noted the printed ranges overlap at endpoints and required **deterministic boundary handling, explicitly documented** — the conventions above are the mandated resolution.

## 5. Load rules — [ASSESSMENT]

- Wind ≥ 55 mph → **No Travel** for every load.
- Wind 45 ≤ w < 55 mph **and** load > 30,000 lb → **No Travel**.
- Wind 35 ≤ w < 45 mph **and** load > 40,000 lb → **Severe**.

## 6. Combined risk per checkpoint — [ASSESSMENT]

- Where multiple weather conditions occur at one checkpoint, use a consistent overall risk classification.
- **No Travel takes precedence.**

**[INTERPRETATION]** Overall checkpoint risk = max of per-condition classes with No Travel considered highest (No Travel > Severe > High > Moderate > Low). The load rules are applied per condition; e.g. wind 38 mph with 45,000 lb load ⇒ Severe for the wind condition. A No Travel checkpoint blocks "safe" recommendation regardless of other conditions.

## 7. Route recommendation — [ASSESSMENT]

Priority order (unchangeable, deterministic lexicographic comparison):

1. Fewest **Severe-risk** miles
2. Fewest **High-risk** miles
3. Lowest **average risk**
4. Shortest **travel time**

- Do not replace with a weighted score that could reverse the order.
- A route containing a No Travel checkpoint **must not** be presented as a safe recommendation.
- If all three candidates violate No Travel rules → display "No safe route found" and explain why.
- Risk miles from discrete checkpoints are estimates; document the sampling approximation; do not claim continuous road-level certainty.

## 8. Map & visualization — [ASSESSMENT]

- Display all three routes, checkpoints, risk levels, ETAs, and route summaries on an **interactive map**.
- Weather **heatmap along the trip corridor** with a **forecast slider spanning 0–48 hours**.
- Slider must use **actual timestamped forecast data**; map, displayed forecast timestamp, and checkpoint values must stay consistent with the selected hour.
- The slider must not be decorative.

## 9. Deliverables — [ASSESSMENT]

1. GitHub repository
2. Hosted application
3. 5–10 minute Loom walkthrough

Constraints: max 4 calendar days, ≤ 16 working hours. The recruiter email mentioned a **$100 bonus on successful completion** — this is not a job offer or guaranteed payment.

## 10. Assessment weighting — [ASSESSMENT]

| Area | Weight |
|---|---:|
| Routes, weather, risk, recommendation logic | 40% |
| UI, map, heatmap smoothness, performance | 40% |
| Code quality | 15% |
| Documentation & walkthrough | 5% |

## 11. Exclusions — [ASSESSMENT]

- No AI chatbot, authentication system, database (as a product feature), analytics platform, or unrelated features unless genuinely necessary. None are part of the stated requirements.
- Do not claim weather-risk scoring guarantees real-world safety or checks vehicle restrictions (bridge clearances, axle limits) — the spec does not require those capabilities.

## 12. Required technology direction — [ASSESSMENT]

Frontend: React, TypeScript, Vite, Tailwind, accessible reusable components.
Backend: Python, Django, Django REST Framework.
Testing: Python tests for business logic/API behavior; frontend type check + production build; Playwright browser E2E verification.
Deployment provider: decide after feasibility is verified.

**[INTERPRETATION]** Map rendering library is our choice (MapLibre GL, open-source, no key) — decision recorded in `docs/DECISIONS.md`.
