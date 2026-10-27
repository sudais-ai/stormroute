"""Mapbox routing service for route generation (Phase 3).

Server-side only. The Mapbox token is read from Django settings (loaded from
the gitignored `backend/.env` by the shared dotenv loader in
`stormroute/__init__.py`) and is treated strictly as a credential: it is never
logged, never returned inside API responses, and never embedded in error
messages. TLS verification is left at library defaults (never disabled).

Live provider reality (verified 2026-10-24, `docs/TEST_LOG.md`): the Mapbox
Directions API with `alternatives=true` returns the primary route plus UP TO
two alternatives. Some corridors yield fewer distinct routes (the recorded
Chicago→Denver probe returned two). This service reports the actual number of
distinct routes received and never fabricates extra options.

Pipeline (deterministic, provider-backed):
    1. geocode origin and destination free text
    2. request driving directions with alternatives + GeoJSON geometry
    3. normalize each provider route (validating shapes/units)
    4. deduplicate only genuinely identical route payloads
    5. compute per-route ETA from the validated departure instant

Error taxonomy — every failure surfaces as {"routesAvailable": false,
"error": {"code", "message", ["stage"]}} with a deterministic HTTP status:

- ProviderConfigurationError  token unset           → 503 config_missing
- ProviderAuthError           upstream 401/403      → 502 auth_failed
- GeocodeFailedError          no geocoding result   → 422 geocode_failed (stage: origin|destination)
- NoRoutesError               zero direction routes → 422 no_routes
- ProviderTimeoutError        connect/read timeout  → 504 provider_timeout
- ProviderRateLimitError      upstream 429          → 429 rate_limited
- ProviderResponseError       malformed payload or other upstream response
                                                    → 502 provider_response
- RouteGeometryError          provider geometry unusable for checkpoint
                              sampling (degenerate/invalid coordinates)
                                                    → 502 geometry_invalid

Phase 4 extension: every successfully normalized route is sampled into
checkpoints (`core.services.checkpoints`) before the response is returned.
Sampling is deterministic and in-memory; it makes no provider calls and never
mutates provider distance/duration/geometry values.

Phase 5 extension: after checkpoint sampling, every checkpoint is enriched
with hourly weather from Open-Meteo (wind, rain rate, snowfall rate at the
checkpoint's arrival hour). No risk scoring or ranking — that's Phase 6.

Messages sent to clients never include provider response text (which could in
theory echo request parameters); they are fixed, user-readable strings.
"""

from __future__ import annotations

import hashlib
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote

import requests
from django.conf import settings

from core.services.checkpoints import (
    DEFAULT_MAX_CHECKPOINTS_PER_ROUTE,
    CheckpointSamplingError,
    sample_route_checkpoints,
)
from core.services.weather import (
    WeatherError,
    WeatherProviderError,
    WeatherRateLimitError,
    WeatherTimeoutError,
    enrich_checkpoints_with_weather,
    fetch_corridor_forecasts,
)
from core.services.weather_heatmap import (
    get_heatmap_for_routes,
    heatmap_to_payload,
)
from core.services.risk import analyze_route_risk
from core.services.scoring import rank_and_recommend

logger = logging.getLogger(__name__)

_MAPBOX_BASE = "https://api.mapbox.com"
_GEOCODE_URL_TMPL = _MAPBOX_BASE + "/geocoding/v5/mapbox.places/{query}.json"
_DIRECTIONS_URL = _MAPBOX_BASE + "/directions/v5/mapbox/driving/{coordinates}"

# (connect, read) seconds — network calls must never hang indefinitely.
_REQUEST_TIMEOUT = (5, 25)
# The app asks Mapbox for the primary route plus up to two alternatives.
_ROUTES_REQUESTED = 3
_MILES_PER_METER = 0.000621371
_MAX_GEOCODE_WORKERS = 2


class ProviderError(Exception):
    """Base for all upstream/config failures with a client-facing shape."""

    code = "provider_error"
    message = "The routing provider is unavailable right now."
    http_status = 502
    # Optional pipeline stage marker, present on geocode failures.
    stage: str | None = None

    def as_payload(self) -> dict:
        payload = {"code": self.code, "message": self.message}
        if self.stage:
            payload["stage"] = self.stage
        return payload


