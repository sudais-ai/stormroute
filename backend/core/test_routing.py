"""Backend tests for Phase 3 route generation — deterministic, fixture-backed.

NEVER performs real HTTP: `requests.get` is patched at the
core.services.routing boundary. The token used is a declared TEST FIXTURE
("pk.test-routing-token-fixture"), not a real credential; every test asserts
it never leaks into responses. Route payloads are synthetic Mapbox shapes
derived from the real structure recorded live on 2026-10-24
(docs/TEST_LOG.md) — clearly test fixtures, never production results.
"""

import json
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from core.services import routing as routing_service
import requests as real_requests

TEST_TOKEN = "pk.test-routing-token-fixture"

INVALID_GEOCODE_BODY = {"features": []}
_PARSABLE = object()  # sentinel → FakeResponse.json() raises ValueError
UNPARSABLE = "unparsable"

_DEPARTURE = "2099-01-01T08:00:00-08:00"
_DEPARTURE_UTC = "2099-01-01T16:00:00+00:00"


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def json(self):
        if self._body is UNPARSABLE:
            raise ValueError("no json available")
        if self._body is _PARSABLE_EMPTY:
            return {}
        return self._body


_PARSABLE_EMPTY = _PARSABLE


def geocode_feature(place_name, center):
    return {"type": "Feature", "text": place_name, "place_name": place_name, "relevance": 0.99, "center": center}


def raw_route(summary, distance_m, duration_s, coordinates):
    return {
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "legs": [{"summary": summary, "distance": distance_m, "duration": duration_s}],
        "distance": distance_m,
        "duration": duration_s,
    }


def _line(a, b, extra=None):
    base = [
        [a[0], a[1]],
        [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2],
        [b[0], b[1]],
    ]
    if extra is not None:
        base = base[:1] + extra + base[1:]
    return base


CHICAGO = [-87.6324, 41.8820]
DENVER = [-104.9861, 39.7417]


class _RouteApiHarness:
    """Patches routing_service.requests.get with deterministic fixtures."""

    def __init__(self, geocode_bodies, directions_body, directions_status=200):
        self.geocode_queue = list(geocode_bodies)
        self.directions = (directions_status, directions_body)
        self.calls = []

    def __enter__(self):
        def fake_get(url, params=None, timeout=None):
            self.calls.append({"url": url, "params": dict(params or {})})
            if "geocoding" in url:
                body = self.geocode_queue.pop(0)
                return FakeResponse(200, body if not isinstance(body, int) else body)
            if "directions" in url:
                status, payload = self.directions
                return FakeResponse(status, payload)
            if "open-meteo" in url:
                # Allow Open-Meteo calls through for tests that don't mock weather
                # Multi-location batch (Phase 9 heatmap): ?latitude=a,b&longitude=...
                query = parse_qs(urlparse(url).query)
                lats = (query.get("latitude") or [""])[0]
                lons = (query.get("longitude") or [""])[0]
                n = len(lats.split(",")) if "," in lats else 0
                if n > 0 and "," in lons and len(lons.split(",")) == n:
                    single = {
                        "hourly": {
                            "time": [f"2099-01-01T{h:02d}:00" for h in range(16, 40)]
                                    + [f"2099-01-02T{h:02d}:00" for h in range(0, 24)],
                            "wind_speed_10m": [10.0] * 48,
                            "rain": [0.0] * 48,
                            "snowfall": [0.0] * 48,
                        }
                    }
                    return FakeResponse(200, [single] * n)
                # Single location: minimal valid forecast covering 48 hours
                return FakeResponse(200, {
                    "hourly": {
                        "time": [f"2099-01-01T{h:02d}:00" for h in range(16, 40)] + [f"2099-01-02T{h:02d}:00" for h in range(0, 24)],
                        "wind_speed_10m": [10.0] * 48,
                        "rain": [0.0] * 48,
                        "snowfall": [0.0] * 48,
                    }
                })
            raise AssertionError(f"unexpected upstream URL in test: coarse={url.split('?')[0]}")

        self._patcher = patch.object(routing_service.requests, "get", side_effect=fake_get)
        self._patcher.start()
        return self

    def __exit__(self, *exc_info):
        self._patcher.stop()


