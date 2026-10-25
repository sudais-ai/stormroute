import json
from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

"""Backend tests for StormRoute.

Sections:
1. Health endpoint (Phase 1 foundation).
2. Trip-input validation endpoint (Phase 2).

All data here is TEST FIXTURES for development verification, not production
results. Departure expectations use deliberate +/- hour margins so no test
depends on an exact wall-clock instant.
"""


def _iso(dt) -> str:
    return dt.isoformat()


def _future(hours: float) -> str:
    return _iso(timezone.now() + timedelta(hours=hours))


def _past(hours: float) -> str:
    return _iso(timezone.now() - timedelta(hours=hours))


def _valid_payload(**overrides) -> dict:
    payload = {
        "origin": "Chicago, IL",
        "destination": "Denver, CO",
        "departureISO": _future(6),
        "loadWeightLb": 34000,
        "checkpointIntervalMiles": 25,
    }
    payload.update(overrides)
    return payload


class HealthEndpointTests(TestCase):
    """Phase 1 fixture: identity contract of GET /api/health/."""

    def setUp(self):
        self.client = Client()

    def test_health_returns_ok_service_identity(self):
        res = self.client.get("/api/health/")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "stormroute-backend")

    def test_health_exposes_version(self):
        res = self.client.get("/api/health/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("version", json.loads(res.content))


class TripValidationEndpointTests(TestCase):
    """Phase 2: POST /api/trips/validate/ contract — validate-only."""

    def setUp(self):
        self.client = Client()
        self.url = "/api/trips/validate/"

    def post_json(self, payload: dict):
        return self.client.post(self.url, json.dumps(payload), content_type="application/json")

    def without_key(self, payload: dict, key: str) -> dict:
        clone = dict(payload)
        clone.pop(key, None)
        return clone

    # ---------- happy path ----------

    def test_valid_trip_returns_200_with_normalized_values(self):
        res = self.post_json(_valid_payload())
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertTrue(data["valid"])
        trip = data["trip"]
        self.assertEqual(trip["origin"], "Chicago, IL")
        self.assertEqual(trip["destination"], "Denver, CO")
        self.assertTrue(trip["departureISO"].endswith("+00:00"))
        self.assertEqual(trip["loadWeightLb"], 34000.0)
        self.assertEqual(trip["checkpointIntervalMiles"], 25)
        # Honest scope: must not claim routing or safety analysis happened.
        self.assertIn("no routing", data["message"].lower())

    def test_valid_trip_trims_whitespace_around_addresses(self):
        res = self.post_json(_valid_payload(origin="  Chicago, IL  ", destination="\tDenver, CO "))
        self.assertEqual(res.status_code, 200)
        trip = json.loads(res.content)["trip"]
        self.assertEqual(trip["origin"], "Chicago, IL")
        self.assertEqual(trip["destination"], "Denver, CO")

    def test_zero_load_weight_is_valid(self):
        res = self.post_json(_valid_payload(loadWeightLb=0))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.content)["trip"]["loadWeightLb"], 0.0)

    def test_all_spec_intervals_are_valid(self):
        for interval in (10, 25, 50):
            res = self.post_json(_valid_payload(checkpointIntervalMiles=interval))
            self.assertEqual(res.status_code, 200, f"interval {interval} must be accepted")
            self.assertEqual(json.loads(res.content)["trip"]["checkpointIntervalMiles"], interval)

    def test_interval_defaults_to_25_when_omitted(self):
        res = self.post_json(self.without_key(_valid_payload(), "checkpointIntervalMiles"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.content)["trip"]["checkpointIntervalMiles"], 25)

    def test_far_future_departure_is_accepted(self):
        res = self.post_json(_valid_payload(departureISO=_future(24 * 30)))
        self.assertEqual(res.status_code, 200)

    # ---------- departure normalization ----------

    def test_naive_timestamp_rejected_not_silently_assumed(self):
        naive = timezone.localdate().isoformat() + "T09:00:00"
        res = self.post_json(_valid_payload(departureISO=naive))
        self.assertEqual(res.status_code, 400)
        self.assertIn("departureISO", json.loads(res.content)["errors"])

    def test_fixed_offset_timestamp_is_flushed_to_utc(self):
        # 2099 deterministic year: far future, DST-proof wall time.
        res = self.post_json(_valid_payload(departureISO="2099-01-01T08:00:00-08:00"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.content)["trip"]["departureISO"], "2099-01-01T16:00:00+00:00")

    # ---------- required / empty / duplicate locations ----------

    def test_missing_origin_rejected_with_field_error(self):
        res = self.post_json(self.without_key(_valid_payload(), "origin"))
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.content)
        self.assertFalse(data["valid"])
        self.assertIn("origin", data["errors"])

    def test_missing_destination_rejected_with_field_error(self):
        res = self.post_json(self.without_key(_valid_payload(), "destination"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("destination", json.loads(res.content)["errors"])

    def test_whitespace_only_origin_rejected(self):
        res = self.post_json(_valid_payload(origin="   "))
        self.assertEqual(res.status_code, 400)
        self.assertIn("origin", json.loads(res.content)["errors"])

    def test_whitespace_only_destination_rejected(self):
        res = self.post_json(_valid_payload(destination=" "))
        self.assertEqual(res.status_code, 400)
        self.assertIn("destination", json.loads(res.content)["errors"])

    def test_identical_origin_and_destination_rejected(self):
        res = self.post_json(_valid_payload(origin="Denver, CO", destination="Denver, CO"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("destination", json.loads(res.content)["errors"])

    def test_identical_after_whitespace_normalization_rejected(self):
        res = self.post_json(_valid_payload(origin="  Denver, CO", destination="Denver, CO  "))
        self.assertEqual(res.status_code, 400)
        self.assertIn("destination", json.loads(res.content)["errors"])

    def test_multiple_errors_all_reported_not_first_only(self):
        bad = {
            "origin": "  ",
            "destination": "",
            "departureISO": "not-a-date",
            "loadWeightLb": -5,
            "checkpointIntervalMiles": 15,
        }
        res = self.post_json(bad)
        self.assertEqual(res.status_code, 400)
        errors = json.loads(res.content)["errors"]
        for field in ("origin", "destination", "departureISO", "loadWeightLb", "checkpointIntervalMiles"):
            self.assertIn(field, errors, f"{field} must be reported alongside the others")

    # ---------- departure edge cases ----------

    def test_missing_departure_rejected(self):
        res = self.post_json(self.without_key(_valid_payload(), "departureISO"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("departureISO", json.loads(res.content)["errors"])

    def test_malformed_departure_string_rejected_not_500(self):
        res = self.post_json(_valid_payload(departureISO="not-a-date"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("departureISO", json.loads(res.content)["errors"])

    def test_past_departure_rejected(self):
        res = self.post_json(_valid_payload(departureISO=_past(1)))
        self.assertEqual(res.status_code, 400)
        self.assertIn("departureISO", json.loads(res.content)["errors"])

    # ---------- load weight ----------

    def test_missing_load_weight_rejected(self):
        res = self.post_json(self.without_key(_valid_payload(), "loadWeightLb"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("loadWeightLb", json.loads(res.content)["errors"])

    def test_negative_load_weight_rejected(self):
        res = self.post_json(_valid_payload(loadWeightLb=-1000))
        self.assertEqual(res.status_code, 400)
        self.assertIn("loadWeightLb", json.loads(res.content)["errors"])

    def test_non_numeric_load_weight_rejected(self):
        res = self.post_json(_valid_payload(loadWeightLb="heavy"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("loadWeightLb", json.loads(res.content)["errors"])

    # ---------- sampling interval ----------

    def test_unsupported_interval_rejected(self):
        for bad in (15, 0, 100):
            res = self.post_json(_valid_payload(checkpointIntervalMiles=bad))
            self.assertEqual(res.status_code, 400, f"interval {bad} must be rejected")
            self.assertIn("checkpointIntervalMiles", json.loads(res.content)["errors"])

    # ---------- transport safety ----------

    def test_malformed_json_body_rejected_with_safe_message(self):
        res = self.client.post(self.url, "{not json", content_type="application/json")
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.content)
        self.assertFalse(data["valid"])
        body_text = json.dumps(data).lower()
        self.assertNotIn("traceback", body_text)
        self.assertNotIn("exception", body_text)

    def test_empty_body_rejected(self):
        res = self.client.post(self.url, "", content_type="application/json")
        self.assertEqual(res.status_code, 400)

    def test_error_response_shape_is_field_map(self):
        res = self.post_json({"origin": ""})
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.content)
        self.assertIn("valid", data)
        self.assertIn("errors", data)
        self.assertFalse(data["valid"])
        self.assertIn("origin", data["errors"])
