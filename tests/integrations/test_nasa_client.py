from __future__ import annotations

import io
import json
from datetime import date
from email.message import Message
from urllib.error import HTTPError

import pytest

from integrations.nasa import nasa_client
from integrations.nasa.nasa_client import NASAAPIError, NASAClient, RateLimitState


class FakeResponse:
    def __init__(self, payload, headers=None):
        self.payload = payload
        self.headers = headers or Message()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_requires_key(monkeypatch):
    monkeypatch.delenv("NASA_API_KEY", raising=False)
    with pytest.raises(NASAAPIError, match="NASA_API_KEY"):
        NASAClient()


def test_apod_validation():
    client = NASAClient("test")
    with pytest.raises(ValueError, match="Choose only"):
        client.apod(day=date(2026, 1, 1), count=2)
    with pytest.raises(ValueError, match="end_date requires"):
        client.apod(end_date=date(2026, 1, 2))


def test_neo_window_validation():
    client = NASAClient("test")
    with pytest.raises(ValueError, match="seven days"):
        client.neo_feed(date(2026, 1, 1), date(2026, 1, 9))


def test_apod_adds_key_and_reads_rate_limit(monkeypatch):
    observed = {}
    headers = Message()
    headers["X-RateLimit-Limit"] = "1000"
    headers["X-RateLimit-Remaining"] = "999"

    def fake_urlopen(request, timeout):
        observed["url"] = request.full_url
        observed["timeout"] = timeout
        return FakeResponse({"title": "Test"}, headers)

    monkeypatch.setattr(nasa_client, "urlopen", fake_urlopen)
    client = NASAClient("secret", timeout_seconds=4)
    assert client.apod(day=date(2026, 1, 2)) == {"title": "Test"}
    assert "api_key=secret" in observed["url"]
    assert "date=2026-01-02" in observed["url"]
    assert observed["timeout"] == 4
    assert client.rate_limit == RateLimitState(limit=1000, remaining=999)


def test_eonet_does_not_send_key(monkeypatch):
    observed = {}

    def fake_urlopen(request, timeout):
        observed["url"] = request.full_url
        return FakeResponse({"events": []})

    monkeypatch.setattr(nasa_client, "urlopen", fake_urlopen)
    result = NASAClient("secret").eonet_events(categories=["wildfires"])
    assert result == {"events": []}
    assert "api_key" not in observed["url"]
    assert "category=wildfires" in observed["url"]


def test_retries_rate_limit(monkeypatch):
    calls = {"count": 0}
    headers = Message()
    headers["Retry-After"] = "0"

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            raise HTTPError(
                request.full_url,
                429,
                "rate limited",
                headers,
                io.BytesIO(b'{"error": "slow down"}'),
            )
        return FakeResponse({"title": "Recovered"})

    monkeypatch.setattr(nasa_client, "urlopen", fake_urlopen)
    monkeypatch.setattr(nasa_client.time, "sleep", lambda _: None)
    client = NASAClient("secret", max_retries=1)
    assert client.apod() == {"title": "Recovered"}
    assert calls["count"] == 2


def test_http_error_preserves_metadata(monkeypatch):
    headers = Message()
    headers["Retry-After"] = "12"

    def fake_urlopen(request, timeout):
        raise HTTPError(
            request.full_url,
            429,
            "rate limited",
            headers,
            io.BytesIO(b'{"error": "quota exceeded"}'),
        )

    monkeypatch.setattr(nasa_client, "urlopen", fake_urlopen)
    client = NASAClient("secret", max_retries=0)
    with pytest.raises(NASAAPIError, match="quota exceeded") as caught:
        client.apod()
    assert caught.value.status_code == 429
    assert caught.value.retry_after == 12


def test_cli_parser():
    args = nasa_client.build_parser().parse_args(
        ["neo", "--start", "2026-08-01", "--end", "2026-08-02"]
    )
    assert args.command == "neo"
    assert args.start == date(2026, 8, 1)
