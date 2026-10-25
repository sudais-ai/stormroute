"""Phase 4 backend tests — deterministic checkpoint sampling + ETA.

Layout:
- pure geometry/ETA tests (SimpleTestCase) exercise core.services.checkpoints
  directly with hand-computed fixtures;
- endpoint integration tests mock Mapbox exactly like test_routing.py so the
  real network is never touched, and assert that Phase 3 route fields remain
  intact while checkpoints are added.

No real token is used anywhere: TEST_TOKEN is the declared fixture from
test_routing.py.
"""

import json
import math
from datetime import datetime, timedelta, timezone as dt_timezone

from django.test import Client, SimpleTestCase, TestCase, override_settings

from core.services import checkpoints as checkpoint_service
from core.test_routing import (
    CHICAGO,
    DENVER,
    TEST_TOKEN,
    _RouteApiHarness,
    _line,
    _ok_directions,
    _valid_payload,
    raw_route,
)

_METERS_PER_MILE = 1609.344
_DEPARTURE_OFFSET = datetime(2099, 1, 1, 8, 0, 0, tzinfo=dt_timezone(timedelta(hours=-8)))
_DEPARTURE_UTC = datetime(2099, 1, 1, 16, 0, 0, tzinfo=dt_timezone.utc)


def total_geometry_meters(coordinates):
    points = checkpoint_service.validate_linestring_coordinates(coordinates)
    return checkpoint_service.cumulative_distances(points)[-1]


def make_route(coordinates, duration=36_000.0, distance=None, route_id="rt_fixture000001"):
    if distance is None:
        distance = total_geometry_meters(coordinates)
    return {
        "routeId": route_id,
        "label": "Route 1",
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "distanceMeters": distance,
        "durationSeconds": duration,
    }


def uncapped_count(total_meters, interval_miles):
    interval_meters = interval_miles * _METERS_PER_MILE
    count = math.floor(total_meters / interval_meters) + 1
    if total_meters - math.floor(total_meters / interval_meters) * interval_meters > 0.5:
        count += 1
    return count


class HaversineTests(SimpleTestCase):
    def test_zero_distance(self):
        self.assertEqual(checkpoint_service.haversine_meters(0.0, 0.0, 0.0, 0.0), 0.0)

    def test_one_degree_of_latitude_is_the_expected_great_circle_length(self):
        # pi/180 * 6_371_008.8 = 111_195.080... m
        self.assertAlmostEqual(
            checkpoint_service.haversine_meters(0.0, 0.0, 0.0, 1.0), 111_195.08, places=1
        )

    def test_distance_is_symmetric(self):
        a = checkpoint_service.haversine_meters(-87.6324, 41.8820, -104.9861, 39.7417)
        b = checkpoint_service.haversine_meters(-104.9861, 39.7417, -87.6324, 41.8820)
        self.assertAlmostEqual(a, b, places=6)

    def test_longitude_and_latitude_are_not_interchangeable(self):
        # At 41°N one degree of longitude is shorter than one degree of latitude.
        one_degree_east = checkpoint_service.haversine_meters(-87.0, 41.0, -86.0, 41.0)
        one_degree_north = checkpoint_service.haversine_meters(-87.0, 41.0, -87.0, 42.0)
        self.assertLess(one_degree_east, one_degree_north)
        self.assertGreater(one_degree_east, 80_000.0)


