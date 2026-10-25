"""Phase 6 backend tests — deterministic weather risk engine.

Covers:
- Wind classification at every boundary value (spec §4 wind table)
- Rain classification at every boundary value (spec §4 rain table)
- Snow classification at every boundary value (spec §4 snow table)
- Load rules (spec §5): No Travel at ≥55 any load; 45–55 + >30k lb; 35–45 + >40k lb → Severe
- Combined checkpoint risk: max of conditions, No Travel precedence (spec §6)
- Unknown data handling: missing/invalid fields → unknown (NOT low)
- Route aggregation: category counts, severe/high miles, avg risk, worst checkpoint
- Deterministic repeated results
- Configurable thresholds via Django settings
- No database persistence, no credential leakage
- No changes to route geometry, distance, duration, ETA
"""

import math
from dataclasses import replace
from django.test import SimpleTestCase, TestCase, override_settings

from core.services import risk as risk_service
from core.services.risk import (
    RiskLevel,
    CheckpointRisk,
    RouteRiskSummary,
    classify_wind,
    classify_rain,
    classify_snow,
    combine_checkpoint_risks,
    classify_checkpoint,
    analyze_route_risk,
    _load_risk_config,
)


class WindClassificationTests(SimpleTestCase):
    """Wind speed classification per spec §4 + §5 load rules.

    Spec boundaries (mph, lower inclusive, upper exclusive unless noted):
      Low       : < 25
      Moderate  : 25 – < 35
      High      : 35 – < 45
      Severe    : 45 – < 55
      No Travel : ≥ 55

    Load rules (spec §5):
      - Wind ≥ 55 mph → No Travel for EVERY load
      - Wind 45 ≤ w < 55 AND load > 30,000 lb → No Travel
      - Wind 35 ≤ w < 45 AND load > 40,000 lb → Severe
    """

    def _cfg(self):
        return _load_risk_config()

    def test_wind_low_under_25(self):
        lvl, factors = classify_wind(24.9, None, self._cfg())
        self.assertEqual(lvl, RiskLevel.LOW)
        self.assertTrue(any("Low" in f for f in factors))

    def test_wind_exact_25_is_moderate(self):
        lvl, _ = classify_wind(25.0, None, self._cfg())
        self.assertEqual(lvl, RiskLevel.MODERATE)

    def test_wind_moderate_25_to_under_35(self):
        lvl, _ = classify_wind(34.9, None, self._cfg())
        self.assertEqual(lvl, RiskLevel.MODERATE)

    def test_wind_exact_35_is_high(self):
        lvl, _ = classify_wind(35.0, None, self._cfg())
        self.assertEqual(lvl, RiskLevel.HIGH)

    def test_wind_high_35_to_under_45(self):
        lvl, _ = classify_wind(44.9, None, self._cfg())
        self.assertEqual(lvl, RiskLevel.HIGH)

    def test_wind_exact_45_is_severe(self):
        lvl, _ = classify_wind(45.0, None, self._cfg())
        self.assertEqual(lvl, RiskLevel.SEVERE)

    def test_wind_severe_45_to_under_55(self):
        lvl, _ = classify_wind(54.9, None, self._cfg())
        self.assertEqual(lvl, RiskLevel.SEVERE)

    def test_wind_exact_55_is_no_travel(self):
        lvl, factors = classify_wind(55.0, None, self._cfg())
        self.assertEqual(lvl, RiskLevel.NO_TRAVEL)
        self.assertTrue(any("No Travel" in f for f in factors))

    def test_wind_over_55_is_no_travel(self):
        lvl, _ = classify_wind(60.0, None, self._cfg())
        self.assertEqual(lvl, RiskLevel.NO_TRAVEL)

    # Load rule: wind ≥ 55 → No Travel ANY load
    def test_wind_55_heavy_load_no_travel_any_load(self):
        lvl, factors = classify_wind(55.0, 45000, self._cfg())
        self.assertEqual(lvl, RiskLevel.NO_TRAVEL)
        self.assertTrue(any("any load" in f for f in factors))

    def test_wind_60_light_load_no_travel_any_load(self):
        lvl, _ = classify_wind(60.0, 10000, self._cfg())
        self.assertEqual(lvl, RiskLevel.NO_TRAVEL)

    # Load rule: wind 45–<55 AND load > 30,000 → No Travel
    def test_wind_45_load_30001_no_travel(self):
        lvl, factors = classify_wind(45.0, 30001, self._cfg())
        self.assertEqual(lvl, RiskLevel.NO_TRAVEL)
        self.assertTrue(any("> 30,000" in f for f in factors))

    def test_wind_50_load_30001_no_travel(self):
        lvl, _ = classify_wind(50.0, 30001, self._cfg())
        self.assertEqual(lvl, RiskLevel.NO_TRAVEL)

    def test_wind_45_load_30000_not_no_travel(self):
        lvl, _ = classify_wind(45.0, 30000, self._cfg())
        self.assertEqual(lvl, RiskLevel.SEVERE)  # base wind rule

    def test_wind_54_load_30000_not_no_travel(self):
        lvl, _ = classify_wind(54.0, 30000, self._cfg())
        self.assertEqual(lvl, RiskLevel.SEVERE)

    # Load rule: wind 35–<45 AND load > 40,000 → Severe
    def test_wind_35_load_40001_severe(self):
        lvl, factors = classify_wind(35.0, 40001, self._cfg())
        self.assertEqual(lvl, RiskLevel.SEVERE)
        self.assertTrue(any("> 40,000" in f for f in factors))

    def test_wind_44_load_40001_severe(self):
        lvl, _ = classify_wind(44.0, 40001, self._cfg())
        self.assertEqual(lvl, RiskLevel.SEVERE)

    def test_wind_35_load_40000_not_severe(self):
        lvl, _ = classify_wind(35.0, 40000, self._cfg())
        self.assertEqual(lvl, RiskLevel.HIGH)  # base wind rule

    def test_wind_44_load_40000_not_severe(self):
        lvl, _ = classify_wind(44.0, 40000, self._cfg())
        self.assertEqual(lvl, RiskLevel.HIGH)

    # None / invalid / negative → unknown
    def test_wind_none_is_unknown(self):
        lvl, factors = classify_wind(None, None, self._cfg())
        self.assertEqual(lvl, RiskLevel.UNKNOWN)
        self.assertTrue(any("unavailable" in f for f in factors))

    def test_wind_negative_is_unknown(self):
        lvl, _ = classify_wind(-5.0, None, self._cfg())
        self.assertEqual(lvl, RiskLevel.UNKNOWN)

    def test_wind_nan_is_unknown(self):
        lvl, _ = classify_wind(float("nan"), None, self._cfg())
        self.assertEqual(lvl, RiskLevel.UNKNOWN)


