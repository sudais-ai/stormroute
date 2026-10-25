"""Phase 5 backend tests — deterministic Open-Meteo weather integration.

Layout:
- Pure weather service tests (SimpleTestCase) exercise core.services.weather
  directly with hand-computed fixtures and mocked requests.get;
- Endpoint integration tests mock Mapbox exactly like test_routing.py and
  assert that Phase 4 route fields remain intact while weather is added.

No real network calls: `requests.get` is patched at the
core.services.weather boundary. The fixture token from test_routing.py
is still used for Mapbox.
"""

import json
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch, MagicMock

from django.test import SimpleTestCase, TestCase, override_settings

from core.services import weather as weather_service
from core.test_routing import (
    CHICAGO,
    DENVER,
    TEST_TOKEN,
    _DEPARTURE,
    _RouteApiHarness,
    _line,
    _ok_directions,
    _valid_payload,
    raw_route,
)

_DEPARTURE_UTC = datetime(2099, 1, 1, 16, 0, 0, tzinfo=dt_timezone.utc)


def make_route_with_checkpoints(
    coordinates,
    duration=36_000.0,
    distance=None,
    route_id="rt_fixture000001",
    interval_miles=25,
    cap=500,
):
    """Helper to build a route with Phase 4 checkpoints already sampled."""
    from core.services.checkpoints import sample_route_checkpoints, cumulative_distances, validate_linestring_coordinates

    if distance is None:
        points = validate_linestring_coordinates(coordinates)
        distance = cumulative_distances(points)[-1]

    route = {
        "routeId": route_id,
        "label": "Route 1",
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "distanceMeters": distance,
        "durationSeconds": duration,
    }
    sampled = sample_route_checkpoints(route, _DEPARTURE_UTC, interval_miles, cap)
    route["checkpoints"] = sampled["checkpoints"]
    route["checkpointSummary"] = sampled["summary"]
    return route


class OpenMeteoUrlTests(SimpleTestCase):
    def test_url_contains_required_params(self):
        url = weather_service._build_open_meteo_url(41.882, -87.632)
        self.assertIn("latitude=41.882", url)
        self.assertIn("longitude=-87.632", url)
        self.assertIn("hourly=wind_speed_10m,rain,snowfall", url)
        self.assertIn("wind_speed_unit=mph", url)
        self.assertIn("precipitation_unit=inch", url)
        self.assertIn("timezone=UTC", url)
        self.assertIn("forecast_days=3", url)

    def test_coordinates_rounded_to_4dp(self):
        url = weather_service._build_open_meteo_url(41.881953, -87.632362)
        self.assertIn("latitude=41.882", url)  # rounded
        self.assertIn("longitude=-87.6324", url)


class WeatherMatchingTests(SimpleTestCase):
    def setUp(self):
        # Minimal valid provider response for 3 hours
        self.provider_response = {
            "hourly": {
                "time": [
                    "2099-01-01T16:00",
                    "2099-01-01T17:00",
                    "2099-01-01T18:00",
                ],
                "wind_speed_10m": [15.5, 18.2, 22.1],
                "rain": [0.0, 0.12, 0.0],
                "snowfall": [0.0, 0.0, 0.0],
            }
        }

    def test_exact_hour_match_returns_values(self):
        target = datetime(2099, 1, 1, 17, 0, 0, tzinfo=dt_timezone.utc)
        wind, rain, snow, matched, provider_time = weather_service._match_weather_at_hour(
            self.provider_response, target
        )
        self.assertEqual(wind, 18.2)
        self.assertEqual(rain, 0.12)
        self.assertEqual(snow, 0.0)
        self.assertEqual(matched, "2099-01-01T17:00")
        self.assertEqual(provider_time, "2099-01-01T17:00")

    def test_out_of_horizon_returns_none(self):
        # Target hour not in provider response
        target = datetime(2099, 1, 1, 20, 0, 0, tzinfo=dt_timezone.utc)
        wind, rain, snow, matched, provider_time = weather_service._match_weather_at_hour(
            self.provider_response, target
        )
        self.assertIsNone(wind)
        self.assertIsNone(rain)
        self.assertIsNone(snow)
        self.assertIsNone(matched)
        self.assertIsNone(provider_time)

    def test_mid_hour_arrival_truncates_to_hour(self):
        # Checkpoint at 17:30 should match 17:00 bucket (truncation done by caller)
        target = datetime(2099, 1, 1, 17, 30, 0, tzinfo=dt_timezone.utc)
        target_hour = weather_service._truncate_to_hour(target)
        wind, rain, snow, matched, provider_time = weather_service._match_weather_at_hour(
            self.provider_response, target_hour
        )
        self.assertEqual(wind, 18.2)
        self.assertEqual(matched, "2099-01-01T17:00")

    def test_null_values_in_provider_returns_none(self):
        provider = {
            "hourly": {
                "time": ["2099-01-01T16:00"],
                "wind_speed_10m": [None],
                "rain": [None],
                "snowfall": [None],
            }
        }
        target = datetime(2099, 1, 1, 16, 0, 0, tzinfo=dt_timezone.utc)
        wind, rain, snow, _, _ = weather_service._match_weather_at_hour(provider, target)
        self.assertIsNone(wind)
        self.assertIsNone(rain)
        self.assertIsNone(snow)

    def test_non_finite_values_treated_as_none(self):
        provider = {
            "hourly": {
                "time": ["2099-01-01T16:00"],
                "wind_speed_10m": [float("nan")],
                "rain": [float("inf")],
                "snowfall": [-float("inf")],
            }
        }
        target = datetime(2099, 1, 1, 16, 0, 0, tzinfo=dt_timezone.utc)
        wind, rain, snow, _, _ = weather_service._match_weather_at_hour(provider, target)
        self.assertIsNone(wind)
        self.assertIsNone(rain)
        self.assertIsNone(snow)


