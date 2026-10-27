"""Phase 7 backend tests -- deterministic route scoring & recommendation.

Covers (spec section 7 lexicographic priority):
- Priority order: fewest severe miles -> fewest high miles -> lowest avg
  risk -> shortest time; each level alone flips the winner.
- NOT a weighted sum: a case where any weighted aggregate would pick the
  other route but lexicographic must not.
- Tie determinism: same input -> identical rankedRouteIds on every call;
  full-value ties constructed in routeId-ascending input order so the
  documented stable ordering holds under either tie behavior.
- No Travel exclusion: ineligible routes never recommended, still ranked.
- All-ineligible -> "no_safe_route_found" with null recommendation.
- Single-route and fewer-than-three honesty (no fabricated entries).
- Explanations: deciding factor, unknown-coverage caveat, per-route text.
- Risk-mile math: severe/high miles == (category count x effective
  checkpoint interval), avg ordinal = mean over valid checkpoints only --
  exercised through the REAL risk.py -> routing payload -> scoring path.
- Payload shape: RouteRecommendation fields the API layer maps to
  recommendedRouteId / rankedRouteIds / routeExplanations.
- Unavailable risk data ("error" summary or missing summary) treated as
  unknown (worst) but still eligible.

Pure logic under test: no DB, no HTTP. Fixtures are literal dicts matching
the exact camelCase shapes routing.py produces (riskSummary payload and
route dicts). All strings ASCII; fixed ids/datetimes; tests independent.
"""

from datetime import datetime, timezone as dt_timezone

from django.test import SimpleTestCase

from core.services.scoring import (
    RouteRecommendation,
    RouteScore,
    compute_route_score,
    rank_and_recommend,
)
from core.services.checkpoints import sample_route_checkpoints
from core.services.risk import analyze_route_risk


_DEPARTURE_UTC = datetime(2099, 1, 1, 16, 0, 0, tzinfo=dt_timezone.utc)


# ---------------------------------------------------------------------------
# Fixture builders (literal dicts, camelCase -- exactly what routing.py hands
# to rank_and_recommend at the Phase 7 call site).
# ---------------------------------------------------------------------------

def make_route(
    route_id,
    duration_seconds,
    distance_miles=100.0,
    label=None,
    duration_readable=None,
    effective_interval_miles=25.0,
):
    """Literal route dict as the routing pipeline normalizes it."""
    return {
        "routeId": route_id,
        "label": label or "Route %s" % route_id,
        "geometry": {
            "type": "LineString",
            "coordinates": [[-87.6324, 41.882], [-104.9861, 39.7417]],
        },
        "distanceMeters": 1_609_344.0,
        "durationSeconds": duration_seconds,
        "distanceMiles": distance_miles,
        "durationReadable": duration_readable or "%.1f h" % (duration_seconds / 3600.0),
        "checkpointSummary": {"effectiveIntervalMiles": effective_interval_miles},
        "checkpoints": [],
    }


def make_risk_summary(
    route_id,
    severe_miles,
    high_miles,
    avg_risk_ordinal,
    no_travel_count=0,
    checkpoints_unknown=0,
    interval_miles=25.0,
    total_checkpoints=4,
):
    """Literal risk summary matching routing.py's riskSummary payload shape.

    Counts are derived from the miles/interval so the fixture stays
    internally consistent with risk.py's count x interval math.
    """
    severe_count = int(round(severe_miles / interval_miles))
    high_count = int(round(high_miles / interval_miles))
    valid = total_checkpoints - checkpoints_unknown
    low_count = max(0, valid - severe_count - high_count - no_travel_count)
    if no_travel_count:
        explanation = (
            "Route has %d No Travel checkpoint(s) -- not recommended for travel."
            % no_travel_count
        )
    elif severe_count:
        explanation = (
            "Route has %d Severe checkpoint(s); est. %.1f severe miles."
            % (severe_count, severe_miles)
        )
    else:
        explanation = "Route conditions checked."
    return {
        "routeId": route_id,
        "totalCheckpoints": total_checkpoints,
        "checkpointsWithWeather": valid,
        "checkpointsUnknown": checkpoints_unknown,
        "lowCount": low_count,
        "moderateCount": 0,
        "highCount": high_count,
        "severeCount": severe_count,
        "noTravelCount": no_travel_count,
        "severeMiles": severe_miles,
        "highMiles": high_miles,
        "avgRiskOrdinal": avg_risk_ordinal,
        "worstCheckpoint": None,
        "explanation": explanation,
    }