class RainClassificationTests(SimpleTestCase):
    """Rainfall rate classification per spec §4 (in/hr).

    Spec boundaries (lower inclusive, upper exclusive except Severe upper bound ≤ 1.00):
      Low       : < 0.10
      Moderate  : 0.10 – < 0.25
      High      : 0.25 – < 0.50
      Severe    : 0.50 – ≤ 1.00  (inclusive upper bound per spec)
      No Travel : > 1.00
    """

    def _cfg(self):
        return _load_risk_config()

    def test_rain_low_under_010(self):
        lvl, _ = classify_rain(0.099, self._cfg())
        self.assertEqual(lvl, RiskLevel.LOW)

    def test_rain_exact_010_is_moderate(self):
        lvl, _ = classify_rain(0.10, self._cfg())
        self.assertEqual(lvl, RiskLevel.MODERATE)

    def test_rain_moderate_010_to_under_025(self):
        lvl, _ = classify_rain(0.249, self._cfg())
        self.assertEqual(lvl, RiskLevel.MODERATE)

    def test_rain_exact_025_is_high(self):
        lvl, _ = classify_rain(0.25, self._cfg())
        self.assertEqual(lvl, RiskLevel.HIGH)

    def test_rain_high_025_to_under_050(self):
        lvl, _ = classify_rain(0.499, self._cfg())
        self.assertEqual(lvl, RiskLevel.HIGH)

    def test_rain_exact_050_is_severe(self):
        lvl, _ = classify_rain(0.50, self._cfg())
        self.assertEqual(lvl, RiskLevel.SEVERE)

    def test_rain_severe_050_to_100_inclusive(self):
        lvl, _ = classify_rain(1.00, self._cfg())
        self.assertEqual(lvl, RiskLevel.SEVERE)

    def test_rain_over_100_is_no_travel(self):
        lvl, factors = classify_rain(1.001, self._cfg())
        self.assertEqual(lvl, RiskLevel.NO_TRAVEL)
        self.assertTrue(any("No Travel" in f for f in factors))

    # None / invalid / negative → unknown
    def test_rain_none_is_unknown(self):
        lvl, _ = classify_rain(None, self._cfg())
        self.assertEqual(lvl, RiskLevel.UNKNOWN)

    def test_rain_negative_is_unknown(self):
        lvl, _ = classify_rain(-0.1, self._cfg())
        self.assertEqual(lvl, RiskLevel.UNKNOWN)