class CheckpointValidationTests(SimpleTestCase):
    def test_valid_checkpoint_extracts_fields(self):
        cp = {
            "checkpointId": "cp_test123",
            "coordinates": [-87.632, 41.882],
            "arrivalISO": "2099-01-01T16:00:00+00:00",
        }
        cp_id, lat, lon, arrival = weather_service._validate_checkpoint_input(cp)
        self.assertEqual(cp_id, "cp_test123")
        self.assertAlmostEqual(lat, 41.882)
        self.assertAlmostEqual(lon, -87.632)
        self.assertEqual(arrival, datetime(2099, 1, 1, 16, 0, 0, tzinfo=dt_timezone.utc))

    def test_missing_checkpoint_id_raises(self):
        with self.assertRaises(ValueError):
            weather_service._validate_checkpoint_input({
                "coordinates": [0, 0],
                "arrivalISO": "2099-01-01T16:00:00+00:00",
            })

    def test_invalid_coordinates_raises(self):
        for bad_coords in (
            [-87.632],  # too short
            [-87.632, 41.882, 100],  # too long
            ["east", 41.882],  # non-numeric
            [float("nan"), 41.882],  # non-finite
            [200.0, 41.882],  # out of range
            [-87.632, 91.0],  # out of range
        ):
            with self.assertRaises(ValueError, msg=str(bad_coords)):
                weather_service._validate_checkpoint_input({
                    "checkpointId": "cp_x",
                    "coordinates": bad_coords,
                    "arrivalISO": "2099-01-01T16:00:00+00:00",
                })

    def test_naive_arrival_iso_rejected(self):
        with self.assertRaises(ValueError):
            weather_service._validate_checkpoint_input({
                "checkpointId": "cp_x",
                "coordinates": [0, 0],
                "arrivalISO": "2099-01-01T16:00:00",  # no timezone
            })


