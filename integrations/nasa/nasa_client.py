"""Compatibility bridge for the standalone NASA Data Hub.

The maintained implementation now lives in apps/nasa_data_hub. This module keeps
older imports working without coupling the hub to the root the_well package.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HUB_ROOT = Path(__file__).resolve().parents[2] / "apps" / "nasa_data_hub"
if str(_HUB_ROOT) not in sys.path:
    sys.path.insert(0, str(_HUB_ROOT))

from nasa_data_hub import NASAAPIError, NASAClient, RateLimit, Settings  # noqa: E402
from nasa_data_hub.cli import build_parser, main  # noqa: E402

RateLimitState = RateLimit

__all__ = [
    "NASAAPIError",
    "NASAClient",
    "RateLimit",
    "RateLimitState",
    "Settings",
    "build_parser",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