class SnowClassificationTests(SimpleTestCase):
    """Snowfall rate classification per spec §4 (in/hr).

    Spec boundaries (lower inclusive, upper exclusive except Severe upper bound ≤ 3.0):
      Low       : < 0.5
      Moderate  : 0.5 – < 1.0
      High      : 1.0 – < 2.0
      Severe    : 2.0 – ≤ 3.0  (inclusive upper bound per spec)
      No Travel : > 3.0
    """

    def _cfg(self):
        return _load_risk_config()

    def test_snow_low_under_05(self):
        lvl, _ = classify_snow(0.49, self._cfg())
        self.assertEqual(lvl, RiskLevel.LOW)

    def test_snow_exact_05_is_moderate(self):
        lvl, _ = classify_snow(0.5, self._cfg())
        self.assertEqual(lvl, RiskLevel.MODERATE)

    def test_snow_moderate_05_to_under_10(self):
        lvl, _ = classify_snow(0.99, self._cfg())
        self.assertEqual(lvl, RiskLevel.MODERATE)

    def test_snow_exact_10_is_high(self):
        lvl, _ = classify_snow(1.0, self._cfg())
        self.assertEqual(lvl, RiskLevel.HIGH)

    def test_snow_high_10_to_under_20(self):
        lvl, _ = classify_snow(1.99, self._cfg())
        self.assertEqual(lvl, RiskLevel.HIGH)

    def test_snow_exact_20_is_severe(self):
        lvl, _ = classify_snow(2.0, self._cfg())
        self.assertEqual(lvl, RiskLevel.SEVERE)

    def test_snow_severe_20_to_30_inclusive(self):
        lvl, _ = classify_snow(3.0, self._cfg())
        self.assertEqual(lvl, RiskLevel.SEVERE)

    def test_snow_over_30_is_no_travel(self):
        lvl, factors = classify_snow(3.01, self._cfg())
        self.assertEqual(lvl, RiskLevel.NO_TRAVEL)
        self.assertTrue(any("No Travel" in f for f in factors))

    # None / invalid / negative → unknown
    def test_snow_none_is_unknown(self):
        lvl, _ = classify_snow(None, self._cfg())
        self.assertEqual(lvl, RiskLevel.UNKNOWN)

    def test_snow_negative_is_unknown(self):
        lvl, _ = classify_snow(-0.1, self._cfg())
        self.assertEqual(lvl, RiskLevel.UNKNOWN)