def ranked_ids(result):
    return [score.route_id for score in result.ranked_routes]


# ---------------------------------------------------------------------------
# 1. Lexicographic priority (spec section 7)
# ---------------------------------------------------------------------------

class LexicographicPriorityTests(SimpleTestCase):
    """Each priority level alone decides the winner when others are equal
    or better for the losing route."""

    def test_route_worse_only_on_severe_miles_loses(self):
        # A loses on severe miles alone, despite better high/avg/duration.
        route_a = make_route("rt_lex_a", 1800.0)          # 0.5 h
        route_b = make_route("rt_lex_b", 7200.0)          # 2.0 h
        # avg 1.5 kept plausible (severe-only corridor excludes low/unknown
        # checkpoints); ranking decides on priority 1 either way.
        summaries = [
            make_risk_summary("rt_lex_a", severe_miles=50.0, high_miles=0.0,
                              avg_risk_ordinal=1.5),
            make_risk_summary("rt_lex_b", severe_miles=49.9, high_miles=25.0,
                              avg_risk_ordinal=3.0),
        ]
        result = rank_and_recommend([route_a, route_b], summaries)
        self.assertEqual(ranked_ids(result), ["rt_lex_b", "rt_lex_a"])
        self.assertEqual(result.recommended_route_id, "rt_lex_b")

    def test_route_worse_only_on_high_miles_loses(self):
        # Severe miles tied; A loses on high miles alone despite better
        # avg risk and duration.
        route_a = make_route("rt_lex_a", 1800.0)
        route_b = make_route("rt_lex_b", 7200.0)
        summaries = [
            make_risk_summary("rt_lex_a", severe_miles=0.0, high_miles=50.0,
                              avg_risk_ordinal=0.0),
            make_risk_summary("rt_lex_b", severe_miles=0.0, high_miles=49.9,
                              avg_risk_ordinal=3.0),
        ]
        result = rank_and_recommend([route_a, route_b], summaries)
        self.assertEqual(ranked_ids(result), ["rt_lex_b", "rt_lex_a"])

    def test_route_worse_only_on_avg_risk_loses(self):
        # Severe and high tied; A loses on avg risk alone despite a much
        # shorter duration.
        route_a = make_route("rt_lex_a", 1800.0)
        route_b = make_route("rt_lex_b", 7200.0)
        summaries = [
            make_risk_summary("rt_lex_a", severe_miles=0.0, high_miles=0.0,
                              avg_risk_ordinal=2.5),
            make_risk_summary("rt_lex_b", severe_miles=0.0, high_miles=0.0,
                              avg_risk_ordinal=2.4),
        ]
        result = rank_and_recommend([route_a, route_b], summaries)
        self.assertEqual(ranked_ids(result), ["rt_lex_b", "rt_lex_a"])

    def test_route_worse_only_on_duration_loses(self):
        # First three levels tied; shortest travel time decides.
        route_a = make_route("rt_lex_a", 7200.0)
        route_b = make_route("rt_lex_b", 3600.0)
        summaries = [
            make_risk_summary("rt_lex_a", severe_miles=5.0, high_miles=5.0,
                              avg_risk_ordinal=1.0),
            make_risk_summary("rt_lex_b", severe_miles=5.0, high_miles=5.0,
                              avg_risk_ordinal=1.0),
        ]
        result = rank_and_recommend([route_a, route_b], summaries)
        self.assertEqual(ranked_ids(result), ["rt_lex_b", "rt_lex_a"])

    def test_lexicographic_beats_weighted_sum_flip(self):
        """Proves the ranking is lexicographic, not a weighted score.

        A is massively better on 3 of 4 metrics (high: 0 vs 10 mi,
        avg: 0.0 vs 3.0, duration: 1 h vs 100 h) and worse on severe by
        only 0.1 mi. A unit-weighted sum gives A=26.1 vs B=138.0, so any
        such weighted score would recommend A. Spec section 7 forbids
        that reversal: B wins on severe miles and must rank first.
        """
        route_a = make_route("rt_weight_fast", 3600.0)      # 1 h, clean otherwise
        route_b = make_route("rt_weight_slow", 360_000.0)   # 100 h
        summaries = [
            make_risk_summary("rt_weight_fast", severe_miles=25.1,
                              high_miles=0.0, avg_risk_ordinal=0.0),
            make_risk_summary("rt_weight_slow", severe_miles=25.0,
                              high_miles=10.0, avg_risk_ordinal=3.0),
        ]
        result = rank_and_recommend([route_a, route_b], summaries)
        self.assertEqual(ranked_ids(result), ["rt_weight_slow", "rt_weight_fast"])
        self.assertEqual(result.recommended_route_id, "rt_weight_slow")


