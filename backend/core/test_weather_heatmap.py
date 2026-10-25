"""Phase 9 heatmap service tests — deterministic, no real HTTP.

Grid generation, provider payload validation/alignment, response
serialization, and multi-route deduped fetch orchestration are tested
against fixtures. The network fetcher is never exercised over real HTTP;
timeout/provider failure paths are simulated with unittest.mock.
"""

from datetime import datetime, timezone
from unittest.mock import patch

from django.test import TestCase

from core.services.weather_heatmap import (
    HeatmapGridPoint,
    RouteHeatmap,
    _build_batch_url,
    _series_from_response,
    generate_route_grid_points,
    get_heatmap_for_routes,
    heatmap_to_payload,
)


def _fixed_series(hours: int, wind: float, rain: float, snow: float) -> dict:
    start = datetime(2099, 1, 1, 16, tzinfo=timezone.utc)
    return {
        "hourly": {
            "time": [(start.replace()).isoformat() for _ in range(hours)],
            "wind_speed_10m": [wind] * hours,
            "rain": [rain] * hours,
            "snowfall": [snow] * hours,
        }
    }


class GridPointGenerationTests(TestCase):
    """`generate_route_grid_points` — deterministic sampling along geometry."""

    def test_rejects_degenerate_geometry(self):
        self.assertEqual(generate_route_grid_points([]), [])
        self.assertEqual(generate_route_grid_points([[-87.6, 41.8]]), [])

    def test_rejects_insufficient_valid_points(self):
        # One invalid coordinate filtered → only one remains → []
        coords = [[-87.6, 41.8], [999.0, 91.0]]
        self.assertEqual(generate_route_grid_points(coords), [])

    def test_rejects_non_positive_spacing_or_cap(self):
        line = [[-87.6, 41.8], [-86.6, 41.8]]
        with self.assertRaises(ValueError):
            generate_route_grid_points(line, spacing_meters=0)
        with self.assertRaises(ValueError):
            generate_route_grid_points(line, max_points=0)

    def test_evenly_spaced_samples_inclusive_of_endpoints(self):
        # ~111 km straight west line → with 11 km spacing ≈ 11 points.
        line = [[-87.6, 41.8], [-88.6, 41.8]]
        pts = generate_route_grid_points(line, spacing_meters=11_000, max_points=60)
        self.assertGreaterEqual(len(pts), 9)
        self.assertLessEqual(len(pts), 13)
        # Endpoints included: first/lon ≈ -87.6, last/lon ≈ -88.6
        self.assertAlmostEqual(pts[0][0], -87.6, places=2)
        self.assertAlmostEqual(pts[-1][0], -88.6, places=2)
        # Lon strictly decreasing (westbound), lat constant.
        for a, b in zip(pts, pts[1:]):
            self.assertLess(b[0], a[0])
            self.assertAlmostEqual(b[1], 41.8, places=6)

    def test_cap_stretches_spacing(self):
        # Enormous line, capped at 60 → 60 points.
        line = [[-87.6, 41.8], [-117.6, 41.8]]  # ~2600 km
        pts = generate_route_grid_points(line, spacing_meters=11_000, max_points=60)
        self.assertEqual(len(pts), 60)

    def test_invalid_vertices_are_filtered(self):
        line = [[-87.6, 41.8], ["x", "y"], [-88.6, 41.8]]
        pts = generate_route_grid_points(line, spacing_meters=11_000, max_points=60)
        self.assertGreaterEqual(len(pts), 2)
        self.assertAlmostEqual(pts[0][0], -87.6, places=2)


class SeriesValidationTests(TestCase):
    """`_series_from_response` — contract validation + hour slicing."""

    def test_valid_payload_sliced_to_forecast_hours_plus_one(self):
        payload = _fixed_series(hours=72, wind=10.0, rain=0.2, snow=0.0)
        series = _series_from_response(payload, forecast_hours=48)
        self.assertIsNotNone(series)
        self.assertEqual(len(series["hours"]), 49)
        # Rounded per policy
        self.assertEqual(series["windMph"][0], 10.0)
        self.assertEqual(series["rainInPerHr"][0], 0.2)

    def test_shorter_provider_response_is_used_honestly(self):
        payload = _fixed_series(hours=10, wind=5.0, rain=0.0, snow=0.0)
        series = _series_from_response(payload, forecast_hours=48)
        self.assertIsNotNone(series)
        self.assertEqual(len(series["hours"]), 10)

    def test_missing_values_become_none(self):
        payload = {
            "hourly": {
                "time": ["2099-01-01T16:00", "2099-01-01T17:00"],
                "wind_speed_10m": [10.0],
                "rain": [None, "bad"],
                "snowfall": [0.0, 0.0],
            }
        }
        series = _series_from_response(payload, forecast_hours=48)
        self.assertIsNotNone(series)
        self.assertEqual(series["windMph"], [10.0, None])
        self.assertEqual(series["rainInPerHr"], [None, None])
        self.assertEqual(series["snowfallInPerHr"], [0.0, 0.0])

    def test_structurally_invalid_payload_returns_none(self):
        self.assertIsNone(_series_from_response(None, 48))
        self.assertIsNone(_series_from_response({"nope": 1}, 48))
        self.assertIsNone(
            _series_from_response({"hourly": {"time": [], "wind_speed_10m": [], "rain": [], "snowfall": []}}, 48)
        )
        # Missing one array → invalid
        self.assertIsNone(_series_from_response({"hourly": {"time": ["2099-01-01T16:00"]}}, 48))


