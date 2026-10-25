"""Checkpoint sampling along provider route geometry (Phase 4).

Pure, deterministic geometry/timing logic. This module knows nothing about
weather providers, HTTP, Django, or MapLibre: it turns one normalized route
(GeoJSON LineString + provider distance/duration) into evenly-spaced
checkpoints with cumulative distance and estimated arrival times.

Sampling policy (documented in docs/DECISIONS.md):

- Coordinates are Mapbox GeoJSON "[longitude, latitude]" pairs. Anything else
  is rejected instead of guessed.
- Travel distance is measured with the haversine formula along the LineString
  vertices (mean Earth radius 6 371 008.8 m). Checkpoints are sampled every
  requested interval of *traveled* distance, never by vertex index and never
  from origin→destination straight-line distance.
- The origin is checkpoint 1 (distance 0). Every full interval then gets a
  checkpoint, and the destination is appended as a final partial segment when
  it does not coincide with the last interval sample. This keeps cumulative
  distance monotonic and never emits duplicate checkpoints.
- A configurable cap (default 500 per route) bounds weather-provider work
  later. When the requested spacing would exceed the cap, the effective
  spacing is widened (never the reverse) so the destination and honesty are
  preserved; the summary reports `capped` + `effectiveIntervalMiles`.
- Positions between vertices are linearly interpolated in coordinate space.
  Each checkpoint reports `interpolated` so consumers can distinguish derived
  positions from actual provider vertices.
- Arrival time = departure + provider duration × (checkpoint cumulative
  distance ÷ geometry length). This spreads the provider's real driving
  duration evenly by distance: constant average speed, no breaks, no live
  traffic and no weather adjustment. That approximation is deliberate and is
  surfaced in the API and UI — it is not claimed to be more than it is.
- Cumulative geometry length and the provider's reported route distance are
  both preserved in the summary. They can differ slightly because the
  overview geometry is simplified; no provider value is silently rewritten.
"""

from __future__ import annotations

import bisect
import hashlib
import math
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any

EARTH_RADIUS_METERS = 6_371_008.8  # IUGG mean Earth radius
METERS_PER_MILE = 1_609.344
DEFAULT_MAX_CHECKPOINTS_PER_ROUTE = 500
# Destination is appended only when it is meaningfully beyond the last sample;
# this avoids a duplicate final checkpoint at rounding noise scale.
_MIN_PARTIAL_SEGMENT_METERS = 0.5
_ID_DIGEST_LENGTH = 12

_ETA_METHOD = "distance-weighted-provider-duration"
_SAMPLING_METHOD = "haversine-distance-along-linestring"


class CheckpointSamplingError(ValueError):
    """Provider geometry or timing cannot be sampled safely.

    The routing pipeline translates this into a safe structured API error;
    no details from this exception ever reach providers or clients.
    """


def _validate_point(point: Any, index: int) -> tuple[float, float]:
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        raise CheckpointSamplingError(f"geometry point {index} is not a [longitude, latitude] pair")
    try:
        longitude = float(point[0])
        latitude = float(point[1])
    except (TypeError, ValueError):
        raise CheckpointSamplingError(f"geometry point {index} is not numeric") from None
    if not (math.isfinite(longitude) and math.isfinite(latitude)):
        raise CheckpointSamplingError(f"geometry point {index} contains a non-finite value")
    if not (-180.0 <= longitude <= 180.0 and -90.0 <= latitude <= 90.0):
        raise CheckpointSamplingError(f"geometry point {index} is outside valid longitude/latitude ranges")
    return longitude, latitude


def validate_linestring_coordinates(coordinates: Any) -> list[tuple[float, float]]:
    """Validate a GeoJSON LineString coordinate array ([lng, lat] pairs)."""
    if not isinstance(coordinates, (list, tuple)) or len(coordinates) < 2:
        raise CheckpointSamplingError("route geometry needs at least two coordinates")
    return [_validate_point(point, index) for index, point in enumerate(coordinates)]


