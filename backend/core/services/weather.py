"""Open-Meteo weather service (Phase 5).

Pure, deterministic provider integration. No Django, no HTTP in tests.
Turns a list of checkpoints (lat/lon + arrivalISO) into per-checkpoint
hourly weather: wind (mph), rain rate (in/hr), snowfall rate (in/hr).

Provider contract (Open-Meteo Forecast API v1):
- Endpoint: GET https://api.open-meteo.com/v1/forecast
- Required params: latitude, longitude, hourly=wind_speed_10m,rain,snowfall,
  wind_speed_unit=mph, precipitation_unit=inch, timezone=UTC
- Optional: forecast_days (max 16; we use 3 for 0-72h coverage)
- Returns: hourly.time (ISO-8601 UTC strings), and arrays for each variable
- Semantics: rain/snowfall are "preceding hour accumulation" → treated as
  hourly rate per the provider's documentation. precipitation_probability
  is explicitly NOT used as a rate.

Matching policy (deterministic):
- Checkpoint arrivalISO is UTC (e.g., "2099-01-01T16:00:00+00:00").
- Provider hourly.time is also UTC (e.g., "2099-01-01T16:00").
- We match the EXACT hour bucket: truncate checkpoint arrival to the hour.
  If the provider has that hour, use it; else mark as unavailable.
- No interpolation between hours; no "nearest hour" fudging — the spec
  says "use the truck's estimated arrival time at each checkpoint to
  select the forecast", and the provider gives hourly buckets.
- Time difference metadata: always 0 when matched, or "out_of_horizon"
  when the checkpoint hour is not present in the response.

Units (provider-native, no conversion):
- wind_speed_10m: mph (requested)
- rain: inches per hour (requested via precipitation_unit=inch)
- snowfall: inches per hour (requested via precipitation_unit=inch)

Error taxonomy — safe structured errors only, no provider text/URL echo:
- WeatherConfigurationError  (config missing)  → not applicable (no key)
- WeatherProviderError       (upstream failure) → 502 weather_provider
- WeatherTimeoutError        (timeout)        → 504 weather_timeout
- WeatherRateLimitError      (429)            → 429 weather_rate_limited
"""

from __future__ import annotations

import concurrent.futures
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

_OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
# (connect, read) seconds
_REQUEST_TIMEOUT = (5, 15)
# Forecast horizon needed for the 0-48h slider + margin.
# Open-Meteo supports up to 16 days; 3 days is 72h, plenty for 48h.
_FORECAST_DAYS = 3
# Worker cap for parallel per-coordinate forecast fetches (stdlib
# concurrent.futures only). Open-Meteo HTTP 429 policy: NO retries are added —
# the fixed cap bounds request bursts and the existing failure path surfaces
# the structured error exactly as the sequential loop did.
# 8 (free-tier ~600 calls/min safe): checkpoint domain only; grid domain is
# batched at ≤50 coordinates per GET, so it adds no per-coordinate calls.
_MAX_PARALLEL_WORKERS = 8


class WeatherError(Exception):
    """Base for weather provider failures with client-facing shape."""

    code = "weather_error"
    message = "Weather data is temporarily unavailable."
    http_status = 502

    def as_payload(self) -> dict:
        return {"code": self.code, "message": self.message}


class WeatherProviderError(WeatherError):
    code = "weather_provider"
    message = (
        "The weather provider returned an unexpected response. "
        "Please try again later."
    )
    http_status = 502


class WeatherTimeoutError(WeatherError):
    code = "weather_timeout"
    message = (
        "The weather provider took too long to answer. "
        "Please try again — your route results are unchanged."
    )
    http_status = 504


class WeatherRateLimitError(WeatherError):
    code = "weather_rate_limited"
    message = "Weather provider rate limit exceeded. Please try again shortly."
    http_status = 429


