import io
import json
import tempfile
import unittest
from datetime import date
from email.message import Message
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from nasa_data_hub import client as module
from nasa_data_hub.client import NASAAPIError, NASAClient, RateLimit


class FakeResponse:
    def __init__(self, payload, headers=None):
        self.payload = payload
        self.headers = headers or Message()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class ClientTests(unittest.TestCase):
    def test_works_with_demo_key(self):
        self.assertEqual(NASAClient().api_key, "DEMO_KEY")

    def test_eonet_never_sends_key(self):
        seen = {}

        def fake_urlopen(request, timeout):
            seen["url"] = request.full_url
            return FakeResponse({"events": []})

        with patch.object(module, "urlopen", fake_urlopen):
            self.assertEqual(NASAClient("secret").eonet_events(), {"events": []})
        self.assertNotIn("secret", seen["url"])
        self.assertNotIn("api_key", seen["url"])

    def test_apod_sends_key_and_tracks_rate_limit(self):
        seen = {}
        headers = Message()
        headers["X-RateLimit-Limit"] = "1000"
        headers["X-RateLimit-Remaining"] = "999"

        def fake_urlopen(request, timeout):
            seen["url"] = request.full_url
            return FakeResponse({"title": "Test"}, headers)

        with patch.object(module, "urlopen", fake_urlopen):
            client = NASAClient("secret")
            self.assertEqual(client.apod(day=date(2026, 8, 2)), {"title": "Test"})
        self.assertIn("api_key=secret", seen["url"])
        self.assertEqual(client.rate_limit, RateLimit(1000, 999))

    def test_cache_identity_does_not_contain_secret(self):
        with tempfile.TemporaryDirectory() as folder:
            client = NASAClient("top-secret", cache_dir=folder)
            with patch.object(
                module,
                "urlopen",
                lambda request, timeout: FakeResponse({"x": 1}),
            ):
                client.apod(day=date(2026, 8, 2))
            names = [p.name for p in Path(folder).glob("*.json")]
            self.assertEqual(len(names), 1)
            self.assertNotIn("top-secret", names[0])

    def test_response_links_and_cache_never_expose_key(self):
        payload = {
            "links": {"self": "https://api.nasa.gov/neo?api_key=top-secret&x=1"},
            "nested": ["https://api.nasa.gov/neo?x=1&API_KEY=top-secret#fragment"],
        }
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(
                module,
                "urlopen",
                lambda request, timeout: FakeResponse(payload),
            ):
                result = NASAClient("top-secret", cache_dir=folder).neo_feed(
                    date(2026, 8, 2)
                )

            serialised = json.dumps(result)
            self.assertNotIn("top-secret", serialised)
            self.assertNotIn("api_key", serialised.lower())
            self.assertEqual(
                result["links"]["self"],
                "https://api.nasa.gov/neo?x=1",
            )
            self.assertEqual(
                result["nested"][0],
                "https://api.nasa.gov/neo?x=1#fragment",
            )
            cache_files = list(Path(folder).glob("*.json"))
            self.assertEqual(len(cache_files), 1)
            cache_text = cache_files[0].read_text(encoding="utf-8")
            self.assertNotIn("top-secret", cache_text)
            self.assertNotIn("api_key", cache_text.lower())

    def test_retries_429(self):
        calls = 0
        headers = Message()
        headers["Retry-After"] = "0"

        def fake_urlopen(request, timeout):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise HTTPError(
                    request.full_url,
                    429,
                    "limited",
                    headers,
                    io.BytesIO(b'{"error":"slow down"}'),
                )
            return FakeResponse({"title": "Recovered"})

        with (
            patch.object(module, "urlopen", fake_urlopen),
            patch.object(module.time, "sleep", lambda _: None),
        ):
            result = NASAClient("secret", max_retries=1).apod()
        self.assertEqual(result["title"], "Recovered")
        self.assertEqual(calls, 2)

    def test_http_error_is_actionable(self):
        headers = Message()

        def fake_urlopen(request, timeout):
            raise HTTPError(
                request.full_url,
                403,
                "forbidden",
                headers,
                io.BytesIO(b'{"error":"API_KEY_INVALID"}'),
            )

        with patch.object(module, "urlopen", fake_urlopen):
            with self.assertRaises(NASAAPIError) as caught:
                NASAClient("bad", max_retries=0).apod()
        self.assertEqual(str(caught.exception), "API_KEY_INVALID")
        self.assertEqual(caught.exception.status_code, 403)

    def test_neo_defaults_to_single_day(self):
        seen = {}

        def fake_urlopen(request, timeout):
            seen["url"] = request.full_url
            return FakeResponse({})

        with patch.object(module, "urlopen", fake_urlopen):
            NASAClient("secret").neo_feed(date(2026, 8, 2))
        self.assertIn("start_date=2026-08-02", seen["url"])
        self.assertIn("end_date=2026-08-02", seen["url"])

    def test_neo_rejects_long_window(self):
        with self.assertRaises(ValueError):
            NASAClient().neo_feed(date(2026, 8, 1), date(2026, 8, 10))


if __name__ == "__main__":
    unittest.main()
