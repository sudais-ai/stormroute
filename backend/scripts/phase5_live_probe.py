"""Phase 5 LIVE weather probe (manual, sandbox, not part of the suite).

Calls the real dev server at POST /api/trips/routes/ and inspects the Phase 5
weather fields on the actual provider-backed response. Never prints the token.

Run (backend dev server must be up):
    backend/.venv/Scripts/python.exe scripts/phase5_live_probe.py
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
    res = requests.post(f"{BASE_URL}/api/trips/routes/", json=payload_dict, timeout=120)
    print("HTTP status:", res.status_code)
    if res.status_code != 200:
        print(res.text[:800])
        raise SystemExit(1)
    return res.json()


def describe(data: dict) -> None:
    print(f"\n[routesAvailable={data['routesAvailable']} routeCount={data['routeCount']}]")
    if not data.get("routesAvailable"):
        print("  Error:", data.get("error"))
        return

    for route in data["routes"]:
        print(f"  {route['label']} [{route['routeId']}] provider {route['distanceMiles']} mi / {route['durationReadable']}")
        print(f"    checkpoints={route['checkpointSummary']['count']}")

        # Weather summary
        wsum = data.get("weatherSummaries", [])
        rsum = next((s for s in wsum if s["routeId"] == route["routeId"]), None)
        if rsum:
            print(
                f"    weather: {rsum['checkpointsWithWeather']}/{rsum['totalCheckpoints']} with data, "
                f"{rsum['checkpointsUnavailable']} unavailable"
            )
            if rsum["providerForecastStartISO"] and rsum["providerForecastEndISO"]:
                print(
                    f"      provider window: {rsum['providerForecastStartISO']} to {rsum['providerForecastEndISO']}"
                )

        # Check first 3 checkpoints' weather
        cps = route.get("checkpoints", [])
        for i, cp in enumerate(cps[:3]):
            w = cp.get("weather")
            if w:
                print(
                    f"      cp {cp['sequence']}: arrival={cp['arrivalISO']} match={w['timeMatch']} "
                    f"wind={w['windMph']}mph rain={w['rainInPerHr']}in/hr snow={w['snowfallInPerHr']}in/hr"
                )
            else:
                print(f"      cp {cp['sequence']}: NO WEATHER FIELD")

        if route.get("weatherError"):
            print(f"      weatherError: {route['weatherError']}")

    body = json.dumps(data)
    print("\ntoken-leak-suspect:", "pk." in body)


def main() -> None:
    data = fetch(payload())
    describe(data)


if __name__ == "__main__":
    main()