# ---------------------------------------------------------------------------
# 2. Tie determinism
# ---------------------------------------------------------------------------

class TieDeterminismTests(SimpleTestCase):
    """Full-value ties: same input must give identical output every call.

    Routes are constructed in routeId-ascending input order, so the
    documented ordering holds under stable-sort (input order preserved)
    AND under an explicit routeId tiebreaker -- both yield routeId
    ascending. Determinism (same-in-same-out) is the spec requirement.
    """

    def _tied_routes(self):
        route_a = make_route("rt_tie_aaa", 3600.0)
        route_b = make_route("rt_tie_bbb", 3600.0)
        summaries = [
            make_risk_summary("rt_tie_aaa", severe_miles=10.0, high_miles=5.0,
                              avg_risk_ordinal=1.5),
            make_risk_summary("rt_tie_bbb", severe_miles=10.0, high_miles=5.0,
                              avg_risk_ordinal=1.5),
        ]
        return [route_a, route_b], summaries

    def test_full_tie_repeated_calls_identical(self):
        routes, summaries = self._tied_routes()
        first = rank_and_recommend(routes, summaries)
        second = rank_and_recommend(routes, summaries)
        self.assertEqual(ranked_ids(first), ranked_ids(second))
        self.assertEqual(first.recommended_route_id, second.recommended_route_id)
        self.assertEqual(first.status, second.status)

    def test_full_tie_routeid_ascending_when_input_sorted(self):
        routes, summaries = self._tied_routes()
        result = rank_and_recommend(routes, summaries)
        self.assertEqual(ranked_ids(result), ["rt_tie_aaa", "rt_tie_bbb"])
        self.assertEqual(result.recommended_route_id, "rt_tie_aaa")

    def test_three_way_tie_deterministic_shuffled_input(self):
        route_a = make_route("rt_tie_aaa", 3600.0)
        route_b = make_route("rt_tie_bbb", 3600.0)
        route_c = make_route("rt_tie_ccc", 3600.0)
        summaries = [
            make_risk_summary("rt_tie_aaa", severe_miles=0.0, high_miles=0.0,
                              avg_risk_ordinal=0.0),
            make_risk_summary("rt_tie_bbb", severe_miles=0.0, high_miles=0.0,
                              avg_risk_ordinal=0.0),
            make_risk_summary("rt_tie_ccc", severe_miles=0.0, high_miles=0.0,
                              avg_risk_ordinal=0.0),
        ]
        shuffled = [route_c, route_a, route_b]
        first = rank_and_recommend(shuffled, summaries)
        second = rank_and_recommend(shuffled, summaries)
        # Determinism: identical output for identical input, whichever way
        # full-value ties are resolved.
        self.assertEqual(ranked_ids(first), ranked_ids(second))
        self.assertEqual(sorted(ranked_ids(first)),
                         ["rt_tie_aaa", "rt_tie_bbb", "rt_tie_ccc"])
        self.assertEqual(len(set(ranked_ids(first))), 3)


# ---------------------------------------------------------------------------
# 3. No Travel exclusion
# ---------------------------------------------------------------------------

