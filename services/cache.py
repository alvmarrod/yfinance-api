"""
Module that implements a thread-safe cache manager with LRU eviction and disk offload.
"""

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path

import threading as tg
from typing import Optional
from datetime import datetime, timedelta

from services.full_ticker_data import FullTickerData, BLOCKS

from utils.progressbar import create_progress_bar

app_logger = logging.getLogger("yfinance-api")


@dataclass
class ExpiredTickerInfo:
    """Info about an expired cache entry for warm-up."""

    ticker: str
    cached_sections: set[str]


@dataclass
class TickerMetadata:
    """Per-block retrieval times for a ticker."""

    ticker: str
    block_retrieval_times: dict[str, datetime]


##############################################################################
#                                CONSTANTS                                   #
##############################################################################

CACHE_DIR: str = "cache"

CACHE_SIZE_LOG_MSG: str = "📊 Cache usage: %s"

##############################################################################
#                                AUX FUNCTIONS                               #
##############################################################################


def get_cached_sections(data: FullTickerData) -> set[str]:
    """Get set of blocks present in the FullTickerData."""
    return data.get_block_sections()


##############################################################################
#                                    CACHE                                   #
##############################################################################


class tsCache:
    """Thread-safe cache with LRU eviction and disk offload (singleton)."""

    _instance: Optional["tsCache"] = None
    _lock: tg.Lock = tg.Lock()

    lock: tg.Lock
    cache: dict[str, FullTickerData]
    adaptive_cache: bool
    cache_size: int
    ttl_seconds: dict[str, int]

    def __new__(cls) -> "tsCache":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        app_logger.info("🆕 Initializating the cache")
        self.lock = tg.Lock()
        self.cache = {}
        self.adaptive_cache = False
        self.cache_size = 225
        self.ttl_seconds = {}
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "tsCache":
        """Get the singleton instance of the cache."""
        return cls()

    def configure(
        self,
        adaptive_cache: bool = False,
        cache_size: int = 225,
        ttl_seconds: Optional[dict[str, int]] = None,
    ) -> None:
        """Configure cache settings."""
        with self.lock:
            self.adaptive_cache = adaptive_cache
            self.cache_size = cache_size
            self.ttl_seconds = ttl_seconds or {}

    def _cache_usage_report(self) -> None:
        """Reports the current status of the cache usage."""
        report_msg: str = CACHE_SIZE_LOG_MSG % create_progress_bar(
            current=len(self.cache), total=self.cache_size, width=10
        )
        app_logger.debug(report_msg)

    def _is_block_expired(self, block: str, retrieval_time: datetime) -> bool:
        """Check if a block has expired based on its TTL."""
        ttl = self.ttl_seconds.get(block, 3600)
        return datetime.now() - retrieval_time > timedelta(seconds=ttl)

    def _find_lru_ticker(self) -> Optional[str]:
        """Find ticker with oldest MAX(block access times)."""
        oldest_time: Optional[datetime] = None
        oldest_ticker: Optional[str] = None

        for ticker, data in self.cache.items():
            ticker_time = data.get_max_block_time()
            if ticker_time is None:
                continue

            if oldest_time is None or ticker_time < oldest_time:
                oldest_time = ticker_time
                oldest_ticker = ticker

        return oldest_ticker

    def _evict_ticker_to_disk(self, ticker: str) -> None:
        """Save all non-empty blocks to disk and remove from memory."""
        data = self.cache[ticker]

        ticker_dir = Path(CACHE_DIR) / ticker
        ticker_dir.mkdir(parents=True, exist_ok=True)

        block_retrieval_times = {}

        for block in BLOCKS:
            block_data = getattr(data, block, None)
            if block_data is not None:
                block_file = ticker_dir / f"{block}.pkl"
                try:
                    with open(block_file, "wb") as f:
                        pickle.dump(block_data, f)

                    time_field = f"{block}_retrieval_time"
                    block_time = getattr(data, time_field, None)
                    if block_time:
                        block_retrieval_times[block] = block_time
                except Exception as e:
                    app_logger.error(f"Error saving {ticker}/{block}: {e}")

        if block_retrieval_times:
            metadata = TickerMetadata(
                ticker=ticker, block_retrieval_times=block_retrieval_times
            )
            metadata_file = ticker_dir / "metadata.pkl"
            try:
                with open(metadata_file, "wb") as f:
                    pickle.dump(metadata, f)
            except Exception as e:
                app_logger.error(f"Error saving {ticker} metadata: {e}")

        del self.cache[ticker]
        app_logger.info(f"💾 Evicted {ticker} to disk")

    def _load_ticker_from_disk(self, ticker: str) -> Optional[FullTickerData]:
        """Load ticker from disk, deleting expired blocks."""
        ticker_dir = Path(CACHE_DIR) / ticker
        metadata_file = ticker_dir / "metadata.pkl"

        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file, "rb") as f:
                metadata: TickerMetadata = pickle.load(f)

            data = FullTickerData(ticker=ticker)
            expired_blocks = []

            for block, retrieval_time in metadata.block_retrieval_times.items():
                block_file = ticker_dir / f"{block}.pkl"

                if not block_file.exists():
                    expired_blocks.append(block)
                    continue

                if self._is_block_expired(block, retrieval_time):
                    block_file.unlink()
                    expired_blocks.append(block)
                    app_logger.debug(f"🗑️ Deleted expired {ticker}/{block}.pkl")
                    continue

                with open(block_file, "rb") as f:
                    block_data = pickle.load(f)

                setattr(data, block, block_data)
                time_field = f"{block}_retrieval_time"
                setattr(data, time_field, retrieval_time)

            if expired_blocks:
                for block in expired_blocks:
                    del metadata.block_retrieval_times[block]

                if metadata.block_retrieval_times:
                    with open(metadata_file, "wb") as f:
                        pickle.dump(metadata, f)
                else:
                    metadata_file.unlink()
                    app_logger.debug(
                        f"🗑️ Deleted {ticker}/metadata.pkl (all blocks expired)"
                    )

            if not metadata.block_retrieval_times:
                return None

            return data

        except Exception as e:
            app_logger.error(f"Error loading {ticker} from disk: {e}")
            return None

    def get_ticker(self, ticker: str) -> Optional[FullTickerData]:
        """Thread-safely return a ticker if it exists in the cache."""
        with self.lock:
            if ticker in self.cache:
                data = self.cache[ticker]

                for block in BLOCKS:
                    time_field = f"{block}_retrieval_time"
                    block_time = getattr(data, time_field, None)
                    if block_time and self._is_block_expired(block, block_time):
                        setattr(data, block, None)
                        setattr(data, time_field, None)

                if data.get_block_sections():
                    return data
                else:
                    del self.cache[ticker]

        data = self._load_ticker_from_disk(ticker)
        if data:
            self.add_ticker(ticker, data)
            return data

        return None

    def add_ticker(self, ticker: str, data: FullTickerData):
        """Thread-safely adds a ticker to the cache with LRU eviction."""
        with self.lock:
            now = datetime.now()

            if ticker in self.cache:
                app_logger.debug(f"♻️ Updating existing cache entry for ticker {ticker}")
                existing = self.cache[ticker]

                for block in BLOCKS:
                    new_value = getattr(data, block, None)
                    if new_value is not None:
                        setattr(existing, block, new_value)
                        time_field = f"{block}_retrieval_time"
                        setattr(existing, time_field, now)
            else:
                if not self.adaptive_cache and len(self.cache) >= self.cache_size:
                    lru_ticker = self._find_lru_ticker()
                    if lru_ticker:
                        self._evict_ticker_to_disk(lru_ticker)

                for block in BLOCKS:
                    if getattr(data, block, None) is not None:
                        time_field = f"{block}_retrieval_time"
                        if getattr(data, time_field, None) is None:
                            setattr(data, time_field, now)

                self.cache[ticker] = data

            self._cache_usage_report()

    def _prune_expired(self) -> int:
        """Remove all expired entries from memory."""
        removed = 0
        expired_tickers = []

        for ticker, data in self.cache.items():
            if not data.get_block_sections():
                expired_tickers.append(ticker)
                continue

            all_expired = True
            for block in BLOCKS:
                time_field = f"{block}_retrieval_time"
                block_time = getattr(data, time_field, None)
                if block_time and not self._is_block_expired(block, block_time):
                    all_expired = False
                    break

            if all_expired:
                expired_tickers.append(ticker)

        for ticker in expired_tickers:
            app_logger.info(f"🗑️ Pruning expired cache entry: {ticker}")
            del self.cache[ticker]
            removed += 1

        if removed > 0:
            app_logger.info(f"🧹 Pruned {removed} expired cache entries")

        return removed

    def persist_to_disk(self) -> None:
        """Persist entire memory cache to disk on shutdown."""
        with self.lock:
            if not self.cache:
                app_logger.debug("Cache is empty, skipping persistence")
                return

            count = 0
            for ticker in list(self.cache.keys()):
                try:
                    self._evict_ticker_to_disk(ticker)
                    count += 1
                except Exception as e:
                    app_logger.error(f"Error persisting {ticker}: {e}")

            app_logger.info(f"💾 Cache persisted to disk: {count} tickers")

    def load_from_disk(self) -> list[ExpiredTickerInfo]:
        """Load cache from disk directory structure."""
        cache_dir = Path(CACHE_DIR)

        if not cache_dir.exists():
            return []

        expired_tickers = []
        loaded_count = 0

        for ticker_dir in cache_dir.iterdir():
            if not ticker_dir.is_dir():
                continue

            ticker = ticker_dir.name
            data = self._load_ticker_from_disk(ticker)

            if data:
                self.add_ticker(ticker, data)
                loaded_count += 1

                expired_blocks = set()
                for block in BLOCKS:
                    time_field = f"{block}_retrieval_time"
                    block_time = getattr(data, time_field, None)
                    if block_time and self._is_block_expired(block, block_time):
                        expired_blocks.add(block)

                if expired_blocks:
                    expired_tickers.append(
                        ExpiredTickerInfo(ticker=ticker, cached_sections=expired_blocks)
                    )

        app_logger.info(f"📂 Loaded {loaded_count} tickers from disk")
        return expired_tickers
