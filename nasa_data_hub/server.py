"""Local HTTP server and browser dashboard for NASA Data Hub."""

from __future__ import annotations

import json
import mimetypes
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .client import NASAAPIError, NASAClient
from .config import Settings

STATIC_DIR = Path(__file__).resolve().parent / "static"


class HubServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], settings: Settings):
        super().__init__(address, HubHandler)
        self.settings = settings
        self.client = NASAClient(
            settings.api_key,
            timeout_seconds=settings.timeout_seconds,
            max_retries=settings.max_retries,
            cache_dir=settings.cache_dir,
            cache_ttl_seconds=settings.cache_ttl_seconds,
        )


class HubHandler(BaseHTTPRequestHandler):
    server: HubServer

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        parsed = urlparse(self.path)
        try:
            if parsed.path.startswith("/api/"):
                self._api(parsed.path, parse_qs(parsed.query))
            else:
                self._static(parsed.path)
        except (NASAAPIError, ValueError) as exc:
            status = (
                HTTPStatus.BAD_GATEWAY
                if isinstance(exc, NASAAPIError)
                else HTTPStatus.BAD_REQUEST
            )
            self._json(
                {
                    "ok": False,
                    "error": str(exc),
                    "status_code": getattr(exc, "status_code", None),
                    "retry_after": getattr(exc, "retry_after", None),
                },
                status,
            )
        except Exception:
            self._json(
                {
                    "ok": False,
                    "error": "Unexpected server error. Check the terminal log.",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            raise

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[NASA Hub] {self.address_string()} - {format % args}")

    def _api(self, path: str, query: dict[str, list[str]]) -> None:
        client = self.server.client
        if path == "/api/health":
            self._json(
                {
                    "ok": True,
                    "service": "NASA Data Hub",
                    "key_mode": self.server.settings.key_mode,
                    "using_demo_key": self.server.settings.using_demo_key,
                    "rate_limit": {
                        "limit": client.rate_limit.limit,
                        "remaining": client.rate_limit.remaining,
                    },
                    "message": (
                        "Running with NASA DEMO_KEY. Add a rotated NASA_API_KEY to .env for higher limits."
                        if self.server.settings.using_demo_key
                        else "Running with a personal NASA API key loaded from the environment."
                    ),
                }
            )
            return

        if path == "/api/apod":
            result = client.apod(day=_optional_date(_first(query, "date")))
        elif path == "/api/neo":
            start = _required_date(_first(query, "start"), "start")
            result = client.neo_feed(start, _optional_date(_first(query, "end")))
        elif path == "/api/donki":
            result = client.donki(
                _first(query, "type") or "FLR",
                start_date=_optional_date(_first(query, "start")),
                end_date=_optional_date(_first(query, "end")),
            )
        elif path == "/api/eonet":
            result = client.eonet_events(
                status=_first(query, "status") or "open",
                limit=_optional_int(_first(query, "limit"), 20),
                days=_optional_int(_first(query, "days"), None),
                categories=query.get("category"),
                sources=query.get("source"),
                geojson=_first(query, "geojson") == "true",
            )
        else:
            self._json(
                {"ok": False, "error": "Unknown API route"}, HTTPStatus.NOT_FOUND
            )
            return

        self._json(
            {
                "ok": True,
                "data": result,
                "rate_limit": {
                    "limit": client.rate_limit.limit,
                    "remaining": client.rate_limit.remaining,
                },
            }
        )

    def _static(self, path: str) -> None:
        relative = "index.html" if path in {"", "/"} else path.lstrip("/")
        target = (STATIC_DIR / relative).resolve()
        try:
            target.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = target.read_bytes()
        content_type = (
            mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        )
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def _json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)


def run_server(settings: Settings, *, open_browser: bool = False) -> None:
    server = HubServer((settings.host, settings.port), settings)
    url = f"http://{settings.host}:{settings.port}"
    print(f"NASA Data Hub running at {url}")
    print(
        "Key mode: DEMO_KEY (limited)"
        if settings.using_demo_key
        else "Key mode: personal key loaded securely"
    )
    print("Press Ctrl+C to stop.")
    if open_browser:
        import webbrowser

        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping NASA Data Hub.")
    finally:
        server.server_close()


def _first(query: dict[str, list[str]], name: str) -> str | None:
    values = query.get(name)
    return values[0] if values else None


def _optional_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _required_date(value: str | None, name: str) -> date:
    if not value:
        raise ValueError(f"{name} is required")
    return date.fromisoformat(value)


def _optional_int(value: str | None, default: int | None) -> int | None:
    return int(value) if value else default
