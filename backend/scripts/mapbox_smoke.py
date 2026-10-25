"""
Live Mapbox confirmation smoke (sandbox, NOT part of the Django test suite).

Purpose: verify the configured MAPBOX_ACCESS_TOKEN actually works and that
Directions with alternatives=true returns real route data (how many routes for
a real corridor). Value privacy: never prints the token; prints statuses,
counts, and coarse geometry only. Run manually: backend/scripts/mapbox_smoke.py
"""

import json
import os
import sys
from pathlib import Path  # noqa: F401

# Standalone runnable outside manage.py: bootstrap Django settings first.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stormroute.settings")

import django

django.setup()

import requests
from django.conf import settings  # noqa: E402

BASE = "https://api.mapbox.com"
PROFILE = "mapbox/driving"


def geocode(token, place):
    r = requests.get(
        f"{BASE}/geocoding/v5/mapbox.places/{requests.utils.quote(place)}.json",
        params={"access_token": token, "limit": 1},
        timeout=20,
    )
    if r.status_code != 200:
        return r.status_code, None
    feats = r.json().get("features") or []
    return r.status_code, feats[0].get("center") if feats else None


def directions(token, o, d):
    coords = f"{o[0]},{o[1]};{d[0]},{d[1]}"
    r = requests.get(
        f"{BASE}/directions/v5/{PROFILE}/{coords}",
        params={"access_token": token, "alternatives": "true", "overview": "simplified"},
        timeout=30,
    )
    if r.status_code != 200:
        return {"status": r.status_code, "error_head": r.text[:120]}
    data = r.json()
    routes = data.get("routes") or []
    return {
        "status": r.status_code,
        "codes": (data.get("code"), r.status_code == 200),
        "route_count": len(routes),
        "routes_coarse": [
            {
                "distance_km": round(x["distance"] / 1000, 1),
                "duration_h": round(x["duration"] / 3600, 2),
            }
            for x in routes
        ],
    }


def main():
    token = settings.MAPBOX_ACCESS_TOKEN
    if not token:
        print("MAPBOX token: unset")
        sys.exit(1)
    print("MAPBOX token: set (value not shown)")

    o_status, o = geocode(token, "Chicago, IL")
    d_status, d = geocode(token, "Denver, CO")
    print(f"geocode 'Chicago, IL': status={o_status} center={o}")
    print(f"geocode 'Denver, CO': status={d_status} center={d}")

    if o and d:
        res = directions(token, o, d)
        print("directions alternatives=true:", json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
