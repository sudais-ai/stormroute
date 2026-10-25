# StormRoute — API Provider Research

Researched: 2026-10-23 (Phase 1). Sources: official provider docs/pages (links inline). Status per item: **[confirmed]** from fetched documentation, **[pending]** needs live verification with credentials in Phases 3/5.

---

## Decision summary

| Concern | Provider | Key required? | Why |
|---|---|---|---|
| Route generation (3 alternatives) | **Mapbox Directions API** | Yes — access token (free tier) | `alternatives=true` returns up to 3 routes total (docs: "up to two alternatives"); professional driving profile; documented distance/duration/geometry fields |
| Geocoding (origin/destination → coords) | **Mapbox Geocoding API (Temporary)** | Same token | Same ecosystem, free tier sufficient, one credential to manage |
| Hourly weather (wind/rain/snow rates) | **Open-Meteo Forecast API** — *pending final confirmation before Phase 5* | **No key** — free tier covers **non-commercial use only** (10,000 calls/day) | Separate hourly `wind_speed_10m`, `rain`, `snowfall` series; units directly requestable (mph, inch); timezone support; covers 0–48h+ easily |
| Map tiles for MapLibre GL | **OpenFreeMap** (public instance) | **No** — no cap, attribution auto-added by MapLibre | Zero-cost vector tiles, no key infrastructure |

## 1. Mapbox Directions API — [confirmed] capability, [pending] live data

- Docs: https://docs.mapbox.com/api/navigation/directions/
- **Alternatives:** `alternatives=true` → "Up to two alternatives may be returned … such a route does not exist in all circumstances." ⇒ provider returns **at most 3 routes, at least 1**; NOT guaranteed 3. Assessment explicitly forbids fabricating a third route → app must honestly display whatever is returned and explain the limitation (fallback decision recorded in DECISIONS).
- **Response fields:** route `distance` (meters), `duration` (seconds), `geometry` (polyline by default; `geometries=geojson` supported; `overview=full/simplified`).
- **Driving profile:** `mapbox/driving` (and `mapbox/driving-traffic`). Alternatives supported on driving profiles.
- **Base URL pattern (v5):** `https://api.mapbox.com/directions/v5/mapbox/driving/{lon};{lat};{lon};{lat}`
- **Auth:** `access_token` query/session token.
- **Pricing/limits [confirmed from docs 2026-10-23; noted discrepancy]:**
  - Without a payment method (trial): **Directions API 10,000 requests/month**; Temporary Geocoding 10,000/month (docs.mapbox.com/accounts/guides/signup — limits table).
  - Product pages reference standard free tiers (≈100,000/month for Geocoding per mapbox.com/geocoding), with trial limits lower before a card is added. Fine for an assessment consuming a few requests per trip.
  - Conclusion: no cost risk for this project under any listed scheme.

## 2. Mapbox Geocoding API — [confirmed] capability

- Docs: https://docs.mapbox.com/api/search/geocoding/ · Product/pricing: https://www.mapbox.com/geocoding
- Forward geocoding `q=` → coordinates; ideal for "origin/destination" free-text entry; language/limit params available.
- **Terminology:** use the *Temporary* endpoint (results not stored) — Permanent Geocoding has no free tier and our use case does not store results.

## 3. Open-Meteo Forecast API — [confirmed] capability (fetched official docs + OpenAPI spec)

