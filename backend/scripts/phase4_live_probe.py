"""Phase 4 LIVE checkpoint probe (manual, sandbox, not part of the suite).

Calls the real dev server at POST /api/trips/routes/ and inspects the Phase 4
checkpoint fields on the actual provider-backed response: counts, interval,
capped flag, cumulative distances, ETA monotonicity, destination inclusion and
checkpoint-ID stability across two identical calls. Never prints the token.

Run (backend dev server must be up):
    backend/.venv/Scripts/python.exe scripts/phase4_live_probe.py
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone as dt_tz
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402

BASE_URL = os.environ.get("PROBE_BASE_URL", "http://127.0.0.1:8001")


def payload() -> dict:
    return {
        "origin": "Chicago, IL",
        "destination": "Denver, CO",
        "departureISO": (datetime.now(dt_tz.utc) + timedelta(hours=12)).isoformat(),
        "loadWeightLb": 34000,
        "checkpointIntervalMiles": 25,
    }


def fetch(payload_dict: dict) -> dict:
    res = requests.post(f"{BASE_URL}/api/trips/routes/", json=payload_dict, timeout=90)
    print("HTTP status:", res.status_code)
    if res.status_code != 200:
        print(res.text[:400])
        raise SystemExit(1)
    return res.json()


def describe(data: dict, label: str) -> list:
    print(f"\n[{label}] routesAvailable={data['routesAvailable']} routeCount={data['routeCount']}")
    ids = []
    for route in data["routes"]:
        summary = route["checkpointSummary"]
        checkpoints = route["checkpoints"]
        ids.append([cp["checkpointId"] for cp in checkpoints])
        first, last = checkpoints[0], checkpoints[-1]
        distances = [cp["distanceFromStartMeters"] for cp in checkpoints]
        arrivals = [cp["arrivalISO"] for cp in checkpoints]
        monotonic_dist = distances == sorted(distances)
        monotonic_eta = arrivals == sorted(arrivals)
        print(
            f"  {route['label']} [{route['routeId']}] provider {route['distanceMiles']} mi / "
            f"{route['durationReadable']} | checkpoints={summary['count']} "
            f"@{summary['effectiveIntervalMiles']} mi (requested {summary['requestedIntervalMiles']}), "
            f"capped={summary['capped']}, max={summary['maxPerRoute']}"
        )
        print(
            f"    geometry {summary['geometryDistanceMiles']} mi vs provider "
            f"{round(summary['providerDistanceMeters'] / 1609.344, 1)} mi; "
            f"first seq={first['sequence']} {first['distanceFromStartMiles']} mi "
            f"interpolated={first['interpolated']}; last seq={last['sequence']} "
            f"{last['distanceFromStartMiles']} mi interpolated={last['interpolated']}"
        )
        print(
            f"    last checkpoint arrival equals route arrival: "
            f"{last['arrivalISO'] == route['arrivalISO']} ({last['arrivalISO']})"
        )
        print(f"    monotonic distances={monotonic_dist}; monotonic ETAs={monotonic_eta}")
        print(
            f"    destination coords preserved: "
            f"{last['coordinates'] == route['geometry']['coordinates'][-1]}"
        )
    return ids


def main() -> None:
    data = fetch(payload())
    ids_first = describe(data, "call 1")
    data2 = fetch(payload())
    ids_second = describe(data2, "call 2")
    stable = ids_first == ids_second
    print("\ncheckpoint IDs identical across repeated identical requests:", stable)
    body = json.dumps(data)
    print("token-leak-suspect:", "pk." in body)


if __name__ == "__main__":
    main()