def haversine_meters(lon_a: float, lat_a: float, lon_b: float, lat_b: float) -> float:
    """Great-circle distance between two [lng, lat] positions, in meters."""
    phi_a = math.radians(lat_a)
    phi_b = math.radians(lat_b)
    delta_phi = math.radians(lat_b - lat_a)
    delta_lambda = math.radians(lon_b - lon_a)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2.0) ** 2
    )
    a = min(1.0, max(0.0, a))
    return 2.0 * EARTH_RADIUS_METERS * math.asin(math.sqrt(a))


def cumulative_distances(points: list[tuple[float, float]]) -> list[float]:
    """Cumulative travel distance at every vertex (first entry is 0.0)."""
    cumulative = [0.0]
    for (lon_a, lat_a), (lon_b, lat_b) in zip(points, points[1:]):
        cumulative.append(cumulative[-1] + haversine_meters(lon_a, lat_a, lon_b, lat_b))
    return cumulative


def _position_at(
    points: list[tuple[float, float]], cumulative: list[float], target_meters: float
) -> tuple[float, float, bool]:
    """Return (longitude, latitude, interpolated) at a traveled-distance target."""
    total = cumulative[-1]
    if target_meters <= 0.0:
        return points[0][0], points[0][1], False
    if target_meters >= total:
        return points[-1][0], points[-1][1], False
    index = bisect.bisect_right(cumulative, target_meters) - 1
    index = min(max(index, 0), len(cumulative) - 2)
    segment_start = cumulative[index]
    segment_length = cumulative[index + 1] - segment_start
    if segment_length <= 0.0:  # duplicated consecutive vertex — no distance to travel
        return points[index][0], points[index][1], False
    fraction = (target_meters - segment_start) / segment_length
    if fraction <= 1e-9:
        return points[index][0], points[index][1], False
    if fraction >= 1.0 - 1e-9:
        return points[index + 1][0], points[index + 1][1], False
    longitude = points[index][0] + (points[index + 1][0] - points[index][0]) * fraction
    latitude = points[index][1] + (points[index + 1][1] - points[index][1]) * fraction
    return longitude, latitude, True


def _checkpoint_id(route_id: str, sequence: int, distance_meters: float, longitude: float, latitude: float) -> str:
    """Stable identifier: same route + same sampled position ⇒ same id."""
    fingerprint = f"{route_id}|{sequence}|{distance_meters:.1f}|{longitude:.6f}|{latitude:.6f}"
    return "cp_" + hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:_ID_DIGEST_LENGTH]


def _validated_departure(departure: datetime) -> datetime:
    if not isinstance(departure, datetime) or departure.tzinfo is None or departure.utcoffset() is None:
        raise CheckpointSamplingError("departure must be a timezone-aware datetime")
    return departure.astimezone(dt_timezone.utc)