class GeometryValidationTests(SimpleTestCase):
    def test_empty_and_single_point_geometry_rejected(self):
        for bad in ([], [[0.0, 0.0]]):
            with self.assertRaises(checkpoint_service.CheckpointSamplingError):
                checkpoint_service.validate_linestring_coordinates(bad)

    def test_malformed_points_rejected(self):
        cases = [
            [[0.0, 0.0], [0.0]],
            [[0.0, 0.0], "0,0"],
            [[0.0, 0.0], [0.0, 0.0, 5.0]],
            [[0.0, 0.0], [float("nan"), 0.0]],
            [[0.0, 0.0], [float("inf"), 0.0]],
            [[0.0, 0.0], [200.0, 0.0]],
            [[0.0, 0.0], [0.0, 91.0]],
            [[0.0, 0.0], ["east", 0.0]],
        ]
        for bad in cases:
            with self.assertRaises(checkpoint_service.CheckpointSamplingError, msg=str(bad)):
                checkpoint_service.validate_linestring_coordinates(bad)

    def test_zero_length_geometry_rejected_after_duplicate_collapse(self):
        coords = [[-87.0, 41.0], [-87.0, 41.0], [-87.0, 41.0]]
        with self.assertRaises(checkpoint_service.CheckpointSamplingError):
            checkpoint_service.sample_route_checkpoints(make_route(coords, distance=1000.0), _DEPARTURE_UTC, 25)

    def test_duplicate_consecutive_vertices_are_safe_and_ignored(self):
        clean = [[0.0, 0.0], [0.0, 1.0]]
        with_dupes = [[0.0, 0.0], [0.0, 0.0], [0.0, 1.0], [0.0, 1.0]]
        a = checkpoint_service.sample_route_checkpoints(make_route(clean), _DEPARTURE_UTC, 25)
        b = checkpoint_service.sample_route_checkpoints(make_route(with_dupes), _DEPARTURE_UTC, 25)
        self.assertEqual(
            [cp["distanceFromStartMeters"] for cp in a["checkpoints"]],
            [cp["distanceFromStartMeters"] for cp in b["checkpoints"]],
        )
        self.assertEqual(len(a["checkpoints"]), len(b["checkpoints"]))


