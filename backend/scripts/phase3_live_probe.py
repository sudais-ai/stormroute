"""Phase 3+ LIVE route-endpoint probe (manual, sandbox, not part of the suite).

Calls the real dev server (default http://127.0.0.1:8001) at
POST /api/trips/routes/ with a valid trip payload and prints only route
counts/metrics - never the token. Requires the backend dev server running
(routing/token lifecycle identical to Playwright/NodGE verification). Example:
    backend/.venv/Scripts/python.exe scripts/phase3_live_probe.py
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone as dt_tz
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402

BASE_URL = os.environ.get("PROBE_BASE_URL", "http://127.0.0.1:8001")


def main() -> None:
    departure = (datetime.now(dt_tz.utc) + timedelta(hours=12)).isoformat()
    payload = {
        "origin": "Chicago, IL",
        "destination": "Denver, CO",
        "departureISO": departure,
        "loadWeightLb": 34000,
        "checkpointIntervalMiles": 25,
    }
    res = requests.post(f"{BASE_URL}/api/trips/routes/", json=payload, timeout=60)
    print("HTTP status:", res.status_code)
    data = res.json()
    if res.status_code == 200 and data.get("routesAvailable"):
        print("routesAvailable:", data["routesAvailable"])
        print("routesRequested:", data["routesRequested"])
        print("routeCount:", data["routeCount"])
        print("threeRoutesReturned:", data["threeRoutesReturned"])
        print("duplicatesDropped:", data["duplicatesDropped"])
        print("warning:", data["warning"])
        for route in data["routes"]:
            print(
                f"  {route['label']} [{route['routeId']}] {route['distanceMiles']} mi, "
                f"{route['durationReadable']}, arrival {route['arrivalISO']}, "
                f"via {route['providerRouteSummary']}, "
                f"geometry-points={len(route['geometry']['coordinates'])}"
            )
        body = res.text
        print("token-leak-suspect:", "pk." in body.replace("pk.", "", 0))
    else:
        print("response:", json.dumps(data, indent=2)[:800])


if __name__ == "__main__":
    main()