class NoTravelExclusionTests(SimpleTestCase):
    """A route with a No Travel checkpoint is never the recommendation."""

    def _routes(self):
        # No Travel route wins every ranking metric but is ineligible.
        no_travel = make_route("rt_nt_best", 1800.0)       # shortest, cleanest
        eligible = make_route("rt_nt_next", 7200.0)
        summaries = [
            make_risk_summary("rt_nt_best", severe_miles=0.0, high_miles=0.0,
                              avg_risk_ordinal=4.0, no_travel_count=2,
                              total_checkpoints=2),
            make_risk_summary("rt_nt_next", severe_miles=25.0, high_miles=25.0,
                              avg_risk_ordinal=5.0 / 3.0, no_travel_count=0,
                              total_checkpoints=3),
        ]
        return [no_travel, eligible], summaries

    def test_no_travel_route_not_recommended_despite_best_metrics(self):
        routes, summaries = self._routes()
        result = rank_and_recommend(routes, summaries)
        self.assertEqual(result.status, "recommended")
        self.assertEqual(result.recommended_route_id, "rt_nt_next")
        # The top-level explanation names only the recommended route.
        self.assertNotIn("rt_nt_best", result.explanation)
        self.assertNotEqual(result.recommended_route_id, "rt_nt_best")
        # Exclusion is flagged in the ineligible route's explanation.
        self.assertIn("No Travel", result.route_explanations["rt_nt_best"])
        self.assertIn("cannot be recommended",
                      result.route_explanations["rt_nt_best"])

    def test_no_travel_route_still_ranked_for_transparency(self):
        routes, summaries = self._routes()
        result = rank_and_recommend(routes, summaries)
        # Ineligible route still appears in the ranking (first: it wins the
        # raw lexicographic tuple) but is never the recommendation.
        self.assertIn("rt_nt_best", ranked_ids(result))
        self.assertEqual(ranked_ids(result)[0], "rt_nt_best")
        self.assertEqual(ranked_ids(result)[1], "rt_nt_next")

    def test_recommended_is_first_eligible_not_first_ranked(self):
        routes, summaries = self._routes()
        result = rank_and_recommend(routes, summaries)
        self.assertNotEqual(result.recommended_route_id, ranked_ids(result)[0])
        self.assertEqual(result.recommended_route_id, "rt_nt_next")


# ---------------------------------------------------------------------------
# 4. All routes ineligible
# ---------------------------------------------------------------------------

class AllIneligibleTests(SimpleTestCase):
    """Every route has No Travel -> 'no_safe_route_found'."""

    def test_all_no_travel_reports_no_safe_route(self):
        routes = [
            make_route("rt_allnt_a", 3600.0),
            make_route("rt_allnt_b", 7200.0),
            make_route("rt_allnt_c", 10_800.0),
        ]
        summaries = [
            make_risk_summary("rt_allnt_a", severe_miles=0.0, high_miles=0.0,
                              avg_risk_ordinal=4.0, no_travel_count=1,
                              total_checkpoints=1),
            make_risk_summary("rt_allnt_b", severe_miles=25.0, high_miles=0.0,
                              avg_risk_ordinal=3.5, no_travel_count=1,
                              total_checkpoints=2),
            make_risk_summary("rt_allnt_c", severe_miles=0.0, high_miles=25.0,
                              avg_risk_ordinal=10.0 / 3.0, no_travel_count=2,
                              total_checkpoints=3),
        ]
        result = rank_and_recommend(routes, summaries)
        self.assertEqual(result.status, "no_safe_route_found")
        self.assertIsNone(result.recommended_route_id)
        # Exact spec wording from scoring.py (ASCII source line).
        self.assertEqual(
            result.explanation,
            "All routes contain No Travel checkpoint(s). No safe route found.",
        )
        # Ranking is still produced for transparency.
        self.assertEqual(
            sorted(ranked_ids(result)),
            ["rt_allnt_a", "rt_allnt_b", "rt_allnt_c"],
        )
        self.assertEqual(len(result.route_explanations), 3)


# ---------------------------------------------------------------------------
# 5. Single route
# ---------------------------------------------------------------------------