class SamplingTests(SimpleTestCase):
    def test_route_shorter_than_interval_returns_origin_and_destination_only(self):
        # ~0.69 mi route, 25-mile interval.
        coords = [[-87.0, 41.0], [-87.0, 41.01]]
        sampled = checkpoint_service.sample_route_checkpoints(make_route(coords), _DEPARTURE_UTC, 25)
        checkpoints = sampled["checkpoints"]
        total = sampled["summary"]["geometryDistanceMeters"]
        self.assertEqual(len(checkpoints), 2)
        self.assertEqual([cp["sequence"] for cp in checkpoints], [1, 2])
        self.assertEqual(checkpoints[0]["distanceFromStartMeters"], 0.0)
        self.assertEqual(checkpoints[-1]["distanceFromStartMeters"], total)
        self.assertEqual(checkpoints[0]["coordinates"], [-87.0, 41.0])
        self.assertEqual(checkpoints[-1]["coordinates"], [-87.0, 41.01])
        self.assertFalse(checkpoints[0]["interpolated"])
        self.assertFalse(checkpoints[-1]["interpolated"])

    def test_round_trip_returns_to_origin_with_nonzero_distance(self):
        # A → B → A: destination coordinates equal the origin, but the route
        # length is real. Checkpoints must follow traveled distance, not
        # coordinate equality, and ids must stay unique despite the shared point.
        coords = [[0.0, 0.0], [0.0, 0.5], [0.0, 0.0]]
        sampled = checkpoint_service.sample_route_checkpoints(
            make_route(coords, duration=7_200.0), _DEPARTURE_UTC, 25
        )
        checkpoints = sampled["checkpoints"]
        summary = sampled["summary"]
        self.assertGreater(summary["geometryDistanceMeters"], 100_000.0)
        self.assertEqual(len(checkpoints), uncapped_count(summary["geometryDistanceMeters"], 25))
        self.assertEqual(checkpoints[0]["coordinates"], [0.0, 0.0])
        self.assertEqual(checkpoints[-1]["coordinates"], [0.0, 0.0])
        self.assertEqual(checkpoints[-1]["distanceFromStartMeters"], summary["geometryDistanceMeters"])
        self.assertGreater(len(checkpoints), 2)
        self.assertEqual(len({cp["checkpointId"] for cp in checkpoints}), len(checkpoints))
        self.assertEqual(
            checkpoints[-1]["arrivalISO"], (_DEPARTURE_UTC + timedelta(seconds=7_200.0)).isoformat()
        )

    def test_destination_is_not_duplicated_when_it_lands_on_an_interval(self):
        coords = [[0.0, 0.0], [0.0, 1.0]]
        total_meters = total_geometry_meters(coords)
        half_interval_miles = (total_meters / 2.0) / _METERS_PER_MILE
        sampled = checkpoint_service.sample_route_checkpoints(
            make_route(coords), _DEPARTURE_UTC, half_interval_miles
        )
        checkpoints = sampled["checkpoints"]
        self.assertEqual(len(checkpoints), 3)
        distances = [cp["distanceFromStartMeters"] for cp in checkpoints]
        self.assertEqual(distances[0], 0.0)
        self.assertAlmostEqual(distances[1], round(total_meters / 2.0, 1), places=1)
        self.assertEqual(distances[-1], sampled["summary"]["geometryDistanceMeters"])
        self.assertEqual(len({cp["checkpointId"] for cp in checkpoints}), 3)

    def test_multi_interval_route_count_matches_distance_formula(self):
        coords = [[0.0, 0.0], [0.0, 3.0]]  # ~207 miles
        total = total_geometry_meters(coords)
        sampled = checkpoint_service.sample_route_checkpoints(make_route(coords), _DEPARTURE_UTC, 25)
        self.assertEqual(sampled["summary"]["count"], uncapped_count(total, 25))
        distances = [cp["distanceFromStartMeters"] for cp in sampled["checkpoints"]]
        self.assertEqual(distances, sorted(distances))
        self.assertEqual(distances[-1], sampled["summary"]["geometryDistanceMeters"])

    def test_partial_final_segment_included_after_last_full_interval(self):
        coords = [[0.0, 0.0], [0.0, 1.0]]  # ~69.09 miles
        total = total_geometry_meters(coords)
        sampled = checkpoint_service.sample_route_checkpoints(make_route(coords), _DEPARTURE_UTC, 25)
        distances = [cp["distanceFromStartMeters"] for cp in sampled["checkpoints"]]
        # 0, 25, 50, then the partial remainder (~19.09) to the destination.
        self.assertEqual(len(distances), 4)
        self.assertAlmostEqual(distances[-1], round(total, 1), places=1)
        self.assertLess(distances[-1] - distances[-2], 25 * _METERS_PER_MILE)

    def test_unevenly_spaced_vertices_are_interpolated_in_the_right_segment(self):
        coords = [[0.0, 0.0], [0.01, 0.0], [0.01, 0.02]]
        first_segment = checkpoint_service.haversine_meters(0.0, 0.0, 0.01, 0.0)
        second_segment = checkpoint_service.haversine_meters(0.01, 0.0, 0.01, 0.02)
        self.assertLess(first_segment, second_segment)
        sampled = checkpoint_service.sample_route_checkpoints(make_route(coords), _DEPARTURE_UTC, 1.0)
        second = sampled["checkpoints"][1]
        # 1 mile falls AFTER the first 0.69-mile vertex, so interpolation must
        # happen on the second (vertical) segment: longitude is pinned at 0.01.
        self.assertAlmostEqual(second["coordinates"][0], 0.01, places=6)
        self.assertGreater(second["coordinates"][1], 0.0)
        self.assertLess(second["coordinates"][1], 0.02)
        self.assertTrue(second["interpolated"])

    def test_longitude_latitude_order_preserved_in_checkpoints(self):
        coords = [[-88.0, 40.0], [-87.0, 40.0]]  # due east along 40°N
        sampled = checkpoint_service.sample_route_checkpoints(make_route(coords), _DEPARTURE_UTC, 5)
        for cp in sampled["checkpoints"]:
            longitude, latitude = cp["coordinates"]
            self.assertAlmostEqual(latitude, 40.0, places=6)
            self.assertGreaterEqual(longitude, -88.0)
            self.assertLessEqual(longitude, -87.0)
        self.assertGreater(len(sampled["checkpoints"]), 2)

    def test_monotonic_distances_and_eta_bounds(self):
        coords = [[-87.0, 41.0], [-95.0, 41.0], [-104.0, 40.0]]
        duration = 50_000.0
        sampled = checkpoint_service.sample_route_checkpoints(make_route(coords, duration=duration), _DEPARTURE_UTC, 25)
        checkpoints = sampled["checkpoints"]
        distances = [cp["distanceFromStartMeters"] for cp in checkpoints]
        arrivals = [datetime.fromisoformat(cp["arrivalISO"]) for cp in checkpoints]
        self.assertEqual(distances, sorted(distances))
        self.assertEqual(arrivals, sorted(arrivals))
        self.assertEqual(arrivals[0], _DEPARTURE_UTC)
        self.assertEqual(arrivals[-1], _DEPARTURE_UTC + timedelta(seconds=duration))

    def test_eta_is_distance_weighted(self):
        coords = [[0.0, 0.0], [0.0, 1.0]]
        total = total_geometry_meters(coords)
        interval_miles = (total / 4.0) / _METERS_PER_MILE
        sampled = checkpoint_service.sample_route_checkpoints(
            make_route(coords, duration=40_000.0), _DEPARTURE_UTC, interval_miles
        )
        checkpoints = sampled["checkpoints"]
        self.assertEqual(len(checkpoints), 5)
        self.assertAlmostEqual(checkpoints[0]["elapsedSeconds"], 0.0, places=1)
        self.assertAlmostEqual(checkpoints[2]["elapsedSeconds"], 20_000.0, delta=2.0)
        self.assertAlmostEqual(checkpoints[-1]["elapsedSeconds"], 40_000.0, delta=2.0)

    def test_departure_offset_is_normalized_to_utc(self):
        coords = [[0.0, 0.0], [0.0, 1.0]]
        sampled = checkpoint_service.sample_route_checkpoints(make_route(coords), _DEPARTURE_OFFSET, 50)
        for cp in sampled["checkpoints"]:
            self.assertTrue(cp["arrivalISO"].endswith("+00:00"), cp["arrivalISO"])
        self.assertEqual(sampled["checkpoints"][0]["arrivalISO"], _DEPARTURE_UTC.isoformat())

    def test_stable_ids_and_sequences(self):
        coords = [[0.0, 0.0], [0.0, 0.5], [0.5, 0.5]]
        route = make_route(coords)
        first = checkpoint_service.sample_route_checkpoints(route, _DEPARTURE_UTC, 25)
        second = checkpoint_service.sample_route_checkpoints(route, _DEPARTURE_UTC, 25)
        ids = [cp["checkpointId"] for cp in first["checkpoints"]]
        self.assertEqual(ids, [cp["checkpointId"] for cp in second["checkpoints"]])
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual([cp["sequence"] for cp in first["checkpoints"]], list(range(1, len(ids) + 1)))
        for cp in first["checkpoints"]:
            self.assertTrue(cp["checkpointId"].startswith("cp_"))
            self.assertEqual(len(cp["checkpointId"]), 15)
            self.assertEqual(cp["routeId"], "rt_fixture000001")

    def test_different_route_ids_produce_different_checkpoint_ids(self):
        coords = [[0.0, 0.0], [0.0, 1.0]]
        a = checkpoint_service.sample_route_checkpoints(make_route(coords, route_id="rt_aaaaaaaaaaaa"), _DEPARTURE_UTC, 25)
        b = checkpoint_service.sample_route_checkpoints(make_route(coords, route_id="rt_bbbbbbbbbbbb"), _DEPARTURE_UTC, 25)
        self.assertNotEqual(
            [cp["checkpointId"] for cp in a["checkpoints"]],
            [cp["checkpointId"] for cp in b["checkpoints"]],
        )

    def test_input_route_is_not_mutated(self):
        coords = [[0.0, 0.0], [0.0, 1.0]]
        route = make_route(coords, duration=10_000.0)
        before = json.dumps(route, sort_keys=True)
        checkpoint_service.sample_route_checkpoints(route, _DEPARTURE_UTC, 25)
        self.assertEqual(json.dumps(route, sort_keys=True), before)

    def test_provider_distance_is_preserved_untouched_in_summary(self):
        coords = [[0.0, 0.0], [0.0, 1.0]]
        route = make_route(coords, distance=123_456.7)
        sampled = checkpoint_service.sample_route_checkpoints(route, _DEPARTURE_UTC, 25)
        self.assertEqual(sampled["summary"]["providerDistanceMeters"], 123_456.7)
        self.assertNotEqual(sampled["summary"]["geometryDistanceMeters"], 123_456.7)


