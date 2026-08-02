"""Smoke test the standalone NASA Data Hub from the parent repository suite."""

from __future__ import annotations

import sys
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parents[2] / "apps" / "nasa_data_hub"
if str(HUB_ROOT) not in sys.path:
    sys.path.insert(0, str(HUB_ROOT))

from nasa_data_hub import NASAClient, RateLimit, Settings  # noqa: E402


def test_standalone_hub_is_available_without_root_packaging():
    client = NASAClient()
    assert client.api_key == "DEMO_KEY"
    assert RateLimit().remaining is None
    assert Settings().using_demo_key