class ProviderConfigurationError(ProviderError):
    code = "config_missing"
    message = (
        "Route generation is temporarily unavailable because the routing "
        "provider credential is not configured on the server."
    )
    http_status = 503


class ProviderAuthError(ProviderError):
    code = "auth_failed"
    message = (
        "The routing provider rejected the server credential. Please try "
        "again later — further details are withheld for security."
    )
    http_status = 502


class GeocodeFailedError(ProviderError):
    code = "geocode_failed"
    http_status = 422

    def __init__(self, stage: str) -> None:
        self.stage = stage
        self.message = (
            f"Could not turn the {stage} into coordinates. Try a more specific "
            "city name or address (for example 'Chicago, IL')."
        )
        super().__init__(self.message)


class NoRoutesError(ProviderError):
    code = "no_routes"
    message = (
        "The provider could not build any drivable route between those two "
        "locations. Check both locations and try again."
    )
    http_status = 422


class ProviderTimeoutError(ProviderError):
    code = "provider_timeout"
    message = (
        "The routing provider took too long to answer. Please try again — "
        "your inputs were not changed."
    )
    http_status = 504


class ProviderRateLimitError(ProviderError):
    code = "rate_limited"
    message = (
        "The routing provider temporarily rate-limited this server. Please "
        "try again in a few moments."
    )
    http_status = 429


class ProviderResponseError(ProviderError):
    code = "provider_response"
    message = "Received an unexpected answer from the routing provider."
    http_status = 502


class RouteGeometryError(ProviderError):
    """Provider route geometry cannot be sampled into safe checkpoints.

    Deliberately distinct from a generic provider response failure so clients
    and logs can tell "provider payload was malformed" apart from "route was
    returned but its geometry is unusable for checkpoint sampling".
    """

    code = "geometry_invalid"
    message = (
        "The routing provider returned route geometry that could not be "
        "sampled into checkpoints safely. Please try the route request again."
    )
    http_status = 502


def _token_or_raise() -> str:
    token = getattr(settings, "MAPBOX_ACCESS_TOKEN", "") or ""
    if not token.strip():
        raise ProviderConfigurationError()
    return token


def _mapbox_get(url: str, params: dict) -> dict:
    """Perform a Mapbox HTTP GET with strict timeouts + safe error mapping.

    Never disables TLS verification, and never logs (or re-raises) anything
    containing the request URL — the URL carries the token as a query
    parameter.
    """
    try:
        response = requests.get(url, params=params, timeout=_REQUEST_TIMEOUT)
    except requests.exceptions.Timeout:
        logger.warning("mapbox_call timeout endpoint=%s", _endpoint_label(url))
        raise ProviderTimeoutError()
    except requests.exceptions.SSLError:
        logger.warning("mapbox_call ssl_failure endpoint=%s", _endpoint_label(url))
        raise ProviderResponseError()
    except requests.exceptions.RequestException:
        # Connection refused / DNS failure / any other transport problem.
        logger.warning("mapbox_call transport_failure endpoint=%s", _endpoint_label(url))
        raise ProviderResponseError()

    status = response.status_code
    if status == 429:
        logger.warning("mapbox_call rate_limited endpoint=%s", _endpoint_label(url))
        raise ProviderRateLimitError()
    if status in (401, 403):
        logger.warning("mapbox_call rejected endpoint=%s status=%s", _endpoint_label(url), status)
        raise ProviderAuthError()
    if status != 200:
        logger.info("mapbox_call unexpected_status endpoint=%s status=%s", _endpoint_label(url), status)
        raise ProviderResponseError()
    try:
        return response.json()
    except ValueError:
        logger.warning("mapbox_call unparsable_json endpoint=%s", _endpoint_label(url))
        raise ProviderResponseError()


def _endpoint_label(url: str) -> str:
    """Coarse endpoint tag for logs; strips path after the resource kind so no
    coordinates/token ever land in a log line."""
    # e.g. https://api.mapbox.com/geocoding/v5/... → "geocoding"
    parts = url.split("?")[0].rstrip("/").split("/")
    return parts[3] if len(parts) > 3 else "mapbox"


