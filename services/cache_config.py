"""Cache configuration loader and dataclasses."""

import json
from dataclasses import dataclass
from pathlib import Path

app_logger = __import__("logging").getLogger("yfinance-api")


@dataclass
class PrefetchScheduleConfig:
    """Cron-based schedule for prefetching data blocks."""

    schedule: dict[str, str]


@dataclass
class TtlConfig:
    """Time-to-live settings for each data block."""

    ttl: dict[str, int]


@dataclass
class CacheConfig:
    """Main configuration for the cache system."""

    tickers: list[str]
    blocks: list[str]
    concurrency: int
    adaptive_cache: bool
    cache_size: int
    prefetch_schedule: PrefetchScheduleConfig
    ttl_seconds: TtlConfig


def load_config(path: str) -> CacheConfig:
    """Load configuration from JSON file."""
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(config_path, "r") as f:
        raw = json.load(f)

    if not isinstance(raw.get("tickers"), list):
        raise TypeError("tickers must be a list")
    if not isinstance(raw.get("blocks"), list):
        raise TypeError("blocks must be a list")
    if not isinstance(raw.get("concurrency"), int):
        raise TypeError("concurrency must be an int")
    if not isinstance(raw.get("adaptive_cache"), bool):
        raise TypeError("adaptive_cache must be a bool")
    if not isinstance(raw.get("cache_size"), int):
        raise TypeError("cache_size must be an int")
    if not isinstance(raw.get("prefetch_schedule"), dict):
        raise TypeError("prefetch_schedule must be a dict")
    if not isinstance(raw.get("ttl_seconds"), dict):
        raise TypeError("ttl_seconds must be a dict")

    return CacheConfig(
        tickers=raw["tickers"],
        blocks=raw["blocks"],
        concurrency=raw["concurrency"],
        adaptive_cache=raw["adaptive_cache"],
        cache_size=raw["cache_size"],
        prefetch_schedule=PrefetchScheduleConfig(raw["prefetch_schedule"]),
        ttl_seconds=TtlConfig(raw["ttl_seconds"]),
    )
