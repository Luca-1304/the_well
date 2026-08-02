"""Configuration loading for NASA Data Hub."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

DEMO_KEY = "DEMO_KEY"


def load_dotenv(path: str | os.PathLike[str] = ".env", *, override: bool = False) -> bool:
    """Load a small, dependency-free .env file.

    Supports KEY=value, optional quotes, blank lines, and comments.
    Existing environment values are preserved unless override=True.
    """
    env_path = Path(path)
    if not env_path.is_file():
        return False

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if override or key not in os.environ:
            os.environ[key] = value
    return True


@dataclass(frozen=True)
class Settings:
    api_key: str = DEMO_KEY
    host: str = "127.0.0.1"
    port: int = 8765
    timeout_seconds: float = 20.0
    max_retries: int = 2
    cache_dir: Path = Path(".cache")
    cache_ttl_seconds: float = 300.0

    @property
    def key_mode(self) -> str:
        return "demo" if self.api_key == DEMO_KEY else "personal"

    @property
    def using_demo_key(self) -> bool:
        return self.api_key == DEMO_KEY

    @classmethod
    def from_env(
        cls,
        *,
        env_file: str | os.PathLike[str] | None = ".env",
        environ: Mapping[str, str] | None = None,
    ) -> "Settings":
        if env_file:
            load_dotenv(env_file)
        values = os.environ if environ is None else environ
        api_key = values.get("NASA_API_KEY", "").strip() or DEMO_KEY
        host = values.get("NASA_HUB_HOST", "127.0.0.1").strip() or "127.0.0.1"
        port = _int(values.get("NASA_HUB_PORT"), 8765, minimum=1, maximum=65535)
        timeout = _float(values.get("NASA_TIMEOUT_SECONDS"), 20.0, minimum=0.1)
        retries = _int(values.get("NASA_MAX_RETRIES"), 2, minimum=0, maximum=10)
        ttl = _float(values.get("NASA_CACHE_TTL_SECONDS"), 300.0, minimum=0.0)
        cache_dir = Path(values.get("NASA_CACHE_DIR", ".cache")).expanduser()
        return cls(
            api_key=api_key,
            host=host,
            port=port,
            timeout_seconds=timeout,
            max_retries=retries,
            cache_dir=cache_dir,
            cache_ttl_seconds=ttl,
        )


def _int(raw: str | None, default: int, *, minimum: int, maximum: int) -> int:
    if raw is None or not raw.strip():
        return default
    value = int(raw)
    if not minimum <= value <= maximum:
        raise ValueError(f"value must be between {minimum} and {maximum}")
    return value


def _float(raw: str | None, default: float, *, minimum: float) -> float:
    if raw is None or not raw.strip():
        return default
    value = float(raw)
    if value < minimum:
        raise ValueError(f"value must be at least {minimum}")
    return value
