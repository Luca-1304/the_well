"""Live upstream probe for NASA Open APIs and EONET."""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import date
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from nasa_data_hub.client import NASAClient  # noqa: E402
from nasa_data_hub.config import Settings  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, default=1)
    parser.add_argument("--require-personal", action="store_true")
    parser.add_argument("--skip-if-demo", action="store_true")
    parser.add_argument("--eonet-only", action="store_true")
    parser.add_argument("--label", default="live")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.passes < 1:
        raise ValueError("passes must be positive")

    settings = Settings.from_env(env_file=None)
    if args.require_personal and settings.using_demo_key:
        message = (
            "Registered-key live soak skipped: configure the GitHub Actions "
            "NASA_API_KEY secret with a newly rotated key."
        )
        if args.skip_if_demo:
            print(message)
            return 0
        raise RuntimeError(message)

    for pass_number in range(1, args.passes + 1):
        with tempfile.TemporaryDirectory(
            prefix=f"nasa-{args.label}-{pass_number}-"
        ) as cache_dir:
            client = NASAClient(
                settings.api_key,
                timeout_seconds=settings.timeout_seconds,
                max_retries=settings.max_retries,
                cache_dir=Path(cache_dir),
                cache_ttl_seconds=0,
            )
            eonet = client.eonet_events(status="open", limit=2)
            if not isinstance(eonet.get("events"), list):
                raise AssertionError("EONET response does not contain an events list")

            if not args.eonet_only:
                apod = client.apod(day=date(2025, 1, 1))
                if not isinstance(apod, dict) or apod.get("date") != "2025-01-01":
                    raise AssertionError(f"Unexpected APOD response: {apod}")

                neo = client.neo_feed(date(2025, 1, 1), date(2025, 1, 1))
                if "near_earth_objects" not in neo:
                    raise AssertionError("NEO response is missing near_earth_objects")

                donki = client.donki(
                    "FLR",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 1, 2),
                )
                if not isinstance(donki, list):
                    raise AssertionError("DONKI response is not a list")

            print(
                f"{args.label} pass {pass_number}/{args.passes}: passed "
                f"(key_mode={settings.key_mode}, "
                f"remaining={client.rate_limit.remaining})",
                flush=True,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
