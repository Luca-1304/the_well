"""Deterministic full-route probe for NASA Data Hub.

This runs the packaged HTTP server with a fake upstream client so every browser
and API route can be exercised repeatedly without consuming NASA rate limits.
"""

from __future__ import annotations

import json
import tempfile
import threading
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from nasa_data_hub.client import RateLimit
from nasa_data_hub.config import Settings
from nasa_data_hub.server import HubServer


class FakeClient:
    rate_limit = RateLimit(limit=1000, remaining=999)

    def apod(self, *, day: date | None = None, **_: object) -> dict[str, object]:
        return {
            "date": (day or date(2025, 1, 1)).isoformat(),
            "title": "Reliability fixture",
            "url": "https://example.invalid/apod.jpg",
        }

    def neo_feed(self, start_date: date, end_date: date | None = None) -> dict[str, object]:
        end = end_date or start_date
        return {
            "element_count": 0,
            "near_earth_objects": {
                start_date.isoformat(): [],
                end.isoformat(): [],
            },
        }

    def donki(self, event_type: str, **_: object) -> list[dict[str, str]]:
        return [{"event_type": event_type, "status": "fixture"}]

    def eonet_events(self, **_: object) -> dict[str, object]:
        return {"events": [{"id": "fixture-event", "title": "Fixture event"}]}


def read_json(url: str) -> tuple[int, dict[str, object], str | None]:
    with urlopen(url, timeout=10) as response:
        return (
            response.status,
            json.loads(response.read().decode("utf-8")),
            response.headers.get("Cache-Control"),
        )


def main() -> int:
    with tempfile.TemporaryDirectory() as cache_dir:
        settings = Settings(
            api_key="DEMO_KEY",
            host="127.0.0.1",
            port=0,
            cache_dir=Path(cache_dir),
        )
        server = HubServer((settings.host, 0), settings)
        server.client = FakeClient()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"

        try:
            with urlopen(base + "/", timeout=10) as response:
                html = response.read().decode("utf-8")
                assert response.status == 200
                assert "NASA Data Hub" in html
                assert response.headers.get("Cache-Control") == "no-store"

            routes = {
                "/api/health": lambda body: body["ok"] is True,
                "/api/apod?date=2025-01-01": lambda body: body["data"]["title"]
                == "Reliability fixture",
                "/api/neo?start=2025-01-01&end=2025-01-01": lambda body: "near_earth_objects"
                in body["data"],
                "/api/donki?type=FLR&start=2025-01-01&end=2025-01-02": lambda body: body[
                    "data"
                ][0]["status"]
                == "fixture",
                "/api/eonet?status=open&limit=2": lambda body: body["data"]["events"][
                    0
                ]["id"]
                == "fixture-event",
            }
            for path, validate in routes.items():
                status, body, cache_control = read_json(base + path)
                assert status == 200, path
                assert body["ok"] is True, (path, body)
                assert cache_control == "no-store", path
                assert validate(body), (path, body)

            for path, expected in (
                ("/api/neo", 400),
                ("/api/unknown", 404),
                ("/missing.txt", 404),
            ):
                try:
                    urlopen(base + path, timeout=10)
                except HTTPError as exc:
                    assert exc.code == expected, (path, exc.code)
                    if path.startswith("/api/"):
                        body = json.loads(exc.read().decode("utf-8"))
                        assert body["ok"] is False
                else:
                    raise AssertionError(f"{path} should return {expected}")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    print("Deterministic packaged dashboard and all API routes: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