def _validated_positive(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise CheckpointSamplingError(f"{label} must be a positive number")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise CheckpointSamplingError(f"{label} must be a positive number") from None
    if not math.isfinite(number) or number <= 0.0:
        raise CheckpointSamplingError(f"{label} must be a positive finite number")
    return number


def _validated_max_checkpoints(max_checkpoints: int | None) -> int:
    if max_checkpoints is None:
        return DEFAULT_MAX_CHECKPOINTS_PER_ROUTE
    if isinstance(max_checkpoints, bool) or not isinstance(max_checkpoints, int) or max_checkpoints < 2:
        raise CheckpointSamplingError("max_checkpoints must be an integer of at least 2")
    return max_checkpoints


def _sampling_spacing(total_meters: float, requested_interval_meters: float, max_checkpoints: int) -> tuple[float, bool]:
    """Pick the actual sampling spacing, widening it only to respect the cap.

    Two slots are reserved for origin and destination, so the resulting count
    (origin + interior samples + destination) can never exceed the cap.
    """
    interior_budget = max_checkpoints - 2
    if interior_budget < 1:
        return total_meters, True
    if math.floor(total_meters / requested_interval_meters) <= interior_budget:
        return requested_interval_meters, False
    widened = math.ceil(total_meters / interior_budget)
    return max(widened, requested_interval_meters), True


def sample_route_checkpoints(
    route: dict,
    departure: datetime,
    interval_miles: float,
    max_checkpoints: int | None = None,
) -> dict:
    """Sample one normalized route into checkpoints + a sampling summary.

    Raises CheckpointSamplingError for malformed geometry, invalid
    duration/distance, naive departure timestamps, or invalid settings.
    Never mutates `route`.
    """
    if not isinstance(route, dict):
        raise CheckpointSamplingError("route must be an object")
    route_id = route.get("routeId")
    if not isinstance(route_id, str) or not route_id.startswith("rt_"):
        raise CheckpointSamplingError("route is missing its stable identifier")
    geometry = route.get("geometry")
    coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
    points = validate_linestring_coordinates(coordinates)

    duration_seconds = _validated_positive(route.get("durationSeconds"), "route duration")
    provider_distance_meters = _validated_positive(route.get("distanceMeters"), "provider route distance")
    interval_miles_value = _validated_positive(interval_miles, "checkpoint interval")
    interval_meters_requested = interval_miles_value * METERS_PER_MILE
    cap = _validated_max_checkpoints(max_checkpoints)

    cumulative = cumulative_distances(points)
    total_meters = cumulative[-1]
    if not math.isfinite(total_meters) or total_meters < _MIN_PARTIAL_SEGMENT_METERS:
        raise CheckpointSamplingError("route geometry has zero usable length")

    spacing_meters, capped = _sampling_spacing(total_meters, interval_meters_requested, cap)
    departure_utc = _validated_departure(departure)

    full_intervals = int(math.floor(total_meters / spacing_meters + 1e-9))
    targets = [index * spacing_meters for index in range(full_intervals + 1)]
    if total_meters - targets[-1] > _MIN_PARTIAL_SEGMENT_METERS:
        targets.append(total_meters)

    checkpoints: list[dict] = []
    for index, target in enumerate(targets):
        longitude, latitude, interpolated = _position_at(points, cumulative, target)
        longitude = round(longitude, 6)
        latitude = round(latitude, 6)
        distance_from_start = round(target, 1)
        elapsed_seconds = duration_seconds * (target / total_meters)
        arrival = departure_utc + timedelta(seconds=elapsed_seconds)
        checkpoints.append(
            {
                "checkpointId": _checkpoint_id(route_id, index + 1, distance_from_start, longitude, latitude),
                "routeId": route_id,
                "sequence": index + 1,
                "coordinates": [longitude, latitude],
                "distanceFromStartMeters": distance_from_start,
                "distanceFromStartMiles": round(target / METERS_PER_MILE, 1),
                "elapsedSeconds": round(elapsed_seconds, 1),
                "arrivalISO": arrival.isoformat(),
                "interpolated": interpolated,
            }
        )

    summary = {
        "count": len(checkpoints),
        "requestedIntervalMiles": round(interval_meters_requested / METERS_PER_MILE, 3),
        "effectiveIntervalMiles": round(spacing_meters / METERS_PER_MILE, 3),
        "capped": capped,
        "maxPerRoute": cap,
        "geometryDistanceMeters": round(total_meters, 1),
        "geometryDistanceMiles": round(total_meters / METERS_PER_MILE, 1),
        "providerDistanceMeters": round(provider_distance_meters, 1),
        "durationSeconds": round(duration_seconds, 1),
        "samplingMethod": _SAMPLING_METHOD,
        "etaMethod": _ETA_METHOD,
    }
    return {"checkpoints": checkpoints, "summary": summary}
