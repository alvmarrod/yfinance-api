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
class RateLimiterConfig:
    """Rate limiter configuration."""

    request_period_seconds: int
    max_requests_per_period: int
    cooldown_seconds: int
    cooldown_fake_events: int


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
    pending_ticker_window_seconds: float
    seconds_sleep_when_rate_hit: float
    rate_limiter: RateLimiterConfig


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
    if not isinstance(raw.get("pending_ticker_window_seconds"), (int, float)):
        raise TypeError("pending_ticker_window_seconds must be a number")
    if not isinstance(raw.get("seconds_sleep_when_rate_hit"), (int, float)):
        raise TypeError("seconds_sleep_when_rate_hit must be a number")
    if not isinstance(raw.get("rate_limiter"), dict):
        raise TypeError("rate_limiter must be a dict")

    rate_limiter_raw = raw["rate_limiter"]
    if not isinstance(rate_limiter_raw.get("request_period_seconds"), int):
        raise TypeError("rate_limiter.request_period_seconds must be an int")
    if not isinstance(rate_limiter_raw.get("max_requests_per_period"), int):
        raise TypeError("rate_limiter.max_requests_per_period must be an int")
    if not isinstance(rate_limiter_raw.get("cooldown_seconds"), int):
        raise TypeError("rate_limiter.cooldown_seconds must be an int")
    if not isinstance(rate_limiter_raw.get("cooldown_fake_events"), int):
        raise TypeError("rate_limiter.cooldown_fake_events must be an int")

    return CacheConfig(
        tickers=raw["tickers"],
        blocks=raw["blocks"],
        concurrency=raw["concurrency"],
        adaptive_cache=raw["adaptive_cache"],
        cache_size=raw["cache_size"],
        prefetch_schedule=PrefetchScheduleConfig(raw["prefetch_schedule"]),
        ttl_seconds=TtlConfig(raw["ttl_seconds"]),
        pending_ticker_window_seconds=float(raw["pending_ticker_window_seconds"]),
        seconds_sleep_when_rate_hit=float(raw["seconds_sleep_when_rate_hit"]),
        rate_limiter=RateLimiterConfig(
            request_period_seconds=rate_limiter_raw["request_period_seconds"],
            max_requests_per_period=rate_limiter_raw["max_requests_per_period"],
            cooldown_seconds=rate_limiter_raw["cooldown_seconds"],
            cooldown_fake_events=rate_limiter_raw["cooldown_fake_events"],
        ),
    )
