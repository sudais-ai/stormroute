"""Deterministic Route Scoring & Recommendation (Phase 7).

Implements the exact lexicographic ranking mandated by the assessment specification.

SPEC MAPPING (verbatim from docs/ASSESSMENT_SPEC.md §7):

Route recommendation priority order (unchangeable, deterministic lexicographic comparison):

1. Fewest **Severe-risk** miles
2. Fewest **High-risk** miles
3. Lowest **average risk**
4. Shortest **travel time**

- Do not replace with a weighted score that could reverse the order.
- A route containing a No Travel checkpoint **must not** be presented as a safe recommendation.
- If all three candidates violate No Travel rules → display "No safe route found" and explain why.
- Risk miles from discrete checkpoints are estimates; document the sampling approximation; do not claim continuous road-level certainty.

Average risk computation (from docs/DECISIONS.md):
- Mean ordinal index over checkpoint risks: Low=0, Moderate=1, High=2, Severe=3, No Travel=4
- Excludes unknown checkpoints
- Keeps No Travel-dominant routes from winning average despite tie-breaks

Determinism:
- Pure functions, no I/O, no global state, no randomness.
- Same input + same config → identical output every time.

No Travel handling:
- Routes with no_travel_count > 0 are marked as ineligible for recommendation
- They still participate in ranking for transparency but are never the "recommended" route
- If all routes have no_travel_count > 0, result is "no_safe_route_found"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RouteScore:
    """Lexicographic score tuple for a route.

    Comparison is done field-by-field in order:
    1. severe_miles (fewer is better)
    2. high_miles (fewer is better)
    3. avg_risk_ordinal (lower is better)
    4. duration_seconds (shorter is better)

    All values are None-safe: None is treated as worst (infinite).
    """

    route_id: str
    severe_miles: float | None
    high_miles: float | None
    avg_risk_ordinal: float | None
    duration_seconds: float | None
    no_travel_count: int
    # Derived for convenience
    is_eligible: bool  # False if no_travel_count > 0

    def to_tuple(self) -> tuple[float | None, float | None, float | None, float | None]:
        """Convert to comparison tuple. None treated as infinity (worst)."""
        return (
            self.severe_miles if self.severe_miles is not None else float("inf"),
            self.high_miles if self.high_miles is not None else float("inf"),
            self.avg_risk_ordinal if self.avg_risk_ordinal is not None else float("inf"),
            self.duration_seconds if self.duration_seconds is not None else float("inf"),
        )

    def __lt__(self, other: "RouteScore") -> bool:
        if not isinstance(other, RouteScore):
            return NotImplemented
        return self.to_tuple() < other.to_tuple()

    def __le__(self, other: "RouteScore") -> bool:
        if not isinstance(other, RouteScore):
            return NotImplemented
        return self.to_tuple() <= other.to_tuple()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RouteScore):
            return NotImplemented
        return self.to_tuple() == other.to_tuple()


@dataclass(frozen=True)
class RouteRecommendation:
    """Recommendation result for a set of routes."""

    # All routes with their scores, sorted by ranking (best first)
    ranked_routes: list[RouteScore]
    # The recommended route (best eligible), or None if no eligible route
    recommended_route_id: str | None
    # "recommended" | "no_safe_route_found" | "no_routes" | "scoring_unavailable"
    status: str
    # Human-readable explanation
    explanation: str
    # Per-route explanations for UI
    route_explanations: dict[str, str]


def _safe_float(val: Any) -> float | None:
    """Safely convert to float, return None on failure."""
    try:
        f = float(val)
        return f if f >= 0 else None
    except (TypeError, ValueError):
        return None


def _safe_int(val: Any) -> int | None:
    """Safely convert to int, return None on failure."""
    try:
        i = int(val)
        return i if i >= 0 else None
    except (TypeError, ValueError):
        return None


def compute_route_score(route: dict, risk_summary: dict | None) -> RouteScore:
    """Compute the lexicographic score tuple for a single route.

    Args:
        route: Route dict with distanceMiles, durationSeconds, checkpointSummary
        risk_summary: RouteRiskSummary dict from Phase 6

    Returns:
        RouteScore with all components needed for lexicographic comparison
    """
    route_id = route.get("routeId", "")

    # Extract risk data
    if risk_summary and "error" not in risk_summary:
        severe_miles = _safe_float(risk_summary.get("severeMiles"))
        high_miles = _safe_float(risk_summary.get("highMiles"))
        avg_risk_ordinal = _safe_float(risk_summary.get("avgRiskOrdinal"))
        no_travel_count = _safe_int(risk_summary.get("noTravelCount")) or 0
    else:
        # Risk analysis unavailable — treat as unknown (worst for ranking)
        severe_miles = None
        high_miles = None
        avg_risk_ordinal = None
        no_travel_count = 0

    # Duration from route
    duration_seconds = _safe_float(route.get("durationSeconds"))

    # Eligibility: No Travel checkpoints make route ineligible for recommendation
    is_eligible = no_travel_count == 0

    return RouteScore(
        route_id=route_id,
        severe_miles=severe_miles,
        high_miles=high_miles,
        avg_risk_ordinal=avg_risk_ordinal,
        duration_seconds=duration_seconds,
        no_travel_count=no_travel_count,
        is_eligible=is_eligible,
    )


def _score_to_str(score: RouteScore) -> str:
    """Human-readable score tuple for explanations."""
    parts = []
    parts.append(
        f"{score.severe_miles:.1f} severe mi"
        if score.severe_miles is not None
        else "severe mi: unknown"
    )
    parts.append(
        f"{score.high_miles:.1f} high mi"
        if score.high_miles is not None
        else "high mi: unknown"
    )
    parts.append(
        f"avg risk {score.avg_risk_ordinal:.2f}"
        if score.avg_risk_ordinal is not None
        else "avg risk: unknown"
    )
    parts.append(
        f"{score.duration_seconds / 3600:.1f} h"
        if score.duration_seconds is not None
        else "duration: unknown"
    )
    return " | ".join(parts)


def _route_explanation(route: dict, risk_summary: dict | None, score: RouteScore, rank: int) -> str:
    """Generate human-readable explanation for a route's ranking."""
    route_id = route.get("routeId", "")
    label = route.get("label", f"Route {route_id[:8]}")

    parts = []

    # No Travel status
    no_travel = score.no_travel_count
    if no_travel > 0:
        parts.append(f"Contains {no_travel} No Travel checkpoint(s) — cannot be recommended.")

    # Rank
    ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(rank, f"{rank}th")
    parts.append(f"Ranked {ordinal} ({_score_to_str(score)}).")

    # Breakdown
    if score.severe_miles is not None and score.severe_miles > 0:
        parts.append(f"Has {score.severe_miles:.1f} severe-risk miles.")
    if score.high_miles is not None and score.high_miles > 0:
        parts.append(f"Has {score.high_miles:.1f} high-risk miles.")

    # Average risk
    if score.avg_risk_ordinal is not None:
        risk_labels = ["Low", "Moderate", "High", "Severe", "No Travel"]
        idx = int(round(score.avg_risk_ordinal))
        if 0 <= idx < len(risk_labels):
            parts.append(f"Average checkpoint risk: {risk_labels[idx]} ({score.avg_risk_ordinal:.2f}).")

    # Distance and duration
    dist = route.get("distanceMiles")
    dur = route.get("durationReadable")
    if dist is not None:
        parts.append(f"Distance: {dist:.1f} mi.")
    if dur:
        parts.append(f"Est. driving time: {dur}.")

    # Coverage caveat
    if risk_summary and risk_summary.get("checkpointsUnknown", 0) > 0:
        unk = risk_summary["checkpointsUnknown"]
        parts.append(f"Note: {unk} checkpoint(s) with unknown weather (excluded from average risk).")

    return " ".join(parts)