class SingleRouteTests(SimpleTestCase):
    def test_single_route_trivially_recommended_with_explanation(self):
        route = make_route("rt_solo", 3600.0)
        summaries = [make_risk_summary("rt_solo", severe_miles=0.0,
                                       high_miles=0.0, avg_risk_ordinal=0.5)]
        result = rank_and_recommend([route], summaries)
        self.assertEqual(result.status, "recommended")
        self.assertEqual(ranked_ids(result), ["rt_solo"])
        self.assertEqual(result.recommended_route_id, "rt_solo")
        self.assertTrue(result.explanation)
        self.assertIn("rt_solo", result.explanation)
        self.assertIn("rt_solo", result.route_explanations)
        self.assertTrue(result.route_explanations["rt_solo"])


# ---------------------------------------------------------------------------
# 6. Fewer than three routes (provider honesty)
# ---------------------------------------------------------------------------

class FewerThanThreeTests(SimpleTestCase):
    def test_two_routes_ranked_without_fabrication(self):
        route_a = make_route("rt_two_a", 7200.0)
        route_b = make_route("rt_two_b", 3600.0)
        summaries = [
            make_risk_summary("rt_two_a", severe_miles=0.0, high_miles=0.0,
                              avg_risk_ordinal=1.0),
            make_risk_summary("rt_two_b", severe_miles=0.0, high_miles=0.0,
                              avg_risk_ordinal=1.0),
        ]
        result = rank_and_recommend([route_a, route_b], summaries)
        self.assertEqual(result.status, "recommended")
        self.assertEqual(ranked_ids(result), ["rt_two_b", "rt_two_a"])
        self.assertEqual(result.recommended_route_id, "rt_two_b")
        # No fabricated entries: exactly the two real route ids.
        self.assertEqual(set(result.route_explanations), {"rt_two_a", "rt_two_b"})
        self.assertEqual(len(result.route_explanations), 2)

    def test_zero_routes_reports_no_routes(self):
        result = rank_and_recommend([], None)
        self.assertEqual(result.status, "no_routes")
        self.assertIsNone(result.recommended_route_id)
        self.assertEqual(ranked_ids(result), [])
        self.assertEqual(
            result.explanation,
            "No routes were returned by the routing provider.",
        )
        self.assertEqual(result.route_explanations, {})


# ---------------------------------------------------------------------------
# 7. Explanations
# ---------------------------------------------------------------------------