def _validate_coordinates_pair(value: Any) -> tuple[float, float]:
    """Accept Mapbox [longitude, latitude]; reject anything else."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ProviderResponseError()
    try:
        lon, lat = float(value[0]), float(value[1])
    except (TypeError, ValueError):
        raise ProviderResponseError() from None
    if not (math.isfinite(lon) and math.isfinite(lat)):
        raise ProviderResponseError()
    if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
        raise ProviderResponseError()
    return lon, lat


def geocode_place(query: str, stage: str) -> dict:
    """Resolve free text into the single best geocoding candidate.

    Returns {"query", "resolvedName", "longitude", "latitude"}. Empty results
    raise GeocodeFailedError carrying the stage ("origin"/"destination") so
    clients can mark the right field.
    """
    token = _token_or_raise()
    url = _GEOCODE_URL_TMPL.format(query=quote(query, safe=""))
    data = _mapbox_get(url, {"access_token": token, "limit": 1})
    features = data.get("features") if isinstance(data, dict) else None
    if not isinstance(features, list) or not features:
        raise GeocodeFailedError(stage)
    feature = features[0]
    if not isinstance(feature, dict):
        raise ProviderResponseError()
    longitude, latitude = _validate_coordinates_pair(feature.get("center"))
    place_name = feature.get("place_name")
    return {
        "query": query,
        "resolvedName": place_name if isinstance(place_name, str) else query,
        "longitude": longitude,
        "latitude": latitude,
    }


def fetch_direction_routes(origin: dict, destination: dict, token: str) -> list:
    """Request driving routes with alternatives; returns raw route dicts.

    Geometries are requested as GeoJSON so every route carries a LineString
    with [longitude, latitude] coordinates.
    """
    coordinates = "{:.6f},{:.6f};{:.6f},{:.6f}".format(
        origin["longitude"], origin["latitude"],
        destination["longitude"], destination["latitude"],
    )
    url = _DIRECTIONS_URL.format(coordinates=coordinates)
    data = _mapbox_get(
        url,
        {
            "access_token": token,
            "alternatives": "true",
            "geometries": "geojson",
            "overview": "full",
        },
    )
    routes = data.get("routes") if isinstance(data, dict) else None
    if not isinstance(routes, list):
        raise ProviderResponseError()
    for route in routes:
        geometry = route.get("geometry") if isinstance(route, dict) else None
        coordinate_list = geometry.get("coordinates") if isinstance(geometry, dict) else None
        if not isinstance(coordinate_list, list) or len(coordinate_list) < 2:
            raise ProviderResponseError()
    return routes


def _route_leg_summary(route: dict) -> str:
    legs = route.get("legs") if isinstance(route, dict) else None
    if not isinstance(legs, list) or not legs:
        return ""
    first = legs[0] if isinstance(legs[0], dict) else {}
    summary = first.get("summary")
    return summary if isinstance(summary, str) else ""


def _readable_duration(seconds: float) -> str:
    """Seconds → '14 h 50 min' or '38 min' (whole minutes, never negative)."""
    total_minutes = max(0, math.floor(seconds / 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours == 0:
        return f"{minutes} min"
    return f"{hours} h {minutes} min"


def _route_fingerprint(route: dict) -> tuple:
    """Deterministic route identity: summary + metrics + endpoint coordinates."""
    try:
        coordinates = route["geometry"]["coordinates"]
        endpoint_bits = "{:.6f}|{:.6f}|{:.6f}|{:.6f}".format(
            coordinates[0][0], coordinates[0][1], coordinates[-1][0], coordinates[-1][1]
        )
        return (
            _route_leg_summary(route),
            float(route["distance"]),
            float(route["duration"]),
            endpoint_bits,
        )
    except (KeyError, TypeError, ValueError, IndexError):
        raise ProviderResponseError() from None


def normalize_route(index: int, route: dict) -> dict:
    """Convert one raw Mapbox route into the canonical JSON structure.

    Coordinates are preserved exactly as the provider sent them —
    [longitude, latitude] order is Mapbox's native form.
    """
    try:
        distance_m = float(route["distance"])
        duration_s = float(route["duration"])
        coordinates = route["geometry"]["coordinates"]
    except (KeyError, TypeError, ValueError):
        raise ProviderResponseError() from None
    if not (math.isfinite(distance_m) and math.isfinite(duration_s)):
        raise ProviderResponseError()

    # The identifier must be stable for identical routes and different for any
    # genuinely different corridor: summary+metrics+endpoint hash achieves that.
    fingerprint_bits = _route_fingerprint(route)
    route_id = "rt_" + hashlib.sha256(
        "|".join(str(bit) for bit in fingerprint_bits).encode("utf-8")
    ).hexdigest()[:12]

    return {
        "routeId": route_id,
        "label": f"Route {index + 1}",
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "distanceMeters": distance_m,
        "distanceMiles": round(distance_m * _MILES_PER_METER, 1),
        "durationSeconds": duration_s,
        "durationReadable": _readable_duration(duration_s),
        "providerRouteSummary": _route_leg_summary(route),
    }


def deduplicate_routes(normalized: list) -> tuple[list, int]:
    """Drop only routes whose summary+metrics+endpoints are fully identical.

    Keeps first-seen order. Near-duplicates (a slightly different corridor)
    always survive — deduplication matches exact replay only. Returns
    (kept, dropped).
    """
    seen: set = set()
    kept: list = []
    dropped = 0
    for route in normalized:
        fingerprint_bits = (
            route["providerRouteSummary"],
            route["distanceMeters"],
            route["durationSeconds"],
            _endpoint_bits_lookup(route["geometry"]["coordinates"]),
        )
        if fingerprint_bits in seen:
            dropped += 1
            continue
        seen.add(fingerprint_bits)
        kept.append(route)
    return kept, dropped


def _endpoint_bits_lookup(coordinates) -> str:
    return "{:.6f}|{:.6f}|{:.6f}|{:.6f}".format(
        coordinates[0][0], coordinates[0][1], coordinates[-1][0], coordinates[-1][1]
    )


def _fewer_than_three_warning(count: int) -> str:
    suffix = "" if count == 1 else "s"
    return (
        f"Mapbox returned {count} distinct route{suffix} for this corridor "
        f"(three were requested). Only real provider options are shown — no "
        f"route is invented. Weather analysis will use exactly "
        f"these {count} route{suffix} at every forecast hour."
    )


def _checkpoint_cap() -> int:
    """Read the per-route checkpoint cap from settings, rejecting bad values."""
    raw = getattr(settings, "CHECKPOINT_MAX_PER_ROUTE", DEFAULT_MAX_CHECKPOINTS_PER_ROUTE)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 2:
        return DEFAULT_MAX_CHECKPOINTS_PER_ROUTE
    return raw


def generate_routes(validated_trip: dict) -> dict:
    """Full routing pipeline for one validated trip.

    Input is TripInputSerializer.validated_data (departure already normalized
    to UTC). Output shape is defined here and mirrored by frontend types.
    """
    total_start = time.perf_counter()
    token = _token_or_raise()
    # Geocode both places concurrently (worker cap 2 — one call per place);
    # results are assigned by position (origin first) so failure/stage
    # attribution keeps today's semantics: an origin failure surfaces first.
    geocode_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=_MAX_GEOCODE_WORKERS) as geocode_pool:
        origin_future = geocode_pool.submit(geocode_place, validated_trip["origin"], "origin")
        destination_future = geocode_pool.submit(
            geocode_place, validated_trip["destination"], "destination"
        )
        origin = origin_future.result()
        destination = destination_future.result()
    geocode_seconds = time.perf_counter() - geocode_start

    directions_start = time.perf_counter()
    raw_routes = fetch_direction_routes(origin, destination, token)
    directions_seconds = time.perf_counter() - directions_start
    if not raw_routes:
        raise NoRoutesError()

    normalized = [normalize_route(index, route) for index, route in enumerate(raw_routes)]
    routes, dropped = deduplicate_routes(normalized)
    if not routes:
        raise NoRoutesError()
    # Mapbox caps alternatives server-side (primary + ≤2); no local truncation.

    departure = datetime.fromisoformat(validated_trip["departureISO"])
    if departure.tzinfo is None:
        # Defensive: the serializer guarantees aware UTC, this branch should
        # never run — fail safely instead of emitting a naive ISO string.
        raise ProviderResponseError()

    interval_miles = validated_trip["checkpointIntervalMiles"]
    checkpoint_cap = _checkpoint_cap()
    sample_start = time.perf_counter()
    for index, route in enumerate(routes):
        arrival = departure + timedelta(seconds=route["durationSeconds"])
        route["arrivalISO"] = arrival.isoformat()
        route["label"] = f"Route {index + 1}"
        # Phase 4: deterministic checkpoint sampling from the provider geometry.
        try:
            sampled = sample_route_checkpoints(route, departure, interval_miles, checkpoint_cap)
        except CheckpointSamplingError:
            # Geometry details are intentionally kept out of logs and responses.
            logger.warning(
                "checkpoint_sampling rejected provider geometry route=%s",
                route["routeId"],
            )
            raise RouteGeometryError() from None
        route["checkpoints"] = sampled["checkpoints"]
        route["checkpointSummary"] = sampled["summary"]
    sample_seconds = time.perf_counter() - sample_start

    # Phase 5: enrich checkpoints with hourly weather from Open-Meteo.
    # This runs after all routes have checkpoints; any weather failure is
    # surfaced as a structured error without losing the route data.
    # Shared corridor fetch: checkpoint enrichment (arrival-hour subsets) and
    # the heatmap builder (first-49h series per point) both derive from ONE
    # pre-fetched coordinate map, so each unique coordinate costs a single
    # Open-Meteo request per run. Open-Meteo 429 policy: no retry logic is
    # added — the service's fixed worker cap bounds the burst and existing
    # failure paths surface the structured error.
    weather_start = time.perf_counter()
    corridor_forecasts, corridor_error = fetch_corridor_forecasts(routes)
    try:
        routes, weather_summaries = enrich_checkpoints_with_weather(
            routes,
            corridor=(corridor_forecasts, corridor_error),
        )
    except WeatherError as e:
        # Log the internal detail but return a safe structured error.
        logger.warning("weather_enrichment failed: %s", e.code)
        # Attach weather error to response without discarding routes
        for route in routes:
            route["weatherError"] = e.as_payload()
        weather_summaries = []
    weather_seconds = time.perf_counter() - weather_start

    # Phase 6: deterministic weather risk analysis per checkpoint + route summary.
    # Runs after weather enrichment; uses the same load weight for all routes.
    load_lb = float(validated_trip["loadWeightLb"])
    risk_start = time.perf_counter()
    risk_summaries = []
    for route in routes:
        try:
            checkpoint_risks, route_risk = analyze_route_risk(route, load_lb)
            route["checkpointRisks"] = [
                {
                    "checkpointId": cr.checkpoint_id,
                    "arrivalISO": cr.arrival_iso,
                    "riskLevel": cr.risk_label,
                    "riskOrdinal": cr.risk_level,
                    "wind": cr.wind.to_str() if cr.wind else None,
                    "rain": cr.rain.to_str() if cr.rain else None,
                    "snow": cr.snow.to_str() if cr.snow else None,
                    "windMph": cr.wind_mph,
                    "rainInPerHr": cr.rain_in_per_hr,
                    "snowfallInPerHr": cr.snowfall_in_per_hr,
                    "factors": cr.factors,
                    "matchedForecastISO": cr.matched_forecast_iso,
                    "timeMatch": cr.time_match,
                }
                for cr in checkpoint_risks
            ]
            route["riskSummary"] = {
                "routeId": route_risk.route_id,
                "totalCheckpoints": route_risk.total_checkpoints,
                "checkpointsWithWeather": route_risk.checkpoints_with_weather,
                "checkpointsUnknown": route_risk.checkpoints_unknown,
                "lowCount": route_risk.low_count,
                "moderateCount": route_risk.moderate_count,
                "highCount": route_risk.high_count,
                "severeCount": route_risk.severe_count,
                "noTravelCount": route_risk.no_travel_count,
                "severeMiles": route_risk.severe_miles,
                "highMiles": route_risk.high_miles,
                "avgRiskOrdinal": route_risk.avg_risk_ordinal,
                "worstCheckpoint": (
                    {
                        "checkpointId": route_risk.worst_checkpoint.checkpoint_id,
                        "arrivalISO": route_risk.worst_checkpoint.arrival_iso,
                        "riskLevel": route_risk.worst_checkpoint.risk_label,
                        "factors": route_risk.worst_checkpoint.factors,
                    }
                    if route_risk.worst_checkpoint
                    else None
                ),
                "explanation": route_risk.explanation,
            }
            risk_summaries.append(route["riskSummary"])
        except Exception as e:
            # Risk analysis must never break the route response
            logger.warning("risk_analysis failed for route=%s: %s", route.get("routeId"), e)
            route["riskSummary"] = {
                "routeId": route.get("routeId", ""),
                "error": "Risk analysis unavailable",
            }
            risk_summaries.append(route["riskSummary"])
    risk_seconds = time.perf_counter() - risk_start

    # Phase 7: deterministic route scoring & recommendation (lexicographic ranking).
    recommendation = rank_and_recommend(routes, risk_summaries)

    count = len(routes)

    # Phase 9: gridded forecast heatmaps for the corridor (0–48 h).
    # Heatmap failures must never break the route response. Series derive
    # from the shared corridor fetch (no second provider pass); standalone
    # callers/tests without it keep the heatmap's own batched fetch.
    heatmap_start = time.perf_counter()
    heatmaps = []
    try:
        heatmaps = get_heatmap_for_routes(routes, pre_fetched_forecasts=corridor_forecasts)
    except Exception:
        logger.warning("heatmap_generation failed", exc_info=True)
        heatmaps = []
    heatmap_seconds = time.perf_counter() - heatmap_start

    total_seconds = time.perf_counter() - total_start
    checkpoint_count = sum(len(route.get("checkpoints", [])) for route in routes)
    # This line only becomes visible with an explicit project LOGGING config
    # (settings deliberately untouched); browser-measured POST timing is the
    # primary latency evidence. Counts only — no coordinates/tokens/PII.
    logger.info(
        "route_timing geocode=%.2f directions=%.2f sample=%.2f "
        "weather=%.2f risk=%.2f heatmap=%.2f total=%.2f routes=%s ckpts=%s",
        geocode_seconds,
        directions_seconds,
        sample_seconds,
        weather_seconds,
        risk_seconds,
        heatmap_seconds,
        total_seconds,
        count,
        checkpoint_count,
    )
    return {
        "trip": {
            "origin": validated_trip["origin"],
            "destination": validated_trip["destination"],
            "departureISO": validated_trip["departureISO"],
            "loadWeightLb": validated_trip["loadWeightLb"],
            "checkpointIntervalMiles": validated_trip["checkpointIntervalMiles"],
        },
        "origin": origin,
        "destination": destination,
        "routesRequested": _ROUTES_REQUESTED,
        "routeCount": count,
        "threeRoutesReturned": count == _ROUTES_REQUESTED,
        # Honest handling for fewer routes: exact provider truth, no synthesis.
        "warning": None if count == _ROUTES_REQUESTED else _fewer_than_three_warning(count),
        "duplicatesDropped": dropped,
        "routes": routes,
        "weatherSummaries": [
            {
                "routeId": s.route_id,
                "totalCheckpoints": s.total_checkpoints,
                "checkpointsWithWeather": s.checkpoints_with_weather,
                "checkpointsUnavailable": s.checkpoints_unavailable,
                "providerForecastStartISO": s.provider_forecast_start_iso,
                "providerForecastEndISO": s.provider_forecast_end_iso,
            }
            for s in weather_summaries
        ],
        "riskSummaries": risk_summaries,
        "recommendation": {
            "status": recommendation.status,
            "explanation": recommendation.explanation,
            "recommendedRouteId": recommendation.recommended_route_id,
            "rankedRouteIds": [s.route_id for s in recommendation.ranked_routes],
            "routeExplanations": recommendation.route_explanations,
        },
        "heatmaps": [heatmap_to_payload(hm) for hm in heatmaps],
    }