class InvalidTimingAndSettingsTests(SimpleTestCase):
    def _route(self, **overrides):
        route = make_route([[0.0, 0.0], [0.0, 1.0]])
        route.update(overrides)
        return route

    def test_invalid_duration_rejected(self):
        for bad in (0, -1, float("nan"), float("inf"), None, "soon"):
            with self.assertRaises(checkpoint_service.CheckpointSamplingError, msg=repr(bad)):
                checkpoint_service.sample_route_checkpoints(self._route(durationSeconds=bad), _DEPARTURE_UTC, 25)

    def test_invalid_provider_distance_rejected(self):
        for bad in (0, -5, float("nan"), None):
            with self.assertRaises(checkpoint_service.CheckpointSamplingError, msg=repr(bad)):
                checkpoint_service.sample_route_checkpoints(self._route(distanceMeters=bad), _DEPARTURE_UTC, 25)

    def test_invalid_interval_rejected(self):
        for bad in (0, -10, float("nan"), float("inf"), None):
            with self.assertRaises(checkpoint_service.CheckpointSamplingError, msg=repr(bad)):
                checkpoint_service.sample_route_checkpoints(self._route(), _DEPARTURE_UTC, bad)

    def test_naive_departure_rejected(self):
        with self.assertRaises(checkpoint_service.CheckpointSamplingError):
            checkpoint_service.sample_route_checkpoints(
                self._route(), datetime(2099, 1, 1, 8, 0, 0), 25
            )

    def test_invalid_max_checkpoints_rejected(self):
        for bad in (0, 1, -5, "500"):
            with self.assertRaises(checkpoint_service.CheckpointSamplingError, msg=repr(bad)):
                checkpoint_service.sample_route_checkpoints(self._route(), _DEPARTURE_UTC, 25, bad)

    def test_route_without_stable_id_rejected(self):
        route = self._route()
        route.pop("routeId")
        with self.assertRaises(checkpoint_service.CheckpointSamplingError):
            checkpoint_service.sample_route_checkpoints(route, _DEPARTURE_UTC, 25)