class ExplanationTests(SimpleTestCase):
    def test_explanation_names_deciding_factor(self):
        # Routes differ ONLY on severe miles: B (0 severe) beats A (25).
        route_a = make_route("rt_exp_loser", 3600.0)
        route_b = make_route("rt_exp_winner", 3600.0)
        summaries = [
            make_risk_summary("rt_exp_loser", severe_miles=25.0,
                              high_miles=0.0, avg_risk_ordinal=1.0),
            make_risk_summary("rt_exp_winner", severe_miles=0.0,
                              high_miles=0.0, avg_risk_ordinal=1.0),
        ]
        result = rank_and_recommend([route_a, route_b], summaries)
        # Top-level explanation names the winner and the priority chain.
        self.assertIn("Recommended: rt_exp_winner", result.explanation)
        self.assertIn("fewest severe miles", result.explanation)
        # The losing route's explanation cites its severe-risk miles, and
        # the winner's does not (it has none).
        self.assertIn("severe-risk miles", result.route_explanations["rt_exp_loser"])
        self.assertNotIn("severe-risk miles",
                         result.route_explanations["rt_exp_winner"])

    def test_unknown_checkpoint_coverage_caveat(self):
        # Sampling-approximation honesty: unknown checkpoints are surfaced
        # as excluded from the average, and only when they exist.
        route_unknown = make_route("rt_cov_unknown", 3600.0)
        route_known = make_route("rt_cov_known", 3600.0)
        summaries = [
            make_risk_summary("rt_cov_unknown", severe_miles=0.0,
                              high_miles=0.0, avg_risk_ordinal=1.0,
                              checkpoints_unknown=2, total_checkpoints=6),
            make_risk_summary("rt_cov_known", severe_miles=0.0,
                              high_miles=0.0, avg_risk_ordinal=1.0,
                              checkpoints_unknown=0, total_checkpoints=4),
        ]
        result = rank_and_recommend([route_unknown, route_known], summaries)
        self.assertIn("checkpoint(s) with unknown weather",
                      result.route_explanations["rt_cov_unknown"])
        self.assertIn("excluded from average risk",
                      result.route_explanations["rt_cov_unknown"])
        self.assertNotIn("unknown weather",
                         result.route_explanations["rt_cov_known"])

    def test_per_route_explanations_cover_all_routes_with_ranks(self):
        routes = [
            make_route("rt_exp_c", 10_800.0),
            make_route("rt_exp_a", 3600.0),
            make_route("rt_exp_b", 7200.0),
        ]
        summaries = [
            make_risk_summary("rt_exp_c", severe_miles=50.0, high_miles=25.0,
                              avg_risk_ordinal=3.0),
            make_risk_summary("rt_exp_a", severe_miles=0.0, high_miles=0.0,
                              avg_risk_ordinal=0.0),
            make_risk_summary("rt_exp_b", severe_miles=25.0, high_miles=0.0,
                              avg_risk_ordinal=1.0),
        ]
        result = rank_and_recommend(routes, summaries)
        self.assertEqual(ranked_ids(result),
                         ["rt_exp_a", "rt_exp_b", "rt_exp_c"])
        self.assertEqual(set(result.route_explanations),
                         {"rt_exp_a", "rt_exp_b", "rt_exp_c"})
        for text in result.route_explanations.values():
            self.assertTrue(text)
        self.assertIn("Ranked 1st", result.route_explanations["rt_exp_a"])
        self.assertIn("Ranked 2nd", result.route_explanations["rt_exp_b"])
        self.assertIn("Ranked 3rd", result.route_explanations["rt_exp_c"])


# ---------------------------------------------------------------------------
# 8. Risk-mile math (real risk.py -> payload -> scoring path)
# ---------------------------------------------------------------------------

def _weather(wind_mph):
    return {
        "windMph": wind_mph,
        "rainInPerHr": 0.0,
        "snowfallInPerHr": 0.0,
        "matchedForecastISO": "2099-01-01T16:00",
        "timeMatch": "exact",
    }


def _sampled_pipeline_route(route_id, coordinates, duration_seconds):
    """Route with Phase 4 checkpoints sampled exactly like test_weather."""
    route = {
        "routeId": route_id,
        "label": "Route %s" % route_id,
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "distanceMeters": 1_609_344.0,
        "durationSeconds": duration_seconds,
        "distanceMiles": 1000.0,
        "durationReadable": "%.1f h" % (duration_seconds / 3600.0),
    }
    sampled = sample_route_checkpoints(route, _DEPARTURE_UTC, 25, 500)
    route["checkpoints"] = sampled["checkpoints"]
    route["checkpointSummary"] = sampled["summary"]
    return route