@dataclass(frozen=True)
class CheckpointWeather:
    """Normalized weather for one checkpoint at its arrival hour."""

    checkpoint_id: str
    # The checkpoint's own arrival timestamp (UTC, from Phase 4)
    arrival_iso: str
    # The provider hour we actually matched (same as arrival hour when available)
    matched_forecast_iso: str | None
    # Time difference: "exact" when matched, "out_of_horizon" when not
    time_match: str
    # Core fields per assessment spec — None when unavailable
    wind_mph: float | None
    rain_in_per_hr: float | None
    snowfall_in_per_hr: float | None
    # Provider metadata
    provider: str = "open-meteo"
    provider_forecast_iso: str | None = None  # the raw provider time string


@dataclass(frozen=True)
class RouteWeatherSummary:
    """Per-route weather coverage metadata."""

    route_id: str
    total_checkpoints: int
    checkpoints_with_weather: int
    checkpoints_unavailable: int
    # ISO timestamp of the earliest/lates forecast hour returned by provider
    provider_forecast_start_iso: str | None
    provider_forecast_end_iso: str | None


def _validate_checkpoint_input(cp: dict) -> tuple[str, float, float, datetime]:
    """Validate and extract required fields from a checkpoint dict."""
    cp_id = cp.get("checkpointId")
    if not isinstance(cp_id, str) or not cp_id:
        raise ValueError("checkpoint missing checkpointId")
    coords = cp.get("coordinates")
    if not (isinstance(coords, (list, tuple)) and len(coords) == 2):
        raise ValueError(f"checkpoint {cp_id} missing valid coordinates")
    try:
        lon = float(coords[0])
        lat = float(coords[1])
    except (TypeError, ValueError):
        raise ValueError(f"checkpoint {cp_id} coordinates not numeric")
    if not (math.isfinite(lon) and math.isfinite(lat)):
        raise ValueError(f"checkpoint {cp_id} coordinates not finite")
    if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
        raise ValueError(f"checkpoint {cp_id} coordinates out of range")
    arrival_iso = cp.get("arrivalISO")
    if not isinstance(arrival_iso, str):
        raise ValueError(f"checkpoint {cp_id} missing arrivalISO")
    try:
        arrival_dt = datetime.fromisoformat(arrival_iso.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"checkpoint {cp_id} arrivalISO not valid ISO-8601")
    if arrival_dt.tzinfo is None or arrival_dt.utcoffset() is None:
        raise ValueError(f"checkpoint {cp_id} arrivalISO not timezone-aware")
    arrival_utc = arrival_dt.astimezone(dt_timezone.utc)
    return cp_id, lat, lon, arrival_utc


def _truncate_to_hour(dt: datetime) -> datetime:
    """Return the same datetime truncated to the hour (minute=second=microsecond=0)."""
    return dt.replace(minute=0, second=0, microsecond=0)


def _build_open_meteo_url(lat: float, lon: float) -> str:
    """Build the Open-Meteo forecast URL for a coordinate."""
    # Coordinates rounded to 4 decimal places (~11m) to reduce cache misses
    # and keep URLs tidy; provider accepts float anyway.
    lat_r = round(lat, 4)
    lon_r = round(lon, 4)
    return (
        f"{_OPEN_METEO_BASE}?"
        f"latitude={lat_r}&longitude={lon_r}"
        f"&hourly=wind_speed_10m,rain,snowfall"
        f"&wind_speed_unit=mph"
        f"&precipitation_unit=inch"
        f"&timezone=UTC"
        f"&forecast_days={_FORECAST_DAYS}"
    )


def _fetch_open_meteo(lat: float, lon: float) -> dict[str, Any]:
    """Fetch one forecast from Open-Meteo. Raises WeatherError subclasses on failure."""
    url = _build_open_meteo_url(lat, lon)
    try:
        resp = requests.get(url, timeout=_REQUEST_TIMEOUT)
    except requests.Timeout:
        raise WeatherTimeoutError() from None
    except requests.ConnectionError:
        raise WeatherProviderError() from None
    except requests.RequestException:
        raise WeatherProviderError() from None

    if resp.status_code == 429:
        raise WeatherRateLimitError()
    if resp.status_code >= 400:
        # Do not log the response body — it may contain diagnostic info
        logger.warning("Open-Meteo HTTP %s for lat=%s lon=%s", resp.status_code, lat, lon)
        raise WeatherProviderError()

    try:
        data = resp.json()
    except ValueError:
        raise WeatherProviderError()

    # Validate required structure
    hourly = data.get("hourly")
    if not isinstance(hourly, dict):
        raise WeatherProviderError()
    required_keys = ("time", "wind_speed_10m", "rain", "snowfall")
    if not all(k in hourly for k in required_keys):
        raise WeatherProviderError()
    times = hourly.get("time")
    if not isinstance(times, list) or not times:
        raise WeatherProviderError()

    return data


