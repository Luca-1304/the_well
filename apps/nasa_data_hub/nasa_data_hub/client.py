"""Dependency-free clients for NASA Open APIs and EONET v3."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

NASA_BASE_URL = "https://api.nasa.gov"
EONET_BASE_URL = "https://eonet.gsfc.nasa.gov/api/v3"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
DONKI_ENDPOINTS = {
    "CME",
    "CMEAnalysis",
    "GST",
    "IPS",
    "FLR",
    "SEP",
    "MPC",
    "RBE",
    "HSS",
    "WSAEnlilSimulations",
    "notifications",
}


class NASAAPIError(RuntimeError):
    """Remote-service failure with safe, actionable metadata."""

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
class RateLimit:
    limit: int | None = None
    remaining: int | None = None


class NASAClient:
    """NASA data client.

    Authentication is optional at construction time because EONET does not need a
    key. Calls to api.nasa.gov use DEMO_KEY by default, so the hub works before a
    personal key is configured.
    """

    def __init__(
        self,
        api_key: str = "DEMO_KEY",
        *,
        timeout_seconds: float = 20.0,
        max_retries: int = 2,
        backoff_seconds: float = 0.5,
        cache_dir: str | Path | None = None,
        cache_ttl_seconds: float = 300.0,
        user_agent: str = "luca-nasa-data-hub/1.0",
    ) -> None:
        self.api_key = api_key.strip() or "DEMO_KEY"
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if backoff_seconds < 0:
            raise ValueError("backoff_seconds cannot be negative")
        if cache_ttl_seconds < 0:
            raise ValueError("cache_ttl_seconds cannot be negative")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.cache_ttl_seconds = cache_ttl_seconds
        self.user_agent = user_agent
        self.rate_limit = RateLimit()

    @staticmethod
    def _normalise_params(params: Mapping[str, Any] | None) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in (params or {}).items():
            if value is None:
                continue
            if isinstance(value, bool):
                output[key] = str(value).lower()
            elif isinstance(value, (list, tuple, set)):
                output[key] = ",".join(str(item) for item in value)
            else:
                output[key] = value
        return output

    def _cache_file(self, safe_url: str) -> Path | None:
        if self.cache_dir is None or self.cache_ttl_seconds <= 0:
            return None
        digest = hashlib.sha256(safe_url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def _read_cache(self, path: Path | None) -> Any | None:
        if path is None or not path.is_file():
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
            return

    @staticmethod
    def _header_int(headers: Any, name: str) -> int | None:
        try:
            raw = headers.get(name)
            return int(raw) if raw is not None else None
        except (TypeError, ValueError, AttributeError):
            return None

    def _update_rate_limit(self, headers: Any) -> None:
        self.rate_limit = RateLimit(
            limit=self._header_int(headers, "X-RateLimit-Limit"),
            remaining=self._header_int(headers, "X-RateLimit-Remaining"),
        )

    @staticmethod
    def _retry_after(headers: Any) -> float | None:
        try:
            raw = headers.get("Retry-After")
            return max(0.0, float(raw)) if raw is not None else None
        except (TypeError, ValueError, AttributeError):
            return None

    @staticmethod
    def _error_message(body: str, fallback: str) -> str:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return body.strip() or fallback
        if isinstance(payload, dict):
            for key in ("error", "msg", "message"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
                if isinstance(value, dict):
                    nested = value.get("message")
                    if nested:
                        return str(nested)
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
        public_params = self._normalise_params(params)
        request_params = dict(public_params)
        if authenticated:
            request_params["api_key"] = self.api_key

        endpoint = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        request_url = endpoint
        if request_params:
            request_url += "?" + urlencode(request_params)

        safe_url = endpoint
        if public_params:
            safe_url += "?" + urlencode(public_params)
        cache_file = self._cache_file(safe_url) if cache else None
        cached = self._read_cache(cache_file)
        if cached is not None:
            return cached

        request = Request(
            request_url,
            headers={"Accept": "application/json", "User-Agent": self.user_agent},
        )
        for attempt in range(self.max_retries + 1):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    if authenticated:
                        self._update_rate_limit(response.headers)
                    payload = _redact_api_keys(
                        json.loads(response.read().decode("utf-8"))
                    )
                    self._write_cache(cache_file, payload)
                    return payload
            except HTTPError as exc:
                if authenticated:
                    self._update_rate_limit(exc.headers)
                body = exc.read().decode("utf-8", errors="replace")
                retry_after = self._retry_after(exc.headers)
                if exc.code in RETRYABLE_STATUS and attempt < self.max_retries:
                    delay = retry_after
                    if delay is None:
                        delay = min(self.backoff_seconds * (2**attempt), 30.0)
                    time.sleep(min(delay, 60.0))
                    continue
                raise NASAAPIError(
                    self._error_message(body, f"NASA service returned HTTP {exc.code}"),
                    status_code=exc.code,
                    retry_after=retry_after,
                ) from exc
            except (URLError, TimeoutError) as exc:
                if attempt < self.max_retries:
                    time.sleep(min(self.backoff_seconds * (2**attempt), 30.0))
                    continue
                raise NASAAPIError(
                    "Could not reach the NASA service. Check the internet connection and try again."
                ) from exc
            except json.JSONDecodeError as exc:
                raise NASAAPIError("NASA service returned invalid JSON") from exc
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
        modes = sum(
            (
                day is not None,
                start_date is not None or end_date is not None,
                count is not None,
            )
        )
        if modes > 1:
            raise ValueError("Choose one APOD mode: date, range, or random count")
        if end_date is not None and start_date is None:
            raise ValueError("APOD end_date requires start_date")
        if start_date and end_date and end_date < start_date:
            raise ValueError("APOD end_date cannot precede start_date")
        if count is not None and not 1 <= count <= 100:
            raise ValueError("APOD count must be between 1 and 100")
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

    def neo_feed(
        self, start_date: date, end_date: date | None = None
    ) -> dict[str, Any]:
        end = end_date or start_date
        if end < start_date:
            raise ValueError("NEO end_date cannot precede start_date")
        if (end - start_date).days > 7:
            raise ValueError("NEO date windows cannot exceed seven days")
        result = self._get(
            NASA_BASE_URL,
            "neo/rest/v1/feed",
            {"start_date": start_date.isoformat(), "end_date": end.isoformat()},
            authenticated=True,
        )
        return _expect_dict(result, "NEO feed")

    def neo_lookup(self, asteroid_id: str | int) -> dict[str, Any]:
        value = str(asteroid_id).strip()
        if not value:
            raise ValueError("asteroid_id cannot be empty")
        result = self._get(
            NASA_BASE_URL,
            f"neo/rest/v1/neo/{value}",
            authenticated=True,
        )
        return _expect_dict(result, "NEO lookup")

    def neo_browse(self, *, page: int = 0, size: int = 20) -> dict[str, Any]:
        if page < 0:
            raise ValueError("page must be zero or greater")
        if not 1 <= size <= 100:
            raise ValueError("size must be between 1 and 100")
        result = self._get(
            NASA_BASE_URL,
            "neo/rest/v1/neo/browse",
            {"page": page, "size": size},
            authenticated=True,
        )
        return _expect_dict(result, "NEO browse")

    def donki(
        self,
        event_type: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        **filters: Any,
    ) -> list[dict[str, Any]]:
        endpoint_lookup = {name.lower(): name for name in DONKI_ENDPOINTS}
        endpoint = endpoint_lookup.get(event_type.strip().lower())
        if endpoint is None:
            allowed = ", ".join(sorted(DONKI_ENDPOINTS))
            raise ValueError(f"Unknown DONKI event type. Use one of: {allowed}")
        if start_date and end_date and end_date < start_date:
            raise ValueError("DONKI end_date cannot precede start_date")
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
            raise NASAAPIError("Unexpected DONKI response shape")
        return result

    def eonet_events(
        self,
        *,
        status: str = "open",
        limit: int = 20,
        days: int | None = None,
        categories: Sequence[str] | None = None,
        sources: Sequence[str] | None = None,
        geojson: bool = False,
    ) -> dict[str, Any]:
        if status not in {"open", "closed", "all"}:
            raise ValueError("EONET status must be open, closed, or all")
        if limit < 1:
            raise ValueError("EONET limit must be positive")
        if days is not None and days < 1:
            raise ValueError("EONET days must be positive")
        result = self._get(
            EONET_BASE_URL,
            "events/geojson" if geojson else "events",
            {
                "status": status,
                "limit": limit,
                "days": days,
                "category": categories,
                "source": sources,
            },
            authenticated=False,
            cache=False,
        )
        return _expect_dict(result, "EONET events")

    def eonet_categories(self) -> dict[str, Any]:
        return _expect_dict(
            self._get(EONET_BASE_URL, "categories", authenticated=False),
            "EONET categories",
        )


def _redact_api_keys(value: Any) -> Any:
    """Remove API credentials echoed inside nested response URLs."""
    if isinstance(value, dict):
        return {key: _redact_api_keys(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_api_keys(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_api_keys(item) for item in value)
    if not isinstance(value, str) or "api_key=" not in value.lower():
        return value

    try:
        parts = urlsplit(value)
    except ValueError:
        return value
    if parts.scheme not in {"http", "https"} or not parts.query:
        return value

    clean_query = urlencode(
        [
            (key, item)
            for key, item in parse_qsl(parts.query, keep_blank_values=True)
            if key.lower() != "api_key"
        ],
        doseq=True,
    )
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, clean_query, parts.fragment)
    )


def _expect_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise NASAAPIError(f"Unexpected {label} response shape")
    return value