- Docs: https://open-meteo.com/en/docs · License: CC BY 4.0 (attribution required) · "No API key, no sign-up, no credit card. Non-commercial use up to 10,000 daily API calls is free."
- **Endpoint:** `GET https://api.open-meteo.com/v1/forecast` with `latitude`, `longitude`, `hourly`, optional `wind_speed_unit=mph`, `temperature_unit=..., precipitation_unit=inch`, `timezone=<tz name or auto>`, `forecast_days≤16`, `forecast_hours` supported for windows.
- **Hourly variables relevant to the spec [confirmed]:**
  - `wind_speed_10m` — instant wind speed at 10 m; unit km/h or **mph** on request (standard reference level).
  - `wind_gusts_10m` — gusts, preceding-hour max (available; not required by spec).
  - `rain` — "Rain from large scale weather systems of the **preceding hour** in millimeter" — with `precipitation_unit=inch` returned in inches → **in/hr rate semantics** (accumulation per hour = hourly rate).
  - `showers` — convective precipitation preceding hour, mm.
  - `snowfall` — "Snowfall amount of the preceding hour in centimeters … For the water equivalent in millimeter, divide by 7" — with inches unit → **in/hr rate semantics**.
  - `precipitation` — total precip (rain+showers+snow water-equivalent) preceding hour; useful cross-check, NOT a substitute for `rain`/`snowfall`.
  - `precipitation_probability` — **percentage probability, preceding hour — explicitly NOT used as a rate** (recorded to satisfy the spec's "do not silently interpret probability as a rate" requirement).
- **Coverage:** hourly series starts 00:00 today local; 168 h by default; `forecast_days=3..4` comfortably covers the required 0–48 h slider (use `forecast_days=4` for margin; `past_days` not needed for forward trips).
- **Timezone:** `timezone=auto` + `utc_offset_seconds` returned; per-checkpoint times will be normalized in backend (Phase 5).
- **Semantics caveat to implement:** Open-Meteo gives accumulation *per preceding hour*, which we treat as the hourly rate at that hour index. This is the provider's rate representation — documented here per the spec's honesty requirement.

## 4. OpenFreeMap tiles — [confirmed] from official site

- https://openfreemap.org/ · style: `https://tiles.openfreemap.org/styles/liberty` · MapLibre GL quick-start documented.
- Public instance: free, no registration, no API keys, no cookies, no view/request caps; commercial use allowed; attribution required (MapLibre adds it automatically). Data © OpenMapTiles / OpenStreetMap.
- Fits MapLibre GL decision (Phase 8) with zero key management.

## 5. Alternatives considered & not selected

| Provider | Verdict | Reason |
|---|---|---|
| OSRM public demo (`router.project-osrm.org`) | rejected | Rates-limited community server, explicitly unsuitable for production hosted use |
| Google Directions Platform | rejected | Billing account required up front; most expensive risk profile for a 4-day assessment |
| TomTom | not selected | Works but small free tier less generous; Mapbox ecosystem cohesion preferred |
| OpenWeatherMap / Tomorrow.io / Met Office | rejected | Keys + free-tier throttles; rain "rate" often not a distinct hourly field (often 3-hour totals or probabilities) — Open-Meteo's explicit hourly `rain`/`snowfall` fields are cleaner vs spec |

## 5a. WeatherAPI.com — evaluated alternative [confirmed from official docs 2026-10-24]

- Docs: https://www.weatherapi.com/docs/forecast-api/ · Pricing: https://www.weatherapi.com/pricing
- **Hourly `hour` element fields (from official field table):**
  - `wind_mph` — hourly wind speed in mph ✓ (imperial unit natively)
  - `precip_mm` / `precip_in` — **"Precipitation amount"** (total precipitation; NOT marked as rain-only) — ⚠ **no separate hourly rain-rate field exists**
  - `snow_cm` — hourly snowfall amount in cm ✓ (separate field)
  - `chance_of_rain` / `chance_of_snow` — **percentage probability** — must NOT be used as a rate
  - `will_it_rain` / `will_it_snow` — 0/1 flags
- **Spec fit:** the assessment requires rainfall rate **separately** from snowfall rate. WeatherAPI.com has no distinct hourly rain rate — deriving rain-only intensity from combined `precip_in` minus snow water-equivalent would be an unverified derivation. Materially weaker fit than Open-Meteo's explicit `rain` hourly field.
- **Free plan limits [confirmed from pricing page]:** 100K calls/month but **forecast horizon only 3 days** on Free; **commercial use NOT permitted** on Free (paid plans for commercial). Paid: Starter $7/mo (7-day forecast, 3M calls).
- **Attribution requirements:** not confirmed from fetched docs — would need verification from their ToS if this provider is ever selected.
- **Verdict:** documented fallback only. If Phase 5 live integration with Open-Meteo hits contract obstacles, revisit with a WeatherAPI.com key (its exact semantics live-tested).

## 5b. Open-Meteo licensing honesty note [corrected 2026-10-24]

- Free tier (10,000 calls/day, no key) applies to **non-commercial use only** with CC BY 4.0 attribution. It is **not** unrestricted for commercial use; a commercial hosted product would require their commercial terms/plan.
- StormRoute as an assessment/demonstration build qualifies as non-commercial. If the app is later used commercially for any real service, revisit licensing or the WeatherAPI.com/paid-plan path.
- Redemption note (per spec honesty requirements): `precipitation` (total) and `precipitation_probability` are NEVER used as the rainfall/snowfall rate; `rain` and `snowfall` hourly fields are the specified sources.

## 6. Unverified assumptions (to verify when integrating)

- [pending] Mapbox alternatives behavior on a real corridor (do we actually get 3 distinct routes for typical long-haul pairs?) — verify in Phase 3 with live calls.
- [pending] Open-Meteo hourly `rain`/`snowfall` value ranges in practice for rate classes (e.g. does model output produce mm-scale hourly rain?) — verify with fixture + live samples in Phase 5.
- [pending] Mapbox trial-token rate limits in practice (within 10k/month plan) — fine.
- Attribution strings for Open-Meteo must appear in the app footer (CC BY 4.0); attribution for OpenFreeMap auto via MapLibre.

## 7. Phase 3 verification updates [confirmed 2026-10-24]

- [resolved] Mapbox alternatives on a real corridor: Chicago→Denver under `alternatives=true` returned **2 distinct real routes** (I-80/I-76 and I-80/I-70), NOT three; per-run variation possible (an earlier probe run also showed a different alternative pair). StormRoute therefore treats "up to three requested" as a **request** that Mapbox may or may not honor and surfaces the honest counts (`routeCount`, `threeRoutesReturned`, warning text). No synthetic third route will ever be injected.
- [resolved] Directions response payload is large in practice (full `overview=full` geometry → 516 KB JSON for Chicago→Denver). No simplification was performed in Phase 3, preserving exact Phase 4 input.
- [resolved — Phase 4, 2026-10-24] Phase 4 also does **not** modify, simplify, or decimate the provider geometry: checkpoint sampling reads it once in memory and returns new checkpoint objects; `geometry`, `distanceMeters`, and `durationSeconds` remain exactly as Phase 3 produced them. Checkpoint travel distance is measured with haversine along those vertices, so the geometry length can differ slightly from Mapbox's reported route distance (live 1,001.9 vs 1,003.1 mi; 1,128.0 vs 1,129.3 mi). Both values are exposed (`geometryDistanceMeters` vs `providerDistanceMeters`); the provider number is never rewritten. ETA uses the provider route-level duration only (no per-leg duration is present in this response), distributed by distance — see `docs/DECISIONS.md` Phase 4 entry.
- [resolved] Mapbox Geocoding filters directly support fuzzy nonsense matching — nonsense strings still geocode to real places (verified live: "Xyznomatch City 99999999" matched Shelf Road, Cañon City, CO). Geocode-empty branches are unit-test-verified instead of being forced live.
- [unchanged-pending] Open-Meteo hourly rain/snow rate magnitudes and license attribution strings (verify Phase 5). Rate-class boundaries remain threshold definitions for Phase 6, not Phase 3.
- Attribution (currently correct in footer): Open-Meteo (CC BY 4.0) + OpenFreeMap/OSM strings already present for later map phases.

## 8. Phase 5 verification updates [confirmed 2026-10-24]

- [resolved] Open-Meteo Forecast API live integration successful: `GET https://api.open-meteo.com/v1/forecast` with `hourly=wind_speed_10m,rain,snowfall`, `wind_speed_unit=mph`, `precipitation_unit=inch`, `timezone=UTC`, `forecast_days=3` returns valid hourly series for Chicago→Denver corridor.
- [resolved] Hourly variables: `wind_speed_10m` (mph), `rain` (inches, preceding-hour accumulation), `snowfall` (inches, preceding-hour accumulation) all present and numerically plausible (wind ~6 mph, rain/snow 0.0 in test corridor).
- [resolved] Matching policy works: checkpoint arrival timestamps truncated to hour match exact provider `hourly.time` buckets (UTC); no interpolation needed for this corridor.
- [resolved] Coordinate deduplication works: multiple checkpoints at same lat/lon (rounded to 4dp) result in single Open-Meteo fetch.
- [resolved] Error handling works: `weather_provider`, `weather_timeout`, `weather_rate_limited` error codes defined and tested; routes preserved on weather failure with structured `weatherError` field.
- [resolved] Free tier sufficient: non-commercial 10k calls/day covers assessment needs (2 routes × ~45 checkpoints = 90 calls per trip, well within limit).
- [resolved] Attribution: Open-Meteo (CC BY 4.0) included in footer and UI copy; no key required.
- [resolved — Phase 5, 2026-10-24] Phase 5 adds `weather` object to each checkpoint and `weatherSummaries[]` to API response; `geometry`, `distanceMeters`, `durationSeconds`, `checkpoints[]`, `checkpointSummary` all remain exactly as Phase 4 produced them. No provider values rewritten.
- [unchanged-pending] Rate-class boundary magnitudes for risk engine (Phase 6) — will use live + fixture samples.
