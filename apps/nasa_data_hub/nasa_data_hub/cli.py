"""Command-line interface for NASA Data Hub."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Sequence

from .client import NASAAPIError, NASAClient
from .config import Settings
from .server import run_server


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use YYYY-MM-DD") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nasa-data-hub",
        description="Local NASA dashboard, API proxy, and command-line client.",
    )
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument("--compact", action="store_true", help="Compact JSON output")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="Start the browser dashboard")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    serve.add_argument("--open", action="store_true", dest="open_browser")

    commands.add_parser("health", help="Show local configuration status")

    doctor = commands.add_parser(
        "doctor", help="Test configuration and a live APOD request"
    )
    doctor.add_argument(
        "--no-live", action="store_true", help="Skip the live NASA request"
    )

    apod = commands.add_parser("apod", help="Get Astronomy Picture of the Day")
    apod.add_argument("--date", type=_date)
    apod.add_argument("--start", type=_date)
    apod.add_argument("--end", type=_date)
    apod.add_argument("--count", type=int)

    neo = commands.add_parser("neo", help="Get near-Earth-object approaches")
    neo.add_argument("--start", type=_date, required=True)
    neo.add_argument("--end", type=_date)

    lookup = commands.add_parser("neo-lookup", help="Look up one asteroid")
    lookup.add_argument("asteroid_id")

    browse = commands.add_parser("neo-browse", help="Browse known asteroids")
    browse.add_argument("--page", type=int, default=0)
    browse.add_argument("--size", type=int, default=20)

    donki = commands.add_parser("donki", help="Get space-weather events")
    donki.add_argument("event_type")
    donki.add_argument("--start", type=_date)
    donki.add_argument("--end", type=_date)

    eonet = commands.add_parser("eonet", help="Get current natural events")
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
        settings = Settings.from_env(env_file=args.env_file)
        if args.command == "serve":
            if args.host or args.port:
                settings = Settings(
                    api_key=settings.api_key,
                    host=args.host or settings.host,
                    port=args.port or settings.port,
                    timeout_seconds=settings.timeout_seconds,
                    max_retries=settings.max_retries,
                    cache_dir=settings.cache_dir,
                    cache_ttl_seconds=settings.cache_ttl_seconds,
                )
            run_server(settings, open_browser=args.open_browser)
            return 0

        if args.command == "health":
            return _print(
                {
                    "ok": True,
                    "key_mode": settings.key_mode,
                    "using_demo_key": settings.using_demo_key,
                    "env_file": str(Path(args.env_file)),
                    "dashboard": f"http://{settings.host}:{settings.port}",
                    "next_step": (
                        "Copy .env.example to .env and add a rotated NASA_API_KEY."
                        if settings.using_demo_key
                        else "Configuration is ready."
                    ),
                },
                compact=args.compact,
            )

        client = NASAClient(
            settings.api_key,
            timeout_seconds=settings.timeout_seconds,
            max_retries=settings.max_retries,
            cache_dir=settings.cache_dir,
            cache_ttl_seconds=settings.cache_ttl_seconds,
        )

        if args.command == "doctor":
            payload: dict[str, Any] = {
                "ok": True,
                "key_mode": settings.key_mode,
                "configuration": "valid",
            }
            if not args.no_live:
                apod = client.apod()
                payload["live_request"] = "passed"
                payload["apod_title"] = (
                    apod.get("title") if isinstance(apod, dict) else None
                )
                payload["rate_limit"] = {
                    "limit": client.rate_limit.limit,
                    "remaining": client.rate_limit.remaining,
                }
            return _print(payload, compact=args.compact)

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
                args.event_type,
                start_date=args.start,
                end_date=args.end,
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
        return _print(result, compact=args.compact)
    except (NASAAPIError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _print(payload: Any, *, compact: bool) -> int:
    print(json.dumps(payload, indent=None if compact else 2, ensure_ascii=False))
    return 0