class CombinedRiskTests(SimpleTestCase):
    """Combined checkpoint risk per spec §6:
    - Overall = max of per-condition classes
    - No Travel > Severe > High > Moderate > Low > Unknown
    - Unknown only propagates if ALL conditions unknown
    """

    def _cfg(self):
        return _load_risk_config()

    def test_max_of_conditions(self):
        # wind=High, rain=Moderate, snow=Low → overall High
        wind_lvl, wind_f = classify_wind(40.0, None, self._cfg())
        rain_lvl, rain_f = classify_rain(0.15, self._cfg())
        snow_lvl, snow_f = classify_snow(0.3, self._cfg())
        overall, _ = combine_checkpoint_risks(wind_lvl, rain_lvl, snow_lvl, wind_f, rain_f, snow_f)
        self.assertEqual(overall, RiskLevel.HIGH)

    def test_no_travel_precedence(self):
        # wind=No Travel, rain=Low, snow=Low → overall No Travel
        wind_lvl, wind_f = classify_wind(55.0, None, self._cfg())
        rain_lvl, rain_f = classify_rain(0.05, self._cfg())
        snow_lvl, snow_f = classify_snow(0.2, self._cfg())
        overall, _ = combine_checkpoint_risks(wind_lvl, rain_lvl, snow_lvl, wind_f, rain_f, snow_f)
        self.assertEqual(overall, RiskLevel.NO_TRAVEL)

    def test_severe_beats_high(self):
        wind_lvl, wind_f = classify_wind(48.0, None, self._cfg())  # Severe
        rain_lvl, rain_f = classify_rain(0.40, self._cfg())  # High
        snow_lvl, snow_f = classify_snow(0.3, self._cfg())  # Low
        overall, _ = combine_checkpoint_risks(wind_lvl, rain_lvl, snow_lvl, wind_f, rain_f, snow_f)
        self.assertEqual(overall, RiskLevel.SEVERE)

    def test_all_unknown_is_unknown(self):
        wind_lvl, wind_f = classify_wind(None, None, self._cfg())
        rain_lvl, rain_f = classify_rain(None, self._cfg())
        snow_lvl, snow_f = classify_snow(None, self._cfg())
        overall, factors = combine_checkpoint_risks(wind_lvl, rain_lvl, snow_lvl, wind_f, rain_f, snow_f)
        self.assertEqual(overall, RiskLevel.UNKNOWN)
        self.assertTrue(any("unavailable" in f for f in factors))

    def test_some_known_some_unknown_uses_known(self):
        wind_lvl, wind_f = classify_wind(30.0, None, self._cfg())  # Moderate
        rain_lvl, rain_f = classify_rain(None, self._cfg())  # Unknown
        snow_lvl, snow_f = classify_snow(None, self._cfg())  # Unknown
        overall, _ = combine_checkpoint_risks(wind_lvl, rain_lvl, snow_lvl, wind_f, rain_f, snow_f)
        self.assertEqual(overall, RiskLevel.MODERATE)


class CheckpointRiskTests(SimpleTestCase):
    """End-to-end checkpoint classification with realistic weather data."""

    def test_typical_checkpoint_low_risk(self):
        cr = classify_checkpoint(
            checkpoint_id="cp_test1",
            arrival_iso="2026-10-25T12:00:00+00:00",
            wind_mph=10.0,
            rain_in_per_hr=0.02,
            snowfall_in_per_hr=0.0,
            load_lb=34000,
            matched_forecast_iso="2026-10-25T12:00",
            time_match="exact",
        )
        self.assertEqual(cr.risk_label, "low")
        self.assertEqual(cr.risk_level, RiskLevel.LOW)
        self.assertIsNotNone(cr.wind)
        self.assertIsNotNone(cr.rain)
        self.assertIsNotNone(cr.snow)

    def test_no_travel_wind_55_any_load(self):
        cr = classify_checkpoint(
            checkpoint_id="cp_test2",
            arrival_iso="2026-10-25T12:00:00+00:00",
            wind_mph=55.0,
            rain_in_per_hr=0.0,
            snowfall_in_per_hr=0.0,
            load_lb=10000,
            matched_forecast_iso="2026-10-25T12:00",
            time_match="exact",
        )
        self.assertEqual(cr.risk_label, "no_travel")
        self.assertEqual(cr.risk_level, RiskLevel.NO_TRAVEL)

    def test_no_travel_wind_50_heavy_load(self):
        cr = classify_checkpoint(
            checkpoint_id="cp_test3",
            arrival_iso="2026-10-25T12:00:00+00:00",
            wind_mph=50.0,
            rain_in_per_hr=0.0,
            snowfall_in_per_hr=0.0,
            load_lb=35000,
            matched_forecast_iso="2026-10-25T12:00",
            time_match="exact",
        )
        self.assertEqual(cr.risk_label, "no_travel")

    def test_severe_wind_38_very_heavy_load(self):
        cr = classify_checkpoint(
            checkpoint_id="cp_test4",
            arrival_iso="2026-10-25T12:00:00+00:00",
            wind_mph=38.0,
            rain_in_per_hr=0.0,
            snowfall_in_per_hr=0.0,
            load_lb=45000,
            matched_forecast_iso="2026-10-25T12:00",
            time_match="exact",
        )
        self.assertEqual(cr.risk_label, "severe")

    def test_no_weather_data_missing_object(self):
        # This is handled by analyze_route_risk, but test the unknown path
        cr = classify_checkpoint(
            checkpoint_id="cp_test5",
            arrival_iso="2026-10-25T12:00:00+00:00",
            wind_mph=None,
            rain_in_per_hr=None,
            snowfall_in_per_hr=None,
            load_lb=34000,
            matched_forecast_iso=None,
            time_match="missing",
        )
        self.assertEqual(cr.risk_label, "unknown")