def _match_weather_at_hour(
    forecast_data: dict[str, Any], target_hour: datetime
) -> tuple[float | None, float | None, float | None, str | None, str | None]:
    """
    Find the provider bucket for target_hour (UTC, already truncated).
    Returns (wind_mph, rain_in_per_hr, snowfall_in_per_hr, matched_iso, provider_time_iso).
    All None + "out_of_horizon" if the hour is not in the response.
    """
    hourly = forecast_data["hourly"]
    times = hourly["time"]  # list of "YYYY-MM-DDTHH:00" strings (UTC)
    winds = hourly["wind_speed_10m"]
    rains = hourly["rain"]
    snowfalls = hourly["snowfall"]

    target_iso = target_hour.strftime("%Y-%m-%dT%H:%M")
    # Provider returns truncated hours like "2099-01-01T16:00"
    try:
        idx = times.index(target_iso)
    except ValueError:
        return None, None, None, None, None

    # Provider may return null for missing hours in some edge cases
    def get_val(arr: list, i: int) -> float | None:
        v = arr[i] if i < len(arr) else None
        return float(v) if v is not None and math.isfinite(v) else None

    wind = get_val(winds, idx)
    rain = get_val(rains, idx)
    snow = get_val(snowfalls, idx)
    provider_time = times[idx] if idx < len(times) else None
    return wind, rain, snow, target_iso, provider_time