class EnrichmentIntegrationTests(SimpleTestCase):
    """Test enrich_checkpoints_with_weather with mocked _fetch_open_meteo."""

    def setUp(self):
        self.route = make_route_with_checkpoints(
            [[-87.632, 41.882], [-104.986, 39.742]],  # ~1000 mi route
            interval_miles=25,
        )
        self.checkpoints = self.route["checkpoints"]
        # Truncate first checkpoint arrival to hour for matching
        first_arrival = datetime.fromisoformat(self.checkpoints[0]["arrivalISO"])
        self.target_hour = first_arrival.replace(minute=0, second=0, microsecond=0)
        # Provider response covering the full route duration (~10 hours from 16:00 to 02:00)
        self.provider_response = {
            "hourly": {
                "time": [f"2099-01-01T{h:02d}:00" for h in range(16, 24)] + [f"2099-01-02T{h:02d}:00" for h in range(0, 3)],
                "wind_speed_10m": [12.5, 14.0] + [15.0] * 9,
                "rain": [0.0, 0.05] + [0.0] * 9,
                "snowfall": [0.0] * 11,
            }
        }

    @patch("core.services.weather._fetch_open_meteo")
    def test_single_route_all_checkpoints_matched(self, mock_fetch):
        mock_fetch.return_value = self.provider_response
        routes, summaries = weather_service.enrich_checkpoints_with_weather([self.route])

        self.assertEqual(len(routes), 1)
        route = routes[0]
        # Each checkpoint should have weather
        for cp in route["checkpoints"]:
            self.assertIn("weather", cp)
            w = cp["weather"]
            self.assertEqual(w["checkpointId"], cp["checkpointId"])
            self.assertEqual(w["timeMatch"], "exact")
            self.assertIsNotNone(w["windMph"])
            self.assertIsNotNone(w["rainInPerHr"])
            self.assertIsNotNone(w["snowfallInPerHr"])
            self.assertEqual(w["provider"], "open-meteo")

        # Summary reflects counts
        summary = summaries[0]
        self.assertEqual(summary.total_checkpoints, len(route["checkpoints"]))
        self.assertEqual(summary.checkpoints_with_weather, len(route["checkpoints"]))
        self.assertEqual(summary.checkpoints_unavailable, 0)

    @patch("core.services.weather._fetch_open_meteo")
    def test_partial_coverage_some_out_of_horizon(self, mock_fetch):
        # Provider only has first hour; later checkpoints fall outside
        limited_response = {
            "hourly": {
                "time": [self.target_hour.strftime("%Y-%m-%dT%H:%M")],
                "wind_speed_10m": [12.5],
                "rain": [0.0],
                "snowfall": [0.0],
            }
        }
        mock_fetch.return_value = limited_response
        routes, summaries = weather_service.enrich_checkpoints_with_weather([self.route])

        route = routes[0]
        with_weather = sum(1 for cp in route["checkpoints"] if cp["weather"]["timeMatch"] == "exact")
        without = sum(1 for cp in route["checkpoints"] if cp["weather"]["timeMatch"] == "out_of_horizon")
        # First several checkpoints (at 16:00, 16:16, 16:32, 16:49) all truncate to 16:00
        self.assertGreater(with_weather, 0)
        self.assertGreater(without, 0)

        # Summary reflects counts
        summary = summaries[0]
        self.assertEqual(summary.total_checkpoints, len(route["checkpoints"]))
        self.assertEqual(summary.checkpoints_with_weather, with_weather)
        self.assertEqual(summary.checkpoints_unavailable, without)

    @patch("core.services.weather._fetch_open_meteo")
    def test_deduplicates_same_coordinates(self, mock_fetch):
        """Two routes sharing the same origin coordinate should only fetch once."""
        mock_fetch.return_value = self.provider_response
        # Create a second route with the SAME origin coordinate
        route2 = make_route_with_checkpoints(
            [[-87.632, 41.882], [-100.0, 40.0]],  # Same origin as self.route
            route_id="rt_fixture000002",
            interval_miles=50,
        )
        routes, _ = weather_service.enrich_checkpoints_with_weather([self.route, route2])
        # Origin coordinate is shared, so should only be fetched once
        # self.route has 1 unique origin, route2 has 1 unique origin (same) + other coords
        # But the test checks that the SAME coordinate isn't fetched twice
        # The mock_fetch is called for each unique (rounded) coordinate
        # Origin: (-87.632, 41.882) -> rounded (-87.632, 41.882)
        # Other coords in route1 are different, route2 has different other coords
        # So we expect: 1 (shared origin) + (n-1) other coords from route1 + (m-1) other coords from route2
        # But since we only care about the shared origin being deduplicated, let's verify
        # that the number of calls is less than total checkpoints across both routes
        total_checkpoints = sum(len(r["checkpoints"]) for r in routes)
        self.assertLess(mock_fetch.call_count, total_checkpoints)
        # And specifically, the shared origin coordinate was only fetched once
        # We can't easily assert the exact count without knowing all coords, but we can
        # verify the deduplication logic works by checking the mock was called with the origin
        origin_calls = [c for c in mock_fetch.call_args_list if c[0][0] == round(41.882, 4) and c[0][1] == round(-87.632, 4)]
        self.assertEqual(len(origin_calls), 1, "Shared origin coordinate should only be fetched once")

    @patch("core.services.weather._fetch_open_meteo")
    def test_provider_timeout_sets_provider_error(self, mock_fetch):
        mock_fetch.side_effect = weather_service.WeatherTimeoutError()
        routes, summaries = weather_service.enrich_checkpoints_with_weather([self.route])
        route = routes[0]
        self.assertIn("weatherError", route)
        self.assertEqual(route["weatherError"]["code"], "weather_timeout")
        # Checkpoints should still exist but without weather
        for cp in route["checkpoints"]:
            self.assertIn("weather", cp)
            self.assertEqual(cp["weather"]["timeMatch"], "provider_error")

    @patch("core.services.weather._fetch_open_meteo")
    def test_provider_rate_limit_sets_error(self, mock_fetch):
        mock_fetch.side_effect = weather_service.WeatherRateLimitError()
        routes, _ = weather_service.enrich_checkpoints_with_weather([self.route])
        self.assertEqual(routes[0]["weatherError"]["code"], "weather_rate_limited")

    @patch("core.services.weather._fetch_open_meteo")
    def test_malformed_provider_response_sets_error(self, mock_fetch):
        mock_fetch.side_effect = weather_service.WeatherProviderError()
        routes, _ = weather_service.enrich_checkpoints_with_weather([self.route])
        self.assertEqual(routes[0]["weatherError"]["code"], "weather_provider")