class RouteRiskAggregationTests(SimpleTestCase):
    """Route-level risk summary aggregation."""

    def _make_route(self, checkpoint_risks: list[CheckpointRisk], interval_miles=25.0) -> dict:
        return {
            "routeId": "rt_test",
            "checkpointSummary": {"effectiveIntervalMiles": interval_miles},
            "checkpoints": [{} for _ in checkpoint_risks],  # placeholder
        }

    def test_mixed_risk_counts(self):
        risks = [
            CheckpointRisk("cp1", "2026-10-25T12:00:00+00:00", RiskLevel.LOW, "low", None, None, None, 10, 0.02, 0.0, [], "2026-10-25T12:00", "exact"),
            CheckpointRisk("cp2", "2026-10-25T13:00:00+00:00", RiskLevel.MODERATE, "moderate", None, None, None, 30, 0.15, 0.0, [], "2026-10-25T13:00", "exact"),
            CheckpointRisk("cp3", "2026-10-25T14:00:00+00:00", RiskLevel.HIGH, "high", None, None, None, 40, 0.30, 0.0, [], "2026-10-25T14:00", "exact"),
            CheckpointRisk("cp4", "2026-10-25T15:00:00+00:00", RiskLevel.SEVERE, "severe", None, None, None, 48, 0.60, 0.0, [], "2026-10-25T15:00", "exact"),
            CheckpointRisk("cp5", "2026-10-25T16:00:00+00:00", RiskLevel.NO_TRAVEL, "no_travel", None, None, None, 55, 0.0, 0.0, [], "2026-10-25T16:00", "exact"),
            CheckpointRisk("cp6", "2026-10-25T17:00:00+00:00", RiskLevel.UNKNOWN, "unknown", None, None, None, None, None, None, [], None, "out_of_horizon"),
        ]
        route = self._make_route(risks, 25.0)
        summary = risk_service.summarize_route_risk(route, risks)

        self.assertEqual(summary.total_checkpoints, 6)
        self.assertEqual(summary.checkpoints_with_weather, 5)
        self.assertEqual(summary.checkpoints_unknown, 1)
        self.assertEqual(summary.low_count, 1)
        self.assertEqual(summary.moderate_count, 1)
        self.assertEqual(summary.high_count, 1)
        self.assertEqual(summary.severe_count, 1)
        self.assertEqual(summary.no_travel_count, 1)
        self.assertEqual(summary.severe_miles, 25.0)  # 1 × 25
        self.assertEqual(summary.high_miles, 25.0)  # 1 × 25
        self.assertAlmostEqual(summary.avg_risk_ordinal, (0+1+2+3+4)/5)
        self.assertIsNotNone(summary.worst_checkpoint)
        self.assertEqual(summary.worst_checkpoint.checkpoint_id, "cp5")
        self.assertIn("No Travel", summary.explanation)

    def test_all_unknown_route(self):
        risks = [
            CheckpointRisk("cp1", "2026-10-25T12:00:00+00:00", RiskLevel.UNKNOWN, "unknown", None, None, None, None, None, None, [], None, "out_of_horizon"),
            CheckpointRisk("cp2", "2026-10-25T13:00:00+00:00", RiskLevel.UNKNOWN, "unknown", None, None, None, None, None, None, [], None, "out_of_horizon"),
        ]
        route = self._make_route(risks)
        summary = risk_service.summarize_route_risk(route, risks)
        self.assertEqual(summary.checkpoints_with_weather, 0)
        self.assertEqual(summary.checkpoints_unknown, 2)
        self.assertIsNone(summary.avg_risk_ordinal)
        self.assertIsNone(summary.worst_checkpoint)

    def test_no_travel_explanation_mentions_not_recommended(self):
        risks = [
            CheckpointRisk("cp1", "2026-10-25T12:00:00+00:00", RiskLevel.NO_TRAVEL, "no_travel", None, None, None, 55, 0.0, 0.0, [], "2026-10-25T12:00", "exact"),
        ]
        route = self._make_route(risks)
        summary = risk_service.summarize_route_risk(route, risks)
        self.assertIn("not recommended", summary.explanation.lower())

    def test_severe_miles_calculation(self):
        risks = [
            CheckpointRisk(f"cp{i}", f"2026-10-25T{12+i}:00:00+00:00", RiskLevel.SEVERE, "severe", None, None, None, 48, 0.6, 0.0, [], f"2026-10-25T{12+i}:00", "exact")
            for i in range(3)
        ]
        route = self._make_route(risks, 25.0)
        summary = risk_service.summarize_route_risk(route, risks)
        self.assertEqual(summary.severe_miles, 75.0)  # 3 × 25

    def test_high_miles_calculation(self):
        risks = [
            CheckpointRisk(f"cp{i}", f"2026-10-25T{12+i}:00:00+00:00", RiskLevel.HIGH, "high", None, None, None, 40, 0.3, 0.0, [], f"2026-10-25T{12+i}:00", "exact")
            for i in range(2)
        ]
        route = self._make_route(risks, 50.0)
        summary = risk_service.summarize_route_risk(route, risks)
        self.assertEqual(summary.high_miles, 100.0)  # 2 × 50


