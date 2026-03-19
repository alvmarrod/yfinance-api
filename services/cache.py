"""
Module that implements a thread-safe cache manager
"""

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path

import threading as tg
from typing import Optional
from datetime import datetime, timedelta

from dataclasses import replace

from services.cache_entry import CacheEntry
from services.full_ticker_data import FullTickerData

from utils.progressbar import create_progress_bar

app_logger = logging.getLogger("yfinance-api")


@dataclass
class ExpiredTickerInfo:
    """Info about an expired cache entry for warm-up."""

    ticker: str
    cached_sections: set[str]


##############################################################################
#                                CONSTANTS                                   #
##############################################################################

CACHE_DIR: str = "cache"
CACHE_PICKLE_FILE: str = "cache/yfinance_api_cache.pkl"

MAX_MEM_CACHE_SIZE: int = 225
MAX_PERSISTED_CACHE_SIZE: int = 225

CACHE_SIZE_LOG_MSG: str = "📊 Cache usage: %s"

##############################################################################
#                                AUX FUNCTIONS                               #
##############################################################################


def _cache_has_expired(entry: CacheEntry) -> bool:
    """Check if a cache entry has expired (older than 1 hour)."""
    return entry.retrieval_time - datetime.now() > timedelta(hours=1)


def get_cached_sections(data: FullTickerData) -> set[str]:
    """Get set of sections present in the FullTickerData."""
    return {
        field
        for field in FullTickerData.__dataclass_fields__.keys()
        if getattr(data, field) is not None and field != "ticker"
    }


def _get_oldest_ticker(entries: list[CacheEntry]) -> str:
    """Returns the ticker of the oldest entry"""
    sorted_entries: list[CacheEntry] = sorted(entries, key=lambda x: x.retrieval_time)

    app_logger.debug(
        "Returning the oldest ticker %s vs newest %s"
        % (sorted_entries[0].retrieval_time, sorted_entries[-1].retrieval_time)
    )

    return sorted_entries[0].ticker


##############################################################################
#                                    CACHE                                   #
##############################################################################


class tsCache:
    """Thread-safe cache with pickle persistence."""

    lock: tg.Lock
    cache: dict[str, CacheEntry]

    def __init__(self):
        app_logger.info("🆕 Initializating the cache")
        self.lock = tg.Lock()
        self.cache = {}

    def _cache_usage_report(self) -> None:
        """Reports the current status of the cache usage."""
        report_msg: str = CACHE_SIZE_LOG_MSG % create_progress_bar(
            current=len(self.cache), total=MAX_MEM_CACHE_SIZE, width=10
        )

        app_logger.debug(report_msg)

    def get_ticker(self, ticker: str) -> Optional[FullTickerData]:
        """Thread-safely return a ticker if it exists in the cache."""
        result: Optional[FullTickerData] = None

        with self.lock:
            cache_result = self.cache.get(ticker, None)

            if cache_result:
                if _cache_has_expired(cache_result):
                    app_logger.debug(f"⏳ Cache entry for {ticker} has expired.")
                    del self.cache[ticker]
                else:
                    result = cache_result.data

        return result

    def add_ticker(self, ticker: str, data: FullTickerData):
        """Thread-safely adds a ticker to the cache.

        If the ticker already exists, it is overwritten and complemented
        """
        with self.lock:
            if ticker in self.cache:
                app_logger.debug(f"♻️ Updating existing cache entry for ticker {ticker}")

                self.cache[ticker].retrieval_time = datetime.now()

                for item in FullTickerData.__dataclass_fields__.keys():
                    new_value = getattr(data, item)
                    if new_value is not None:
                        self.cache[ticker].data = replace(
                            self.cache[ticker].data, **{item: new_value}
                        )

            else:
                app_logger.debug(f"➕ Adding new cache entry for ticker {ticker}")

                if len(self.cache) > MAX_MEM_CACHE_SIZE:
                    oldest_ticker: str = _get_oldest_ticker(list(self.cache.values()))
                    del self.cache[oldest_ticker]

                self.cache[ticker] = CacheEntry(
                    ticker=ticker, retrieval_time=datetime.now(), data=data
                )

            self._cache_usage_report()

    def _prune_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        removed = 0
        expired_tickers = [
            ticker for ticker, entry in self.cache.items() if _cache_has_expired(entry)
        ]

        for ticker in expired_tickers:
            app_logger.info(f"🗑️ Pruning expired cache entry: {ticker}")
            del self.cache[ticker]
            removed += 1

        if removed > 0:
            app_logger.info(f"🧹 Pruned {removed} expired cache entries")

        return removed

    def persist_to_disk(self) -> None:
        """Persist cache to pickle file for later restoration."""
        with self.lock:
            if not self.cache:
                app_logger.debug("Cache is empty, skipping persistence")
                return

            Path(CACHE_DIR).mkdir(exist_ok=True)

            cache_to_persist = dict(self.cache)

            if len(cache_to_persist) > MAX_PERSISTED_CACHE_SIZE:
                sorted_entries = sorted(
                    cache_to_persist.items(),
                    key=lambda x: x[1].retrieval_time,
                    reverse=True,
                )
                cache_to_persist = dict(sorted_entries[:MAX_PERSISTED_CACHE_SIZE])
                app_logger.info(
                    f"📦 Cached {MAX_PERSISTED_CACHE_SIZE} entries for persistence"
                )

            try:
                with open(CACHE_PICKLE_FILE, "wb") as f:
                    pickle.dump(cache_to_persist, f)
                app_logger.info(f"💾 Cache persisted to {CACHE_PICKLE_FILE}")
            except Exception as e:
                app_logger.error(f"❌ Failed to persist cache: {e}")

    def load_from_disk(self) -> list[ExpiredTickerInfo]:
        """Load cache from pickle file. Returns list of expired tickers for warmup."""
        pickle_path = Path(CACHE_PICKLE_FILE)

        if not pickle_path.exists():
            app_logger.debug("No cache file found, starting with empty cache")
            return []

        try:
            with open(pickle_path, "rb") as f:
                loaded_cache: dict[str, CacheEntry] = pickle.load(f)

            self.cache = loaded_cache
            app_logger.info(f"📂 Loaded {len(self.cache)} cache entries from disk")

            expired_tickers: list[ExpiredTickerInfo] = []
            for ticker, entry in self.cache.items():
                if _cache_has_expired(entry):
                    expired_tickers.append(
                        ExpiredTickerInfo(
                            ticker=ticker,
                            cached_sections=get_cached_sections(entry.data),
                        )
                    )

            self._prune_expired()
            remaining = len(self.cache)
            app_logger.info(f"✅ Cache ready with {remaining} valid entries")

            return expired_tickers

        except Exception as e:
            app_logger.error(f"❌ Failed to load cache from disk: {e}")
            return []