class WeatherErrorPayloadTests(SimpleTestCase):
    def test_weather_errors_have_safe_payloads(self):
        for err_class, code in [
            (weather_service.WeatherProviderError, "weather_provider"),
            (weather_service.WeatherTimeoutError, "weather_timeout"),
            (weather_service.WeatherRateLimitError, "weather_rate_limited"),
        ]:
            err = err_class()
            payload = err.as_payload()
            self.assertEqual(payload["code"], code)
            self.assertIn("message", payload)
            self.assertNotIn("pk.", str(payload))  # no token-like strings


@override_settings(MAPBOX_ACCESS_TOKEN=TEST_TOKEN)
class EndpointWeatherIntegrationTests(TestCase):
    def setUp(self):
        self.url = "/api/trips/routes/"
        from django.test import Client
        self.client = Client()

    def post_json(self, payload):
        return self.client.post(self.url, json.dumps(payload), content_type="application/json")

    def _harness(self, routes):
        geocodes = [
            {"features": [{"place_name": "Chicago, Illinois, United States", "center": CHICAGO}]},
            {"features": [{"place_name": "Denver, Colorado, United States", "center": DENVER}]},
        ]
        return _RouteApiHarness(geocodes, _ok_directions(routes))

    def _long_route(self, **overrides):
        defaults = dict(
            summary="I-80 W; I-76 W",
            distance_m=1_614_300.0,
            duration_s=53_400.0,
            coordinates=_line(CHICAGO, DENVER),
        )
        defaults.update(overrides)
        return raw_route(defaults["summary"], defaults["distance_m"], defaults["duration_s"], defaults["coordinates"])

    @patch("core.services.weather._fetch_open_meteo")
    def test_weather_added_to_checkpoints_in_response(self, mock_fetch):
        # Provider response covering all checkpoint hours for 2 routes
        # Route from Chicago to Denver takes ~14.8 hours (53400 seconds)
        # Departure is 2099-01-01T16:00:00+00:00, arrival ~2099-01-02T06:50:00+00:00
        # Need forecast from 16:00 to 07:00 next day = 15 hours
        # Provide 24 hours to be safe
        provider_response = {
            "hourly": {
                "time": [f"2099-01-01T{h:02d}:00" for h in range(16, 24)] + [f"2099-01-02T{h:02d}:00" for h in range(0, 12)],
                "wind_speed_10m": [10.0] * 20,
                "rain": [0.0] * 20,
                "snowfall": [0.0] * 20,
            }
        }
        mock_fetch.return_value = provider_response

        with self._harness([self._long_route()]):
            res = self.post_json(_valid_payload())

        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertTrue(data["routesAvailable"])
        self.assertIn("weatherSummaries", data)
        self.assertEqual(len(data["weatherSummaries"]), 1)

        route = data["routes"][0]
        self.assertEqual(len(route["checkpoints"]), route["checkpointSummary"]["count"])
        # Every checkpoint should have weather
        for cp in route["checkpoints"]:
            self.assertIn("weather", cp)
            w = cp["weather"]
            self.assertEqual(w["checkpointId"], cp["checkpointId"])
            self.assertEqual(w["timeMatch"], "exact")
            self.assertIsNotNone(w["windMph"])
            self.assertEqual(w["provider"], "open-meteo")

        # Summary counts
        summary = data["weatherSummaries"][0]
        self.assertEqual(summary["totalCheckpoints"], route["checkpointSummary"]["count"])
        self.assertEqual(summary["checkpointsWithWeather"], route["checkpointSummary"]["count"])
        self.assertEqual(summary["checkpointsUnavailable"], 0)

    @patch("core.services.weather._fetch_open_meteo")
    def test_partial_coverage_reported_in_summary(self, mock_fetch):
        # Only first 3 hours available (16:00, 17:00, 18:00)
        provider_response = {
            "hourly": {
                "time": ["2099-01-01T16:00", "2099-01-01T17:00", "2099-01-01T18:00"],
                "wind_speed_10m": [10.0, 12.0, 15.0],
                "rain": [0.0, 0.0, 0.0],
                "snowfall": [0.0, 0.0, 0.0],
            }
        }
        mock_fetch.return_value = provider_response

        with self._harness([self._long_route()]):
            res = self.post_json(_valid_payload())

        route = json.loads(res.content)["routes"][0]
        summary = json.loads(res.content)["weatherSummaries"][0]
        self.assertLess(summary["checkpointsWithWeather"], summary["totalCheckpoints"])
        self.assertGreater(summary["checkpointsUnavailable"], 0)

    @patch("core.services.weather._fetch_open_meteo")
    def test_provider_timeout_returns_routes_with_weather_error(self, mock_fetch):
        mock_fetch.side_effect = weather_service.WeatherTimeoutError()

        with self._harness([self._long_route()]):
            res = self.post_json(_valid_payload())

        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertTrue(data["routesAvailable"])
        route = data["routes"][0]
        self.assertIn("weatherError", route)
        self.assertEqual(route["weatherError"]["code"], "weather_timeout")
        # Route data preserved
        self.assertEqual(route["distanceMeters"], 1_614_300.0)
        self.assertEqual(route["durationSeconds"], 53_400.0)

    @patch("core.services.weather._fetch_open_meteo")
    def test_phase_four_fields_preserved_with_weather(self, mock_fetch):
        provider_response = {
            "hourly": {
                "time": ["2099-01-01T16:00", "2099-01-01T17:00"],
                "wind_speed_10m": [10.0, 12.0],
                "rain": [0.0, 0.0],
                "snowfall": [0.0, 0.0],
            }
        }
        mock_fetch.return_value = provider_response

        with self._harness([self._long_route()]):
            res = self.post_json(_valid_payload())

        route = json.loads(res.content)["routes"][0]
        # Phase 3 fields
        self.assertEqual(route["distanceMeters"], 1_614_300.0)
        self.assertEqual(route["durationSeconds"], 53_400.0)
        self.assertEqual(route["durationReadable"], "14 h 50 min")
        self.assertEqual(route["geometry"]["coordinates"], _line(CHICAGO, DENVER))
        self.assertEqual(route["arrivalISO"], "2099-01-02T06:50:00+00:00")
        # Phase 4 fields
        self.assertIn("checkpoints", route)
        self.assertIn("checkpointSummary", route)
        # Phase 5 fields
        self.assertIn("weather", route["checkpoints"][0])
        self.assertIn("weatherSummaries", json.loads(res.content))

    @patch("core.services.weather._fetch_open_meteo")
    def test_no_token_leak_in_response(self, mock_fetch):
        provider_response = {
            "hourly": {"time": ["2099-01-01T16:00"], "wind_speed_10m": [10.0], "rain": [0.0], "snowfall": [0.0]},
        }
        mock_fetch.return_value = provider_response

        with self._harness([self._long_route()]):
            res = self.post_json(_valid_payload())

        body = res.content.decode("utf-8")
        self.assertNotIn(TEST_TOKEN, body)
        self.assertNotIn("pk.", body)