class RiskDeterminismTests(SimpleTestCase):
    """Same input + same config → identical output every time."""

    def test_classify_checkpoint_deterministic(self):
        for _ in range(10):
            cr = classify_checkpoint(
                checkpoint_id="cp_det",
                arrival_iso="2026-10-25T12:00:00+00:00",
                wind_mph=30.0,
                rain_in_per_hr=0.15,
                snowfall_in_per_hr=0.5,
                load_lb=34000,
                matched_forecast_iso="2026-10-25T12:00",
                time_match="exact",
            )
            self.assertEqual(cr.risk_label, "moderate")

    def test_analyze_route_deterministic(self):
        route = {
            "routeId": "rt_det",
            "checkpointSummary": {"effectiveIntervalMiles": 25.0},
            "checkpoints": [
                {
                    "checkpointId": "cp1",
                    "arrivalISO": "2026-10-25T12:00:00+00:00",
                    "weather": {
                        "windMph": 20.0,
                        "rainInPerHr": 0.05,
                        "snowfallInPerHr": 0.0,
                        "matchedForecastISO": "2026-10-25T12:00",
                        "timeMatch": "exact",
                    },
                },
                {
                    "checkpointId": "cp2",
                    "arrivalISO": "2026-10-25T13:00:00+00:00",
                    "weather": {
                        "windMph": 30.0,
                        "rainInPerHr": 0.15,
                        "snowfallInPerHr": 0.0,
                        "matchedForecastISO": "2026-10-25T13:00",
                        "timeMatch": "exact",
                    },
                },
            ],
        }
        results = [analyze_route_risk(route, 34000) for _ in range(5)]
        for i in range(1, 5):
            self.assertEqual(results[i][0][0].risk_label, results[0][0][0].risk_label)
            self.assertEqual(results[i][1].explanation, results[0][1].explanation)