class MaximumCheckpointTests(SimpleTestCase):
    def test_cap_widens_spacing_and_keeps_destination(self):
        coords = [[0.0, 0.0], [0.0, 5.0]]  # ~345.9 miles
        total = total_geometry_meters(coords)
        sampled = checkpoint_service.sample_route_checkpoints(make_route(coords), _DEPARTURE_UTC, 10, max_checkpoints=20)
        checkpoints = sampled["checkpoints"]
        summary = sampled["summary"]
        self.assertLessEqual(len(checkpoints), 20)
        self.assertTrue(summary["capped"])
        self.assertGreater(summary["effectiveIntervalMiles"], 10.0)
        self.assertEqual(summary["maxPerRoute"], 20)
        self.assertEqual(checkpoints[0]["distanceFromStartMeters"], 0.0)
        self.assertAlmostEqual(checkpoints[-1]["distanceFromStartMeters"], round(total, 1), places=1)

    def test_uncapped_when_interval_already_below_cap(self):
        coords = [[0.0, 0.0], [0.0, 5.0]]
        total = total_geometry_meters(coords)
        sampled = checkpoint_service.sample_route_checkpoints(make_route(coords), _DEPARTURE_UTC, 10, max_checkpoints=500)
        self.assertFalse(sampled["summary"]["capped"])
        self.assertEqual(sampled["summary"]["effectiveIntervalMiles"], 10.0)
        self.assertEqual(sampled["summary"]["count"], uncapped_count(total, 10))

    def test_dense_geometry_stays_within_cap(self):
        # ~111 km straight line sampled at 1-mile spacing with a 25 cap.
        coords = [[0.0, 0.0], [0.0, 1.0]]
        sampled = checkpoint_service.sample_route_checkpoints(make_route(coords), _DEPARTURE_UTC, 1, max_checkpoints=25)
        self.assertLessEqual(len(sampled["checkpoints"]), 25)