def _collect_provider_forecast_bounds(forecast_data: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract earliest and latest forecast hours from provider response."""
    hourly = forecast_data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return None, None
    return times[0], times[-1]


def _grouped_checkpoint_coords(
    routes: list[dict],
) -> dict[tuple[float, float], list[tuple[dict, str, datetime]]]:
    """Group checkpoints by unique (lat, lon) to avoid duplicate fetches.

    Key: (rounded_lat, rounded_lon). Validation happens here; a malformed
    checkpoint raises ValueError exactly as it always has.
    """
    coord_to_checkpoints: dict[tuple[float, float], list[tuple[dict, str, datetime]]] = {}
    for route in routes:
        for cp in route.get("checkpoints", []):
            cp_id, lat, lon, arrival_utc = _validate_checkpoint_input(cp)
            key = (round(lat, 4), round(lon, 4))
            coord_to_checkpoints.setdefault(key, []).append((cp, cp_id, arrival_utc))
    return coord_to_checkpoints


def _fetch_many_forecasts(
    coord_keys: list[tuple[float, float]],
) -> tuple[dict[tuple[float, float], dict[str, Any]], tuple[float, float] | None, WeatherError | None]:
    """Fetch Open-Meteo forecasts for every unique coordinate in parallel.

    Each unique rounded coordinate is one `_fetch_open_meteo` call (the HTTP
    seam stays in this module — tests mock at this boundary), executed by a
    fixed-size ThreadPoolExecutor so the request burst stays bounded. All
    futures complete before anything is consumed: `executor.map` preserves
    input order, and the serial assignment below into the returned maps keeps
    downstream state deterministic (no shared mutable state touched by
    workers). Failure semantics: the FIRST failure in input order wins
    (`weather_error` was effectively last-wins in the old serial loop;
    input-order-first is deterministic and carries the same payload shapes).
    Only WeatherError family failures are captured, like before — anything
    unexpected still propagates.
    """
    def _one(key: tuple[float, float]):
        lat, lon = key
        try:
            return (key, _fetch_open_meteo(lat, lon), None)
        except WeatherError as e:
            return (key, None, e)

    forecasts: dict[tuple[float, float], dict[str, Any]] = {}
    error_key: tuple[float, float] | None = None
    weather_error: WeatherError | None = None
    if coord_keys:
        # map() yields results in input order, so the error winner above is
        # deterministic regardless of which worker finishes first.
        with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_PARALLEL_WORKERS) as pool:
            for key, payload, err in pool.map(_one, coord_keys):
                if err is not None:
                    if weather_error is None:
                        weather_error, error_key = err, key
                else:
                    forecasts[key] = payload
    return forecasts, error_key, weather_error


def _fetch_batched_grid(
    grid_keys: list[tuple[float, float]],
) -> dict[tuple[float, float], dict[str, Any]]:
    """Batched transport for the GRID-ONLY corridor coordinate domain.

    Delegates to the heatmap module's multi-location transport
    (`fetch_batched_payloads` — ≤50 coordinates per GET, input order
    preserved, key alignment by construction) so grid-only coordinates cost
    a small number of HTTP calls instead of one request per coordinate.
    Returns only successfully fetched keys: failures stay MISSING from the
    returned map (they degrade to "unknown" heatmap points exactly like
    today's batch-failure behavior) and NEVER surface as a route-level
    weatherError. No retries; 429 handling stays with the checkpoint
    domain's `_fetch_open_meteo` error path.
    """
    from core.services.weather_heatmap import fetch_batched_payloads  # noqa: PLC0415
    return fetch_batched_payloads(grid_keys)


def fetch_corridor_forecasts(
    routes: list[dict],
) -> tuple[dict[tuple[float, float], dict[str, Any]], WeatherError | None]:
    """One shared corridor fetch for both weather consumers.

    Merges the checkpoint coordinate universe (route enrichment) with the
    heatmap grid coordinate universe so every unique rounded coordinate costs
    exactly ONE Open-Meteo request per run; both consumers derive their needs
    from the returned map (checkpoint enrichment = arrival-hour subsets,
    heatmap builder = first-49h series per point).

    Transport split (Round 5):
    - CHECKPOINT coordinates keep the per-coordinate executor path
      (`_fetch_open_meteo` seam — tests mock at this boundary), with the
      same first-failure-in-input-order error semantics as before.
    - GRID-ONLY coordinates (route grid keys minus checkpoint keys) use the
      batched multi-location transport (`_fetch_batched_grid`); their
      failures produce MISSING keys, never a route-level weatherError.

    Returns
    (forecasts, weather_error) where weather_error is limited to failures on
    CHECKPOINT coordinates: route-level weatherError semantics stay as before,
    while grid-only failures degrade to "unknown" heatmap points exactly like
    today's batch-failure behavior.
    """
    coord_to_checkpoints = _grouped_checkpoint_coords(routes)
    checkpoint_keys = list(coord_to_checkpoints.keys())
    checkpoint_set = set(checkpoint_keys)
    # Lazy import: weather_heatmap imports error classes from this module at
    # load time, so the dependency direction can't be a top-level cycle.
    from core.services.weather_heatmap import route_grid_keys  # noqa: PLC0415
    _grids, grid_keys = route_grid_keys(routes)
    grid_only_keys = [key for key in grid_keys if key not in checkpoint_set]
    forecasts, _error_key, error = _fetch_many_forecasts(checkpoint_keys)
    # The executor pass covers ONLY checkpoint coordinates now, so any
    # captured failure is checkpoint-domain by construction (the old
    # combined pass had the same outcome: input order put checkpoint keys
    # first, so the first failure attributed to corridor_error was always
    # a checkpoint coordinate).
    corridor_error = error
    if grid_only_keys:
        forecasts.update(_fetch_batched_grid(grid_only_keys))
    return forecasts, corridor_error


def enrich_checkpoints_with_weather(
    routes: list[dict],
    corridor: tuple[dict[tuple[float, float], dict[str, Any]], WeatherError | None] | None = None,
) -> tuple[list[dict], list[RouteWeatherSummary]]:
    """
    Main entry point: given the Phase 4 routes (each has checkpoints),
    fetch weather for every checkpoint and return:
      - the same routes list, mutated in place with `weather` field on each checkpoint
      - a list of RouteWeatherSummary for the response metadata

    `corridor` optionally carries a pre-fetched shared forecast map from
    fetch_corridor_forecasts so enrichment derives from it without issuing
    its own HTTP pass.

    This function makes live HTTP calls to Open-Meteo. In tests, it is
    mocked at the module boundary (requests.get or _fetch_open_meteo).
    """
    if not routes:
        return routes, []

    # Validation + grouping pass — raises ValueError on malformed checkpoints
    # exactly as before, even when corridor carries a pre-fetched map.
    coord_to_checkpoints = _grouped_checkpoint_coords(routes)
    if corridor is None:
        forecasts, _error_key, weather_error = _fetch_many_forecasts(
            list(coord_to_checkpoints.keys())
        )
    else:
        forecasts, weather_error = corridor

    # If any fetch failed, mark all routes with the error and return early
    if weather_error:
        for route in routes:
            route["weatherError"] = weather_error.as_payload()
            for cp in route.get("checkpoints", []):
                cp["weather"] = {
                    "checkpointId": cp.get("checkpointId", ""),
                    "arrivalISO": cp.get("arrivalISO", ""),
                    "matchedForecastISO": None,
                    "timeMatch": "provider_error",
                    "windMph": None,
                    "rainInPerHr": None,
                    "snowfallInPerHr": None,
                    "provider": "open-meteo",
                    "providerForecastISO": None,
                }
        return routes, []

    # Now assign weather to each checkpoint
    summaries: list[RouteWeatherSummary] = []
    for route in routes:
        route_id = route.get("routeId", "")
        checkpoints = route.get("checkpoints", [])
        total = len(checkpoints)
        with_weather = 0
        unavailable = 0
        provider_start: str | None = None
        provider_end: str | None = None

        for cp in checkpoints:
            cp_id, lat, lon, arrival_utc = _validate_checkpoint_input(cp)
            key = (round(lat, 4), round(lon, 4))
            forecast = forecasts.get(key)
            if forecast is None:
                # Should not happen since we fetched for all coords
                cp["weather"] = {
                    "checkpointId": cp_id,
                    "arrivalISO": cp["arrivalISO"],
                    "matchedForecastISO": None,
                    "timeMatch": "provider_error",
                    "windMph": None,
                    "rainInPerHr": None,
                    "snowfallInPerHr": None,
                    "provider": "open-meteo",
                    "providerForecastISO": None,
                }
                unavailable += 1
                continue

            if provider_start is None:
                s, e = _collect_provider_forecast_bounds(forecast)
                provider_start, provider_end = s, e

            target_hour = _truncate_to_hour(arrival_utc)
            wind, rain, snow, matched_iso, provider_time_iso = _match_weather_at_hour(
                forecast, target_hour
            )

            if wind is None and rain is None and snow is None:
                # Hour not in provider response
                cp["weather"] = {
                    "checkpointId": cp_id,
                    "arrivalISO": cp["arrivalISO"],
                    "matchedForecastISO": None,
                    "timeMatch": "out_of_horizon",
                    "windMph": None,
                    "rainInPerHr": None,
                    "snowfallInPerHr": None,
                    "provider": "open-meteo",
                    "providerForecastISO": None,
                }
                unavailable += 1
            else:
                cp["weather"] = {
                    "checkpointId": cp_id,
                    "arrivalISO": cp["arrivalISO"],
                    "matchedForecastISO": matched_iso,
                    "timeMatch": "exact",
                    "windMph": wind,
                    "rainInPerHr": rain,
                    "snowfallInPerHr": snow,
                    "provider": "open-meteo",
                    "providerForecastISO": provider_time_iso,
                }
                with_weather += 1

        summaries.append(
            RouteWeatherSummary(
                route_id=route_id,
                total_checkpoints=total,
                checkpoints_with_weather=with_weather,
                checkpoints_unavailable=unavailable,
                provider_forecast_start_iso=provider_start,
                provider_forecast_end_iso=provider_end,
            )
        )

    return routes, summaries