class ConfigOverrideTests(TestCase):
    """Thresholds configurable via Django settings."""

    @override_settings(
        RISK_WIND_LOW_MAX=20.0,
        RISK_WIND_MODERATE_MAX=30.0,
        RISK_WIND_HIGH_MAX=40.0,
        RISK_WIND_SEVERE_MAX=50.0,
        RISK_WIND_NO_TRAVEL_ANY_LOAD=50.0,
        RISK_WIND_NO_TRAVEL_HEAVY_LOAD=40.0,
        RISK_WIND_SEVERE_HEAVY_LOAD=30.0,
        RISK_RAIN_LOW_MAX=0.05,
        RISK_RAIN_MODERATE_MAX=0.20,
        RISK_RAIN_HIGH_MAX=0.40,
        RISK_RAIN_SEVERE_MAX=0.80,
        RISK_SNOW_LOW_MAX=0.3,
        RISK_SNOW_MODERATE_MAX=0.8,
        RISK_SNOW_HIGH_MAX=1.5,
        RISK_SNOW_SEVERE_MAX=2.5,
        RISK_HEAVY_LOAD_THRESHOLD_LB=25000,
        RISK_VERY_HEAVY_LOAD_THRESHOLD_LB=35000,
    )
    def test_custom_thresholds_used(self):
        cfg = _load_risk_config()
        self.assertEqual(cfg["wind_low_max"], 20.0)
        self.assertEqual(cfg["wind_moderate_max"], 30.0)
        self.assertEqual(cfg["rain_low_max"], 0.05)
        self.assertEqual(cfg["heavy_load_threshold_lb"], 25000)

        # Wind 22 mph with custom thresholds → Moderate (not Low as in spec default)
        lvl, _ = classify_wind(22.0, None, cfg)
        self.assertEqual(lvl, RiskLevel.MODERATE)

        # Load rule uses custom threshold
        lvl, _ = classify_wind(42.0, 26000, cfg)  # > 25k custom heavy load
        self.assertEqual(lvl, RiskLevel.NO_TRAVEL)


class IntegrationTests(TestCase):
    """Integration: analyze_route_risk with full route payload from routing service."""

    def test_analyze_route_risk_with_realistic_payload(self):
        route = {
            "routeId": "rt_integration",
            "checkpointSummary": {"effectiveIntervalMiles": 25.0},
            "checkpoints": [
                {
                    "checkpointId": "cp_1",
                    "arrivalISO": "2026-10-25T12:00:00+00:00",
                    "weather": {
                        "windMph": 10.0,
                        "rainInPerHr": 0.02,
                        "snowfallInPerHr": 0.0,
                        "matchedForecastISO": "2026-10-25T12:00",
                        "timeMatch": "exact",
                    },
                },
                {
                    "checkpointId": "cp_2",
                    "arrivalISO": "2026-10-25T13:00:00+00:00",
                    "weather": {
                        "windMph": 30.0,
                        "rainInPerHr": 0.15,
                        "snowfallInPerHr": 0.0,
                        "matchedForecastISO": "2026-10-25T13:00",
                        "timeMatch": "exact",
                    },
                },
                {
                    "checkpointId": "cp_3",
                    "arrivalISO": "2026-10-25T14:00:00+00:00",
                    "weather": {
                        "windMph": None,  # missing → unknown
                        "rainInPerHr": None,
                        "snowfallInPerHr": None,
                        "matchedForecastISO": None,
                        "timeMatch": "out_of_horizon",
                    },
                },
            ],
        }
        cp_risks, summary = analyze_route_risk(route, 34000)

        self.assertEqual(len(cp_risks), 3)
        self.assertEqual(cp_risks[0].risk_label, "low")
        self.assertEqual(cp_risks[1].risk_label, "moderate")
        self.assertEqual(cp_risks[2].risk_label, "unknown")

        self.assertEqual(summary.total_checkpoints, 3)
        self.assertEqual(summary.checkpoints_with_weather, 2)
        self.assertEqual(summary.checkpoints_unknown, 1)
        self.assertIsNotNone(summary.worst_checkpoint)
        self.assertEqual(summary.worst_checkpoint.risk_level.to_str(), "moderate")


class NoDBSafetyTests(SimpleTestCase):
    """Risk service must not use Django ORM or persist anything."""

    def test_no_database_access(self):
        # classify_checkpoint, classify_wind, etc. are pure functions
        # If they touched DB, this would fail due to SimpleTestCase
        classify_checkpoint(
            checkpoint_id="cp_db",
            arrival_iso="2026-10-25T12:00:00+00:00",
            wind_mph=20.0,
            rain_in_per_hr=0.05,
            snowfall_in_per_hr=0.0,
            load_lb=34000,
            matched_forecast_iso="2026-10-25T12:00",
            time_match="exact",
        )

    def test_no_credential_leakage_in_errors(self):
        # Risk service doesn't make HTTP calls; verify no settings leak
        from core.services.risk import _load_risk_config
        cfg = _load_risk_config()
        # Config should only contain thresholds, not secrets
        for v in cfg.values():
            self.assertNotIn("key", str(v).lower())
            self.assertNotIn("secret", str(v).lower())
            self.assertNotIn("token", str(v).lower())


