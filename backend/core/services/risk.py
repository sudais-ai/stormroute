"""Deterministic Weather Risk Engine (Phase 6).

Implements the exact classification rules mandated by the assessment specification.

SPEC MAPPING (verbatim from docs/ASSESSMENT_SPEC.md §4–6):

Wind speed (mph) — boundary convention: lower bound inclusive, upper bound exclusive
  Low       : < 25
  Moderate  : 25 – < 35
  High      : 35 – < 45
  Severe    : 45 – < 55
  No Travel : ≥ 55

Rainfall rate (in/hr)
  Low       : < 0.10
  Moderate  : 0.10 – < 0.25
  High      : 0.25 – < 0.50
  Severe    : 0.50 – ≤ 1.00
  No Travel : > 1.00

Snowfall rate (in/hr)
  Low       : < 0.5
  Moderate  : 0.5 – < 1.0
  High      : 1.0 – < 2.0
  Severe    : 2.0 – ≤ 3.0
  No Travel : > 3.0

Load rules (from spec §5):
  - Wind ≥ 55 mph → No Travel for EVERY load.
  - Wind 45 ≤ w < 55 mph AND load > 30,000 lb → No Travel.
  - Wind 35 ≤ w < 45 mph AND load > 40,000 lb → Severe.

Combined checkpoint risk (§6):
  - Overall = max(per-condition class) with No Travel > Severe > High > Moderate > Low.
  - No Travel takes precedence (if any condition is No Travel, checkpoint is No Travel).

Unknown data handling:
  - Missing/invalid/out-of-horizon weather fields → risk = "unknown" (NOT low).
  - A checkpoint with ANY unknown field and NO condition classified as
    No Travel/Severe/High/Moderate → overall "unknown".
  - If a checkpoint has known values that yield a risk category AND some
    unknown fields, the known risk applies (unknown fields don't downgrade).

Route-level summary:
  - Counts per risk category across checkpoints with valid weather.
  - Checkpoints with unknown/unavailable data counted separately.
  - Most concerning valid checkpoint identified.
  - Severe-miles and High-miles estimated from checkpoint spacing
    (checkpoint interval × count of checkpoints in that category).
    This is an estimate — documented approximation, not continuous road data.

Determinism:
  - Pure functions, no I/O, no global state, no randomness.
  - Same input + same config → identical output every time.

Configuration:
  - Thresholds loaded from Django settings with safe defaults matching spec.
  - Can be overridden via environment without code changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any

# Risk severity ordinal for comparisons and averaging
class RiskLevel(IntEnum):
    UNKNOWN = -1
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @classmethod
    def from_str(cls, s: str) -> RiskLevel:
        return {
            "unknown": cls.UNKNOWN,
            "low": cls.LOW,
            "moderate": cls.MODERATE,
            "high": cls.HIGH,
            "severe": cls.SEVERE,
            "no_travel": cls.NO_TRAVEL,
        }[s.lower()]

    def to_str(self) -> str:
        return {
            self.UNKNOWN: "unknown",
            self.LOW: "low",
            self.MODERATE: "moderate",
            self.HIGH: "high",
            self.SEVERE: "severe",
            self.NO_TRAVEL: "no_travel",
        }[self]


@dataclass(frozen=True)
class CheckpointRisk:
    """Risk classification for one checkpoint at its arrival hour."""

    checkpoint_id: str
    arrival_iso: str
    risk_level: RiskLevel
    risk_label: str  # "low" | "moderate" | "high" | "severe" | "no_travel" | "unknown"
    # Per-condition contributions
    wind: RiskLevel | None
    rain: RiskLevel | None
    snow: RiskLevel | None
    # Source weather values (for evidence/explanation)
    wind_mph: float | None
    rain_in_per_hr: float | None
    snowfall_in_per_hr: float | None
    # Explanation for UI
    factors: list[str]
    # Provider metadata
    matched_forecast_iso: str | None
    time_match: str  # "exact" | "out_of_horizon" | "provider_error"


@dataclass(frozen=True)
class RouteRiskSummary:
    """Route-level risk aggregation."""

    route_id: str
    total_checkpoints: int
    checkpoints_with_weather: int
    checkpoints_unknown: int
    # Category counts (only checkpoints with valid weather)
    low_count: int
    moderate_count: int
    high_count: int
    severe_count: int
    no_travel_count: int
    # Estimated risk miles (checkpoint interval × count)
    severe_miles: float
    high_miles: float
    # Average risk ordinal over valid checkpoints (excludes unknown)
    avg_risk_ordinal: float | None
    # Most concerning valid checkpoint
    worst_checkpoint: CheckpointRisk | None
    # Human-readable explanation
    explanation: str


# -------- Configuration (loaded from Django settings with safe defaults) --------

# Wind thresholds (mph) — lower bounds for each band
WIND_LOW_MAX = 25.0       # < 25 = Low
WIND_MODERATE_MAX = 35.0  # < 35 = Moderate (i.e., 25–<35)
WIND_HIGH_MAX = 45.0      # < 45 = High (35–<45)
WIND_SEVERE_MAX = 55.0    # < 55 = Severe (45–<55)
# No Travel: ≥ 55

# Rain thresholds (in/hr)
RAIN_LOW_MAX = 0.10
RAIN_MODERATE_MAX = 0.25
RAIN_HIGH_MAX = 0.50
RAIN_SEVERE_MAX = 1.00
# No Travel: > 1.00

# Snow thresholds (in/hr)
SNOW_LOW_MAX = 0.5
SNOW_MODERATE_MAX = 1.0
SNOW_HIGH_MAX = 2.0
SNOW_SEVERE_MAX = 3.0
# No Travel: > 3.0

# Load rules
WIND_NO_TRAVEL_ANY_LOAD = 55.0      # ≥ 55 → No Travel any load
WIND_NO_TRAVEL_HEAVY_LOAD = 45.0    # ≥ 45 → No Travel if load > 30,000
WIND_SEVERE_HEAVY_LOAD = 35.0       # ≥ 35 → Severe if load > 40,000
HEAVY_LOAD_THRESHOLD_LB = 30_000
VERY_HEAVY_LOAD_THRESHOLD_LB = 40_000


def _load_risk_config() -> dict[str, Any]:
    """Load risk thresholds from Django settings with spec-compliant defaults.

    Settings are optional; if missing or invalid, the hard-coded spec values
    are used. This keeps the service testable without Django and makes
    thresholds configurable for deployment.
    """
    try:
        from django.conf import settings
    except Exception:
        settings = None

    def get_float(path: str, default: float) -> float:
        if settings is None:
            return default
        val = getattr(settings, path, default)
        try:
            f = float(val)
            return f if f >= 0 else default
        except (TypeError, ValueError):
            return default

    def get_int(path: str, default: int) -> int:
        if settings is None:
            return default
        val = getattr(settings, path, default)
        try:
            i = int(val)
            return i if i > 0 else default
        except (TypeError, ValueError):
            return default

    return {
        # Wind
        "wind_low_max": get_float("RISK_WIND_LOW_MAX", WIND_LOW_MAX),
        "wind_moderate_max": get_float("RISK_WIND_MODERATE_MAX", WIND_MODERATE_MAX),
        "wind_high_max": get_float("RISK_WIND_HIGH_MAX", WIND_HIGH_MAX),
        "wind_severe_max": get_float("RISK_WIND_SEVERE_MAX", WIND_SEVERE_MAX),
        "wind_no_travel_any_load": get_float("RISK_WIND_NO_TRAVEL_ANY_LOAD", WIND_NO_TRAVEL_ANY_LOAD),
        "wind_no_travel_heavy_load": get_float("RISK_WIND_NO_TRAVEL_HEAVY_LOAD", WIND_NO_TRAVEL_HEAVY_LOAD),
        "wind_severe_heavy_load": get_float("RISK_WIND_SEVERE_HEAVY_LOAD", WIND_SEVERE_HEAVY_LOAD),
        # Rain
        "rain_low_max": get_float("RISK_RAIN_LOW_MAX", RAIN_LOW_MAX),
        "rain_moderate_max": get_float("RISK_RAIN_MODERATE_MAX", RAIN_MODERATE_MAX),
        "rain_high_max": get_float("RISK_RAIN_HIGH_MAX", RAIN_HIGH_MAX),
        "rain_severe_max": get_float("RISK_RAIN_SEVERE_MAX", RAIN_SEVERE_MAX),
        # Snow
        "snow_low_max": get_float("RISK_SNOW_LOW_MAX", SNOW_LOW_MAX),
        "snow_moderate_max": get_float("RISK_SNOW_MODERATE_MAX", SNOW_MODERATE_MAX),
        "snow_high_max": get_float("RISK_SNOW_HIGH_MAX", SNOW_HIGH_MAX),
        "snow_severe_max": get_float("RISK_SNOW_SEVERE_MAX", SNOW_SEVERE_MAX),
        # Load thresholds
        "heavy_load_threshold_lb": get_int("RISK_HEAVY_LOAD_THRESHOLD_LB", HEAVY_LOAD_THRESHOLD_LB),
        "very_heavy_load_threshold_lb": get_int("RISK_VERY_HEAVY_LOAD_THRESHOLD_LB", VERY_HEAVY_LOAD_THRESHOLD_LB),
    }


# -------- Classification functions (pure, deterministic) --------

def classify_wind(wind_mph: float | None, load_lb: float | None, cfg: dict[str, Any]) -> tuple[RiskLevel, list[str]]:
    """Classify wind risk per spec §4 (wind) + §5 (load rules).

    Boundary convention: lower bound inclusive, upper bound exclusive.
    E.g., 25.0 mph → Moderate (since 25–<35), 35.0 mph → High.

    Load rules applied in order of precedence:
      1. wind ≥ 55 → No Travel (any load)
      2. wind 45–<55 AND load > 30,000 → No Travel
      3. wind 35–<45 AND load > 40,000 → Severe
    """
    factors = []

    if wind_mph is None or not isinstance(wind_mph, (int, float)) or not (wind_mph >= 0):
        return RiskLevel.UNKNOWN, ["wind data unavailable"]

    w = float(wind_mph)

    # Load rules checked first (they can upgrade to No Travel / Severe)
    heavy_load = load_lb is not None and load_lb > cfg["heavy_load_threshold_lb"]
    very_heavy_load = load_lb is not None and load_lb > cfg["very_heavy_load_threshold_lb"]

    no_travel_any = cfg["wind_no_travel_any_load"]
    no_travel_heavy = cfg["wind_no_travel_heavy_load"]
    severe_heavy = cfg["wind_severe_heavy_load"]

    if w >= no_travel_any:
        factors.append(f"wind {w:.1f} mph ≥ {no_travel_any:.0f} mph → No Travel (any load)")
        return RiskLevel.NO_TRAVEL, factors

    if w >= no_travel_heavy and heavy_load:
        factors.append(f"wind {w:.1f} mph in [{no_travel_heavy:.0f}, {no_travel_any:.0f}) + load {load_lb:.0f} lb > {cfg['heavy_load_threshold_lb']:,} lb → No Travel")
        return RiskLevel.NO_TRAVEL, factors

    if w >= severe_heavy and very_heavy_load:
        factors.append(f"wind {w:.1f} mph in [{severe_heavy:.0f}, {no_travel_heavy:.0f}) + load {load_lb:.0f} lb > {cfg['very_heavy_load_threshold_lb']:,} lb → Severe")
        return RiskLevel.SEVERE, factors

    # Base wind classification (spec §4 table)
    if w < cfg["wind_low_max"]:
        factors.append(f"wind {w:.1f} mph < {cfg['wind_low_max']:.0f} → Low")
        return RiskLevel.LOW, factors
    elif w < cfg["wind_moderate_max"]:
        factors.append(f"wind {w:.1f} mph in [{cfg['wind_low_max']:.0f}, {cfg['wind_moderate_max']:.0f}) → Moderate")
        return RiskLevel.MODERATE, factors
    elif w < cfg["wind_high_max"]:
        factors.append(f"wind {w:.1f} mph in [{cfg['wind_moderate_max']:.0f}, {cfg['wind_high_max']:.0f}) → High")
        return RiskLevel.HIGH, factors
    elif w < cfg["wind_severe_max"]:
        factors.append(f"wind {w:.1f} mph in [{cfg['wind_high_max']:.0f}, {cfg['wind_severe_max']:.0f}) → Severe")
        return RiskLevel.SEVERE, factors
    else:
        # w >= wind_severe_max (55) but didn't trigger No Travel above —
        # this shouldn't happen with spec defaults, but handle gracefully
        factors.append(f"wind {w:.1f} mph ≥ {cfg['wind_severe_max']:.0f} → No Travel")
        return RiskLevel.NO_TRAVEL, factors


def classify_rain(rain_in_per_hr: float | None, cfg: dict[str, Any]) -> tuple[RiskLevel, list[str]]:
    """Classify rainfall rate risk per spec §4 (rain).

    Boundary convention: lower bound inclusive, upper bound exclusive.
    Note: Severe upper bound is ≤ 1.00 (inclusive per spec), No Travel is > 1.00.
    """
    factors = []

    if rain_in_per_hr is None or not isinstance(rain_in_per_hr, (int, float)) or not (rain_in_per_hr >= 0):
        return RiskLevel.UNKNOWN, ["rain data unavailable"]

    r = float(rain_in_per_hr)

    if r < cfg["rain_low_max"]:
        factors.append(f"rain {r:.3f} in/hr < {cfg['rain_low_max']:.2f} → Low")
        return RiskLevel.LOW, factors
    elif r < cfg["rain_moderate_max"]:
        factors.append(f"rain {r:.3f} in/hr in [{cfg['rain_low_max']:.2f}, {cfg['rain_moderate_max']:.2f}) → Moderate")
        return RiskLevel.MODERATE, factors
    elif r < cfg["rain_high_max"]:
        factors.append(f"rain {r:.3f} in/hr in [{cfg['rain_moderate_max']:.2f}, {cfg['rain_high_max']:.2f}) → High")
        return RiskLevel.HIGH, factors
    elif r <= cfg["rain_severe_max"]:  # ≤ 1.00 inclusive per spec
        factors.append(f"rain {r:.3f} in/hr in [{cfg['rain_high_max']:.2f}, {cfg['rain_severe_max']:.2f}] → Severe")
        return RiskLevel.SEVERE, factors
    else:
        factors.append(f"rain {r:.3f} in/hr > {cfg['rain_severe_max']:.2f} → No Travel")
        return RiskLevel.NO_TRAVEL, factors


def classify_snow(snowfall_in_per_hr: float | None, cfg: dict[str, Any]) -> tuple[RiskLevel, list[str]]:
    """Classify snowfall rate risk per spec §4 (snow).

    Boundary convention: lower bound inclusive, upper bound exclusive.
    Severe upper bound is ≤ 3.0 (inclusive), No Travel is > 3.0.
    """
    factors = []

    if snowfall_in_per_hr is None or not isinstance(snowfall_in_per_hr, (int, float)) or not (snowfall_in_per_hr >= 0):
        return RiskLevel.UNKNOWN, ["snow data unavailable"]

    s = float(snowfall_in_per_hr)

    if s < cfg["snow_low_max"]:
        factors.append(f"snow {s:.2f} in/hr < {cfg['snow_low_max']:.1f} → Low")
        return RiskLevel.LOW, factors
    elif s < cfg["snow_moderate_max"]:
        factors.append(f"snow {s:.2f} in/hr in [{cfg['snow_low_max']:.1f}, {cfg['snow_moderate_max']:.1f}) → Moderate")
        return RiskLevel.MODERATE, factors
    elif s < cfg["snow_high_max"]:
        factors.append(f"snow {s:.2f} in/hr in [{cfg['snow_moderate_max']:.1f}, {cfg['snow_high_max']:.1f}) → High")
        return RiskLevel.HIGH, factors
    elif s <= cfg["snow_severe_max"]:  # ≤ 3.0 inclusive per spec
        factors.append(f"snow {s:.2f} in/hr in [{cfg['snow_high_max']:.1f}, {cfg['snow_severe_max']:.1f}] → Severe")
        return RiskLevel.SEVERE, factors
    else:
        factors.append(f"snow {s:.2f} in/hr > {cfg['snow_severe_max']:.1f} → No Travel")
        return RiskLevel.NO_TRAVEL, factors


def combine_checkpoint_risks(
    wind_level: RiskLevel,
    rain_level: RiskLevel,
    snow_level: RiskLevel,
    wind_factors: list[str],
    rain_factors: list[str],
    snow_factors: list[str],
) -> tuple[RiskLevel, list[str]]:
    """Combine per-condition risks into overall checkpoint risk.

    Rule: overall = max(per-condition) with NO_TRAVEL > SEVERE > HIGH > MODERATE > LOW > UNKNOWN.
    Unknown only propagates if ALL conditions are unknown.
    """
    all_factors = wind_factors + rain_factors + snow_factors

    levels = [wind_level, rain_level, snow_level]

    # If all unknown → unknown
    if all(l == RiskLevel.UNKNOWN for l in levels):
        return RiskLevel.UNKNOWN, ["all weather data unavailable"]

    # Max of known levels (UNKNOWN = -1, so it won't win unless all are unknown)
    worst = max(levels)
    return worst, all_factors


def classify_checkpoint(
    checkpoint_id: str,
    arrival_iso: str,
    wind_mph: float | None,
    rain_in_per_hr: float | None,
    snowfall_in_per_hr: float | None,
    load_lb: float | None,
    matched_forecast_iso: str | None,
    time_match: str,
) -> CheckpointRisk:
    """Classify a single checkpoint's overall weather risk.

    This is the main entry point for per-checkpoint risk analysis.
    """
    cfg = _load_risk_config()

    wind_level, wind_factors = classify_wind(wind_mph, load_lb, cfg)
    rain_level, rain_factors = classify_rain(rain_in_per_hr, cfg)
    snow_level, snow_factors = classify_snow(snowfall_in_per_hr, cfg)

    overall_level, factors = combine_checkpoint_risks(
        wind_level, rain_level, snow_level,
        wind_factors, rain_factors, snow_factors,
    )

    return CheckpointRisk(
        checkpoint_id=checkpoint_id,
        arrival_iso=arrival_iso,
        risk_level=overall_level,
        risk_label=overall_level.to_str(),
        wind=wind_level if wind_level != RiskLevel.UNKNOWN else None,
        rain=rain_level if rain_level != RiskLevel.UNKNOWN else None,
        snow=snow_level if snow_level != RiskLevel.UNKNOWN else None,
        wind_mph=wind_mph,
        rain_in_per_hr=rain_in_per_hr,
        snowfall_in_per_hr=snowfall_in_per_hr,
        factors=factors,
        matched_forecast_iso=matched_forecast_iso,
        time_match=time_match,
    )


# -------- Route-level aggregation --------

def _checkpoint_interval_miles(route: dict) -> float:
    """Extract effective checkpoint interval from route summary."""
    summary = route.get("checkpointSummary", {})
    return float(summary.get("effectiveIntervalMiles", 25.0))


def summarize_route_risk(
    route: dict,
    checkpoint_risks: list[CheckpointRisk],
) -> RouteRiskSummary:
    """Aggregate checkpoint risks into a route-level summary.

    Severe/High miles are estimated as: count × checkpoint_interval_miles.
    This is an approximation based on discrete sampling — documented.
    """
    total = len(checkpoint_risks)
    valid_risks = [r for r in checkpoint_risks if r.risk_level != RiskLevel.UNKNOWN]
    unknown_risks = [r for r in checkpoint_risks if r.risk_level == RiskLevel.UNKNOWN]

    with_weather = len(valid_risks)
    unknown_count = len(unknown_risks)

    # Category counts
    low_count = sum(1 for r in valid_risks if r.risk_level == RiskLevel.LOW)
    moderate_count = sum(1 for r in valid_risks if r.risk_level == RiskLevel.MODERATE)
    high_count = sum(1 for r in valid_risks if r.risk_level == RiskLevel.HIGH)
    severe_count = sum(1 for r in valid_risks if r.risk_level == RiskLevel.SEVERE)
    no_travel_count = sum(1 for r in valid_risks if r.risk_level == RiskLevel.NO_TRAVEL)

    # Estimated risk miles
    interval = _checkpoint_interval_miles(route)
    severe_miles = severe_count * interval
    high_miles = high_count * interval

    # Average risk ordinal (excludes unknown)
    avg_ordinal = None
    if with_weather > 0:
        avg_ordinal = sum(r.risk_level for r in valid_risks) / with_weather

    # Most concerning valid checkpoint (max risk level, tie-break by first occurrence)
    worst = None
    for r in checkpoint_risks:
        if r.risk_level != RiskLevel.UNKNOWN:
            if worst is None or r.risk_level > worst.risk_level:
                worst = r

    # Explanation
    parts = []
    if no_travel_count > 0:
        parts.append(f"{no_travel_count} No Travel checkpoint(s)")
    if severe_count > 0:
        parts.append(f"{severe_count} Severe")
    if high_count > 0:
        parts.append(f"{high_count} High")
    if moderate_count > 0:
        parts.append(f"{moderate_count} Moderate")
    if low_count > 0:
        parts.append(f"{low_count} Low")
    if unknown_count > 0:
        parts.append(f"{unknown_count} unknown")

    if not parts:
        explanation = "No checkpoints"
    elif no_travel_count > 0:
        explanation = f"Route has {no_travel_count} No Travel checkpoint(s) — not recommended for travel. " + ", ".join(parts)
    elif severe_count > 0:
        explanation = f"Route has {severe_count} Severe checkpoint(s); est. {severe_miles:.1f} severe miles. " + ", ".join(parts)
    elif high_count > 0:
        explanation = f"Route has {high_count} High checkpoint(s); est. {high_miles:.1f} high miles. " + ", ".join(parts)
    else:
        explanation = "Route conditions: " + ", ".join(parts)

    return RouteRiskSummary(
        route_id=route.get("routeId", ""),
        total_checkpoints=total,
        checkpoints_with_weather=with_weather,
        checkpoints_unknown=unknown_count,
        low_count=low_count,
        moderate_count=moderate_count,
        high_count=high_count,
        severe_count=severe_count,
        no_travel_count=no_travel_count,
        severe_miles=severe_miles,
        high_miles=high_miles,
        avg_risk_ordinal=avg_ordinal,
        worst_checkpoint=worst,
        explanation=explanation,
    )


def analyze_route_risk(route: dict, load_lb: float | None) -> tuple[list[CheckpointRisk], RouteRiskSummary]:
    """Analyze all checkpoints on a route and return per-checkpoint + route summary.

    This is the main entry point for route risk analysis.
    """
    checkpoint_risks = []
    for cp in route.get("checkpoints", []):
        weather = cp.get("weather")
        if not weather:
            # No weather object at all — treat as unknown
            checkpoint_risks.append(CheckpointRisk(
                checkpoint_id=cp.get("checkpointId", ""),
                arrival_iso=cp.get("arrivalISO", ""),
                risk_level=RiskLevel.UNKNOWN,
                risk_label="unknown",
                wind=None, rain=None, snow=None,
                wind_mph=None, rain_in_per_hr=None, snowfall_in_per_hr=None,
                factors=["weather data missing"],
                matched_forecast_iso=None,
                time_match="missing",
            ))
            continue

        cp_risk = classify_checkpoint(
            checkpoint_id=cp.get("checkpointId", ""),
            arrival_iso=cp.get("arrivalISO", ""),
            wind_mph=weather.get("windMph"),
            rain_in_per_hr=weather.get("rainInPerHr"),
            snowfall_in_per_hr=weather.get("snowfallInPerHr"),
            load_lb=load_lb,
            matched_forecast_iso=weather.get("matchedForecastISO"),
            time_match=weather.get("timeMatch", "unknown"),
        )
        checkpoint_risks.append(cp_risk)

    route_summary = summarize_route_risk(route, checkpoint_risks)
    return checkpoint_risks, route_summary