def _risk_summary_payload(route_risk):
    """Serialize RouteRiskSummary exactly as routing.py's Phase 6 block."""
    return {
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


# Latitude fixed: 1 degree of longitude here is roughly 51 miles, so the
# two-point line is under one 25-mi interval (2 checkpoints) and the
# three-point line lands between one and two intervals (3 checkpoints).
_LAT = 41.8820
_LINE_2CP = [[-87.6324, _LAT], [-87.2, _LAT]]
_LINE_3CP = [[-87.6324, _LAT], [-87.2, _LAT], [-86.9, _LAT]]


class RiskMileMathTests(SimpleTestCase):
    """severeMiles/highMiles = category count x effectiveIntervalMiles,
    avgRiskOrdinal = mean ordinal over valid (non-unknown) checkpoints.
    Exercised through the real sampling -> risk -> scoring chain."""

    def test_severe_miles_from_single_severe_checkpoint(self):
        route = _sampled_pipeline_route("rt_math_sev", _LINE_2CP, 3600.0)
        self.assertEqual(len(route["checkpoints"]), 2)
        route["checkpoints"][0]["weather"] = _weather(10.0)   # Low
        route["checkpoints"][1]["weather"] = _weather(50.0)   # Severe (load 30k)
        checkpoint_risks, route_risk = analyze_route_risk(route, 30_000)
        self.assertEqual(route_risk.severe_count, 1)
        interval = route["checkpointSummary"]["effectiveIntervalMiles"]
        self.assertEqual(route_risk.severe_miles, 1 * interval)
        self.assertEqual(route_risk.high_miles, 0.0)
        result = rank_and_recommend([route], [_risk_summary_payload(route_risk)])
        score = result.ranked_routes[0]
        self.assertEqual(score.route_id, "rt_math_sev")
        self.assertEqual(score.severe_miles, interval)
        self.assertEqual(score.high_miles, 0.0)
        self.assertEqual(score.no_travel_count, 0)
        self.assertTrue(score.is_eligible)
        self.assertEqual(result.recommended_route_id, "rt_math_sev")

    def test_high_miles_from_two_high_checkpoints(self):
        route = _sampled_pipeline_route("rt_math_high", _LINE_3CP, 7200.0)
        self.assertEqual(len(route["checkpoints"]), 3)
        route["checkpoints"][0]["weather"] = _weather(10.0)   # Low
        route["checkpoints"][1]["weather"] = _weather(40.0)   # High
        route["checkpoints"][2]["weather"] = _weather(40.0)   # High
        _, route_risk = analyze_route_risk(route, 30_000)
        self.assertEqual(route_risk.high_count, 2)
        interval = route["checkpointSummary"]["effectiveIntervalMiles"]
        self.assertEqual(route_risk.high_miles, 2 * interval)
        self.assertEqual(route_risk.severe_miles, 0.0)
        result = rank_and_recommend([route], [_risk_summary_payload(route_risk)])
        score = result.ranked_routes[0]
        self.assertEqual(score.high_miles, 2 * interval)
        self.assertEqual(score.severe_miles, 0.0)

    def test_avg_risk_ordinal_excludes_unknown_checkpoints(self):
        route = _sampled_pipeline_route("rt_math_avg", _LINE_3CP, 7200.0)
        self.assertEqual(len(route["checkpoints"]), 3)
        route["checkpoints"][0]["weather"] = _weather(10.0)   # Low  -> 0
        route["checkpoints"][1]["weather"] = _weather(50.0)   # Severe -> 3
        # Checkpoint 3 gets NO weather object -> unknown, excluded from avg.
        _, route_risk = analyze_route_risk(route, 30_000)
        self.assertEqual(route_risk.checkpoints_unknown, 1)
        self.assertEqual(route_risk.checkpoints_with_weather, 2)
        self.assertAlmostEqual(route_risk.avg_risk_ordinal, (0 + 3) / 2)
        result = rank_and_recommend([route], [_risk_summary_payload(route_risk)])
        score = result.ranked_routes[0]
        self.assertAlmostEqual(score.avg_risk_ordinal, 1.5)
        self.assertTrue(score.is_eligible)
        # Coverage caveat is surfaced for the unknown checkpoint.
        self.assertIn("1 checkpoint(s) with unknown weather",
                      result.route_explanations["rt_math_avg"])


# ---------------------------------------------------------------------------
# 9. Payload shape
# ---------------------------------------------------------------------------

class PayloadShapeTests(SimpleTestCase):
    def test_recommendation_payload_fields_and_types(self):
        routes = [
            make_route("rt_shape_b", 7200.0),
            make_route("rt_shape_a", 3600.0),
            make_route("rt_shape_c", 10_800.0),
        ]
        summaries = [
            make_risk_summary("rt_shape_b", severe_miles=0.0, high_miles=25.0,
                              avg_risk_ordinal=2.0),
            make_risk_summary("rt_shape_a", severe_miles=0.0, high_miles=0.0,
                              avg_risk_ordinal=1.0),
            make_risk_summary("rt_shape_c", severe_miles=25.0, high_miles=0.0,
                              avg_risk_ordinal=3.0),
        ]
        result = rank_and_recommend(routes, summaries)
        self.assertIsInstance(result, RouteRecommendation)
        self.assertIsInstance(result.ranked_routes, list)
        for score in result.ranked_routes:
            self.assertIsInstance(score, RouteScore)
        self.assertEqual(ranked_ids(result),
                         ["rt_shape_a", "rt_shape_b", "rt_shape_c"])
        self.assertIsInstance(result.recommended_route_id, str)
        self.assertEqual(result.recommended_route_id,
                         result.ranked_routes[0].route_id)
        self.assertIn(result.status, {"recommended", "no_safe_route_found",
                                      "no_routes", "scoring_unavailable"})
        self.assertEqual(result.status, "recommended")
        self.assertIsInstance(result.explanation, str)
        self.assertTrue(result.explanation)
        self.assertIsInstance(result.route_explanations, dict)
        self.assertEqual(set(result.route_explanations),
                         {score.route_id for score in result.ranked_routes})
        # RouteScore carries every field the API mapping needs.
        first = result.ranked_routes[0]
        self.assertEqual(first.severe_miles, 0.0)
        self.assertEqual(first.high_miles, 0.0)
        self.assertEqual(first.avg_risk_ordinal, 1.0)
        self.assertEqual(first.duration_seconds, 3600.0)
        self.assertEqual(first.no_travel_count, 0)
        self.assertTrue(first.is_eligible)


# ---------------------------------------------------------------------------
# 10. Unavailable risk data
# ---------------------------------------------------------------------------

class UnavailableRiskTests(SimpleTestCase):
    """Risk summaries with an error (or missing entirely) are treated as
    unknown: worst for ranking (None -> infinity), still eligible."""

    def test_error_summary_treated_as_unknown_but_eligible(self):
        good = make_route("rt_risk_good", 7200.0)
        errored = make_route("rt_risk_err", 3600.0)
        summaries = [
            # Plausible fixture: counts stay within the 4-checkpoint corridor.
            make_risk_summary("rt_risk_good", severe_miles=100.0,
                              high_miles=0.0, avg_risk_ordinal=3.0),
            {"routeId": "rt_risk_err", "error": "Risk analysis unavailable"},
        ]
        result = rank_and_recommend([good, errored], summaries)
        # Unknown metrics rank worst despite the shorter duration.
        self.assertEqual(ranked_ids(result), ["rt_risk_good", "rt_risk_err"])
        self.assertEqual(result.recommended_route_id, "rt_risk_good")
        err_score = result.ranked_routes[1]
        self.assertIsNone(err_score.severe_miles)
        self.assertIsNone(err_score.high_miles)
        self.assertIsNone(err_score.avg_risk_ordinal)
        self.assertEqual(err_score.no_travel_count, 0)
        self.assertTrue(err_score.is_eligible)
        # Explanation honestly reports the unknowns.
        self.assertIn("severe mi: unknown",
                      result.route_explanations["rt_risk_err"])
        self.assertIn("avg risk: unknown",
                      result.route_explanations["rt_risk_err"])

    def test_missing_summary_treated_as_unknown_but_eligible(self):
        good = make_route("rt_risk_good", 7200.0)
        orphan = make_route("rt_risk_orphan", 3600.0)  # no summary passed
        summaries = [
            # Plausible fixture: counts stay within the 4-checkpoint corridor.
            make_risk_summary("rt_risk_good", severe_miles=100.0,
                              high_miles=0.0, avg_risk_ordinal=3.0),
        ]
        result = rank_and_recommend([good, orphan], summaries)
        self.assertEqual(ranked_ids(result), ["rt_risk_good", "rt_risk_orphan"])
        orphan_score = result.ranked_routes[1]
        self.assertIsNone(orphan_score.severe_miles)
        self.assertTrue(orphan_score.is_eligible)
        # compute_route_score agrees directly.
        direct = compute_route_score(orphan, None)
        self.assertIsNone(direct.severe_miles)
        self.assertTrue(direct.is_eligible)
        self.assertEqual(direct.to_tuple(),
                         (float("inf"), float("inf"), float("inf"), 3600.0))