class BatchUrlTests(TestCase):
    def test_url_contains_all_coordinates_and_params(self):
        coords = [(-87.6324, 41.8820), (-104.9861, 39.7417)]
        url = _build_batch_url(coords)
        self.assertIn("api.open-meteo.com/v1/forecast", url)
        self.assertIn("latitude=41.882,39.7417", url)
        self.assertIn("longitude=-87.6324,-104.9861", url)
        self.assertIn("hourly=wind_speed_10m,rain,snowfall", url)
        self.assertIn("wind_speed_unit=mph", url)
        self.assertIn("precipitation_unit=inch", url)
        self.assertIn("timezone=UTC", url)


class GetHeatmapForRoutesTests(TestCase):
    """Orchestration: dedupe across routes, batching, failure tolerance."""

    def _route(self, route_id: str, line):
        return {
            "routeId": route_id,
            "geometry": {"type": "LineString", "coordinates": line},
        }

    def test_no_routes_returns_empty_list(self):
        self.assertEqual(get_heatmap_for_routes([]), [])

    def test_no_valid_geometry_returns_empty_grid_points(self):
        heatmap = get_heatmap_for_routes(
            [self._route("r1", [[-87.6, 41.8]])],
            fetcher=lambda coords: ([None] * len(coords)),
        )
        self.assertEqual(len(heatmap), 1)
        self.assertEqual(heatmap[0].route_id, "r1")
        self.assertEqual(heatmap[0].grid_points, [])
        self.assertIsNone(heatmap[0].forecast_start_iso)

    def test_two_routes_share_deduped_fetches(self):
        # Two routes with IDENTICAL geometry → union of unique keys should
        # be fetched exactly once (deduped).
        line = [[-87.6, 41.8], [-88.6, 41.8]]
        calls = []

        def fake_fetcher(coords):
            calls.append(list(coords))
            return [_series_from_response(_fixed_series(49, 10.0, 0.0, 0.0), 48) for _ in coords]

        heatmaps = get_heatmap_for_routes(
            [self._route("r1", line), self._route("r2", line)],
            fetcher=fake_fetcher,
            batch_size=100,
        )
        self.assertEqual(len(heatmaps), 2)
        for hm in heatmaps:
            self.assertGreaterEqual(len(hm.grid_points), 9)
            self.assertEqual(hm.forecast_hours, 48)
            self.assertIsNotNone(hm.forecast_start_iso)
            self.assertIsNotNone(hm.forecast_end_iso)
        # Both routes received the SAME grid points (shared corridor fetch).
        r1_keys = [(gp.longitude, gp.latitude) for gp in heatmaps[0].grid_points]
        r2_keys = [(gp.longitude, gp.latitude) for gp in heatmaps[1].grid_points]
        self.assertEqual(r1_keys, r2_keys)
        # Dedupe: coordinates in one batch appear at most once.
        fetched = [c for batch in calls for c in batch]
        self.assertEqual(len(fetched), len(set(fetched)))

    def test_provider_failure_yields_heatmap_without_points(self):
        line = [[-87.6, 41.8], [-88.6, 41.8]]
        heatmaps = get_heatmap_for_routes(
            [self._route("r1", line)],
            fetcher=lambda coords: [None] * len(coords),
        )
        self.assertEqual(len(heatmaps), 1)
        self.assertEqual(heatmaps[0].grid_points, [])
        self.assertIsNone(heatmaps[0].forecast_start_iso)

    def test_result_never_raises_on_fetcher_exception(self):
        line = [[-87.6, 41.8], [-88.6, 41.8]]

        def exploding_fetcher(_coords):
            raise RuntimeError("simulated unexpected failure")

        with patch(
            "core.services.weather_heatmap.requests.get",
            side_effect=RuntimeError("should never be called"),
        ):
            heatmaps = get_heatmap_for_routes(
                [self._route("r1", line)],
                fetcher=exploding_fetcher,
            )
        self.assertEqual(heatmaps[0].grid_points, [])


class PayloadSerializationTests(TestCase):
    def test_payload_shape_and_roundtrip(self):
        grid_point = HeatmapGridPoint(
            longitude=-87.6,
            latitude=41.8,
            hours=["2099-01-01T16:00"],
            wind_mph=[10.0],
            rain_in_per_hr=[0.0],
            snowfall_in_per_hr=[0.0],
        )
        heat = RouteHeatmap(
            route_id="r1",
            grid_points=[grid_point],
            forecast_start_iso="2099-01-01T16:00",
            forecast_end_iso="2099-01-01T16:00",
            forecast_hours=48,
        )
        payload = heatmap_to_payload(heat)
        self.assertEqual(payload["routeId"], "r1")
        self.assertEqual(len(payload["gridPoints"]), 1)
        gp = payload["gridPoints"][0]
        self.assertEqual(gp["longitude"], -87.6)
        self.assertEqual(gp["hours"], ["2099-01-01T16:00"])
        self.assertEqual(gp["windMph"], [10.0])
        self.assertEqual(payload["forecastStartISO"], "2099-01-01T16:00")
        self.assertEqual(payload["forecastHours"], 48)