def _ok_directions(routes):
    return {"code": "Ok", "waypoints": [], "routes": routes}


def _valid_payload(**overrides):
    payload = {
        "origin": "Chicago, IL",
        "destination": "Denver, CO",
        "departureISO": _DEPARTURE,
        "loadWeightLb": 34000,
        "checkpointIntervalMiles": 25,
    }
    payload.update(overrides)
    return payload


@override_settings(MAPBOX_ACCESS_TOKEN=TEST_TOKEN)
class TripRoutesEndpointTests(TestCase):
    """POST /api/trips/routes/ contract with mocked Mapbox fixtures."""

    def setUp(self):
        self.client = Client()
        self.url = "/api/trips/routes/"

    def post_json(self, payload):
        return self.client.post(self.url, json.dumps(payload), content_type="application/json")

    def _assert_no_token(self, res):
        self.assertNotIn(TEST_TOKEN.encode(), res.content)
        self.assertNotIn(TEST_TOKEN, json.dumps(json.loads(res.content)))

    def _standard_harness(self, routes):
        geocodes = [
            {"features": [geocode_feature("Chicago, Illinois, United States", CHICAGO)]},
            {"features": [geocode_feature("Denver, Colorado, United States", DENVER)]},
        ]
        return _RouteApiHarness(geocodes, _ok_directions(routes))

    # ---------- success: three routes ----------

    def test_three_routes_full_normalized_shape(self):
        routes = [
            raw_route("I-80 W; I-76 W", 1_614_300.0, 53_400.0, _line(CHICAGO, DENVER)),
            raw_route("US-30; I-76 W", 1_817_400.0, 60_300.0, _line(CHICAGO, DENVER, extra=[[-95.0, 41.0]])),
            raw_route("I-80 W; US-425 N", 1_750_000.0, 58_000.0, _line(CHICAGO, DENVER, extra=[[-93.5, 40.4]])),
        ]
        with self._standard_harness(routes) as harness:
            res = self.post_json(_valid_payload())
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertTrue(data["routesAvailable"])
        self.assertEqual(data["routeCount"], 3)
        self.assertTrue(data["threeRoutesReturned"])
        self.assertIsNone(data["warning"])
        self.assertEqual(data["routesRequested"], 3)
        self.assertEqual(data["duplicatesDropped"], 0)
        # geocoded endpoint details, honest provider resolution
        self.assertEqual(data["origin"]["resolvedName"], "Chicago, Illinois, United States")
        self.assertEqual(data["destination"]["resolvedName"], "Denver, Colorado, United States")
        self.assertEqual(data["origin"]["longitude"], CHICAGO[0])
        self.assertEqual(data["origin"]["latitude"], CHICAGO[1])
        # normalized per-route shape
        first = data["routes"][0]
        for key in ("routeId", "label", "geometry", "distanceMeters", "distanceMiles",
                    "durationSeconds", "durationReadable", "providerRouteSummary", "arrivalISO"):
            self.assertIn(key, first)
        self.assertEqual([r["label"] for r in data["routes"]], ["Route 1", "Route 2", "Route 3"])
        ids = [r["routeId"] for r in data["routes"]]
        self.assertEqual(len(set(ids)), 3, "distinct routes must yield distinct ids")
        for rid in ids:
            self.assertTrue(rid.startswith("rt_"))
            self.assertEqual(len(rid), 15)
        self._assert_no_token(res)

    def test_coordinates_preserved_longitude_first(self):
        coords = [[-87.632400, 41.882000], [-95.500000, 41.000000], [-104.986100, 39.741700]]
        with self._standard_harness([raw_route("I-80 W", 1_614_300.0, 53_400.0, coords)]):
            res = self.post_json(_valid_payload())
        got = json.loads(res.content)["routes"][0]["geometry"]["coordinates"]
        self.assertEqual(got[0], [round(-87.632400, 6), round(41.882000, 6)])
        # untouched order: longitude strictly before latitude
        for pair in got:
            self.assertLess(pair[1], 90.0)
            self.assertGreater(pair[1], -90.0)
            self.assertLess(pair[0], 180.0)
            self.assertGreater(pair[0], -180.0)
        self.assertEqual(got, coords if False else [
            [-87.6324, 41.882], [-95.5, 41.0], [-104.9861, 39.7417]
        ])

    def test_upstream_request_parameters_are_correct(self):
        routes = [raw_route("I-80 W", 1_614_300.0, 53_400.0, _line(CHICAGO, DENVER))]
        with self._standard_harness(routes) as harness:
            self.post_json(_valid_payload())
        geocode_calls = [c for c in harness.calls if "geocoding" in c["url"]]
        directions_calls = [c for c in harness.calls if "directions" in c["url"]]
        self.assertEqual(len(geocode_calls), 2)
        self.assertEqual(len(directions_calls), 1)
        # token only ever goes to Mapbox as the API key param; never logged
        self.assertEqual(geocode_calls[0]["params"]["access_token"], TEST_TOKEN)
        self.assertEqual(geocode_calls[0]["params"]["limit"], 1)
        d = directions_calls[0]["params"]
        self.assertEqual(d["access_token"], TEST_TOKEN)
        self.assertEqual(d["alternatives"], "true")
        self.assertEqual(d["geometries"], "geojson")
        self.assertEqual(d["overview"], "full")
        self.assertIn("directions/v5/mapbox/driving/", directions_calls[0]["url"])

    # ---------- success: fewer than three ----------

    def test_two_routes_warn_truthfully(self):
        routes = [
            raw_route("I-80 W; I-76 W", 1_614_300.0, 53_400.0, _line(CHICAGO, DENVER)),
            raw_route("US-30; I-76 W", 1_817_400.0, 60_300.0, _line(CHICAGO, DENVER, extra=[[-95.0, 41.0]])),
        ]
        with self._standard_harness(routes):
            res = self.post_json(_valid_payload())
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertEqual(data["routeCount"], 2)
        self.assertFalse(data["threeRoutesReturned"])
        self.assertIn("2 distinct routes", data["warning"])
        self.assertEqual(len(data["routes"]), 2)
        self._assert_no_token(res)

    def test_single_route_warns_with_singular_text(self):
        with self._standard_harness([raw_route("I-80 W", 1_614_300.0, 53_400.0, _line(CHICAGO, DENVER))]):
            res = self.post_json(_valid_payload())
        data = json.loads(res.content)
        self.assertEqual(data["routeCount"], 1)
        self.assertIn("1 distinct route", data["warning"])
        self.assertNotIn("1 distinct routes", data["warning"])

    # ---------- deduplication ----------

    def test_identical_replay_route_is_dropped(self):
        replay = raw_route("I-80 W; I-76 W", 1_614_300.0, 53_400.0, _line(CHICAGO, DENVER))
        distinct = raw_route("US-30; I-76 W", 1_817_400.0, 60_300.0, _line(CHICAGO, DENVER, extra=[[-95.0, 41.0]]))
        with self._standard_harness([replay, dict(replay), distinct]):
            res = self.post_json(_valid_payload())
        data = json.loads(res.content)
        self.assertEqual(data["routeCount"], 2)
        self.assertEqual(data["duplicatesDropped"], 1)
        self.assertEqual([r["label"] for r in data["routes"]], ["Route 1", "Route 2"])
        self.assertIn("2 distinct routes", data["warning"])

    def test_similar_but_distinct_corridors_are_kept(self):
        a = raw_route("I-80 W; I-76 W", 1_614_300.0, 53_400.0, _line(CHICAGO, DENVER))
        # same endpoints, slightly different metrics/summary → SEEK distinct
        b = raw_route("I-80 W; I-76 W", 1_614_301.0, 53_400.0, _line(CHICAGO, DENVER))
        with self._standard_harness([a, b]):
            res = self.post_json(_valid_payload())
        data = json.loads(res.content)
        self.assertEqual(data["routeCount"], 2)
        self.assertEqual(data["duplicatesDropped"], 0)

    # ---------- unit conversions + ETA ----------

    def test_distance_duration_conversions(self):
        # 1_609_344 m ⇒ 1001.3 mi (km-mile multiplier fixture); 2 h → readable.
        meters, seconds = 1_609_344.0, 7200.0
        with self._standard_harness([raw_route("I-80 W", meters, seconds, _line(CHICAGO, DENVER))]):
            res = self.post_json(_valid_payload())
        route = json.loads(res.content)["routes"][0]
        self.assertEqual(route["distanceMeters"], meters)
        self.assertAlmostEqual(route["distanceMiles"], round(meters * routing_service._MILES_PER_METER, 1))
        self.assertEqual(route["durationReadable"], "2 h 0 min")

    def test_arrival_iso_per_route_from_duration(self):
        with self._standard_harness([
            raw_route("Fast", 1_000_000.0, 36_000.0, _line(CHICAGO, DENVER)),          # 10 h
            raw_route("Mid", 1_200_000.0, 37_800.0, _line(CHICAGO, DENVER, extra=[[-95.0, 41.0]])),  # 10.5 h
        ]):
            res = self.post_json(_valid_payload())
        arrivals = [r["arrivalISO"] for r in json.loads(res.content)["routes"]]
        self.assertEqual(arrivals[0], "2099-01-02T02:00:00+00:00")   # 16:00 + 10 h
        self.assertEqual(arrivals[1], "2099-01-02T02:30:00+00:00")   # 16:00 + 10 h 30 m

    # ---------- invalid input (Phase 2 contract reused) ----------

    def test_invalid_interval_returns_input_errors_not_provider_code(self):
        with self._standard_harness([]) as harness:  # no upstream calls expected
            res = self.post_json(_valid_payload(checkpointIntervalMiles=15))
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.content)
        self.assertFalse(data["routesAvailable"])
        self.assertIn("checkpointIntervalMiles", data["inputErrors"])
        self.assertEqual(harness.calls, [], "invalid input must not trigger provider calls")
        self._assert_no_token(res)

    def test_past_departure_rejected_before_provider_call(self):
        past = (timezone.now() - timezone.timedelta(hours=2)).isoformat()
        with self._standard_harness([]) as harness:
            res = self.post_json(_valid_payload(departureISO=past))
        self.assertEqual(res.status_code, 400)
        self.assertIn("departureISO", json.loads(res.content)["inputErrors"])
        self.assertEqual(harness.calls, [])

    def test_malformed_json_body(self):
        res = self.client.post(self.url, "{not json", content_type="application/json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(json.loads(res.content)["error"]["code"], "malformed_request")

    # ---------- provider failures ----------

    def test_missing_token_config(self):
        with override_settings(MAPBOX_ACCESS_TOKEN=""):
            with _RouteApiHarness([], _ok_directions([])) as harness:
                res = self.post_json(_valid_payload())
        self.assertEqual(res.status_code, 503)
        self.assertEqual(json.loads(res.content)["error"]["code"], "config_missing")
        self._assert_no_token(res)

    def test_geocode_empty_results_stage_marks_origin_or_destination(self):
        geocodes = [
            {"features": [geocode_feature("Chicago, Illinois, United States", CHICAGO)]},
            INVALID_GEOCODE_BODY,
        ]
        with _RouteApiHarness(geocodes, _ok_directions([])):
            res = self.post_json(_valid_payload())
        self.assertEqual(res.status_code, 422)
        error = json.loads(res.content)["error"]
        self.assertEqual(error["code"], "geocode_failed")
        self.assertEqual(error["stage"], "destination")
        self._assert_no_token(res)

        geocodes = [INVALID_GEOCODE_BODY, INVALID_GEOCODE_BODY]
        with _RouteApiHarness(geocodes, _ok_directions([])):
            res = self.post_json(_valid_payload())
        self.assertEqual(json.loads(res.content)["error"]["stage"], "origin")

    def test_directions_zero_routes(self):
        geocodes = [
            {"features": [geocode_feature("Chicago, Illinois, United States", CHICAGO)]},
            {"features": [geocode_feature("Denver, Colorado, United States", DENVER)]},
        ]
        with _RouteApiHarness(geocodes, _ok_directions([])):
            res = self.post_json(_valid_payload())
        self.assertEqual(res.status_code, 422)
        self.assertEqual(json.loads(res.content)["error"]["code"], "no_routes")
        self._assert_no_token(res)

    def test_rate_limit_maps_to_429(self):
        geocodes = [
            {"features": [geocode_feature("Chicago, Illinois, United States", CHICAGO)]},
            {"features": [geocode_feature("Denver, Colorado, United States", DENVER)]},
        ]
        with _RouteApiHarness(geocodes, {"code": "TooManyRequests", "message": "Throttled"}, directions_status=429):
            res = self.post_json(_valid_payload())
        self.assertEqual(res.status_code, 429)
        self.assertEqual(json.loads(res.content)["error"]["code"], "rate_limited")
        self._assert_no_token(res)

    def test_auth_rejection_maps_to_502_with_clean_message(self):
        geocodes = [
            {"features": [geocode_feature("Chicago, Illinois, United States", CHICAGO)]},
            {"features": [geocode_feature("Denver, Colorado, United States", DENVER)]},
        ]
        with _RouteApiHarness(geocodes, {}, directions_status=403):
            res = self.post_json(_valid_payload())
        self.assertEqual(res.status_code, 502)
        data = json.loads(res.content)
        self.assertEqual(data["error"]["code"], "auth_failed")
        detail = data["error"]["message"]
        self.assertNotIn(TEST_TOKEN, detail)
        self._assert_no_token(res)

    def test_timeout_maps_to_504(self):
        def fake_timeout(url, params=None, timeout=None):
            raise real_requests.exceptions.Timeout("connect timeout")

        with patch.object(routing_service.requests, "get", side_effect=fake_timeout):
            res = self.post_json(_valid_payload())
        self.assertEqual(res.status_code, 504)
        self.assertEqual(json.loads(res.content)["error"]["code"], "provider_timeout")

    def test_malformed_directions_payload_maps_to_502(self):
        geocodes = [
            {"features": [geocode_feature("Chicago, Illinois, United States", CHICAGO)]},
            {"features": [geocode_feature("Denver, Colorado, United States", DENVER)]},
        ]
        with _RouteApiHarness(geocodes, {"code": "Ok", "unexpected": True}):
            res = self.post_json(_valid_payload())
        self.assertEqual(res.status_code, 502)
        self.assertEqual(json.loads(res.content)["error"]["code"], "provider_response")

    def test_route_missing_distance_maps_to_502(self):
        geocodes = [
            {"features": [geocode_feature("Chicago, Illinois, United States", CHICAGO)]},
            {"features": [geocode_feature("Denver, Colorado, United States", DENVER)]},
        ]
        broken = raw_route("I-80 W", 1_614_300.0, 53_400.0, _line(CHICAGO, DENVER))
        broken.pop("distance")
        with _RouteApiHarness(geocodes, _ok_directions([broken])):
            res = self.post_json(_valid_payload())
        self.assertEqual(json.loads(res.content)["error"]["code"], "provider_response")

    def test_unparsable_directions_json_maps_to_502(self):
        geocodes = [
            {"features": [geocode_feature("Chicago, Illinois, United States", CHICAGO)]},
            {"features": [geocode_feature("Denver, Colorado, United States", DENVER)]},
        ]
        with _RouteApiHarness(geocodes, UNPARSABLE):
            res = self.post_json(_valid_payload())
        self.assertEqual(json.loads(res.content)["error"]["code"], "provider_response")

    # ---------- persistence & token hygiene ----------

    def test_no_database_persistence_anywhere_in_pipeline(self):
        routes = [
            raw_route("I-80 W", 1_614_300.0, 53_400.0, _line(CHICAGO, DENVER)),
            raw_route("US-30", 1_817_400.0, 60_300.0, _line(CHICAGO, DENVER, extra=[[-95.0, 41.0]])),
        ]
        with CaptureQueriesContext(connection) as ctx:
            with self._standard_harness(routes):
                res = self.post_json(_valid_payload())
        self.assertEqual(res.status_code, 200)
        writes = [
            q for q in ctx.captured_queries
            if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        ]
        self.assertEqual(writes, [], "route generation must never persist anything")

    # ---------- Phase 9: heatmaps in the route response ----------

    def _two_routes(self):
        return [
            raw_route("I-80 W", 1_614_300.0, 53_400.0, _line(CHICAGO, DENVER)),
            raw_route("US-30", 1_817_400.0, 60_300.0, _line(CHICAGO, DENVER, extra=[[-95.0, 41.0]])),
        ]

    def test_heatmaps_present_with_grid_points_in_response(self):
        with self._standard_harness(self._two_routes()):
            res = self.post_json(_valid_payload())
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertIn("heatmaps", data)
        hms = data["heatmaps"]
        self.assertEqual(len(hms), data["routeCount"])
        ids = {r["routeId"] for r in data["routes"]}
        self.assertEqual({h["routeId"] for h in hms}, ids)
        for hm in hms:
            self.assertEqual(hm["forecastHours"], 48)
            self.assertEqual(len(hm["gridPoints"]) > 0, True,
                             "non-degenerate corridor must yield grid points")
            gp = hm["gridPoints"][0]
            for key in ("longitude", "latitude", "hours", "windMph", "rainInPerHr", "snowfallInPerHr"):
                self.assertIn(key, gp)
            self.assertEqual(len(gp["hours"]), len(gp["windMph"]))
            self.assertEqual(len(gp["hours"]) <= 49, True, "provider buckets ≤ 49 (0–48 h)")
            # Faked provider series: first bucket hour is deterministic
            self.assertEqual(gp["hours"][0], "2099-01-01T16:00")
            self.assertFalse(hm["forecastStartISO"] is None)
            self.assertFalse(hm["forecastEndISO"] is None)
        # Dedupe across routes: distinct corridor variants → distinct route ids,
        # each route keeps its own grid-point list.
        first, second = hms[0], hms[1]
        self.assertNotEqual(first["routeId"], second["routeId"])

    def test_heatmap_generation_failure_never_breaks_routes(self):
        original = routing_service.get_heatmap_for_routes

        def boom(*args, **kwargs):
            raise RuntimeError("simulated heatmap outage")

        with patch.object(routing_service, "get_heatmap_for_routes", boom):
            with self._standard_harness(self._two_routes()) as harness:
                res = self.post_json(_valid_payload())
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertEqual(data["routeCount"], 2)
        self.assertEqual(data["heatmaps"], [], "outage must degrade to absent, not fail")
        # Weather enrichment (non-heatmap path) must remain live: the harness
        # served open-meteo responses, so checkpoints still got weather.
        self.assertTrue(data["routes"][0].get("checkpoints"))
        self.assertIsNotNone(res.content)


class RoutingServiceUnitTests(TestCase):
    """Pure-function checks against the routing service helpers."""

    def test_readable_duration_boundaries(self):
        cases = {
            0: "0 min",
            59.4: "0 min",
            60.0: "1 min",
            3_600.0: "1 h 0 min",
            53_400.0: "14 h 50 min",
        }
        for seconds, expected in cases.items():
            self.assertEqual(routing_service._readable_duration(seconds), expected)

    def test_fingerprint_distinguishes_metrics_and_summary(self):
        a = raw_route("I-80 W", 100.0, 60.0, [[-87.0, 41.0], [-104.0, 39.0]])
        b = raw_route("I-80 W", 100.5, 60.0, [[-87.0, 41.0], [-104.0, 39.0]])
        c = raw_route("US-30", 100.0, 60.0, [[-87.0, 41.0], [-104.0, 39.0]])
        self.assertNotEqual(routing_service._route_fingerprint(a), routing_service._route_fingerprint(b))
        self.assertNotEqual(routing_service._route_fingerprint(a), routing_service._route_fingerprint(c))

    def test_invalid_coordinate_pair_rejected(self):
        with self.assertRaises(routing_service.ProviderResponseError):
            routing_service._validate_coordinates_pair([200.0, 91.0])      # out of range
        with self.assertRaises(routing_service.ProviderResponseError):
            routing_service._validate_coordinates_pair([0.0])              # wrong arity
        with self.assertRaises(routing_service.ProviderResponseError):
            routing_service._validate_coordinates_pair("x,y")              # not a sequence

    def test_geocode_url_quotes_query_string(self):
        """geocode_place must percent-encode the raw query (spaces, commas)."""
        recorded: list = []

        def fake(url, params=None, timeout=None):
            recorded.append(url)
            return FakeResponse(200, {"features": [geocode_feature("x", CHICAGO)]})

        with patch.object(routing_service.requests, "get", side_effect=fake):
            routing_service.geocode_place("Chicago, IL", stage="origin")
        self.assertIn("Chicago%2C%20IL.json", recorded[-1])