@override_settings(MAPBOX_ACCESS_TOKEN=TEST_TOKEN)
class EndpointCheckpointIntegrationTests(TestCase):
    def setUp(self):
        self.url = "/api/trips/routes/"
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

    def test_checkpoints_are_returned_for_each_route(self):
        routes = [
            self._long_route(),
            self._long_route(summary="US-30; I-76 W", distance_m=1_817_400.0, duration_s=60_300.0,
                             coordinates=_line(CHICAGO, DENVER, extra=[[-95.0, 41.0]])),
        ]
        with self._harness(routes):
            res = self.post_json(_valid_payload())
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertEqual(data["routeCount"], 2)
        for route in data["routes"]:
            self.assertIn("checkpoints", route)
            self.assertIn("checkpointSummary", route)
            summary = route["checkpointSummary"]
            self.assertEqual(summary["count"], len(route["checkpoints"]))
            self.assertEqual(summary["requestedIntervalMiles"], 25)
            self.assertFalse(summary["capped"])
            self.assertEqual(summary["maxPerRoute"], 500)
            self.assertEqual(summary["providerDistanceMeters"], round(route["distanceMeters"], 1))
            first, last = route["checkpoints"][0], route["checkpoints"][-1]
            self.assertEqual(first["sequence"], 1)
            self.assertEqual(first["distanceFromStartMeters"], 0.0)
            self.assertEqual(first["coordinates"], route["geometry"]["coordinates"][0])
            self.assertEqual(last["coordinates"], route["geometry"]["coordinates"][-1])
            self.assertEqual(last["distanceFromStartMeters"], summary["geometryDistanceMeters"])
            self.assertEqual(last["arrivalISO"], route["arrivalISO"])
            for checkpoint in route["checkpoints"]:
                self.assertEqual(checkpoint["routeId"], route["routeId"])
                self.assertTrue(checkpoint["checkpointId"].startswith("cp_"))
            ids = [cp["checkpointId"] for cp in route["checkpoints"]]
            self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn(TEST_TOKEN.encode(), res.content)

    def test_ten_mile_interval_yields_more_checkpoints_than_fifty(self):
        with self._harness([self._long_route()]):
            ten = json.loads(self.post_json(_valid_payload(checkpointIntervalMiles=10)).content)
        with self._harness([self._long_route()]):
            fifty = json.loads(self.post_json(_valid_payload(checkpointIntervalMiles=50)).content)
        ten_route = ten["routes"][0]
        fifty_route = fifty["routes"][0]
        self.assertGreater(ten_route["checkpointSummary"]["count"], fifty_route["checkpointSummary"]["count"])
        total = ten_route["checkpointSummary"]["geometryDistanceMeters"]
        self.assertEqual(ten_route["checkpointSummary"]["count"], uncapped_count(total, 10))
        self.assertEqual(fifty_route["checkpointSummary"]["count"], uncapped_count(total, 50))

    @override_settings(CHECKPOINT_MAX_PER_ROUTE=12)
    def test_settings_cap_disclosed_in_response(self):
        with self._harness([self._long_route()]):
            res = self.post_json(_valid_payload(checkpointIntervalMiles=10))
        route = json.loads(res.content)["routes"][0]
        summary = route["checkpointSummary"]
        self.assertTrue(summary["capped"])
        self.assertLessEqual(summary["count"], 12)
        self.assertGreater(summary["effectiveIntervalMiles"], 10.0)
        self.assertEqual(route["checkpoints"][-1]["distanceFromStartMeters"], summary["geometryDistanceMeters"])

    def test_degenerate_geometry_returns_structured_geometry_error(self):
        broken = raw_route(
            "Loop", 1_000.0, 600.0, [[-87.0, 41.0], [-87.0, 41.0], [-87.0, 41.0]]
        )
        with self._harness([broken]):
            res = self.post_json(_valid_payload())
        self.assertEqual(res.status_code, 502)
        data = json.loads(res.content)
        self.assertFalse(data["routesAvailable"])
        self.assertEqual(data["error"]["code"], "geometry_invalid")
        self.assertNotIn(TEST_TOKEN.encode(), res.content)

    def test_out_of_range_coordinate_returns_structured_geometry_error(self):
        broken = raw_route("Bad", 1_000.0, 600.0, [[-87.0, 41.0], [200.0, 41.0]])
        with self._harness([broken]):
            res = self.post_json(_valid_payload())
        self.assertEqual(res.status_code, 502)
        self.assertEqual(json.loads(res.content)["error"]["code"], "geometry_invalid")

    def test_phase_three_route_fields_remain_unchanged(self):
        raw = self._long_route()
        with self._harness([raw]):
            res = self.post_json(_valid_payload())
        route = json.loads(res.content)["routes"][0]
        self.assertEqual(route["distanceMeters"], 1_614_300.0)
        self.assertEqual(route["durationSeconds"], 53_400.0)
        self.assertEqual(route["durationReadable"], "14 h 50 min")
        self.assertEqual(route["geometry"]["coordinates"], _line(CHICAGO, DENVER))
        self.assertEqual(route["arrivalISO"], "2099-01-02T06:50:00+00:00")

    def test_checkpoint_departure_is_the_validated_utc_instant(self):
        with self._harness([self._long_route()]):
            data = json.loads(self.post_json(_valid_payload()).content)
        first = data["routes"][0]["checkpoints"][0]
        self.assertEqual(first["arrivalISO"], "2099-01-01T16:00:00+00:00")
        self.assertEqual(data["trip"]["departureISO"], "2099-01-01T16:00:00+00:00")
