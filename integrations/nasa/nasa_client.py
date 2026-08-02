"""NASA Open APIs helper. Set NASA_API_KEY in the environment; never commit it."""

import json
import os
from datetime import date
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.nasa.gov"


def _key() -> str:
    value = os.getenv("NASA_API_KEY", "").strip()
    if not value:
        raise RuntimeError("NASA_API_KEY is not set")
    return value


def _get(path: str, **params):
    params["api_key"] = _key()
    url = f"{BASE_URL}/{path.lstrip('/')}?{urlencode(params)}"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "the-well/1.0"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def apod(day: date | None = None):
    params = {"thumbs": "true"}
    if day:
        params["date"] = day.isoformat()
    return _get("planetary/apod", **params)


def near_earth_objects(start: date, end: date | None = None):
    params = {"start_date": start.isoformat()}
    if end:
        params["end_date"] = end.isoformat()
    return _get("neo/rest/v1/feed", **params)


def space_weather(event_type: str, start: date, end: date):
    allowed = {"CME", "GST", "IPS", "FLR", "SEP", "MPC", "RBE", "HSS"}
    event_type = event_type.upper()
    if event_type not in allowed:
        raise ValueError(f"event_type must be one of {sorted(allowed)}")
    return _get(
        f"DONKI/{event_type}",
        startDate=start.isoformat(),
        endDate=end.isoformat(),
    )


if __name__ == "__main__":
    print(json.dumps(apod(), indent=2))
