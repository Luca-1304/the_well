"""Compatibility tests for the NASA integration's former import path."""

from integrations.nasa import NASAClient, RateLimit, RateLimitState, Settings


def test_legacy_imports_point_to_standalone_hub():
    client = NASAClient()
    assert client.api_key == "DEMO_KEY"
    assert RateLimitState is RateLimit
    assert Settings().using_demo_key