def rank_and_recommend(
    routes: list[dict],
    risk_summaries: list[dict] | None,
) -> RouteRecommendation:
    """Rank routes by lexicographic score and determine recommendation.

    Lexicographic order (spec §7):
    1. Fewest Severe-risk miles
    2. Fewest High-risk miles
    3. Lowest average risk (mean ordinal)
    4. Shortest travel time

    No Travel handling:
    - Routes with no_travel_count > 0 are ineligible for recommendation
    - If all routes ineligible → "no_safe_route_found"
    - Ineligible routes still ranked for transparency

    Args:
        routes: List of route dicts from routing pipeline
        risk_summaries: List of RouteRiskSummary dicts from Phase 6

    Returns:
        RouteRecommendation with ranked routes, recommended route, status, and explanations
    """
    # Map risk summaries by routeId for quick lookup
    risk_by_id = {}
    if risk_summaries:
        for rs in risk_summaries:
            if isinstance(rs, dict) and "routeId" in rs:
                risk_by_id[rs["routeId"]] = rs

    # Compute scores for all routes
    scores = []
    for route in routes:
        risk = risk_by_id.get(route.get("routeId"))
        scores.append(compute_route_score(route, risk))

    # Sort by lexicographic score (best first)
    ranked = sorted(scores)

    # Find best eligible route
    recommended = None
    for s in ranked:
        if s.is_eligible:
            recommended = s
            break

    # Determine status
    if not routes:
        status = "no_routes"
        explanation = "No routes were returned by the routing provider."
    elif recommended is None:
        # All routes have No Travel
        status = "no_safe_route_found"
        explanation = "All routes contain No Travel checkpoint(s). No safe route found."
    else:
        status = "recommended"
        explanation = f"Recommended: {recommended.route_id} — best eligible route by lexicographic ranking (fewest severe miles → fewest high miles → lowest avg risk → shortest time)."

    # Generate per-route explanations
    route_explanations = {}
    for rank, score in enumerate(ranked, 1):
        route = next(r for r in routes if r.get("routeId") == score.route_id)
        risk = risk_by_id.get(score.route_id)
        route_explanations[score.route_id] = _route_explanation(route, risk, score, rank)

    return RouteRecommendation(
        ranked_routes=ranked,
        recommended_route_id=recommended.route_id if recommended else None,
        status=status,
        explanation=explanation,
        route_explanations=route_explanations,
    )