class NoMutationTests(SimpleTestCase):
    """Risk analysis must not mutate route geometry, distance, duration, ETA."""

    def test_route_unchanged_after_analysis(self):
        original_geometry = [[-87.6, 41.8], [-88.0, 41.5]]
        route = {
            "routeId": "rt_mut",
            "geometry": {"type": "LineString", "coordinates": original_geometry},
            "distanceMeters": 1614300,
            "distanceMiles": 1003.1,
            "durationSeconds": 53400,
            "arrivalISO": "2026-10-25T18:30:00+00:00",
            "checkpointSummary": {"effectiveIntervalMiles": 25.0},
            "checkpoints": [
                {
                    "checkpointId": "cp1",
                    "arrivalISO": "2026-10-25T12:00:00+00:00",
                    "coordinates": [-87.6, 41.8],
                    "distanceFromStartMeters": 0,
                    "weather": {
                        "windMph": 15.0,
                        "rainInPerHr": 0.0,
                        "snowfallInPerHr": 0.0,
                        "matchedForecastISO": "2026-10-25T12:00",
                        "timeMatch": "exact",
                    },
                },
            ],
        }
        # Deep copy for comparison
        import copy
        route_copy = copy.deepcopy(route)

        analyze_route_risk(route, 34000)

        # Verify core fields unchanged
        self.assertEqual(route["geometry"]["coordinates"], route_copy["geometry"]["coordinates"])
        self.assertEqual(route["distanceMeters"], route_copy["distanceMeters"])
        self.assertEqual(route["distanceMiles"], route_copy["distanceMiles"])
        self.assertEqual(route["durationSeconds"], route_copy["durationSeconds"])
        self.assertEqual(route["arrivalISO"], route_copy["arrivalISO"])


class BoundaryMatrixTests(SimpleTestCase):
    """Comprehensive boundary value matrix for all three weather dimensions.

    Tests exact boundary values from spec tables to ensure deterministic handling.
    """

    def _cfg(self):
        return _load_risk_config()

    def test_wind_boundaries(self):
        boundaries = [
            (24.999, RiskLevel.LOW),
            (25.0, RiskLevel.MODERATE),
            (34.999, RiskLevel.MODERATE),
            (35.0, RiskLevel.HIGH),
            (44.999, RiskLevel.HIGH),
            (45.0, RiskLevel.SEVERE),
            (54.999, RiskLevel.SEVERE),
            (55.0, RiskLevel.NO_TRAVEL),
        ]
        for val, expected in boundaries:
            with self.subTest(val=val):
                lvl, _ = classify_wind(val, None, self._cfg())
                self.assertEqual(lvl, expected, f"wind {val} → {lvl}, expected {expected}")

    def test_rain_boundaries(self):
        boundaries = [
            (0.0999, RiskLevel.LOW),
            (0.10, RiskLevel.MODERATE),
            (0.2499, RiskLevel.MODERATE),
            (0.25, RiskLevel.HIGH),
            (0.4999, RiskLevel.HIGH),
            (0.50, RiskLevel.SEVERE),
            (1.00, RiskLevel.SEVERE),  # inclusive upper per spec
            (1.001, RiskLevel.NO_TRAVEL),
        ]
        for val, expected in boundaries:
            with self.subTest(val=val):
                lvl, _ = classify_rain(val, self._cfg())
                self.assertEqual(lvl, expected, f"rain {val} → {lvl}, expected {expected}")

    def test_snow_boundaries(self):
        boundaries = [
            (0.499, RiskLevel.LOW),
            (0.5, RiskLevel.MODERATE),
            (0.999, RiskLevel.MODERATE),
            (1.0, RiskLevel.HIGH),
            (1.999, RiskLevel.HIGH),
            (2.0, RiskLevel.SEVERE),
            (3.0, RiskLevel.SEVERE),  # inclusive upper per spec
            (3.001, RiskLevel.NO_TRAVEL),
        ]
        for val, expected in boundaries:
            with self.subTest(val=val):
                lvl, _ = classify_snow(val, self._cfg())
                self.assertEqual(lvl, expected, f"snow {val} → {lvl}, expected {expected}")