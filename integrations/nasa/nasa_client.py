"""Secure NASA Open APIs and EONET client with a small command-line interface."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

NASA_BASE_URL = "https://api.nasa.gov"
EONET_BASE_URL = "https://eonet.gsfc.nasa.gov/api/v3"
_RETRYABLE = {429, 500, 502, 503, 504}
_DONKI = {
    "CME", "CMEAnalysis", "GST", "IPS", "FLR", "SEP", "MPC", "RBE", "HSS",
    "WSAEnlilSimulations", "notifications",
}


class NASAAPIError(RuntimeError):
    """NASA service failure with optional HTTP metadata."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


@dataclass(frozen=True)
class RateLimitState:
    """Latest api.nasa.gov rate-limit headers."""

    limit: int | None = None
    remaining: int | None = None


class NASAClient:
    """Dependency-free client for APOD, NeoWs, DONKI, and EONET v3."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout_seconds: float = 20.0,
        max_retries: int = 3,
        backoff_seconds: float = 0.5,
        cache_dir: str | os.PathLike[str] | None = None,
        cache_ttl_seconds: float = 300.0,
        user_agent: str = "the-well-nasa-client/2.0",
    ) -> None:
        self.api_key = (api_key or os.getenv("NASA_API_KEY", "")).strip()
        if not self.api_key:
            raise NASAAPIError(
                "NASA_API_KEY is missing. Set it in the environment or pass api_key."
            )
        if timeout_seconds <= 0 or max_retries < 0 or backoff_seconds < 0:
            raise ValueError("Invalid timeout/retry configuration")
        if cache_ttl_seconds < 0:
            raise ValueError("cache_ttl_seconds cannot be negative")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.cache_dir = Path(cache_dir).expanduser() if cache_dir else None
        self.cache_ttl_seconds = cache_ttl_seconds
        self.user_agent = user_agent
        self.rate_limit = RateLimitState()

    @classmethod
    def from_env(cls, **kwargs: Any) -> "NASAClient":
        return cls(**kwargs)

    @staticmethod
    def _params(values: Mapping[str, Any] | None) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in (values or {}).items():
            if value is None:
                continue
            if isinstance(value, bool):
                output[key] = str(value).lower()
            elif isinstance(value, (list, tuple, set)):
                output[key] = ",".join(str(item) for item in value)
            else:
                output[key] = value
        return output

    def _cache_path(self, url: str) -> Path | None:
        if self.cache_dir is None or self.cache_ttl_seconds == 0:
            return None
        name = hashlib.sha256(url.encode("utf-8")).hexdigest() + ".json"
        return self.cache_dir / name

    def _read_cache(self, path: Path | None) -> Any | None:
        if path is None or not path.exists():
            return None
        try:
            if time.time() - path.stat().st_mtime > self.cache_ttl_seconds:
                return None
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _write_cache(self, path: Path | None, payload: Any) -> None:
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload), encoding="utf-8")
            temporary.replace(path)
        except OSError:
            pass

    @staticmethod
    def _header_int(headers: Any, name: str) -> int | None:
        raw = headers.get(name)
        try:
            return int(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None

    def _set_rate_limit(self, headers: Any) -> None:
        self.rate_limit = RateLimitState(
            self._header_int(headers, "X-RateLimit-Limit"),
            self._header_int(headers, "X-RateLimit-Remaining"),
        )

    @staticmethod
    def _retry_after(headers: Any) -> float | None:
        raw = headers.get("Retry-After")
        try:
            return max(0.0, float(raw)) if raw is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _error_text(body: str, fallback: str) -> str:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return body.strip() or fallback
        if isinstance(payload, dict):
            for key in ("error", "msg", "message"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
                if isinstance(value, dict) and value.get("message"):
                    return str(value["message"])
        return fallback

    def _get(
        self,
        base_url: str,
        path: str,
        params: Mapping[str, Any] | None = None,
        *,
        authenticated: bool,
        cache: bool = True,
    ) -> Any:
        query = self._params(params)
        if authenticated:
            query["api_key"] = self.api_key
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        if query:
            url += "?" + urlencode(query)

        cache_path = self._cache_path(url) if cache else None
        cached = self._read_cache(cache_path)
        if cached is not None:
            return cached

        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": self.user_agent},
        )
        for attempt in range(self.max_retries + 1):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    self._set_rate_limit(response.headers)
                    payload = json.loads(response.read().decode("utf-8"))
                    self._write_cache(cache_path, payload)
                    return payload
            except HTTPError as exc:
                self._set_rate_limit(exc.headers)
                body = exc.read().decode("utf-8", errors="replace")
                retry_after = self._retry_after(exc.headers)
                if exc.code in _RETRYABLE and attempt < self.max_retries:
                    delay = retry_after
                    if delay is None:
                        delay = min(self.backoff_seconds * (2**attempt), 30.0)
                    time.sleep(min(delay, 60.0))
                    continue
                raise NASAAPIError(
                    self._error_text(body, f"NASA returned HTTP {exc.code}"),
                    status_code=exc.code,
                    retry_after=retry_after,
                ) from exc
            except (URLError, TimeoutError) as exc:
                if attempt < self.max_retries:
                    time.sleep(min(self.backoff_seconds * (2**attempt), 30.0))
                    continue
                raise NASAAPIError(f"NASA request failed: {exc}") from exc
            except json.JSONDecodeError as exc:
                raise NASAAPIError("NASA returned invalid JSON") from exc
        raise NASAAPIError("NASA request failed after retries")

    def apod(
        self,
        *,
        day: date | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        count: int | None = None,
        thumbnails: bool = True,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Get one APOD, a date range, or random APOD entries."""
        mode_count = sum(
            (day is not None, start_date is not None or end_date is not None, count is not None)
        )
        if mode_count > 1:
            raise ValueError("Choose only day, date range, or count")
        if end_date is not None and start_date is None:
            raise ValueError("end_date requires start_date")
        if start_date and end_date and end_date < start_date:
            raise ValueError("end_date cannot precede start_date")
        if count is not None and not 1 <= count <= 100:
            raise ValueError("count must be between 1 and 100")
        return self._get(
            NASA_BASE_URL,
            "planetary/apod",
            {
                "date": day.isoformat() if day else None,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "count": count,
                "thumbs": thumbnails,
            },
            authenticated=True,
        )

    def neo_feed(self, start_date: date, end_date: date | None = None) -> dict[str, Any]:
        """Get close-approach objects for a maximum seven-day window."""
        end = end_date or start_date + timedelta(days=7)
        if end < start_date:
            raise ValueError("end_date cannot precede start_date")
        if (end - start_date).days > 7:
            raise ValueError("NeoWs feed windows cannot exceed seven days")
        result = self._get(
            NASA_BASE_URL,
            "neo/rest/v1/feed",
            {"start_date": start_date.isoformat(), "end_date": end.isoformat()},
            authenticated=True,
        )
        if not isinstance(result, dict):
            raise NASAAPIError("Unexpected NeoWs feed response")
        return result

    def neo_lookup(self, asteroid_id: str | int) -> dict[str, Any]:
        value = str(asteroid_id).strip()
        if not value:
            raise ValueError("asteroid_id cannot be empty")
        result = self._get(
            NASA_BASE_URL, f"neo/rest/v1/neo/{value}", authenticated=True
        )
        if not isinstance(result, dict):
            raise NASAAPIError("Unexpected NeoWs lookup response")
        return result

    def neo_browse(self, *, page: int = 0, size: int = 20) -> dict[str, Any]:
        if page < 0 or not 1 <= size <= 100:
            raise ValueError("page must be >= 0 and size must be 1..100")
        result = self._get(
            NASA_BASE_URL,
            "neo/rest/v1/neo/browse",
            {"page": page, "size": size},
            authenticated=True,
        )
        if not isinstance(result, dict):
            raise NASAAPIError("Unexpected NeoWs browse response")
        return result

    def donki(
        self,
        event_type: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        **filters: Any,
    ) -> list[dict[str, Any]]:
        """Query a current DONKI event family."""
        lookup = {name.lower(): name for name in _DONKI}
        endpoint = lookup.get(event_type.strip().lower())
        if endpoint is None:
            raise ValueError(f"event_type must be one of: {', '.join(sorted(_DONKI))}")
        if start_date and end_date and end_date < start_date:
            raise ValueError("end_date cannot precede start_date")
        result = self._get(
            NASA_BASE_URL,
            f"DONKI/{endpoint}",
            {
                "startDate": start_date.isoformat() if start_date else None,
                "endDate": end_date.isoformat() if end_date else None,
                **filters,
            },
            authenticated=True,
            cache=False,
        )
        if not isinstance(result, list):
            raise NASAAPIError("Unexpected DONKI response")
        return result

    def donki_notifications(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        notification_type: str = "all",
    ) -> list[dict[str, Any]]:
        return self.donki(
            "notifications",
            start_date=start_date,
            end_date=end_date,
            type=notification_type,
        )

    def eonet_events(
        self,
        *,
        status: str = "open",
        limit: int = 20,
        days: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        categories: Sequence[str] | None = None,
        sources: Sequence[str] | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        geojson: bool = False,
    ) -> dict[str, Any]:
        """Get near-real-time natural events from current EONET v3."""
        if status not in {"open", "closed", "all"}:
            raise ValueError("status must be open, closed, or all")
        if limit < 1 or (days is not None and days < 1):
            raise ValueError("limit and days must be positive")
        if start_date and end_date and end_date < start_date:
            raise ValueError("end_date cannot precede start_date")
        result = self._get(
            EONET_BASE_URL,
            "events/geojson" if geojson else "events",
            {
                "status": status,
                "limit": limit,
                "days": days,
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
                "category": categories,
                "source": sources,
                "bbox": bbox,
            },
            authenticated=False,
            cache=False,
        )
        if not isinstance(result, dict):
            raise NASAAPIError("Unexpected EONET response")
        return result

    def eonet_event(self, event_id: str) -> dict[str, Any]:
        if not event_id.strip():
            raise ValueError("event_id cannot be empty")
        result = self._get(
            EONET_BASE_URL,
            f"events/{event_id.strip()}",
            authenticated=False,
            cache=False,
        )
        if not isinstance(result, dict):
            raise NASAAPIError("Unexpected EONET event response")
        return result

    def eonet_categories(self) -> dict[str, Any]:
        return self._get(EONET_BASE_URL, "categories", authenticated=False)

    def eonet_sources(self) -> dict[str, Any]:
        return self._get(EONET_BASE_URL, "sources", authenticated=False)

    def eonet_layers(self, category: str | None = None) -> dict[str, Any]:
        path = f"layers/{category.strip()}" if category else "layers"
        return self._get(EONET_BASE_URL, path, authenticated=False)


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use YYYY-MM-DD") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="the-well-nasa")
    parser.add_argument("--cache-dir", help="Optional response-cache directory")
    parser.add_argument("--compact", action="store_true", help="Compact JSON output")
    commands = parser.add_subparsers(dest="command", required=True)

    apod = commands.add_parser("apod", help="Astronomy Picture of the Day")
    apod.add_argument("--date", type=_date)
    apod.add_argument("--start", type=_date)
    apod.add_argument("--end", type=_date)
    apod.add_argument("--count", type=int)

    neo = commands.add_parser("neo", help="Near-Earth object feed")
    neo.add_argument("--start", type=_date, required=True)
    neo.add_argument("--end", type=_date)

    lookup = commands.add_parser("neo-lookup", help="Look up one asteroid")
    lookup.add_argument("asteroid_id")

    browse = commands.add_parser("neo-browse", help="Browse asteroids")
    browse.add_argument("--page", type=int, default=0)
    browse.add_argument("--size", type=int, default=20)

    donki = commands.add_parser("donki", help="Space-weather events")
    donki.add_argument("event_type")
    donki.add_argument("--start", type=_date)
    donki.add_argument("--end", type=_date)

    eonet = commands.add_parser("eonet", help="Natural events")
    eonet.add_argument("--status", choices=("open", "closed", "all"), default="open")
    eonet.add_argument("--limit", type=int, default=20)
    eonet.add_argument("--days", type=int)
    eonet.add_argument("--category", action="append")
    eonet.add_argument("--source", action="append")
    eonet.add_argument("--geojson", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        client = NASAClient.from_env(cache_dir=args.cache_dir)
        if args.command == "apod":
            result = client.apod(
                day=args.date,
                start_date=args.start,
                end_date=args.end,
                count=args.count,
            )
        elif args.command == "neo":
            result = client.neo_feed(args.start, args.end)
        elif args.command == "neo-lookup":
            result = client.neo_lookup(args.asteroid_id)
        elif args.command == "neo-browse":
            result = client.neo_browse(page=args.page, size=args.size)
        elif args.command == "donki":
            result = client.donki(
                args.event_type, start_date=args.start, end_date=args.end
            )
        else:
            result = client.eonet_events(
                status=args.status,
                limit=args.limit,
                days=args.days,
                categories=args.category,
                sources=args.source,
                geojson=args.geojson,
            )
        print(json.dumps(result, indent=None if args.compact else 2))
        return 0
    except (NASAAPIError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "EONET_BASE_URL",
    "NASAAPIError",
    "NASA_BASE_URL",
    "NASAClient",
    "RateLimitState",
    "build_parser",
    "main",
]
