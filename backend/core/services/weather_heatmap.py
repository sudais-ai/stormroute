"""Weather Heatmap Service (Phase 9).

Gridded forecast samples along each route corridor for the 0–48 h
forecast slider. Pure, deterministic assembly + provider contract only;
no Django, no HTTP in tests (the fetcher is injectable).

Provider contract (Open-Meteo Forecast API v1):
- Endpoint: GET https://api.open-meteo.com/v1/forecast
- Multi-location: `latitude=a,b,c&longitude=...` returns a JSON **array**,
  one entry per requested coordinate in the same order (single coordinate
  returns a single object).
- Requested hourly variables: wind_speed_10m, rain, snowfall
- Units: wind mph, precipitation inches/hour, timezone=UTC, 3 forecast days.

Grid design (deterministic, disclosed approximation):
- Points are sampled along the provider geometry at a fixed meter spacing
  (capped per route) — NOT road-level certainty; values between grid
  points/facades are approximations.
- Coordinates are deduplicated across ALL routes by rounding (both routes
  on the same corridor share the same sampled weather).
- Each grid point stores the provider's first 49 hourly buckets
  (0…48 h inclusive) so the slider maps hour offsets to REAL timestamps.

Error policy: heatmap failures must never break the route response.
Individual point failures become `null` weather values ("unknown"),
batch/group failures simply omit the affected points.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import requests
import json

from core.services.weather import (
    WeatherError,
    WeatherProviderError,
    WeatherRateLimitError,
    WeatherTimeoutError,
)

logger = logging.getLogger(__name__)

_OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
# (connect, read) seconds — must never hang indefinitely.
_REQUEST_TIMEOUT = (5, 15)
# Horizon: slider covers 0–48 h inclusive → 49 provider hourly buckets.
_FORECAST_HOURS = 48
# Grid spacing (~11 km). Deliberately coarse: matches the provider's own
# grid resolution so extra density would imply a precision we do not have.
_DEFAULT_GRID_SPACING_METERS = 11_000.0
_DEFAULT_MAX_POINTS_PER_ROUTE = 60
# Coordinates per Open-Meteo multi-location request.
_DEFAULT_BATCH_SIZE = 50

EARTH_RADIUS_METERS = 6_371_008.8
_METERS_PER_DEGREE = 111_320.0


def _round_key(lat: float, lon: float) -> Tuple[float, float]:
    """Stable dedupe key (~11 m at 4 decimals)."""
    return (round(lat, 4), round(lon, 4))


def _is_valid_latlon(lat: float, lon: float) -> bool:
    return (
        isinstance(lat, (int, float))
        and isinstance(lon, (int, float))
        and math.isfinite(lat)
        and math.isfinite(lon)
        and -90.0 <= lat <= 90.0
        and -180.0 <= lon <= 180.0
    )


def generate_route_grid_points(
    coordinates: Sequence[Sequence[float]],
    spacing_meters: float = _DEFAULT_GRID_SPACING_METERS,
    max_points: int = _DEFAULT_MAX_POINTS_PER_ROUTE,
) -> List[Tuple[float, float]]:
    """Sample points `[lon, lat]` along a LineString at ~`spacing_meters`.

    Deterministic: evenly spaced along cumulative haversine length; when the
    cap is reached the spacing is stretched (not fewer endpoints).
    Returns [] for degenerate geometry (fewer than 2 valid points).

    Raises ValueError when spacing/max_points are non-positive (test guard).
    """
    if spacing_meters <= 0 or max_points <= 0:
        raise ValueError("spacing_meters and max_points must be positive")
    if not coordinates or len(coordinates) < 2:
        return []

    validated: List[Tuple[float, float]] = []
    for coord in coordinates:
        try:
            lon, lat = float(coord[0]), float(coord[1])
        except (TypeError, ValueError, IndexError):
            continue
        if _is_valid_latlon(lat, lon):
            validated.append((lon, lat))
    if len(validated) < 2:
        return []

    # Cumulative haversine distances (meters) along the linestring.
    distances = [0.0]
    for i in range(1, len(validated)):
        lon1, lat1 = validated[i - 1]
        lon2, lat2 = validated[i]
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        )
        seg = 2 * EARTH_RADIUS_METERS * math.asin(min(1.0, math.sqrt(a)))
        distances.append(distances[-1] + seg)

    total = distances[-1]

    # Number of segments = samples - 1; stretch spacing when capped.
    segments = int(total // spacing_meters) + 1
    if segments > max_points - 1:
        segments = max_points - 1
    segments = max(segments, 1)

    grid: List[Tuple[float, float]] = []
    for seg_index in range(segments + 1):
        target = total * seg_index / segments
        # Advance to the vertex containing `target`.
        i = 0
        while i < len(distances) - 2 and distances[i + 1] < target:
            i += 1
        start = distances[i]
        end = distances[i + 1]
        frac = 0.0 if end <= start else (target - start) / (end - start)
        frac = max(0.0, min(1.0, frac))
        lon1, lat1 = validated[i]
        lon2, lat2 = validated[i + 1]
        grid.append((lon1 + (lon2 - lon1) * frac, lat1 + (lat2 - lat1) * frac))

    if len(grid) < 2:
        return []
    return grid


def _series_from_response(payload: Any, forecast_hours: int) -> Optional[Dict[str, List[float | None]]]:
    """Validate one provider location payload and slice `forecast_hours+1` buckets.

    Returns None when the payload is structurally invalid; None per value
    when a single hour/value is missing or non-finite.
    """
    if not isinstance(payload, dict):
        return None
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        return None
    times = hourly.get("time")
    winds = hourly.get("wind_speed_10m")
    rains = hourly.get("rain")
    snows = hourly.get("snowfall")
    if not isinstance(times, list) or not times:
        return None
    if not isinstance(winds, list) or not isinstance(rains, list) or not isinstance(snows, list):
        return None

    # 0–48 h inclusive → forecast_hours + 1 buckets.
    n = min(len(times), forecast_hours + 1)

    def _value(arr: List[Any], i: int) -> Optional[float]:
        if i >= len(arr):
            return None
        v = arr[i]
        if not isinstance(v, (int, float)) or not math.isfinite(float(v)):
            return None
        return float(v)

    hours: List[str] = []
    wind: List[Optional[float]] = []
    rain: List[Optional[float]] = []
    snow: List[Optional[float]] = []
    for i in range(n):
        t = times[i]
        hours.append(t if isinstance(t, str) else str(t))
        w = _value(winds, i)
        r = _value(rains, i)
        s = _value(snows, i)
        wind.append(None if w is None else round(w, 1))
        rain.append(None if r is None else round(r, 3))
        snow.append(None if s is None else round(s, 3))

    return {"hours": hours, "windMph": wind, "rainInPerHr": rain, "snowfallInPerHr": snow}


def _build_batch_url(coords: List[Tuple[float, float]]) -> str:
    lats = ",".join(f"{round(lat, 4)}" for _, lat in coords)
    lons = ",".join(f"{round(lon, 4)}" for lon, _ in coords)
    return (
        f"{_OPEN_METEO_BASE}"
        f"?latitude={lats}&longitude={lons}"
        f"&hourly=wind_speed_10m,rain,snowfall"
        f"&wind_speed_unit=mph&precipitation_unit=inch&timezone=UTC"
        f"&forecast_days=3"
    )


def _fetch_batch(coords: List[Tuple[float, float]]) -> List[Optional[Dict[str, List[float | None]]]]:
    """Fetch one batch of coordinates.

    Never raises for provider issues: failures become all-None entries so a
    heatmap outage degrades to 'unknown' exactly like missing weather.
    """
    out: List[Optional[Dict[str, List[float | None]]]] = [None] * len(coords)
    try:
        resp = requests.get(_build_batch_url(coords), timeout=_REQUEST_TIMEOUT)
    except (requests.Timeout, requests.ConnectionError, requests.RequestException) as e:
        logger.warning("heatmap batch fetch failed: %s", type(e).__name__)
        return out

    if resp.status_code != 200:
        logger.warning("heatmap batch HTTP %s", resp.status_code)
        return out

    try:
        data = resp.json()
    except (ValueError, json.JSONDecodeError):
        return out

    # Multi-location → array aligned with request order; single → object.
    location_payloads: List[Any] = data if isinstance(data, list) else [data]
    if len(location_payloads) != len(coords):
        logger.warning(
            "heatmap batch size mismatch: requested=%s received=%s",
            len(coords),
            len(location_payloads),
        )
        return out

    for i, payload in enumerate(location_payloads):
        out[i] = _series_from_response(payload, _FORECAST_HOURS)
    return out


@dataclass(frozen=True)
class HeatmapGridPoint:
    longitude: float
    latitude: float
    hours: List[str]
    wind_mph: List[Optional[float]]
    rain_in_per_hr: List[Optional[float]]
    snowfall_in_per_hr: List[Optional[float]]


@dataclass(frozen=True)
class RouteHeatmap:
    route_id: str
    grid_points: List[HeatmapGridPoint]
    forecast_start_iso: str | None
    forecast_end_iso: str | None
    forecast_hours: int


def get_heatmap_for_routes(
    routes: List[dict],
    fetcher: Callable[..., List[Optional[Dict[str, List[float | None]]]]] = _fetch_batch,
    forecast_hours: int = _FORECAST_HOURS,
    max_points_per_route: int = _DEFAULT_MAX_POINTS_PER_ROUTE,
    batch_size: int = _DEFAULT_BATCH_SIZE,
    grid_spacing_meters: float = _DEFAULT_GRID_SPACING_METERS,
) -> List[RouteHeatmap]:
    """Generate heatmaps for every route, sharing one deduped fetch set."""
    heatmaps: List[RouteHeatmap] = []
    routes = routes or []

    # 1. Grid coordinate samples per route (deduped across routes).
    route_grids: Dict[str, List[Tuple[float, float]]] = {}
    dedupe: Dict[Tuple[float, float], None] = {}  # ordered set
    for route in routes:
        route_id = str(route.get("routeId", ""))
        geometry = route.get("geometry") or {}
        coords = geometry.get("coordinates") or []
        points = generate_route_grid_points(
            coords, spacing_meters=grid_spacing_meters, max_points=max_points_per_route
        )
        route_grids[route_id] = points
        for lon, lat in points:
            dedupe.setdefault(_round_key(lat, lon), None)

    if not dedupe:
        return [
            RouteHeatmap(route_id, [], None, None, forecast_hours)
            for route in routes
        ]

    all_coords = list(dedupe.keys())  # (lat, lon) rounded keys

    # 2. Batched provider fetch over the union of coordinates.
    forecast_by_key: Dict[Tuple[float, float], Optional[Dict[str, List[float | None]]]] = {}
    for start in range(0, len(all_coords), max(batch_size, 1)):
        batch = all_coords[start : start + max(batch_size, 1)]
        coords = [(lon, lat) for lat, lon in batch]
        try:
            series_list = fetcher(coords)
        except Exception as e:  # never propagate into the route pipeline
            logger.warning("heatmap fetcher raised %s", type(e).__name__)
            series_list = [None] * len(batch)
        for (lat, lon), series in zip(batch, series_list):
            forecast_by_key[(lat, lon)] = series

    # 3. Assemble per-route heatmaps from the shared fetch data.
    for route in routes:
        route_id = str(route.get("routeId", ""))
        points: List[HeatmapGridPoint] = []
        for lon, lat in route_grids.get(route_id, []):
            series = forecast_by_key.get(_round_key(lat, lon))
            if not series:
                continue
            points.append(
                HeatmapGridPoint(
                    longitude=round(lon, 6),
                    latitude=round(lat, 6),
                    hours=list(series["hours"]),
                    wind_mph=list(series["windMph"]),
                    rain_in_per_hr=list(series["rainInPerHr"]),
                    snowfall_in_per_hr=list(series["snowfallInPerHr"]),
                )
            )

        first_hours = [p.hours[0] for p in points if p.hours]
        last_hours = [p.hours[-1] for p in points if p.hours]
        heatmaps.append(
            RouteHeatmap(
                route_id=route_id,
                grid_points=points,
                forecast_start_iso=min(first_hours) if first_hours else None,
                forecast_end_iso=max(last_hours) if last_hours else None,
                forecast_hours=forecast_hours,
            )
        )
    return heatmaps


def heatmap_to_payload(heatmap: RouteHeatmap) -> dict:
    """Serialize a RouteHeatmap into the API response contract (camelCase)."""
    return {
        "routeId": heatmap.route_id,
        "gridPoints": [
            {
                "longitude": gp.longitude,
                "latitude": gp.latitude,
                "hours": gp.hours,
                "windMph": gp.wind_mph,
                "rainInPerHr": gp.rain_in_per_hr,
                "snowfallInPerHr": gp.snowfall_in_per_hr,
            }
            for gp in heatmap.grid_points
        ],
        "forecastStartISO": heatmap.forecast_start_iso,
        "forecastEndISO": heatmap.forecast_end_iso,
        "forecastHours": heatmap.forecast_hours,
    }


# Exported for views/routing error taxonomy completeness.
__all__ = [
    "HeatmapGridPoint",
    "RouteHeatmap",
    "WeatherError",
    "WeatherProviderError",
    "WeatherRateLimitError",
    "WeatherTimeoutError",
    "generate_route_grid_points",
    "get_heatmap_for_routes",
    "heatmap_to_payload",
]
